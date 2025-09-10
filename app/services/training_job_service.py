# backend/app/services/training_job_service.py
import json
import os
import uuid
from typing import Any, Dict, Optional
from ..core.config import settings
from .database_service import DatabaseService
from .kubernetes_service import KubernetesService

class TrainingJobService:
    TRAINER_IMAGE = settings.trainer_image
    NAMESPACE = settings.k8s_namespace
    PVC_NAME = settings.k8s_pvc_name

    def __init__(self):
        self.k8s = KubernetesService(namespace=self.NAMESPACE)

    def _abs_from_file_uri(self, uri: str) -> str:
        return uri[len("file://") :] if uri.startswith("file://") else uri

    def create_job(
        self,
        *,
        owner_sub: str,
        configuration: Dict[str, Any],
        cpu_request: str = "100m",
        mem_request: str = "256Mi",
        cpu_limit: str = "1",
        mem_limit: str = "1Gi",
        dataset_url: Optional[str] = None,
        output_model_url: Optional[str] = None,
        output_metrics_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        job_name = f"train-{job_id[:8]}"

        x_col = configuration["x_column"]
        y_col = configuration["y_column"]
        fit_intercept = str(configuration.get("hyperparams_json", {}).get("fit_intercept", True)).lower()

        env: Dict[str, str] = {
            "X_COLUMN": x_col,
            "Y_COLUMN": y_col,
            "FIT_INTERCEPT": "true" if fit_intercept == "true" else "false",
            "USER_SUB": owner_sub,
            "JOB_ID": job_id,
        }

        sub_paths = None
        if configuration["dataset_uri"].startswith("file://") and self.PVC_NAME:
            abs_dataset = self._abs_from_file_uri(configuration["dataset_uri"])
            root = os.path.abspath(settings.storage_root)
            if not abs_dataset.startswith(root):
                raise ValueError("Dataset path is outside storage_root.")
            rel_dataset = os.path.relpath(abs_dataset, root)
            artifacts_rel = os.path.join("artifacts", owner_sub, job_id)
            sub_paths = {"dataset": rel_dataset, "artifacts": artifacts_rel}
        else:
            if not dataset_url or not output_model_url or not output_metrics_url:
                raise ValueError("Missing presigned URLs for dataset/artifacts in URL mode.")
            env["DATASET_URL"] = dataset_url
            env["OUTPUT_MODEL_URL"] = output_model_url
            env["OUTPUT_METRICS_URL"] = output_metrics_url

        # persist "queued"
        db = DatabaseService()
        try:
            db.insert_job(
                job_id=job_id,
                owner_sub=owner_sub,
                configuration_id=configuration["id"],
                k8s_job_name=job_name,
                resources={
                    "cpu_request": cpu_request,
                    "mem_request": mem_request,
                    "cpu_limit": cpu_limit,
                    "mem_limit": mem_limit,
                },
                status="queued",
            )
        finally:
            db.close()

        # k8s job
        k8s_name = self.k8s.create_training_job(
            job_name=job_name,
            image=self.TRAINER_IMAGE,
            env=env,
            cpu_request=cpu_request,
            mem_request=mem_request,
            cpu_limit=cpu_limit,
            mem_limit=mem_limit,
            pv_claim_name=self.PVC_NAME,
            sub_paths=sub_paths,
        )

        # persist "running"
        db = DatabaseService()
        try:
            db.set_job_status(job_id=job_id, owner_sub=owner_sub, status="running")
        finally:
            db.close()

        return {"id": job_id, "k8s_job_name": k8s_name, "status": "running"}

    def refresh_and_get(self, *, owner_sub: str, job_id: str) -> Dict[str, Any]:
        db = DatabaseService()
        try:
            job = db.get_job(job_id=job_id, owner_sub=owner_sub)
            if not job:
                raise KeyError("Job not found.")

            if job["status"] in ("succeeded", "failed"):
                return job

            status = self.k8s.get_job_status(job["k8s_job_name"])
            if status in ("succeeded", "failed"):
                model_uri = None
                metrics_json = None
                if self.PVC_NAME:
                    artifacts_dir = os.path.join(settings.storage_root, "artifacts", owner_sub, job_id)
                    m_path = os.path.join(artifacts_dir, "metrics.json")
                    p_path = os.path.join(artifacts_dir, "model.pkl")
                    if os.path.exists(m_path):
                        with open(m_path, "r") as f:
                            metrics_json = f.read()
                    if os.path.exists(p_path):
                        model_uri = f"file://{os.path.abspath(p_path)}"
                db.set_job_status(
                    job_id=job_id,
                    owner_sub=owner_sub,
                    status=status,
                    model_uri=model_uri,
                    metrics_json=metrics_json,
                )
                job = db.get_job(job_id=job_id, owner_sub=owner_sub) or job
            return job
        finally:
            db.close()
