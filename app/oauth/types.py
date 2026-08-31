from dataclasses import dataclass
from typing import Protocol


class OAuthProviderError(Exception):
    """Raised when an OAuth provider cannot complete authentication safely."""


@dataclass(frozen=True)
class OAuthIdentity:
    subject: str
    email: str



class OAuthProvider(Protocol):
    name: str

    async def authorization_url(self, redirect_uri: str, state: str) -> str: ...

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthIdentity: ...
