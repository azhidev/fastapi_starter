from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ALTER COLUMN "username" DROP NOT NULL;
        ALTER TABLE "user" ALTER COLUMN "email" SET NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ALTER COLUMN "username" SET NOT NULL;
        ALTER TABLE "user" ALTER COLUMN "email" DROP NOT NULL;"""
