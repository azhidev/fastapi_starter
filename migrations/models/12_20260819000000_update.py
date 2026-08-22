from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DELETE FROM "user_role" AS duplicate
        USING "user_role" AS retained
        WHERE duplicate.ctid < retained.ctid
          AND duplicate."user_id" = retained."user_id"
          AND duplicate."role_id" = retained."role_id";
        CREATE UNIQUE INDEX IF NOT EXISTS "uidx_user_role_user_id_d0bad3"
            ON "user_role" ("user_id", "role_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        SELECT 1;"""
