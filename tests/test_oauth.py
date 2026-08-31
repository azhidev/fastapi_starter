import asyncio
from fastapi.testclient import TestClient
from tortoise import Tortoise

from app.core.security import pwd_context
from app.db.tortoise import TORTOISE_ORM
from app.models.oauth import OAuthAccount
from app.models.user import User
from app.oauth import factory as oauth_factory
from app.oauth.factory import require_oauth_provider
from app.oauth.google import GoogleOAuthProvider
from app.oauth.types import OAuthIdentity
from main import app


class FakeGoogleClient:
    def __init__(self) -> None:
        self.authorization_redirect_uri: str | None = None
        self.exchange: tuple[str, str] | None = None

    async def get_authorization_url(self, redirect_uri: str, **kwargs: object) -> str:
        self.authorization_redirect_uri = redirect_uri
        assert kwargs["state"] == "oauth-state"
        return "https://accounts.example/authorize"

    async def get_access_token(
        self,
        code: str,
        redirect_uri: str,
    ) -> dict[str, str | int]:
        self.exchange = (code, redirect_uri)
        return {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_at": 1_900_000_000,
        }

    async def get_id_email(self, access_token: str) -> tuple[str, str]:
        assert access_token == "google-access-token"
        return "google-subject", "User@Example.COM"


class FakeOAuthProvider:
    name = "reference"

    def __init__(self, subject: str = "subject-1", email: str = "oauth@example.com") -> None:
        self.subject = subject
        self.email = email
        self.authorization_calls: list[tuple[str, str]] = []
        self.exchange_calls: list[tuple[str, str]] = []

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        self.authorization_calls.append((redirect_uri, state))
        return "https://provider.example/authorize"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthIdentity:
        self.exchange_calls.append((code, redirect_uri))
        return OAuthIdentity(subject=self.subject, email=self.email)


def _override_provider(provider: FakeOAuthProvider) -> None:
    app.dependency_overrides[require_oauth_provider] = lambda: provider


def _clear_provider_override() -> None:
    app.dependency_overrides.pop(require_oauth_provider, None)


def _complete_oauth_callback(
    client: TestClient,
    provider: FakeOAuthProvider,
    code: str,
):
    login = client.get("/api/v1/auth/oauth/login", follow_redirects=False)
    assert login.status_code == 307, login.text
    state = provider.authorization_calls[-1][1]
    return client.get(
        "/api/v1/auth/oauth/callback",
        params={"code": code, "state": state},
    )


async def _oauth_snapshot(provider: str, subject: str) -> tuple[int, int]:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        account = await OAuthAccount.get(provider=provider, subject=subject)
        assert account.user_id
        return await User.all().count(), await OAuthAccount.all().count()
    finally:
        await Tortoise.close_connections()


async def _seed_inactive_oauth_user(email: str) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        await User.create(
            email=email,
            hashed_password=pwd_context.hash("unusable-password"),
            is_active=False,
        )
    finally:
        await Tortoise.close_connections()


def test_google_provider_normalizes_the_external_boundary():
    fake_client = FakeGoogleClient()
    provider = GoogleOAuthProvider("client-id", "client-secret", client=fake_client)

    async def scenario():
        authorization_url = await provider.authorization_url(
            "https://api.example/oauth/callback",
            "oauth-state",
        )
        authentication = await provider.exchange_code(
            "authorization-code",
            "https://api.example/oauth/callback",
        )
        return authorization_url, authentication

    authorization_url, authentication = asyncio.run(scenario())

    assert authorization_url == "https://accounts.example/authorize"
    assert fake_client.authorization_redirect_uri == "https://api.example/oauth/callback"
    assert fake_client.exchange == (
        "authorization-code",
        "https://api.example/oauth/callback",
    )
    assert authentication == OAuthIdentity(
        subject="google-subject",
        email="user@example.com",
    )


def test_generic_oauth_routes_report_unconfigured_provider(client, monkeypatch):
    monkeypatch.setattr(oauth_factory, "get_configured_oauth_provider", lambda: None)

    login = client.get("/api/v1/auth/oauth/login")
    callback = client.get(
        "/api/v1/auth/oauth/callback",
        params={"code": "code", "state": "state"},
    )

    for response in (login, callback):
        assert response.status_code == 503
        assert response.json() == {"detail": "OAuth provider is not configured"}


def test_generic_oauth_login_delegates_authorization_url(client):
    provider = FakeOAuthProvider()
    _override_provider(provider)
    try:
        response = client.get("/api/v1/auth/oauth/login", follow_redirects=False)
    finally:
        _clear_provider_override()

    assert response.status_code == 307
    assert response.headers["location"] == "https://provider.example/authorize"
    assert len(provider.authorization_calls) == 1
    redirect_uri, state = provider.authorization_calls[0]
    assert redirect_uri == "http://localhost:8000/api/v1/auth/oauth/callback"
    assert state
    assert "oauth_state=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]


def test_oauth_callback_rejects_invalid_state(client):
    provider = FakeOAuthProvider()
    _override_provider(provider)
    try:
        login = client.get("/api/v1/auth/oauth/login", follow_redirects=False)
        assert login.status_code == 307, login.text
        callback = client.get(
            "/api/v1/auth/oauth/callback",
            params={"code": "code", "state": "invalid-state"},
        )
    finally:
        _clear_provider_override()

    assert callback.status_code == 400
    assert callback.json() == {"detail": "Invalid OAuth state"}
    assert provider.exchange_calls == []


def test_oauth_callback_creates_and_reuses_account_with_jwt_login(fresh_database):
    provider = FakeOAuthProvider()
    _override_provider(provider)
    try:
        with TestClient(app) as client:
            first_callback = _complete_oauth_callback(client, provider, "first-code")
            assert first_callback.status_code == 200, first_callback.text
            first_headers = {
                "Authorization": f"Bearer {first_callback.json()['access_token']}"
            }
            first_user = client.get("/api/v1/users/me", headers=first_headers)
            assert first_user.status_code == 200, first_user.text
            assert first_user.json()["email"] == "oauth@example.com"

            second_callback = _complete_oauth_callback(client, provider, "second-code")
            assert second_callback.status_code == 200, second_callback.text
            second_headers = {
                "Authorization": f"Bearer {second_callback.json()['access_token']}"
            }
            second_user = client.get("/api/v1/users/me", headers=second_headers)
            assert second_user.status_code == 200, second_user.text
            assert second_user.json()["id"] == first_user.json()["id"]
    finally:
        _clear_provider_override()

    snapshot = asyncio.run(_oauth_snapshot(provider.name, provider.subject))
    assert snapshot == (2, 1)


def test_oauth_callback_links_an_existing_user_by_normalized_email(fresh_database):
    provider = FakeOAuthProvider(email="LINKED@EXAMPLE.COM")
    _override_provider(provider)
    try:
        with TestClient(app) as client:
            registered = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "linked-user",
                    "email": "linked@example.com",
                    "password": "strong-password",
                },
            )
            assert registered.status_code == 201, registered.text

            callback = _complete_oauth_callback(client, provider, "link-code")
            assert callback.status_code == 200, callback.text
            headers = {"Authorization": f"Bearer {callback.json()['access_token']}"}
            linked_user = client.get("/api/v1/users/me", headers=headers)
            assert linked_user.status_code == 200, linked_user.text
            assert linked_user.json()["id"] == registered.json()["id"]
    finally:
        _clear_provider_override()

    snapshot = asyncio.run(_oauth_snapshot(provider.name, provider.subject))
    assert snapshot == (2, 1)


def test_oauth_callback_rejects_inactive_linked_user(fresh_database):
    email = "inactive-oauth@example.com"
    asyncio.run(_seed_inactive_oauth_user(email))
    provider = FakeOAuthProvider(email=email)
    _override_provider(provider)
    try:
        with TestClient(app) as client:
            callback = _complete_oauth_callback(client, provider, "inactive-code")
    finally:
        _clear_provider_override()

    assert callback.status_code == 403
    assert callback.json() == {"detail": "Inactive user"}
