from datetime import datetime, timedelta, timezone
from typing import Any

from httpx_oauth.clients.google import GoogleOAuth2

from app.oauth.types import (
    OAuthAuthentication,
    OAuthCredentials,
    OAuthIdentity,
    OAuthProviderError,
)


class GoogleOAuthProvider:
    name = "google"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        client: GoogleOAuth2 | None = None,
    ) -> None:
        self._client = client or GoogleOAuth2(client_id, client_secret)

    async def authorization_url(self, redirect_uri: str) -> str:
        try:
            return await self._client.get_authorization_url(
                redirect_uri,
                scope=("openid", "email", "profile"),
                prompt="consent",
            )
        except Exception as exc:
            raise OAuthProviderError("Could not create OAuth authorization URL") from exc

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthAuthentication:
        try:
            token_data = await self._client.get_access_token(code, redirect_uri)
            access_token = token_data.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise OAuthProviderError("OAuth provider returned no access token")
            identity_data = await self._client.get_id_email(access_token)
        except OAuthProviderError:
            raise
        except Exception as exc:
            raise OAuthProviderError("OAuth provider exchange failed") from exc

        subject, email = identity_data
        if not isinstance(subject, str) or not subject:
            raise OAuthProviderError("OAuth provider returned no subject")
        if not isinstance(email, str) or not email:
            raise OAuthProviderError("OAuth provider returned no email")

        refresh_token = token_data.get("refresh_token")
        return OAuthAuthentication(
            identity=OAuthIdentity(subject=subject, email=email.strip().lower()),
            credentials=OAuthCredentials(
                access_token=access_token,
                refresh_token=refresh_token if isinstance(refresh_token, str) else None,
                expires_at=_token_expiration(token_data),
            ),
        )


def _token_expiration(token_data: dict[str, Any]) -> datetime | None:
    expires_at = token_data.get("expires_at")
    if isinstance(expires_at, datetime):
        return expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    if isinstance(expires_at, (int, float)):
        return datetime.fromtimestamp(expires_at, tz=timezone.utc)

    expires_in = token_data.get("expires_in")
    if isinstance(expires_in, (int, float)):
        return datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    return None
