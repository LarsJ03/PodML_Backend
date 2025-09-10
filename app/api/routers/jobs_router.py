# backend/app/api/routers/jobs_router.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from ...api.router_auth import get_current_sub
from ...api.deps import get_db
from ...services.database_service import DatabaseService
from ...services.training_job_service import TrainingJobService
from ...schemas.jobs import JobCreateIn, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobOut, status_code=201)
def create_job(
    payload: JobCreateIn,
    owner_sub: str = Depends(get_current_sub),
    db: DatabaseService = Depends(get_db),
):
    cfg = db.get_configuration(cfg_id=payload.configuration_id, owner_sub=owner_sub)
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuration not found")

    svc = TrainingJobService()
    try:
        out = svc.create_job(
            owner_sub=owner_sub,
            configuration=cfg,  # already parsed hyperparams_json by DB layer
            cpu_request=payload.cpu_request or "100m",
            mem_request=payload.mem_request or "256Mi",
            cpu_limit=payload.cpu_limit or "1",
            mem_limit=payload.mem_limit or "1Gi",
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create job") from e

    # load + return
    job = db.get_job(job_id=out["id"], owner_sub=owner_sub)
    return JobOut(**job)

@router.get("", response_model=List[JobOut])
def list_jobs(
    owner_sub: str = Depends(get_current_sub),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DatabaseService = Depends(get_db),
):
    rows = db.list_jobs(owner_sub=owner_sub, limit=limit, offset=offset)
    return [JobOut(**r) for r in rows]

@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, owner_sub: str = Depends(get_current_sub), db: DatabaseService = Depends(get_db)):
    # let service refresh + persist terminal state, but read/write via DB class
    svc = TrainingJobService()
    try:
        # service uses db internally only for K8s artifacts; we still read back via db
        refreshed = svc.refresh_and_get(owner_sub=owner_sub, job_id=job_id)
        return JobOut(**refreshed)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load job")
