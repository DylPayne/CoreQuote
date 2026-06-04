-- Align non-drawer global default cutting rules with the May 2026 spreadsheet.
-- Drawer formulas are intentionally excluded.

WITH desired_defaults(unit_type_key, variant_config_patch) AS (
    VALUES
        ('Wall Door'::text, '{"default_shelves":2}'::jsonb),
        ('Tall Door'::text, '{"default_shelves":5}'::jsonb)
)
UPDATE unit_configs
SET variant_config = unit_configs.variant_config || desired_defaults.variant_config_patch,
    updated_at = now()
FROM desired_defaults
WHERE unit_configs.company_id IS NULL
  AND unit_configs.is_default = true
  AND unit_configs.status = 'active'
  AND unit_configs.unit_type_key = desired_defaults.unit_type_key;

WITH desired_rows(
    unit_type_key,
    sort_order,
    section,
    description,
    length_formula,
    width_formula,
    qty_formula,
    condition_formula
) AS (
    VALUES
        ('Wall Door'::text, 20, 'carcass', 'Base', 'w', 'd', '1', ''),
        ('Wall Door'::text, 30, 'carcass', 'Top', 'w', 'd', '1', ''),
        ('Wall Door'::text, 100, 'panel', 'Door', 'h - panel_gap_mm + 20', '(w / num_doors) - panel_gap_mm', 'num_doors', 'num_doors > 0'),
        ('Tall Door'::text, 30, 'carcass', 'Top', 'w', 'd', '1', '')
)
UPDATE cutting_rule_rows
SET section = desired_rows.section,
    description = desired_rows.description,
    length_formula = desired_rows.length_formula,
    width_formula = desired_rows.width_formula,
    qty_formula = desired_rows.qty_formula,
    condition_formula = desired_rows.condition_formula,
    meta = cutting_rule_rows.meta || '{"source":"flip_quote_may_2026_non_drawer_defaults"}'::jsonb,
    updated_at = now()
FROM cutting_rulesets
JOIN desired_rows ON desired_rows.unit_type_key = cutting_rulesets.unit_type_key
WHERE cutting_rule_rows.ruleset_id = cutting_rulesets.id
  AND cutting_rule_rows.sort_order = desired_rows.sort_order
  AND cutting_rulesets.company_id IS NULL
  AND cutting_rulesets.is_default = true
  AND cutting_rulesets.status = 'active';

UPDATE cutting_rulesets
SET updated_at = now()
WHERE company_id IS NULL
  AND is_default = true
  AND status = 'active'
  AND unit_type_key IN ('Wall Door', 'Tall Door');
