from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user_role" (
    "user_id" VARCHAR(20) NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "role_id" VARCHAR(20) NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
)
;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "user_role";"""
