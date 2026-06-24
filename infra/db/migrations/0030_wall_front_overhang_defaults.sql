ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS wall_front_overhang_default JSONB NOT NULL DEFAULT
    '{"enabled":false,"amount_mm":20,"edge":"bottom","apply_to":"all","front_indexes":[]}'::jsonb;

ALTER TABLE quotes
DROP CONSTRAINT IF EXISTS quotes_wall_front_overhang_default_object_chk;

ALTER TABLE quotes
ADD CONSTRAINT quotes_wall_front_overhang_default_object_chk
CHECK (jsonb_typeof(wall_front_overhang_default) = 'object');

COMMENT ON COLUMN quotes.wall_front_overhang_default IS
    'Quote-level default for handle-free wall-unit front overhang geometry.';
