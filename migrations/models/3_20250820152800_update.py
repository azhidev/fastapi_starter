from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "countries" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "label" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
        CREATE TABLE IF NOT EXISTS "provinces" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "label" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "country_id" INT NOT NULL REFERENCES "countries" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "provinces";
        DROP TABLE IF EXISTS "countries";"""
