from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class JobCreateIn(BaseModel):
    configuration_id: str
    # Optional resource overrides
    cpu_request: Optional[str] = Field(default=None, examples=["100m"])
    mem_request: Optional[str] = Field(default=None, examples=["256Mi"])
    cpu_limit: Optional[str] = Field(default=None, examples=["1"])
    mem_limit: Optional[str] = Field(default=None, examples=["1Gi"])

class JobOut(BaseModel):
    id: str
    owner_sub: str
    configuration_id: str
    status: str
    k8s_job_name: str
    model_uri: Optional[str] = None
    metrics_json: Optional[str] = None
