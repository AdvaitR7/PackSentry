-- PackSentry Phase 4 Migration: Idempotency support (ADR-0009)
-- Enables atomic de-duplication of inspection requests across process boundaries.

ALTER TABLE app.inspection ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE app.inspection ADD COLUMN IF NOT EXISTS request_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_inspection_idempotency_key
    ON app.inspection (idempotency_key)
    WHERE idempotency_key IS NOT NULL;
