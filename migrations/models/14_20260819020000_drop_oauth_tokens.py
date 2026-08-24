from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "oauthaccount" DROP COLUMN IF EXISTS "access_token";
        ALTER TABLE "oauthaccount" DROP COLUMN IF EXISTS "refresh_token";
        ALTER TABLE "oauthaccount" DROP COLUMN IF EXISTS "expires_at";
        ALTER TABLE "oauthaccount" ALTER COLUMN "id" DROP DEFAULT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        SELECT 1;"""
