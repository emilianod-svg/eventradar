from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "events" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "title" VARCHAR(300) NOT NULL,
    "slug" VARCHAR(350) NOT NULL UNIQUE,
    "description" TEXT,
    "start_at" TIMESTAMPTZ NOT NULL,
    "end_at" TIMESTAMPTZ,
    "recurrence_text" VARCHAR(200),
    "venue_name" VARCHAR(300) NOT NULL,
    "address" VARCHAR(500),
    "latitude" DECIMAL(9,6),
    "longitude" DECIMAL(9,6),
    "price_text" VARCHAR(200),
    "category" VARCHAR(100),
    "image_url" TEXT,
    "quality_score" DECIMAL(4,3) NOT NULL  DEFAULT 0,
    "status" VARCHAR(9) NOT NULL  DEFAULT 'ACTIVE',
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_events_start_a_b8e467" ON "events" ("start_at");
CREATE INDEX IF NOT EXISTS "idx_events_status_c1e5d2" ON "events" ("status");
CREATE INDEX IF NOT EXISTS "idx_events_categor_e8b646" ON "events" ("category");
COMMENT ON COLUMN "events"."status" IS 'ACTIVE: ACTIVE\nUPDATED: UPDATED\nCANCELLED: CANCELLED\nARCHIVED: ARCHIVED';
CREATE TABLE IF NOT EXISTS "executions" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "status" VARCHAR(9) NOT NULL  DEFAULT 'RUNNING',
    "triggered_by" VARCHAR(20) NOT NULL  DEFAULT 'manual',
    "started_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "finished_at" TIMESTAMPTZ,
    "metrics" JSONB NOT NULL,
    "error_message" TEXT
);
COMMENT ON COLUMN "executions"."status" IS 'RUNNING: RUNNING\nCOMPLETED: COMPLETED\nPARTIAL: PARTIAL\nFAILED: FAILED';
CREATE TABLE IF NOT EXISTS "sources" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(200) NOT NULL,
    "base_url" VARCHAR(500) NOT NULL,
    "adapter_type" VARCHAR(50) NOT NULL,
    "active" BOOL NOT NULL  DEFAULT True,
    "reliability_score" DECIMAL(4,3) NOT NULL  DEFAULT 0.5,
    "contact_notes" TEXT,
    "last_reviewed_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "event_change_history" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "field_name" VARCHAR(100) NOT NULL,
    "old_value" TEXT,
    "new_value" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "event_id" UUID NOT NULL REFERENCES "events" ("id") ON DELETE CASCADE,
    "execution_id" UUID REFERENCES "executions" ("id") ON DELETE CASCADE,
    "source_id" UUID REFERENCES "sources" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "event_sources" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "source_url" VARCHAR(500) NOT NULL,
    "is_primary" BOOL NOT NULL  DEFAULT True,
    "contributed_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "event_id" UUID NOT NULL REFERENCES "events" ("id") ON DELETE CASCADE,
    "source_id" UUID NOT NULL REFERENCES "sources" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_event_sourc_event_i_d30b26" UNIQUE ("event_id", "source_id", "source_url")
);
CREATE TABLE IF NOT EXISTS "execution_sources" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "status" VARCHAR(20) NOT NULL  DEFAULT 'PENDING',
    "items_collected" INT NOT NULL  DEFAULT 0,
    "items_accepted" INT NOT NULL  DEFAULT 0,
    "error_message" TEXT,
    "duration_ms" DOUBLE PRECISION,
    "execution_id" UUID NOT NULL REFERENCES "executions" ("id") ON DELETE CASCADE,
    "source_id" UUID NOT NULL REFERENCES "sources" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_execution_s_executi_37c80c" UNIQUE ("execution_id", "source_id")
);
CREATE TABLE IF NOT EXISTS "raw_contents" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "url" VARCHAR(500) NOT NULL,
    "raw_text" TEXT NOT NULL,
    "image_urls" JSONB NOT NULL,
    "published_at" TIMESTAMPTZ,
    "fetched_at" TIMESTAMPTZ NOT NULL,
    "content_hash" VARCHAR(64) NOT NULL,
    "adapter_metadata" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "source_id" UUID NOT NULL REFERENCES "sources" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_raw_content_source__414b7f" UNIQUE ("source_id", "content_hash")
);
CREATE TABLE IF NOT EXISTS "classifications" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "is_event" BOOL NOT NULL,
    "confidence" DECIMAL(4,3) NOT NULL,
    "extracted_fields" JSONB NOT NULL,
    "evidence" JSONB NOT NULL,
    "model_name" VARCHAR(100),
    "prompt_version" VARCHAR(50),
    "tokens_used" INT,
    "latency_ms" DOUBLE PRECISION,
    "cost_usd" DECIMAL(8,4),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "raw_content_id" UUID NOT NULL REFERENCES "raw_contents" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "evaluation_decisions" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "decision" VARCHAR(6) NOT NULL,
    "reasons" JSONB NOT NULL,
    "score" DECIMAL(4,3),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "classification_id" UUID NOT NULL REFERENCES "classifications" ("id") ON DELETE CASCADE,
    "duplicate_of_id" UUID REFERENCES "events" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "evaluation_decisions"."decision" IS 'ACCEPT: ACCEPT\nREJECT: REJECT\nREVIEW: REVIEW\nMERGE: MERGE';
CREATE TABLE IF NOT EXISTS "review_items" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "status" VARCHAR(20) NOT NULL  DEFAULT 'PENDING',
    "reason" TEXT,
    "reviewed_by" VARCHAR(100),
    "reviewed_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "classification_id" UUID NOT NULL REFERENCES "classifications" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "source_score_history" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "previous_score" DECIMAL(4,3) NOT NULL,
    "new_score" DECIMAL(4,3) NOT NULL,
    "processed_count" INT NOT NULL  DEFAULT 0,
    "accepted_count" INT NOT NULL  DEFAULT 0,
    "rejected_count" INT NOT NULL  DEFAULT 0,
    "avg_extraction_quality" DECIMAL(4,3),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "execution_id" UUID REFERENCES "executions" ("id") ON DELETE CASCADE,
    "source_id" UUID NOT NULL REFERENCES "sources" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
