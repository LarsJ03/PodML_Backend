# backend/app/api/deps.py
from contextlib import contextmanager
from typing import Generator
from ..services.database_service import DatabaseService

def get_db() -> Generator[DatabaseService, None, None]:
    db = DatabaseService()
    try:
        yield db
    finally:
        db.close()
