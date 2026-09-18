"""Application settings.

Every value is read from the environment (or a local .env file). Nothing
secret is hard-coded, so the same image can run in dev, staging and prod
with different credentials injected by the platform.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- application ---
    APP_NAME: str = "MedReturn"
    ENVIRONMENT: str = "development"
    API_PREFIX: str = "/api"

    # --- database ---
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "medreturn"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "medreturn"

    # --- security ---
    JWT_SECRET: str = Field(default="insecure-dev-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # --- AI / decision engine ---
    DEMO_MODE: bool = True
    CONFIDENCE_THRESHOLD: float = 0.80
    MODEL_PATH: str = "../ml/models/model.pth"
    MODEL_VERSION: str = "v1.2"

    # --- rewards ---
    CREDITS_PER_VERIFIED_RETURN: int = 50

    # --- uploads ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 5

    # --- email ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@medreturn.in"
    SMTP_TLS: bool = True

    # --- external service abstractions ---
    MAPS_PROVIDER: str = "demo"
    MAPS_API_KEY: str = ""
    HARDWARE_ENDPOINT: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if v is None:
            return []

        if isinstance(v, str):
            value = v.strip()
            if not value:
                return []

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass

            return [o.strip() for o in value.split(",") if o.strip()]

        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]

        return v

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def email_configured(self) -> bool:
        return bool(self.SMTP_HOST)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
