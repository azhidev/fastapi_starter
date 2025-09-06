from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "calendars" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "utc_year" VARCHAR(4) NOT NULL,
    "utc_month" VARCHAR(2) NOT NULL,
    "utc_day" VARCHAR(2) NOT NULL,
    "moon_sign_id" INT NOT NULL REFERENCES "moon_signs" ("id") ON DELETE CASCADE,
    "phase_id" INT NOT NULL REFERENCES "phases" ("id") ON DELETE CASCADE,
    "recommendation_id" INT NOT NULL REFERENCES "recommendations" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_calendars_utc_yea_a1d40a" UNIQUE ("utc_year", "utc_month", "utc_day")
);
        CREATE TABLE IF NOT EXISTS "moon_signs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "en_name" VARCHAR(50) NOT NULL,
    "ar_name" VARCHAR(50) NOT NULL,
    "fa_name" VARCHAR(50) NOT NULL
);
        CREATE TABLE IF NOT EXISTS "phases" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "en_name" VARCHAR(50) NOT NULL,
    "ar_name" VARCHAR(50) NOT NULL,
    "fa_name" VARCHAR(50) NOT NULL
);
        CREATE TABLE IF NOT EXISTS "recommendations" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "en_name" VARCHAR(300) NOT NULL,
    "ar_name" VARCHAR(300) NOT NULL,
    "fa_name" VARCHAR(300) NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "moon_signs";
        DROP TABLE IF EXISTS "calendars";
        DROP TABLE IF EXISTS "phases";
        DROP TABLE IF EXISTS "recommendations";"""
