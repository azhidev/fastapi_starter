from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user_role" (
    "user_id" VARCHAR(20) NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "role_id" VARCHAR(20) NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);
        CREATE UNIQUE INDEX IF NOT EXISTS "uidx_user_role_user_id_d0bad3"
            ON "user_role" ("user_id", "role_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        SELECT 1;"""
