import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from tortoise import Tortoise

from app.api.v1.users import pwd_context
from app.core import security
from app.core.security import DUMMY_PASSWORD_HASH, verify_token
from app.db.tortoise import TORTOISE_ORM
from app.models.user import Role, User
from main import app


def _register(client: TestClient, username: str, email: str, password: str = "strong-password"):
    return client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )


def _login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = _login(client, "admin", "admin-password")
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_inactive_users() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        inactive_user = await User.create(
            username="inactive-user",
            email="inactive-user@example.com",
            hashed_password=pwd_context.hash("inactive-password"),
            is_active=False,
        )
        inactive_admin = await User.create(
            username="inactive-admin",
            email="inactive-admin@example.com",
            hashed_password=pwd_context.hash("inactive-admin-password"),
            is_active=False,
        )
        admin_role = await Role.get(name="admin")
        await inactive_admin.roles.add(admin_role)
        assert inactive_user.id
    finally:
        await Tortoise.close_connections()


@pytest.fixture
def client_with_inactive_users(fresh_database):
    asyncio.run(_seed_inactive_users())
    with TestClient(app) as test_client:
        yield test_client


def test_registration_normalizes_email_and_rejects_case_insensitive_duplicate(client):
    created = _register(client, "case-email-one", "Mixed.Email@Example.COM")

    assert created.status_code == 201, created.text
    assert created.json()["email"] == "mixed.email@example.com"
    assert created.json()["is_active"] is True
    assert "password" not in created.json()
    assert "hashed_password" not in created.json()

    duplicate = _register(client, "case-email-two", "MIXED.EMAIL@example.com")

    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Username or email already registered"}


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "   ", "email": "valid@example.com", "password": "strong-password"},
        {"username": "valid", "email": "valid@example.com", "password": "    "},
        {"username": "valid", "email": "not-an-email", "password": "strong-password"},
        {
            "username": "valid",
            "email": "valid@example.com",
            "password": "strong-password",
            "is_active": False,
        },
    ],
)
def test_registration_rejects_malformed_or_extra_fields(client, payload):
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422


def test_invalid_and_inactive_logins_use_generic_errors_and_dummy_verification(
    client_with_inactive_users,
    monkeypatch,
):
    verified_hashes: list[str] = []
    real_verify = pwd_context.verify

    def tracking_verify(secret, password_hash, *args, **kwargs):
        verified_hashes.append(password_hash)
        return real_verify(secret, password_hash, *args, **kwargs)

    monkeypatch.setattr(pwd_context, "verify", tracking_verify)

    wrong_password = _login(client_with_inactive_users, "admin", "wrong-password")
    missing_user = _login(client_with_inactive_users, "missing-user", "wrong-password")
    inactive_user = _login(
        client_with_inactive_users,
        "inactive-user",
        "inactive-password",
    )

    for response in (wrong_password, missing_user, inactive_user):
        assert response.status_code == 401
        assert response.json() == {"detail": "Incorrect username or password"}
        assert response.headers["www-authenticate"] == "Bearer"

    assert verified_hashes[0] != DUMMY_PASSWORD_HASH
    assert verified_hashes[1:] == [DUMMY_PASSWORD_HASH, DUMMY_PASSWORD_HASH]


def test_login_uses_configured_jwt_lifetime(client, monkeypatch):
    lifetime_seconds = 137
    monkeypatch.setattr(security.settings, "jwt_lifetime_seconds", lifetime_seconds)
    issued_at = int(datetime.now(timezone.utc).timestamp())

    response = _login(client, "admin", "admin-password")

    assert response.status_code == 200, response.text
    payload = verify_token(response.json()["access_token"])
    assert payload is not None
    assert issued_at + lifetime_seconds <= payload["exp"] <= issued_at + lifetime_seconds + 2


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "ops/admin"},
        {"name": "ops admin"},
        {"name": "manager", "unexpected": True},
    ],
)
def test_role_creation_rejects_invalid_names_and_extras(client, payload):
    response = client.post("/api/v1/roles/", headers=_admin_headers(client), json=payload)

    assert response.status_code == 422


def test_duplicate_role_creation_returns_generic_conflict(client):
    headers = _admin_headers(client)
    created = client.post(
        "/api/v1/roles/",
        headers=headers,
        json={"name": "manager", "description": "Manages users"},
    )
    duplicate = client.post(
        "/api/v1/roles/",
        headers=headers,
        json={"name": "manager", "description": "Different description"},
    )

    assert created.status_code == 201, created.text
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Role already exists"}


def test_inactive_admin_does_not_allow_removing_last_active_admin(
    client_with_inactive_users,
):
    headers = _admin_headers(client_with_inactive_users)
    current_admin = client_with_inactive_users.get("/api/v1/users/me", headers=headers)
    assert current_admin.status_code == 200, current_admin.text

    removal = client_with_inactive_users.delete(
        f"/api/v1/users/{current_admin.json()['id']}/roles/admin",
        headers=headers,
    )

    assert removal.status_code == 409
    assert removal.json() == {"detail": "Cannot remove the last active admin role"}
    assert client_with_inactive_users.get("/api/v1/roles/", headers=headers).status_code == 200

    users = client_with_inactive_users.get("/api/v1/admin/", headers=headers)
    inactive_admin_id = next(
        user["id"] for user in users.json() if user["username"] == "inactive-admin"
    )
    inactive_removal = client_with_inactive_users.delete(
        f"/api/v1/users/{inactive_admin_id}/roles/admin",
        headers=headers,
    )
    assert inactive_removal.status_code == 204
