from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        SELECT 1;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        SELECT 1;"""
