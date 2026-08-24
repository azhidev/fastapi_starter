from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

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
    port: int = Field(default=8000, ge=1, le=65535, alias="PORT")

    database_url: str = Field(
        default="postgres://postgres:postgres@localhost:5432/app",
        alias="DATABASE_URL",
    )
    secret: str = Field(..., min_length=32, alias="SECRET")
    jwt_lifetime_seconds: int = Field(
        60 * 60 * 24,
        gt=0,
        le=60 * 60 * 24 * 30,
        alias="JWT_LIFETIME_SECONDS",
    )

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
    def validate_configuration(self) -> "Settings":
        if self.cors_allow_credentials and "*" in self.cors_origin_list:
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' when CORS_ALLOW_CREDENTIALS is enabled"
            )

        has_google_id = bool(self.google_client_id)
        has_google_secret = bool(self.google_client_secret)
        if self.oauth_provider == "google" and not (has_google_id and has_google_secret):
            raise ValueError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required when "
                "OAUTH_PROVIDER=google"
            )
        if self.oauth_provider is None and (has_google_id or has_google_secret):
            raise ValueError("OAUTH_PROVIDER must be selected when OAuth credentials are set")

        redirect = urlsplit(self.oauth_redirect_uri)
        if redirect.scheme not in {"http", "https"} or not redirect.netloc:
            raise ValueError("OAUTH_REDIRECT_URI must be an absolute HTTP(S) URL")

        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be disabled in production")
            insecure_secrets = {
                "change-me-change-me-change-me-change-me",
                "test-secret-key-with-at-least-32-characters",
            }
            if self.secret in insecure_secrets or len(set(self.secret)) < 8:
                raise ValueError("SECRET is not suitable for production")
            if self.oauth_provider is not None and redirect.scheme != "https":
                raise ValueError("OAUTH_REDIRECT_URI must use HTTPS in production")

        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
