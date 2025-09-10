from typing import Dict, Optional
from kubernetes import client, config


class KubernetesService:
    def __init__(self, namespace: str = "default"):
        # Try in-cluster, fall back to kubeconfig (local dev)
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()
        self.ns = namespace
        self.batch = client.BatchV1Api()

    def create_training_job(
        self,
        *,
        job_name: str,
        image: str,
        env: Dict[str, str],
        cpu_request: str = "100m",
        mem_request: str = "256Mi",
        cpu_limit: str = "1",
        mem_limit: str = "1Gi",
        pv_claim_name: Optional[str] = None,
        sub_paths: Optional[Dict[str, str]] = None,  # {"dataset": "uploads/...csv", "artifacts": "artifacts/.../job_id"}
    ) -> str:
        # Env
        env_vars = [client.V1EnvVar(name=k, value=v) for k, v in env.items()]

        volume_mounts = []
        volumes = []
        # Optional PVC mount (dev)
        if pv_claim_name:
            volumes.append(
                client.V1Volume(
                    name="podml-data",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=pv_claim_name
                    ),
                )
            )
            if sub_paths:
                if "dataset" in sub_paths:
                    volume_mounts.append(
                        client.V1VolumeMount(
                            name="podml-data",
                            mount_path="/data/dataset",
                            sub_path=sub_paths["dataset"],
                            read_only=True,
                        )
                    )
                    env_vars.append(client.V1EnvVar(name="DATASET_PATH", value="/data/dataset"))
                if "artifacts" in sub_paths:
                    volume_mounts.append(
                        client.V1VolumeMount(
                            name="podml-data",
                            mount_path="/data/artifacts",
                            sub_path=sub_paths["artifacts"],
                            read_only=False,
                        )
                    )
                    env_vars.append(client.V1EnvVar(name="OUTPUT_DIR", value="/data/artifacts"))

        container = client.V1Container(
            name="trainer",
            image=image,
            image_pull_policy="IfNotPresent",
            env=env_vars,
            volume_mounts=volume_mounts or None,
            resources=client.V1ResourceRequirements(
                requests={"cpu": cpu_request, "memory": mem_request},
                limits={"cpu": cpu_limit, "memory": mem_limit},
            ),
        )

        pod_spec = client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            security_context=client.V1PodSecurityContext(run_as_non_root=True),
            volumes=volumes or None,
        )

        tpl = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": "podml", "job": job_name}),
            spec=pod_spec,
        )

        job_spec = client.V1JobSpec(
            template=tpl,
            backoff_limit=0,
            ttl_seconds_after_finished=600,
        )

        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=job_name, labels={"app": "podml"}),
            spec=job_spec,
        )

        created = self.batch.create_namespaced_job(namespace=self.ns, body=job)
        return created.metadata.name

    def get_job_status(self, job_name: str) -> str:
        j = self.batch.read_namespaced_job_status(name=job_name, namespace=self.ns)
        conds = j.status.conditions or []
        if any(c.type == "Failed" and c.status == "True" for c in conds):
            return "failed"
        if j.status.succeeded and j.status.succeeded > 0:
            return "succeeded"
        if j.status.active and j.status.active > 0:
            return "running"
        return "queued"
