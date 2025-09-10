from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


# ===== Configurations =====

class ConfigurationCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    dataset_uri: str = Field(..., min_length=1)
    x_column: str = Field(..., min_length=1)
    y_column: str = Field(..., min_length=1)
    model_type: str = "linear_regression"
    hyperparams: Optional[Dict[str, Any]] = None


class ConfigurationOut(BaseModel):
    id: str
    owner_sub: str
    name: str
    dataset_uri: str
    x_column: str
    y_column: str
    model_type: str
    hyperparams_json: Optional[Dict[str, Any]] = None
    created_at: str
