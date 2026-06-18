WITH ranked_active_company_rulesets AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY company_id, unit_type_key
            ORDER BY is_default DESC, version DESC, updated_at DESC, id DESC
        ) AS activation_rank
    FROM cutting_rulesets
    WHERE company_id IS NOT NULL
      AND status = 'active'
)
UPDATE cutting_rulesets
SET status = 'archived',
    is_default = false
FROM ranked_active_company_rulesets
WHERE cutting_rulesets.id = ranked_active_company_rulesets.id
  AND ranked_active_company_rulesets.activation_rank > 1;

CREATE UNIQUE INDEX IF NOT EXISTS cutting_rulesets_one_active_company_key_idx
    ON cutting_rulesets(company_id, unit_type_key)
    WHERE company_id IS NOT NULL AND status = 'active';

COMMENT ON INDEX cutting_rulesets_one_active_company_key_idx IS
    'Ensures each company has one active cutting ruleset per unit type; quote cutlists use that company ruleset before the built-in default.';
