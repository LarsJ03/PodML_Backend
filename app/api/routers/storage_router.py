# backend/app/api/routers/storage_router.py
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from ...services.storage_service import StorageService
from ...api.router_auth import get_current_sub

router = APIRouter(prefix="/storage", tags=["storage"])

@router.post("/upload", status_code=201)
async def upload_csv(
    file: UploadFile = File(...),
    owner_sub: str = Depends(get_current_sub),
):
    """
    Accept multipart/form-data with a CSV file. Save locally and return a URI.
    Response: { "uri": "file:///abs/path.csv", "path": "/abs/path.csv", "filename": "xyz.csv" }
    """
    svc = StorageService()
    try:
        abs_path, uri = svc.save_csv(owner_sub=owner_sub, upload=file)
        return {"uri": uri, "path": abs_path, "filename": file.filename or "upload.csv"}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload file.") from e
