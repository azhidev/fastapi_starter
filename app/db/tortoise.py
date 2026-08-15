"""Tortoise ORM runtime configuration and Aerich integration."""

from tortoise import Tortoise

from app.core.config import get_settings

settings = get_settings()

# Aerich imports this object directly when generating and applying migrations.
TORTOISE_ORM = {
    "connections": {"default": str(settings.database_url)},
    "apps": {
        "models": {
            "models": [
                "app.models.oauth",
                "app.models.project",
                "app.models.task",
                "app.models.user",
                "aerich.models",
            ],
            "default_connection": "default",
        }
    },
}


async def init_db() -> None:
    """Initialize database connections without modifying the schema."""
    await Tortoise.init(config=TORTOISE_ORM)


async def close_db() -> None:
    """Close all database connections created by Tortoise."""
    await Tortoise.close_connections()
