import asyncio
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tortoise import Tortoise

TEST_DB_PATH = (Path(__file__).parent / ".test.sqlite3").resolve()

os.environ["APP_ENV"] = "test"
os.environ["SECRET"] = "test-secret-key-with-at-least-32-characters"
os.environ["DATABASE_URL"] = f"sqlite://{TEST_DB_PATH}"
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""

from app.api.v1.users import pwd_context  # noqa: E402
from app.db.tortoise import TORTOISE_ORM  # noqa: E402
from app.models.user import Role, User  # noqa: E402
from main import app  # noqa: E402


async def _prepare_database() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        # Production schema changes go through Aerich. Tests use an isolated,
        # disposable SQLite database so the API suite stays self-contained.
        await Tortoise.generate_schemas()

        admin_role = await Role.create(name="admin", description="Administrator")
        admin = await User.create(
            username="admin",
            email="admin@example.com",
            hashed_password=pwd_context.hash("admin-password"),
        )
        await admin.roles.add(admin_role)
    finally:
        await Tortoise.close_connections()


@pytest.fixture(autouse=True)
def fresh_database():
    TEST_DB_PATH.unlink(missing_ok=True)
    asyncio.run(_prepare_database())
    yield
    TEST_DB_PATH.unlink(missing_ok=True)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
