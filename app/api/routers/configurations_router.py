# backend/app/api/routers/configurations_router.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from ...api.deps import get_db
from ...api.router_auth import get_current_sub
from ...schemas.database import ConfigurationCreateIn, ConfigurationOut
from ...services.database_service import DatabaseService

router = APIRouter(prefix="/configurations", tags=["configurations"])

@router.post("", response_model=ConfigurationOut, status_code=201)
def create_configuration(
    payload: ConfigurationCreateIn,
    owner_sub: str = Depends(get_current_sub),
    db: DatabaseService = Depends(get_db),
):
    try:
        created = db.create_configuration(
            owner_sub=owner_sub,
            name=payload.name.strip(),
            dataset_uri=payload.dataset_uri.strip(),
            x_column=payload.x_column.strip(),
            y_column=payload.y_column.strip(),
            model_type=(payload.model_type or "linear_regression").strip(),
            hyperparams=payload.hyperparams or None,
        )
        return ConfigurationOut(**created)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create configuration.") from e

@router.get("", response_model=List[ConfigurationOut])
def list_configurations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    owner_sub: str = Depends(get_current_sub),
    db: DatabaseService = Depends(get_db),
):
    try:
        rows = db.list_configurations(owner_sub=owner_sub, limit=limit, offset=offset)
        return [ConfigurationOut(**r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list configurations.") from e
