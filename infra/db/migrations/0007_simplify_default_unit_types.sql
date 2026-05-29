-- Simplify global default unit families to:
--   Base Draw, Base Door, Wall Door, Tall Door
-- and retire pantry-specific built-in defaults.

UPDATE cutting_rulesets
SET status = 'archived',
    updated_at = now()
WHERE company_id IS NULL
  AND is_default = true
  AND status = 'active'
  AND unit_type_key IN (
    'Base 1 Draw', 'Base 2 Draw', 'Base 3 Draw', 'Base 4 Draw',
    'Base 1 Door', 'Base 2 Door',
    'Wall 1 Door', 'Wall 2 Door',
    'Tall Standard', 'Tall Pantry'
  );

UPDATE unit_configs
SET status = 'archived',
    updated_at = now()
WHERE company_id IS NULL
  AND is_default = true
  AND status = 'active'
  AND unit_type_key IN (
    'Base 1 Draw', 'Base 2 Draw', 'Base 3 Draw', 'Base 4 Draw',
    'Base 1 Door', 'Base 2 Door',
    'Wall 1 Door', 'Wall 2 Door',
    'Tall Standard', 'Tall Pantry'
  );

-- Ensure any previous active simplified defaults are archived before reseeding.
UPDATE cutting_rulesets
SET status = 'archived',
    updated_at = now()
WHERE company_id IS NULL
  AND is_default = true
  AND status = 'active'
  AND unit_type_key IN ('Base Draw', 'Base Door', 'Wall Door', 'Tall Door');

UPDATE unit_configs
SET status = 'archived',
    updated_at = now()
WHERE company_id IS NULL
  AND is_default = true
  AND status = 'active'
  AND unit_type_key IN ('Base Draw', 'Base Door', 'Wall Door', 'Tall Door');

WITH desired_unit_configs AS (
    SELECT *
    FROM (
        VALUES
            (
                NULL::uuid,
                'Base Draw'::text,
                'Base Draw'::text,
                'base'::text,
                'drawer'::text,
                1::integer,
                'active'::text,
                true::boolean,
                '{"num_drawers":3,"drawer_side_h":200,"panel_gap_mm":3}'::jsonb,
                780::integer,
                600::integer,
                580::integer,
                300::integer,
                2400::integer,
                150::integer,
                1200::integer,
                150::integer,
                700::integer
            ),
            (
                NULL::uuid,
                'Base Door'::text,
                'Base Door'::text,
                'base'::text,
                'door'::text,
                1::integer,
                'active'::text,
                true::boolean,
                '{"num_doors":2,"default_shelves":1,"shelf_setback":20,"panel_gap_mm":3}'::jsonb,
                780::integer,
                600::integer,
                580::integer,
                300::integer,
                2400::integer,
                150::integer,
                1200::integer,
                150::integer,
                700::integer
            ),
            (
                NULL::uuid,
                'Wall Door'::text,
                'Wall Door'::text,
                'wall'::text,
                'wall'::text,
                1::integer,
                'active'::text,
                true::boolean,
                '{"num_doors":2,"default_shelves":1,"shelf_setback":20,"panel_gap_mm":3}'::jsonb,
                720::integer,
                600::integer,
                330::integer,
                300::integer,
                2400::integer,
                150::integer,
                1200::integer,
                150::integer,
                450::integer
            ),
            (
                NULL::uuid,
                'Tall Door'::text,
                'Tall Door'::text,
                'tall'::text,
                'tall'::text,
                1::integer,
                'active'::text,
                true::boolean,
                '{"num_doors":2,"default_shelves":4,"shelf_setback":20,"panel_gap_mm":3}'::jsonb,
                2100::integer,
                600::integer,
                580::integer,
                1800::integer,
                2700::integer,
                150::integer,
                1200::integer,
                150::integer,
                700::integer
            )
    ) AS rows(
        company_id,
        unit_type_key,
        label,
        category,
        variant_type,
        version,
        status,
        is_default,
        variant_config,
        default_height,
        default_width,
        default_depth,
        height_min,
        height_max,
        width_min,
        width_max,
        depth_min,
        depth_max
    )
),
upserted_unit_configs AS (
    INSERT INTO unit_configs (
        company_id,
        unit_type_key,
        label,
        category,
        variant_type,
        version,
        status,
        is_default,
        variant_config,
        default_height,
        default_width,
        default_depth,
        height_min,
        height_max,
        width_min,
        width_max,
        depth_min,
        depth_max
    )
    SELECT
        company_id,
        unit_type_key,
        label,
        category,
        variant_type,
        version,
        status,
        is_default,
        variant_config,
        default_height,
        default_width,
        default_depth,
        height_min,
        height_max,
        width_min,
        width_max,
        depth_min,
        depth_max
    FROM desired_unit_configs
    ON CONFLICT (unit_type_key, version) WHERE company_id IS NULL
    DO UPDATE SET
        label = EXCLUDED.label,
        category = EXCLUDED.category,
        variant_type = EXCLUDED.variant_type,
        status = EXCLUDED.status,
        is_default = EXCLUDED.is_default,
        variant_config = EXCLUDED.variant_config,
        default_height = EXCLUDED.default_height,
        default_width = EXCLUDED.default_width,
        default_depth = EXCLUDED.default_depth,
        height_min = EXCLUDED.height_min,
        height_max = EXCLUDED.height_max,
        width_min = EXCLUDED.width_min,
        width_max = EXCLUDED.width_max,
        depth_min = EXCLUDED.depth_min,
        depth_max = EXCLUDED.depth_max,
        updated_at = now()
    RETURNING id, unit_type_key, category, variant_type
),
resolved_unit_configs AS (
    SELECT id, unit_type_key, category, variant_type
    FROM upserted_unit_configs
),
upserted_rulesets AS (
    INSERT INTO cutting_rulesets (
        company_id,
        unit_config_id,
        unit_type_key,
        name,
        description,
        status,
        version,
        is_default
    )
    SELECT
        NULL,
        id,
        unit_type_key,
        'Default ' || unit_type_key,
        'Global default ruleset seeded from simplified CoreQuote cutting logic.',
        'active',
        1,
        true
    FROM resolved_unit_configs
    ON CONFLICT (unit_type_key, version) WHERE company_id IS NULL
    DO UPDATE SET
        unit_config_id = EXCLUDED.unit_config_id,
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        status = EXCLUDED.status,
        is_default = EXCLUDED.is_default,
        updated_at = now()
    RETURNING id, unit_config_id
),
source_rows AS (
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
    FROM upserted_rulesets cr
    JOIN resolved_unit_configs uc ON uc.id = cr.unit_config_id
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
               false, false, false, false
        WHERE uc.variant_type IN ('door', 'wall', 'tall')

        UNION ALL

        SELECT 100, 'panel', 'Door',
               'h - panel_gap_mm',
               '(w / num_doors) - panel_gap_mm',
               'num_doors',
               'num_doors > 0',
               'length',
               false,
               true,
               true,
               true,
               true
        WHERE uc.variant_type IN ('door', 'wall', 'tall')
    ) AS rows ON true
),
upserted_rows AS (
    INSERT INTO cutting_rule_rows (
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
        meta
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
        '{"source":"builtin_default_simplified"}'::jsonb
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
    RETURNING id
)
SELECT count(*) FROM upserted_rows;
