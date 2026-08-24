from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

from app.core import security


def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin-password"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_documentation_paths_are_intentionally_public(client: TestClient):
    for path in ("/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"):
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)


def test_invalid_bearer_is_rejected_consistently_on_public_and_private_routes(
    client: TestClient,
):
    headers = {"Authorization": "Bearer invalid-token"}

    for path in ("/", "/api/v1/users/me"):
        response = client.get(path, headers=headers)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid authentication credentials"}
        assert response.headers["www-authenticate"] == "Bearer"


def test_only_typed_access_tokens_are_accepted(client: TestClient):
    legacy_token = jwt.encode(
        {
            "sub": "0" * 20,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        security.settings.secret,
        algorithm=security.ALGORITHM,
    )
    unknown_user_token = security.create_access_token({"sub": "0" * 20})

    for token in (legacy_token, unknown_user_token):
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid authentication credentials"}
        assert response.headers["www-authenticate"] == "Bearer"


def test_auth_resource_paths_reject_malformed_identifiers(client: TestClient):
    headers = admin_headers(client)
    malformed_id = "x" * 21
    valid_missing_id = "0" * 20
    overlong_role_name = "r" * 51

    cases = [
        ("GET", f"/api/v1/users/{malformed_id}"),
        ("GET", f"/api/v1/users/{malformed_id}/roles"),
        ("POST", f"/api/v1/users/{malformed_id}/roles/admin"),
        ("DELETE", f"/api/v1/users/{malformed_id}/roles/admin"),
        ("POST", f"/api/v1/users/{valid_missing_id}/roles/{overlong_role_name}"),
        ("DELETE", f"/api/v1/roles/{malformed_id}"),
    ]

    for method, path in cases:
        response = client.request(method, path, headers=headers)
        assert response.status_code == 422, (method, path, response.text)
        assert response.headers["content-type"].startswith("application/json")

    missing_user = client.get(f"/api/v1/users/{valid_missing_id}", headers=headers)
    assert missing_user.status_code == 404
    assert missing_user.json() == {"detail": "User not found"}
