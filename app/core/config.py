from functools import lru_cache
from pathlib import Path

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgres://postgres:postgres@db:5432/app",
        alias="DATABASE_URL",
    )
    secret: str = Field(..., min_length=32, alias="SECRET")
    jwt_lifetime_seconds: int = Field(60 * 60 * 24, alias="JWT_LIFETIME_SECONDS")
    port: int = Field(alias="PORT", default=8000)
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:  # singleton per process
    return Settings()
