from fastapi.testclient import TestClient


def register_user(client: TestClient, username: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "strong-password",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(client: TestClient, username: str, password: str = "strong-password") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_public_root_and_private_user_endpoint(client: TestClient):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["status"] == "ok"

    private = client.get("/api/v1/users/me")
    assert private.status_code == 401
    assert private.headers["www-authenticate"] == "Bearer"


def test_registration_login_and_self_access(client: TestClient):
    user = register_user(client, "alice")
    headers = auth_headers(client, "alice")

    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["email"] == "alice@example.com"


def test_role_management_requires_admin(client: TestClient):
    user = register_user(client, "alice")
    user_headers = auth_headers(client, "alice")

    denied = client.post(
        f"/api/v1/users/{user['id']}/roles/admin",
        headers=user_headers,
    )
    assert denied.status_code == 403

    admin_headers = auth_headers(client, "admin", "admin-password")
    allowed = client.post(
        f"/api/v1/users/{user['id']}/roles/admin",
        headers=admin_headers,
    )
    assert allowed.status_code == 204

    roles = client.get(f"/api/v1/users/{user['id']}/roles", headers=user_headers)
    assert roles.status_code == 200
    assert {role["name"] for role in roles.json()} == {"admin"}


def test_projects_and_tasks_are_scoped_to_the_owner(client: TestClient):
    register_user(client, "alice")
    register_user(client, "bob")
    alice_headers = auth_headers(client, "alice")
    bob_headers = auth_headers(client, "bob")

    project_response = client.post(
        "/api/v1/projects/",
        headers=alice_headers,
        json={"name": "Alice project", "description": "private"},
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()

    hidden_project = client.get(
        f"/api/v1/projects/{project['id']}",
        headers=bob_headers,
    )
    assert hidden_project.status_code == 404

    hidden_create = client.post(
        f"/api/v1/projects/{project['id']}/tasks/",
        headers=bob_headers,
        json={"title": "Should not exist"},
    )
    assert hidden_create.status_code == 404

    task_response = client.post(
        f"/api/v1/projects/{project['id']}/tasks/",
        headers=alice_headers,
        json={"title": "Ship the API"},
    )
    assert task_response.status_code == 201, task_response.text
    task = task_response.json()
    assert task["done"] is False

    hidden_toggle = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/toggle",
        headers=bob_headers,
    )
    assert hidden_toggle.status_code == 404

    owner_toggle = client.post(
        f"/api/v1/projects/{project['id']}/tasks/{task['id']}/toggle",
        headers=alice_headers,
    )
    assert owner_toggle.status_code == 200
    assert owner_toggle.json()["done"] is True
