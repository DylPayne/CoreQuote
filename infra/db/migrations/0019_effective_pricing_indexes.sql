CREATE INDEX IF NOT EXISTS price_lists_active_effective_idx
    ON price_lists(company_id, status, effective_from, effective_to);

CREATE INDEX IF NOT EXISTS price_list_items_effective_lookup_idx
    ON price_list_items(company_id, price_list_id, item_type, item_key, price_component, effective_from DESC, effective_to);

CREATE INDEX IF NOT EXISTS supplier_item_costs_effective_lookup_idx
    ON supplier_item_costs(company_id, item_supplier_id, effective_from DESC, effective_to);

COMMENT ON COLUMN price_list_items.effective_from IS 'Timestamp when this price row starts applying to new quote pricing evidence.';
COMMENT ON COLUMN price_list_items.effective_to IS 'Exclusive timestamp when this price row stops applying. Null means no scheduled end yet.';
COMMENT ON COLUMN supplier_item_costs.effective_from IS 'Timestamp when this supplier cost starts applying to refresh workflows.';
COMMENT ON COLUMN supplier_item_costs.effective_to IS 'Exclusive timestamp when this supplier cost stops applying. Null means no scheduled end yet.';
