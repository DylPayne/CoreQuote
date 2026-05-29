CREATE TABLE IF NOT EXISTS unit_configs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id              UUID REFERENCES companies(id) ON DELETE RESTRICT,
    unit_type_key           TEXT NOT NULL,
    label                   TEXT NOT NULL,
    category                TEXT NOT NULL CHECK (category IN ('base', 'wall', 'tall', 'custom')),
    variant_type            TEXT NOT NULL CHECK (variant_type IN ('drawer', 'door', 'wall', 'tall', 'custom')),
    version                 INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    status                  TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('draft', 'active', 'archived')),
    is_default              BOOLEAN NOT NULL DEFAULT false,
    based_on_unit_config_id UUID REFERENCES unit_configs(id) ON DELETE SET NULL,
    variant_config          JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(variant_config) = 'object'),
    default_height          INTEGER NOT NULL CHECK (default_height > 0),
    default_width           INTEGER NOT NULL CHECK (default_width > 0),
    default_depth           INTEGER NOT NULL CHECK (default_depth > 0),
    height_min              INTEGER NOT NULL CHECK (height_min > 0),
    height_max              INTEGER NOT NULL CHECK (height_max >= height_min),
    width_min               INTEGER NOT NULL CHECK (width_min > 0),
    width_max               INTEGER NOT NULL CHECK (width_max >= width_min),
    depth_min               INTEGER NOT NULL CHECK (depth_min > 0),
    depth_max               INTEGER NOT NULL CHECK (depth_max >= depth_min),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS unit_configs_global_key_version_idx
    ON unit_configs(unit_type_key, version)
    WHERE company_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS unit_configs_company_key_version_idx
    ON unit_configs(company_id, unit_type_key, version)
    WHERE company_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS unit_configs_one_active_global_key_idx
    ON unit_configs(unit_type_key)
    WHERE company_id IS NULL AND status = 'active';

CREATE UNIQUE INDEX IF NOT EXISTS unit_configs_one_active_company_key_idx
    ON unit_configs(company_id, unit_type_key)
    WHERE company_id IS NOT NULL AND status = 'active';

CREATE INDEX IF NOT EXISTS unit_configs_visible_idx
    ON unit_configs(company_id, status, category, label);

DROP TRIGGER IF EXISTS unit_configs_set_updated_at ON unit_configs;
CREATE TRIGGER unit_configs_set_updated_at
BEFORE UPDATE ON unit_configs
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS cutting_rulesets (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id            UUID REFERENCES companies(id) ON DELETE RESTRICT,
    unit_config_id        UUID REFERENCES unit_configs(id) ON DELETE SET NULL,
    unit_type_key         TEXT NOT NULL,
    name                  TEXT NOT NULL,
    description           TEXT NOT NULL DEFAULT '',
    status                TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    version               INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    based_on_ruleset_id   UUID REFERENCES cutting_rulesets(id) ON DELETE SET NULL,
    is_default            BOOLEAN NOT NULL DEFAULT false,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS cutting_rulesets_global_key_version_idx
    ON cutting_rulesets(unit_type_key, version)
    WHERE company_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS cutting_rulesets_company_key_version_name_idx
    ON cutting_rulesets(company_id, unit_type_key, version, name)
    WHERE company_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS cutting_rulesets_one_active_default_global_key_idx
    ON cutting_rulesets(unit_type_key)
    WHERE company_id IS NULL AND status = 'active' AND is_default = true;

CREATE INDEX IF NOT EXISTS cutting_rulesets_visible_idx
    ON cutting_rulesets(company_id, unit_type_key, status, version DESC);

DROP TRIGGER IF EXISTS cutting_rulesets_set_updated_at ON cutting_rulesets;
CREATE TRIGGER cutting_rulesets_set_updated_at
BEFORE UPDATE ON cutting_rulesets
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS cutting_rule_rows (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruleset_id          UUID NOT NULL REFERENCES cutting_rulesets(id) ON DELETE CASCADE,
    sort_order          INTEGER NOT NULL CHECK (sort_order > 0),
    section             TEXT NOT NULL CHECK (section IN ('carcass', 'panel', 'hardware', 'extra_panel')),
    description         TEXT NOT NULL,
    length_formula      TEXT NOT NULL DEFAULT '',
    width_formula       TEXT NOT NULL DEFAULT '',
    qty_formula         TEXT NOT NULL DEFAULT '1',
    condition_formula   TEXT NOT NULL DEFAULT '',
    grain_direction     TEXT NOT NULL DEFAULT 'none' CHECK (grain_direction IN ('none', 'length', 'width')),
    can_rotate          BOOLEAN NOT NULL DEFAULT true,
    edge_long_1         BOOLEAN NOT NULL DEFAULT false,
    edge_long_2         BOOLEAN NOT NULL DEFAULT false,
    edge_short_1        BOOLEAN NOT NULL DEFAULT false,
    edge_short_2        BOOLEAN NOT NULL DEFAULT false,
    meta                JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(meta) = 'object'),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ruleset_id, sort_order)
);

CREATE INDEX IF NOT EXISTS cutting_rule_rows_ruleset_idx
    ON cutting_rule_rows(ruleset_id, sort_order);

DROP TRIGGER IF EXISTS cutting_rule_rows_set_updated_at ON cutting_rule_rows;
CREATE TRIGGER cutting_rule_rows_set_updated_at
BEFORE UPDATE ON cutting_rule_rows
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

INSERT INTO unit_configs (
    company_id, unit_type_key, label, category, variant_type, version, status, is_default,
    variant_config, default_height, default_width, default_depth,
    height_min, height_max, width_min, width_max, depth_min, depth_max
)
VALUES
    (NULL, 'Base 3 Draw', 'Base 3 Draw', 'base', 'drawer', 1, 'active', true, '{"num_drawers":3,"drawer_side_h":200,"panel_gap_mm":3}'::jsonb, 780, 600, 580, 300, 2400, 150, 1200, 150, 700),
    (NULL, 'Base 1 Draw', 'Base 1 Draw', 'base', 'drawer', 1, 'active', true, '{"num_drawers":1,"drawer_side_h":200,"panel_gap_mm":3}'::jsonb, 780, 600, 580, 300, 2400, 150, 1200, 150, 700),
    (NULL, 'Base 2 Draw', 'Base 2 Draw', 'base', 'drawer', 1, 'active', true, '{"num_drawers":2,"drawer_side_h":200,"panel_gap_mm":3}'::jsonb, 780, 600, 580, 300, 2400, 150, 1200, 150, 700),
    (NULL, 'Base 4 Draw', 'Base 4 Draw', 'base', 'drawer', 1, 'active', true, '{"num_drawers":4,"drawer_side_h":200,"panel_gap_mm":3}'::jsonb, 780, 600, 580, 300, 2400, 150, 1200, 150, 700),
    (NULL, 'Base 2 Door', 'Base 2 Door', 'base', 'door', 1, 'active', true, '{"num_doors":2,"default_shelves":1,"shelf_setback":20,"panel_gap_mm":3}'::jsonb, 780, 600, 580, 300, 2400, 150, 1200, 150, 700),
    (NULL, 'Base 1 Door', 'Base 1 Door', 'base', 'door', 1, 'active', true, '{"num_doors":1,"default_shelves":1,"shelf_setback":20,"panel_gap_mm":3}'::jsonb, 780, 400, 580, 300, 2400, 150, 1200, 150, 700),
    (NULL, 'Wall 2 Door', 'Wall 2 Door', 'wall', 'wall', 1, 'active', true, '{"num_doors":2,"default_shelves":1,"shelf_setback":20,"panel_gap_mm":3}'::jsonb, 720, 600, 330, 300, 2400, 150, 1200, 150, 450),
    (NULL, 'Wall 1 Door', 'Wall 1 Door', 'wall', 'wall', 1, 'active', true, '{"num_doors":1,"default_shelves":1,"shelf_setback":20,"panel_gap_mm":3}'::jsonb, 720, 400, 330, 300, 2400, 150, 1200, 150, 450),
    (NULL, 'Tall Standard', 'Tall Standard', 'tall', 'tall', 1, 'active', true, '{"num_doors":2,"default_shelves":4,"shelf_setback":20,"panel_gap_mm":3,"is_pantry":false}'::jsonb, 2100, 600, 580, 1800, 2400, 150, 1200, 150, 700),
    (NULL, 'Tall Pantry', 'Tall Pantry', 'tall', 'tall', 1, 'active', true, '{"num_doors":2,"default_shelves":6,"shelf_setback":20,"panel_gap_mm":3,"is_pantry":true}'::jsonb, 2400, 600, 580, 2100, 2700, 150, 1200, 150, 700)
ON CONFLICT DO NOTHING;

INSERT INTO cutting_rulesets (
    company_id, unit_config_id, unit_type_key, name, description, status, version, is_default
)
SELECT
    NULL,
    id,
    unit_type_key,
    'Default ' || label,
    'Global default ruleset seeded from CoreQuote built-in cutting logic.',
    'active',
    1,
    true
FROM unit_configs
WHERE company_id IS NULL
  AND version = 1
ON CONFLICT DO NOTHING;

WITH source_rows AS (
    SELECT
        cr.id AS ruleset_id,
        rows.sort_order,
        rows.section,
        rows.description,
        rows.length_formula,
        rows.width_formula,
        rows.qty_formula,
        rows.condition_formula,
        rows.grain_direction,
        rows.can_rotate,
        rows.edge_long_1,
        rows.edge_long_2,
        rows.edge_short_1,
        rows.edge_short_2
    FROM cutting_rulesets cr
    JOIN unit_configs uc ON uc.id = cr.unit_config_id
    JOIN LATERAL (
        SELECT *
        FROM (
            VALUES
                (10, 'carcass', 'Side', 'h - (2 * t)', 'd - t', '2', '', 'none', true, false, false, false, false),
                (20, 'carcass', 'Base', 'w', 'd', '1', '', 'none', true, false, false, false, false),
                (30, 'carcass', 'Rail', 'w', '100', '2', '', 'none', true, false, false, false, false),
                (40, 'carcass', 'Backing', 'h - (2 * t)', 'w', '1', '', 'none', true, false, false, false, false)
        ) AS base_rows(sort_order, section, description, length_formula, width_formula, qty_formula, condition_formula, grain_direction, can_rotate, edge_long_1, edge_long_2, edge_short_1, edge_short_2)
        WHERE uc.category IN ('base', 'tall')

        UNION ALL

        SELECT *
        FROM (
            VALUES
                (10, 'carcass', 'Side', 'h - (2 * t)', 'd - t', '2', '', 'none', true, false, false, false, false),
                (20, 'carcass', 'Top', 'w', 'd', '1', '', 'none', true, false, false, false, false),
                (30, 'carcass', 'Bottom', 'w', 'd', '1', '', 'none', true, false, false, false, false),
                (40, 'carcass', 'Backing', 'h - (2 * t)', 'w', '1', '', 'none', true, false, false, false, false)
        ) AS wall_rows(sort_order, section, description, length_formula, width_formula, qty_formula, condition_formula, grain_direction, can_rotate, edge_long_1, edge_long_2, edge_short_1, edge_short_2)
        WHERE uc.category = 'wall'

        UNION ALL

        SELECT *
        FROM (
            VALUES
                (50, 'carcass', 'Drawer Front/Back', 'drawer_width', 'drawer_front_back_height', 'num_drawers * 2', 'num_drawers > 0', 'none', true, false, false, false, false),
                (60, 'carcass', 'Drawer Side', 'drawer_depth', 'drawer_side_height', 'num_drawers * 2', 'num_drawers > 0', 'none', true, false, false, false, false),
                (70, 'carcass', 'Drawer Base', 'drawer_width', 'drawer_depth - (2 * t)', 'num_drawers', 'num_drawers > 0', 'none', true, false, false, false, false),
                (100, 'panel', 'Drawer Front', 'drawer_front_height', 'w - panel_gap_mm', 'num_drawers', 'num_drawers > 0', 'length', false, true, true, true, true)
        ) AS drawer_rows(sort_order, section, description, length_formula, width_formula, qty_formula, condition_formula, grain_direction, can_rotate, edge_long_1, edge_long_2, edge_short_1, edge_short_2)
        WHERE uc.variant_type = 'drawer'

        UNION ALL

        SELECT 50, 'carcass', 'Shelf', 'w - (2 * t)', 'd - t - shelf_setback',
               'num_shelves', 'num_shelves > 0', 'none', true,
               true, false, false, false
        WHERE uc.variant_type IN ('door', 'wall', 'tall')

        UNION ALL

        SELECT 60, 'carcass', 'Mid-Rail', 'w', '100', '1', 'is_pantry', 'none', true,
               false, false, false, false
        WHERE COALESCE((uc.variant_config ->> 'is_pantry')::boolean, false) = true

        UNION ALL

        SELECT 100, 'panel', 'Door',
               CASE WHEN COALESCE((uc.variant_config ->> 'is_pantry')::boolean, false)
                    THEN '(h / 2) - panel_gap_mm'
                    ELSE 'h - panel_gap_mm'
               END,
               '(w / num_doors) - panel_gap_mm',
               CASE WHEN COALESCE((uc.variant_config ->> 'is_pantry')::boolean, false)
                    THEN 'num_doors * 2'
                    ELSE 'num_doors'
               END,
               'num_doors > 0',
               'length',
               false,
               true,
               true,
               true,
               true
        WHERE uc.variant_type IN ('door', 'wall', 'tall')
    ) AS rows ON true
    WHERE cr.company_id IS NULL
      AND cr.is_default = true
),
upserted_rows AS (
    INSERT INTO cutting_rule_rows (
        ruleset_id, sort_order, section, description, length_formula, width_formula,
        qty_formula, condition_formula, grain_direction, can_rotate,
        edge_long_1, edge_long_2, edge_short_1, edge_short_2, meta
    )
    SELECT
        ruleset_id,
        sort_order,
        section,
        description,
        length_formula,
        width_formula,
        qty_formula,
        condition_formula,
        grain_direction,
        can_rotate,
        edge_long_1,
        edge_long_2,
        edge_short_1,
        edge_short_2,
        '{"source":"builtin_default"}'::jsonb
    FROM source_rows
    ON CONFLICT (ruleset_id, sort_order) DO UPDATE SET
        section = EXCLUDED.section,
        description = EXCLUDED.description,
        length_formula = EXCLUDED.length_formula,
        width_formula = EXCLUDED.width_formula,
        qty_formula = EXCLUDED.qty_formula,
        condition_formula = EXCLUDED.condition_formula,
        grain_direction = EXCLUDED.grain_direction,
        can_rotate = EXCLUDED.can_rotate,
        edge_long_1 = EXCLUDED.edge_long_1,
        edge_long_2 = EXCLUDED.edge_long_2,
        edge_short_1 = EXCLUDED.edge_short_1,
        edge_short_2 = EXCLUDED.edge_short_2,
        meta = EXCLUDED.meta,
        updated_at = now()
    RETURNING id, ruleset_id, sort_order
)
SELECT count(*) FROM upserted_rows;

COMMENT ON TABLE unit_configs IS 'Global and company-owned cabinet unit definitions. Global defaults have company_id null and are visible to every company.';
COMMENT ON COLUMN unit_configs.company_id IS 'Null means global/default configuration visible to all companies.';
COMMENT ON COLUMN unit_configs.version IS 'Monotonic version for preserving historical quote and ruleset behavior.';
COMMENT ON COLUMN unit_configs.variant_config IS 'PostgreSQL JSONB object for unit-family settings that are not common columns.';
COMMENT ON TABLE cutting_rulesets IS 'Versioned cutting formula sets. Global defaults have company_id null; company-specific copies can override them.';
COMMENT ON TABLE cutting_rule_rows IS 'Ordered formula rows for a cutting ruleset.';
COMMENT ON COLUMN cutting_rule_rows.edge_long_1 IS 'Whether the first long edge of this generated cut row must be edged.';
COMMENT ON COLUMN cutting_rule_rows.edge_long_2 IS 'Whether the second long edge of this generated cut row must be edged.';
COMMENT ON COLUMN cutting_rule_rows.edge_short_1 IS 'Whether the first short edge of this generated cut row must be edged.';
COMMENT ON COLUMN cutting_rule_rows.edge_short_2 IS 'Whether the second short edge of this generated cut row must be edged.';
