-- Multi-panel capture: an inspection may now carry up to 4 SIDE panels alongside
-- PDP and BACK. Several rows therefore share a role, so role alone no longer
-- identifies an image and ORDER BY role is no longer deterministic.
--
-- `seq` is the 1-based sequence within a role. PDP and BACK are always 1, so the
-- DEFAULT makes every pre-existing row correct without a backfill.

ALTER TABLE app.inspection_image
    ADD COLUMN IF NOT EXISTS seq SMALLINT NOT NULL DEFAULT 1;

-- Replaces the (inspection_id, role) lookup index; role is no longer selective
-- on its own now that up to four rows can share the SIDE value.
CREATE INDEX IF NOT EXISTS idx_inspection_image_lookup_seq
    ON app.inspection_image(inspection_id, role, seq);
