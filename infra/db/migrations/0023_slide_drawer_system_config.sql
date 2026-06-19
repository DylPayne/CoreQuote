ALTER TABLE slides
ADD COLUMN IF NOT EXISTS drawer_system_kind TEXT NOT NULL DEFAULT 'conventional'
    CHECK (drawer_system_kind IN ('conventional', 'metal')),
ADD COLUMN IF NOT EXISTS drawer_system_config JSONB NOT NULL DEFAULT '{}'::jsonb
    CHECK (jsonb_typeof(drawer_system_config) = 'object');

COMMENT ON COLUMN slides.drawer_system_kind IS 'conventional for timber drawer boxes, metal for configurable supplied drawer-side systems.';
COMMENT ON COLUMN slides.drawer_system_config IS 'Configurable metal drawer-system planning data: formulas, compatibility limits, and accessory lines.';
