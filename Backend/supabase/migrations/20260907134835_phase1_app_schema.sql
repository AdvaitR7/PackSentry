-- PackSentry Phase 1 Migration: App Schema & Private Storage Bucket
-- Implements ADR-0008 (Citations non-nullable) & ADR-0013 (app schema + private inspection-evidence)

-- 1. Dedicated Schema Creation & Permission Hardening
CREATE SCHEMA IF NOT EXISTS app;

-- Revoke all access from public, anon, and authenticated roles (FastAPI is sole gateway via service_role)
REVOKE ALL ON SCHEMA app FROM public, anon, authenticated;
GRANT USAGE ON SCHEMA app TO postgres, service_role;

-- Set default privileges for new objects in app schema
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON TABLES TO postgres, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON SEQUENCES TO postgres, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON ROUTINES TO postgres, service_role;

-- 2. Citations Table
CREATE TABLE IF NOT EXISTS app.citation (
    id TEXT PRIMARY KEY,
    provision TEXT NOT NULL,
    instrument TEXT NOT NULL,
    gsr TEXT NOT NULL,
    gazette_date DATE NOT NULL,
    effective_from DATE,
    effective_to DATE,
    source_url TEXT NOT NULL,
    source_sha256 TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Rules Catalog Table
CREATE TABLE IF NOT EXISTS app.rule (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Rule Versions Table (citation_id is NOT NULL per ADR-0008)
CREATE TABLE IF NOT EXISTS app.rule_version (
    id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL REFERENCES app.rule(id) ON DELETE RESTRICT,
    citation_id TEXT NOT NULL REFERENCES app.citation(id) ON DELETE RESTRICT,
    effective_from DATE NOT NULL,
    effective_to DATE,
    required_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. Inspections Lifecycle & Results Table
CREATE TABLE IF NOT EXISTS app.inspection (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    overall TEXT,
    overall_ui_bucket TEXT,
    summary JSONB,
    context JSONB NOT NULL,
    ocr_document JSONB,
    declaration_set JSONB,
    engine JSONB,
    error_code TEXT,
    error_message TEXT,
    lease_timeout TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_inspection_status ON app.inspection(status);
CREATE INDEX IF NOT EXISTS idx_inspection_created_at ON app.inspection(created_at DESC);

-- 6. Inspection Images Metadata Table
CREATE TABLE IF NOT EXISTS app.inspection_image (
    id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL REFERENCES app.inspection(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_inspection_image_lookup ON app.inspection_image(inspection_id, role);

-- 7. Inspection Rule Results Table (Immutable Snapshot)
CREATE TABLE IF NOT EXISTS app.inspection_rule_result (
    id BIGSERIAL PRIMARY KEY,
    inspection_id TEXT NOT NULL REFERENCES app.inspection(id) ON DELETE CASCADE,
    rule_id TEXT NOT NULL REFERENCES app.rule(id) ON DELETE RESTRICT,
    rule_version_id TEXT NOT NULL REFERENCES app.rule_version(id) ON DELETE RESTRICT,
    verdict TEXT NOT NULL,
    ui_bucket TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    message TEXT NOT NULL,
    observed TEXT,
    expected TEXT,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence JSONB NOT NULL,
    applicability JSONB NOT NULL,
    citation_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rule_result_inspection ON app.inspection_rule_result(inspection_id);
CREATE INDEX IF NOT EXISTS idx_rule_result_verdict ON app.inspection_rule_result(verdict);

-- 8. Enable Row-Level Security (RLS) on all tables (Defense in depth per ADR-0013)
ALTER TABLE app.citation ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.rule ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.rule_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.inspection ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.inspection_image ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.inspection_rule_result ENABLE ROW LEVEL SECURITY;

-- 9. Private Evidence Storage Bucket Configuration
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'inspection-evidence',
    'inspection-evidence',
    false,
    12582912, -- 12 MB cap per image per ADR-0009
    ARRAY['image/jpeg', 'image/png', 'image/webp']
)
ON CONFLICT (id) DO UPDATE SET
    public = false,
    file_size_limit = 12582912,
    allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp'];
