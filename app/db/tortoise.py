"""Database bootstrap + Aerich config.

* `TORTOISE_ORM` is the dict Aerich expects when you run
    $ aerich init -t app.db.tortoise.TORTOISE_ORM

* `init_db()` still registers the connection for FastAPI runtime.
"""

from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise
from app.core.config import get_settings

settings = get_settings()
# print(str(settings.database_url), "-" * 100)
# ---------------------------------------------------------------------------
# Aerich‑compatible configuration dict
# ---------------------------------------------------------------------------
TORTOISE_ORM = {
    "connections": {"default": str(settings.database_url)},
    "apps": {
        "models": {
            "models": [
                "app.models.oauth",
                "app.models.project",
                "app.models.country",
                "app.models.task",
                "app.models.user",
                "aerich.models",  # built‑in Aerich migration table
            ],
            "default_connection": "default",
        }
    },
}

# ---------------------------------------------------------------------------
# Register with FastAPI at runtime
# ---------------------------------------------------------------------------


# def init_db(app: FastAPI) -> None:
#     register_tortoise(
#         app,
#         config=TORTOISE_ORM,
#         generate_schemas=False,  # migrations handle DDL
#         add_exception_handlers=True,
#     )
