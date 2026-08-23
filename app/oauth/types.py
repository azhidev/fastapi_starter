from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class OAuthProviderError(Exception):
    """Raised when an OAuth provider cannot complete authentication safely."""


@dataclass(frozen=True)
class OAuthIdentity:
    subject: str
    email: str


@dataclass(frozen=True)
class OAuthCredentials:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class OAuthAuthentication:
    identity: OAuthIdentity
    credentials: OAuthCredentials


class OAuthProvider(Protocol):
    name: str

    async def authorization_url(self, redirect_uri: str) -> str: ...

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthAuthentication: ...
