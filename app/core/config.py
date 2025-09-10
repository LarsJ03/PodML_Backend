# backend/app/core/config.py
from typing import List, Optional
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend/app
DEFAULT_DB = str(BASE_DIR / "app.db")
DEFAULT_STORAGE_ROOT = str(BASE_DIR / "storage")   # local storage for dev

class Settings(BaseSettings):
    # -------- App --------
    app_name: str = "PodML API"
    api_prefix: str = "/api"

    # -------- Database --------
    database_path: str = DEFAULT_DB
    database_url: Optional[str] = None

    # -------- Storage (local dev / PV) --------
    storage_root: str = DEFAULT_STORAGE_ROOT  # created if missing

    # -------- Auth / dev --------
    allow_debug_sub: bool = True
    debug_sub_header: str = "X-Debug-Sub"

    # -------- AWS / Cognito (JWT verification) --------
    aws_region: Optional[str] = None
    aws_cognito_user_pool_id: Optional[str] = None
    aws_cognito_client_id: Optional[str] = None

    # -------- CORS --------
    cors_origins: List[str] = ["http://localhost:3000"]

    # -------- Kubernetes / Trainer (PV mode) --------
    k8s_pvc_name: Optional[str] = None        # e.g. "podml-pvc"
    k8s_namespace: str = "default"
    trainer_image: str = "podml-trainer:latest"

    # Pydantic v2 settings config (replaces inner Config)
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_csv(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @property
    def cognito_issuer(self) -> str:
        if not self.aws_region or not self.aws_cognito_user_pool_id:
            raise ValueError("Missing aws_region or aws_cognito_user_pool_id")
        return f"https://cognito-idp.{self.aws_region}.amazonaws.com/{self.aws_cognito_user_pool_id}"

    @property
    def cognito_jwks_url(self) -> str:
        return f"{self.cognito_issuer}/.well-known/jwks.json"


settings = Settings()
