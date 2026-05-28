CREATE TABLE IF NOT EXISTS pricing_settings (
    company_id            UUID PRIMARY KEY REFERENCES companies(id) ON DELETE RESTRICT,
    vat_rate_bps          INTEGER NOT NULL DEFAULT 1500 CHECK (vat_rate_bps >= 0),
    default_markup_bps    INTEGER NOT NULL DEFAULT 2500 CHECK (default_markup_bps >= 0),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS pricing_settings_set_updated_at ON pricing_settings;
CREATE TRIGGER pricing_settings_set_updated_at
BEFORE UPDATE ON pricing_settings
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

ALTER TABLE price_list_items
    ADD COLUMN IF NOT EXISTS price_component TEXT NOT NULL DEFAULT 'unit';

ALTER TABLE price_list_items
    ADD COLUMN IF NOT EXISTS effective_from TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE price_list_items
    ADD COLUMN IF NOT EXISTS effective_to TIMESTAMPTZ;

ALTER TABLE price_list_items
    ADD COLUMN IF NOT EXISTS replaces_id UUID REFERENCES price_list_items(id) ON DELETE SET NULL;

ALTER TABLE price_list_items
    DROP CONSTRAINT IF EXISTS price_list_items_price_list_id_item_type_item_key_key;

UPDATE price_list_items
SET price_component = split_part(item_key, '::', 3),
    item_key = split_part(item_key, '::', 1) || '::' || split_part(item_key, '::', 2)
WHERE item_type = 'board'
  AND item_key ~ '^board::[^:]+::[^:]+$';

UPDATE price_list_items
SET price_component = 'unit'
WHERE price_component = '';

DROP INDEX IF EXISTS price_list_items_active_item_unique_idx;
CREATE UNIQUE INDEX price_list_items_active_item_unique_idx
    ON price_list_items (price_list_id, item_type, item_key, price_component)
    WHERE effective_to IS NULL;

CREATE INDEX IF NOT EXISTS price_list_items_history_idx
    ON price_list_items (price_list_id, item_type, item_key, price_component, effective_from DESC);

DROP INDEX IF EXISTS price_lists_one_active_per_company_idx;
CREATE UNIQUE INDEX price_lists_one_active_per_company_idx
    ON price_lists (company_id)
    WHERE status = 'active';

COMMENT ON TABLE pricing_settings IS 'Company-scoped pricing defaults such as VAT and default markup.';
COMMENT ON COLUMN price_list_items.price_component IS 'Specific component of an item being priced, such as unit, sheet, sqm, edging_m, or labour_board.';
COMMENT ON COLUMN price_list_items.effective_from IS 'Timestamp when this price row became effective.';
COMMENT ON COLUMN price_list_items.effective_to IS 'Null while active. Set when replaced or retired so historical prices remain available.';
COMMENT ON COLUMN price_list_items.replaces_id IS 'Previous price row replaced by this row, if the price was updated.';
