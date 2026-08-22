from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "task";
        DROP TABLE IF EXISTS "project";
        DROP TABLE IF EXISTS "calendars";
        DROP TABLE IF EXISTS "moon_signs";
        DROP TABLE IF EXISTS "phases";
        DROP TABLE IF EXISTS "recommendations";
        DROP TABLE IF EXISTS "provinces";
        DROP TABLE IF EXISTS "countries";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        SELECT 1;"""
