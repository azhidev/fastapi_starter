from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "countries" ADD "timezone" VARCHAR(20);
        ALTER TABLE "countries" ADD "time_offset_minutes" SMALLINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "countries" DROP COLUMN "timezone";
        ALTER TABLE "countries" DROP COLUMN "time_offset_minutes";"""
