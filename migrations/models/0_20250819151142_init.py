from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" VARCHAR(20) NOT NULL PRIMARY KEY,
    "username" VARCHAR(255) NOT NULL UNIQUE,
    "email" VARCHAR(255) UNIQUE,
    "hashed_password" VARCHAR(255) NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_user_usernam_9987ab" ON "user" ("username");
CREATE INDEX IF NOT EXISTS "idx_user_email_1b4f1c" ON "user" ("email");
CREATE TABLE IF NOT EXISTS "oauthaccount" (
    "id" VARCHAR(20) NOT NULL PRIMARY KEY DEFAULT 'd2i98bjndlt077cakvjg',
    "provider" VARCHAR(50) NOT NULL,
    "subject" VARCHAR(255) NOT NULL,
    "access_token" TEXT NOT NULL,
    "expires_at" TIMESTAMPTZ,
    "refresh_token" TEXT,
    "user_id" VARCHAR(20) NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_oauthaccoun_provide_0d7455" UNIQUE ("provider", "subject")
);
CREATE TABLE IF NOT EXISTS "project" (
    "id" VARCHAR(20) NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "owner_id" VARCHAR(20) NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "task" (
    "id" VARCHAR(20) NOT NULL PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "done" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "project_id" VARCHAR(20) NOT NULL REFERENCES "project" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "role" (
    "id" VARCHAR(20) NOT NULL PRIMARY KEY,
    "name" VARCHAR(50) NOT NULL UNIQUE,
    "description" TEXT
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "user_role" (
    "user_id" VARCHAR(20) NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "role_id" VARCHAR(20) NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_user_role_user_id_d0bad3" ON "user_role" ("user_id", "role_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
