ALTER TABLE pricing_settings
    ADD COLUMN IF NOT EXISTS carcass_markup_bps INTEGER NOT NULL DEFAULT 2500 CHECK (carcass_markup_bps >= 0),
    ADD COLUMN IF NOT EXISTS door_panel_markup_bps INTEGER NOT NULL DEFAULT 2500 CHECK (door_panel_markup_bps >= 0),
    ADD COLUMN IF NOT EXISTS component_markup_bps INTEGER NOT NULL DEFAULT 2500 CHECK (component_markup_bps >= 0),
    ADD COLUMN IF NOT EXISTS handle_markup_bps INTEGER NOT NULL DEFAULT 2500 CHECK (handle_markup_bps >= 0),
    ADD COLUMN IF NOT EXISTS extras_markup_bps INTEGER NOT NULL DEFAULT 2500 CHECK (extras_markup_bps >= 0),
    ADD COLUMN IF NOT EXISTS fabrication_markup_bps INTEGER NOT NULL DEFAULT 2500 CHECK (fabrication_markup_bps >= 0),
    ADD COLUMN IF NOT EXISTS install_markup_bps INTEGER NOT NULL DEFAULT 2500 CHECK (install_markup_bps >= 0),
    ADD COLUMN IF NOT EXISTS delivery_markup_bps INTEGER NOT NULL DEFAULT 2500 CHECK (delivery_markup_bps >= 0),
    ADD COLUMN IF NOT EXISTS joinery_commission_bps INTEGER NOT NULL DEFAULT 0 CHECK (joinery_commission_bps >= 0),
    ADD COLUMN IF NOT EXISTS labour_cents_per_m2 INTEGER NOT NULL DEFAULT 2000 CHECK (labour_cents_per_m2 >= 0),
    ADD COLUMN IF NOT EXISTS consumables_cents_per_m2 INTEGER NOT NULL DEFAULT 1000 CHECK (consumables_cents_per_m2 >= 0),
    ADD COLUMN IF NOT EXISTS install_day_cost_cents INTEGER NOT NULL DEFAULT 190000 CHECK (install_day_cost_cents >= 0),
    ADD COLUMN IF NOT EXISTS delivery_base_cents INTEGER NOT NULL DEFAULT 95000 CHECK (delivery_base_cents >= 0),
    ADD COLUMN IF NOT EXISTS install_units_per_day INTEGER NOT NULL DEFAULT 3 CHECK (install_units_per_day > 0),
    ADD COLUMN IF NOT EXISTS delivery_units_per_trip INTEGER NOT NULL DEFAULT 20 CHECK (delivery_units_per_trip > 0),
    ADD COLUMN IF NOT EXISTS minimum_install_days_bps INTEGER NOT NULL DEFAULT 5000 CHECK (minimum_install_days_bps >= 0),
    ADD COLUMN IF NOT EXISTS minimum_delivery_trips_bps INTEGER NOT NULL DEFAULT 5000 CHECK (minimum_delivery_trips_bps >= 0);

UPDATE pricing_settings
SET carcass_markup_bps = default_markup_bps,
    door_panel_markup_bps = default_markup_bps,
    component_markup_bps = default_markup_bps,
    handle_markup_bps = default_markup_bps,
    extras_markup_bps = default_markup_bps,
    fabrication_markup_bps = default_markup_bps,
    install_markup_bps = default_markup_bps,
    delivery_markup_bps = default_markup_bps
WHERE carcass_markup_bps = 2500
  AND door_panel_markup_bps = 2500
  AND component_markup_bps = 2500
  AND handle_markup_bps = 2500
  AND extras_markup_bps = 2500
  AND fabrication_markup_bps = 2500
  AND install_markup_bps = 2500
  AND delivery_markup_bps = 2500;

COMMENT ON COLUMN pricing_settings.carcass_markup_bps IS 'Markup applied to carcass board material and related base materials.';
COMMENT ON COLUMN pricing_settings.door_panel_markup_bps IS 'Markup applied to door, drawer-front, flap, and visible panel material.';
COMMENT ON COLUMN pricing_settings.component_markup_bps IS 'Markup applied to slides, hinges, and flap mechanisms.';
COMMENT ON COLUMN pricing_settings.handle_markup_bps IS 'Markup applied to handle hardware.';
COMMENT ON COLUMN pricing_settings.extras_markup_bps IS 'Markup applied to selected quote extras.';
COMMENT ON COLUMN pricing_settings.fabrication_markup_bps IS 'Markup applied to labour and fabrication cost buckets.';
COMMENT ON COLUMN pricing_settings.install_markup_bps IS 'Markup applied to installation labour.';
COMMENT ON COLUMN pricing_settings.delivery_markup_bps IS 'Markup applied to delivery charges.';
COMMENT ON COLUMN pricing_settings.joinery_commission_bps IS 'Commission applied to joinery and visible-panel sell totals before VAT.';
COMMENT ON COLUMN pricing_settings.labour_cents_per_m2 IS 'Base unit assembly labour cost per square metre of carcass board usage.';
COMMENT ON COLUMN pricing_settings.consumables_cents_per_m2 IS 'Base consumables cost per square metre of carcass board usage.';
COMMENT ON COLUMN pricing_settings.install_day_cost_cents IS 'Base installation cost per install day.';
COMMENT ON COLUMN pricing_settings.delivery_base_cents IS 'Base delivery cost per delivery unit.';
COMMENT ON COLUMN pricing_settings.install_units_per_day IS 'Cabinet unit count divisor used to estimate installation days.';
COMMENT ON COLUMN pricing_settings.delivery_units_per_trip IS 'Cabinet unit count divisor used to estimate delivery units.';
COMMENT ON COLUMN pricing_settings.minimum_install_days_bps IS 'Minimum install days represented as decimal-day basis points; 5000 is 0.5 days.';
COMMENT ON COLUMN pricing_settings.minimum_delivery_trips_bps IS 'Minimum delivery units represented as basis points; 5000 is 0.5.';
