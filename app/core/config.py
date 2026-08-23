from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = Field(default="FastAPI Starter", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    app_env: Literal["development", "test", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    debug: bool = Field(default=False, alias="DEBUG")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    database_url: str = Field(
        default="postgres://postgres:postgres@localhost:5432/app",
        alias="DATABASE_URL",
    )
    secret: str = Field(..., min_length=32, alias="SECRET")
    jwt_lifetime_seconds: int = Field(60 * 60 * 24, alias="JWT_LIFETIME_SECONDS")

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")

    oauth_provider: Literal["google"] | None = Field(default=None, alias="OAUTH_PROVIDER")
    oauth_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/oauth/callback",
        alias="OAUTH_REDIRECT_URI",
    )
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_cors(self) -> "Settings":
        if self.cors_allow_credentials and "*" in self.cors_origin_list:
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' when CORS_ALLOW_CREDENTIALS is enabled"
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
