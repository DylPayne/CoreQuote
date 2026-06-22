ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS hardware_catalog_snapshot JSONB;

ALTER TABLE quotes
DROP CONSTRAINT IF EXISTS quotes_hardware_catalog_snapshot_object_chk;

ALTER TABLE quotes
ADD CONSTRAINT quotes_hardware_catalog_snapshot_object_chk
CHECK (
    hardware_catalog_snapshot IS NULL
    OR jsonb_typeof(hardware_catalog_snapshot) = 'object'
);

COMMENT ON COLUMN quotes.hardware_catalog_snapshot IS
'Frozen hardware/catalog rows used by non-draft quotes so later library edits do not change hardware pick lists, pricing, or hardware-driven cutting outputs.';
