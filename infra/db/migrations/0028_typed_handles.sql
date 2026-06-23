ALTER TABLE handles
    ADD COLUMN IF NOT EXISTS handle_type TEXT NOT NULL DEFAULT 'standard',
    ADD COLUMN IF NOT EXISTS front_reduction_mm INTEGER NOT NULL DEFAULT 0;

ALTER TABLE handles
    DROP CONSTRAINT IF EXISTS handles_handle_type_check,
    ADD CONSTRAINT handles_handle_type_check
        CHECK (handle_type IN ('standard', 'full_length', 'c_channel', 'j_channel'));

ALTER TABLE handles
    DROP CONSTRAINT IF EXISTS handles_front_reduction_mm_check,
    ADD CONSTRAINT handles_front_reduction_mm_check
        CHECK (front_reduction_mm >= 0);

CREATE INDEX IF NOT EXISTS handles_company_type_idx ON handles(company_id, handle_type);

COMMENT ON COLUMN handles.handle_type IS 'Handle behavior: standard, full_length, c_channel, or j_channel.';
COMMENT ON COLUMN handles.front_reduction_mm IS 'Front dimension reduction used by full-length profile and channel handles.';
