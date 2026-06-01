ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS custom_panels JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE quotes
DROP CONSTRAINT IF EXISTS quotes_custom_panels_object_chk;

ALTER TABLE quotes
ADD CONSTRAINT quotes_custom_panels_object_chk
CHECK (jsonb_typeof(custom_panels) = 'object');

COMMENT ON COLUMN quotes.custom_panels IS
'Quote-scoped custom panel configuration (presets, auto runs, and manual rows).';
