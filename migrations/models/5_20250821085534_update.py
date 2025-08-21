from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "provinces" ADD "iso_3166_2" VARCHAR(10);
        ALTER TABLE "provinces" DROP COLUMN "iso_alpha2";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "provinces" ADD "iso_alpha2" VARCHAR(5);
        ALTER TABLE "provinces" DROP COLUMN "iso_3166_2";"""
