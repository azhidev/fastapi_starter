from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "provinces" ADD "tz" DOUBLE PRECISION;
        ALTER TABLE "provinces" ADD "lat" DOUBLE PRECISION;
        ALTER TABLE "provinces" ADD "lng" DOUBLE PRECISION;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "provinces" DROP COLUMN "tz";
        ALTER TABLE "provinces" DROP COLUMN "lat";
        ALTER TABLE "provinces" DROP COLUMN "lng";"""
