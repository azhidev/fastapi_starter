from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "countries" ADD "iso_alpha2" VARCHAR(5);
        ALTER TABLE "provinces" ADD "iso_alpha2" VARCHAR(5);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "countries" DROP COLUMN "iso_alpha2";
        ALTER TABLE "provinces" DROP COLUMN "iso_alpha2";"""
