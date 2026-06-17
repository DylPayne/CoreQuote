ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS production_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE quotes
DROP CONSTRAINT IF EXISTS quotes_production_metadata_object_chk;

ALTER TABLE quotes
ADD CONSTRAINT quotes_production_metadata_object_chk
CHECK (jsonb_typeof(production_metadata) = 'object');

ALTER TABLE quote_units
ADD COLUMN IF NOT EXISTS production_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE quote_units
DROP CONSTRAINT IF EXISTS quote_units_production_metadata_object_chk;

ALTER TABLE quote_units
ADD CONSTRAINT quote_units_production_metadata_object_chk
CHECK (jsonb_typeof(production_metadata) = 'object');

COMMENT ON COLUMN quotes.production_metadata IS
'Quote-scoped workshop production instructions by material role, including edge-banding, grain, rotation, and notes.';

COMMENT ON COLUMN quote_units.production_metadata IS
'Unit-scoped workshop production instruction overrides by material role.';
