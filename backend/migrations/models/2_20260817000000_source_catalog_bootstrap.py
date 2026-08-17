from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "sources" ADD COLUMN IF NOT EXISTS "canonical_base_url" VARCHAR(500);
        ALTER TABLE "sources" ADD COLUMN IF NOT EXISTS "validation_status" VARCHAR(30) NOT NULL DEFAULT 'catalog';
        ALTER TABLE "sources" ADD COLUMN IF NOT EXISTS "validation_checked_at" TIMESTAMPTZ;
        ALTER TABLE "sources" ADD COLUMN IF NOT EXISTS "validation_error" TEXT;
        ALTER TABLE "sources" ADD COLUMN IF NOT EXISTS "validation_final_url" VARCHAR(500);
        ALTER TABLE "sources" ADD COLUMN IF NOT EXISTS "discovered_from_url" VARCHAR(500);
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY base_url ORDER BY created_at, id) AS rn
            FROM "sources"
        )
        UPDATE "sources" AS s
        SET active = FALSE,
            canonical_base_url = NULL,
            validation_status = 'duplicate_inactive'
        FROM ranked
        WHERE s.id = ranked.id AND ranked.rn > 1;
        UPDATE "sources"
        SET "canonical_base_url" = COALESCE("canonical_base_url", "base_url")
        WHERE "canonical_base_url" IS NULL AND active = TRUE;
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_sources_canonical_base_url"
        ON "sources" ("canonical_base_url")
        WHERE "canonical_base_url" IS NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_sources_canonical_base_url";
        ALTER TABLE "sources" DROP COLUMN IF EXISTS "discovered_from_url";
        ALTER TABLE "sources" DROP COLUMN IF EXISTS "validation_final_url";
        ALTER TABLE "sources" DROP COLUMN IF EXISTS "validation_error";
        ALTER TABLE "sources" DROP COLUMN IF EXISTS "validation_checked_at";
        ALTER TABLE "sources" DROP COLUMN IF EXISTS "validation_status";
        ALTER TABLE "sources" DROP COLUMN IF EXISTS "canonical_base_url";"""
