from functools import lru_cache

from fastapi import HTTPException, status

from app.core.config import Settings, get_settings
from app.oauth.google import GoogleOAuthProvider
from app.oauth.types import OAuthProvider


def build_oauth_provider(settings: Settings) -> OAuthProvider | None:
    if settings.oauth_provider is None:
        return None
    if settings.oauth_provider == "google":
        if not settings.google_client_id or not settings.google_client_secret:
            return None
        return GoogleOAuthProvider(settings.google_client_id, settings.google_client_secret)
    return None


@lru_cache()
def get_configured_oauth_provider() -> OAuthProvider | None:
    return build_oauth_provider(get_settings())


def require_oauth_provider() -> OAuthProvider:
    provider = get_configured_oauth_provider()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth provider is not configured",
        )
    return provider
