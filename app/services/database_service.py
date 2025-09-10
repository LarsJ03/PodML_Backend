# backend/app/services/database_service.py
import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from ..core.config import settings

INIT_SQL = """
PRAGMA foreign_keys = ON;

-- configurations
CREATE TABLE IF NOT EXISTS configurations (
    id TEXT PRIMARY KEY,
    owner_sub TEXT NOT NULL,
    name TEXT NOT NULL,
    dataset_uri TEXT NOT NULL,
    x_column TEXT NOT NULL,
    y_column TEXT NOT NULL,
    model_type TEXT NOT NULL DEFAULT 'linear_regression',
    hyperparams_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_configurations_owner
    ON configurations (owner_sub, created_at DESC);

-- training_jobs
CREATE TABLE IF NOT EXISTS training_jobs (
  id TEXT PRIMARY KEY,
  owner_sub TEXT NOT NULL,
  configuration_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',  -- queued|running|succeeded|failed
  k8s_job_name TEXT NOT NULL,
  model_uri TEXT,
  metrics_json TEXT,
  resources_json TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(configuration_id) REFERENCES configurations(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_training_jobs_owner
    ON training_jobs (owner_sub, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_training_jobs_cfg
    ON training_jobs (configuration_id, created_at DESC);
"""

def _parse_hp(row: sqlite3.Row | Dict[str, Any]) -> Dict[str, Any]:
    d = dict(row)
    if d.get("hyperparams_json"):
        try:
            d["hyperparams_json"] = json.loads(d["hyperparams_json"])
        except Exception:
            d["hyperparams_json"] = None
    else:
        d["hyperparams_json"] = None
    return d

class DatabaseService:
    """
    Repository-style DB service for all persistence.
    Routers/services must call methods here; no raw SQL outside.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.database_path
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def _ensure_schema(self):
        with self.conn:
            self.conn.executescript(INIT_SQL)

    # ============ CONFIGURATIONS ============
    def create_configuration(
        self,
        *,
        owner_sub: str,
        name: str,
        dataset_uri: str,
        x_column: str,
        y_column: str,
        model_type: str = "linear_regression",
        hyperparams: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cfg_id = str(uuid.uuid4())
        hp_json = json.dumps(hyperparams) if hyperparams else None
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO configurations (id, owner_sub, name, dataset_uri, x_column, y_column, model_type, hyperparams_json)
                VALUES (?,  ?,         ?,    ?,          ?,       ?,        ?,           ?)
                """,
                (cfg_id, owner_sub, name, dataset_uri, x_column, y_column, model_type, hp_json),
            )
            row = self.conn.execute(
                "SELECT * FROM configurations WHERE id = ? AND owner_sub = ?",
                (cfg_id, owner_sub),
            ).fetchone()
        return _parse_hp(row)

    def list_configurations(self, *, owner_sub: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM configurations
            WHERE owner_sub = ?
            ORDER BY datetime(created_at) DESC
            LIMIT ? OFFSET ?
            """,
            (owner_sub, limit, offset),
        ).fetchall()
        return [_parse_hp(r) for r in rows]

    def get_configuration(self, *, cfg_id: str, owner_sub: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM configurations WHERE id = ? AND owner_sub = ?",
            (cfg_id, owner_sub),
        ).fetchone()
        return _parse_hp(row) if row else None

    # ============ JOBS ============
    def insert_job(
        self,
        *,
        job_id: str,
        owner_sub: str,
        configuration_id: str,
        k8s_job_name: str,
        resources: Dict[str, Any],
        status: str = "queued",
    ) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO training_jobs (id, owner_sub, configuration_id, status, k8s_job_name, resources_json)
                VALUES (?,  ?,         ?,                ?,      ?,            ?)
                """,
                (job_id, owner_sub, configuration_id, status, k8s_job_name, json.dumps(resources)),
            )

    def list_jobs(self, *, owner_sub: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM training_jobs
            WHERE owner_sub = ?
            ORDER BY datetime(created_at) DESC
            LIMIT ? OFFSET ?
            """,
            (owner_sub, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_job(self, *, job_id: str, owner_sub: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM training_jobs WHERE id = ? AND owner_sub = ?",
            (job_id, owner_sub),
        ).fetchone()
        return dict(row) if row else None

    def set_job_status(
        self, *, job_id: str, owner_sub: str, status: str, model_uri: Optional[str] = None, metrics_json: Optional[str] = None
    ) -> None:
        with self.conn:
            self.conn.execute(
                """
                UPDATE training_jobs
                SET status = ?, 
                    model_uri = COALESCE(?, model_uri),
                    metrics_json = COALESCE(?, metrics_json),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND owner_sub = ?
                """,
                (status, model_uri, metrics_json, job_id, owner_sub),
            )
