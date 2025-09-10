# backend/app/services/storage_service.py
import os
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from ..core.config import settings


class StorageService:
    """
    Simple local storage for development.
    Saves CSV uploads under: <storage_root>/uploads/<owner_sub>/<uuid>.csv
    Returns a canonical URI: file://<abs_path>
    """

    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.storage_root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "uploads").mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _is_csv(upload: UploadFile) -> bool:
        # basic checks: filename extension OR content-type
        fname = (upload.filename or "").lower()
        if fname.endswith(".csv"):
            return True
        ctype = (upload.content_type or "").lower()
        return ctype in {"text/csv", "application/vnd.ms-excel"}

    def save_csv(self, owner_sub: str, upload: UploadFile) -> Tuple[str, str]:
        """
        Saves an uploaded CSV file. Returns (abs_path, uri).
        URI format for dev: file://<absolute_path>
        """
        if not self._is_csv(upload):
            raise ValueError("Only CSV files are supported in development storage.")

        # enforce per-user folders
        folder = self.root / "uploads" / owner_sub
        folder.mkdir(parents=True, exist_ok=True)

        # generate unique filename with .csv
        file_id = str(uuid.uuid4())
        fname = f"{file_id}.csv"
        dest = folder / fname

        # write stream to disk
        with dest.open("wb") as f:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        # canonical dev URI (you can later switch to s3://...)
        uri = f"file://{dest.resolve()}"
        return str(dest.resolve()), uri
