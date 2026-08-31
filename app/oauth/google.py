from httpx_oauth.clients.google import GoogleOAuth2

from app.oauth.types import OAuthIdentity, OAuthProviderError


class GoogleOAuthProvider:
    name = "google"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        client: GoogleOAuth2 | None = None,
    ) -> None:
        self._client = client or GoogleOAuth2(client_id, client_secret)

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        try:
            return await self._client.get_authorization_url(
                redirect_uri,
                state=state,
                scope=("openid", "email", "profile"),
                prompt="consent",
            )
        except Exception as exc:
            raise OAuthProviderError("Could not create OAuth authorization URL") from exc

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthIdentity:
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

        return OAuthIdentity(subject=subject, email=email.strip().lower())
