CREATE TABLE IF NOT EXISTS project_pricing_settings (
    project_id                  UUID PRIMARY KEY,
    company_id                  UUID NOT NULL,
    vat_rate_bps                INTEGER NOT NULL DEFAULT 1500 CHECK (vat_rate_bps >= 0),
    default_markup_bps          INTEGER NOT NULL DEFAULT 2500 CHECK (default_markup_bps >= 0),
    carcass_markup_bps          INTEGER NOT NULL DEFAULT 2500 CHECK (carcass_markup_bps >= 0),
    door_panel_markup_bps       INTEGER NOT NULL DEFAULT 2500 CHECK (door_panel_markup_bps >= 0),
    component_markup_bps        INTEGER NOT NULL DEFAULT 2500 CHECK (component_markup_bps >= 0),
    handle_markup_bps           INTEGER NOT NULL DEFAULT 2500 CHECK (handle_markup_bps >= 0),
    extras_markup_bps           INTEGER NOT NULL DEFAULT 2500 CHECK (extras_markup_bps >= 0),
    fabrication_markup_bps      INTEGER NOT NULL DEFAULT 2500 CHECK (fabrication_markup_bps >= 0),
    install_markup_bps          INTEGER NOT NULL DEFAULT 2500 CHECK (install_markup_bps >= 0),
    delivery_markup_bps         INTEGER NOT NULL DEFAULT 2500 CHECK (delivery_markup_bps >= 0),
    joinery_commission_bps      INTEGER NOT NULL DEFAULT 0 CHECK (joinery_commission_bps >= 0),
    labour_cents_per_m2         INTEGER NOT NULL DEFAULT 2000 CHECK (labour_cents_per_m2 >= 0),
    consumables_cents_per_m2    INTEGER NOT NULL DEFAULT 1000 CHECK (consumables_cents_per_m2 >= 0),
    install_day_cost_cents      INTEGER NOT NULL DEFAULT 190000 CHECK (install_day_cost_cents >= 0),
    delivery_base_cents         INTEGER NOT NULL DEFAULT 95000 CHECK (delivery_base_cents >= 0),
    install_units_per_day       INTEGER NOT NULL DEFAULT 3 CHECK (install_units_per_day >= 1),
    delivery_units_per_trip     INTEGER NOT NULL DEFAULT 20 CHECK (delivery_units_per_trip >= 1),
    minimum_install_days_bps    INTEGER NOT NULL DEFAULT 5000 CHECK (minimum_install_days_bps >= 0),
    minimum_delivery_trips_bps  INTEGER NOT NULL DEFAULT 5000 CHECK (minimum_delivery_trips_bps >= 0),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT project_pricing_settings_project_company_fk
        FOREIGN KEY (project_id, company_id)
        REFERENCES projects(id, company_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS project_pricing_settings_company_id_idx
    ON project_pricing_settings(company_id);

DROP TRIGGER IF EXISTS project_pricing_settings_set_updated_at ON project_pricing_settings;
CREATE TRIGGER project_pricing_settings_set_updated_at
BEFORE UPDATE ON project_pricing_settings
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS quote_pricing_settings (
    quote_id                    UUID PRIMARY KEY,
    company_id                  UUID NOT NULL,
    vat_rate_bps                INTEGER NOT NULL DEFAULT 1500 CHECK (vat_rate_bps >= 0),
    default_markup_bps          INTEGER NOT NULL DEFAULT 2500 CHECK (default_markup_bps >= 0),
    carcass_markup_bps          INTEGER NOT NULL DEFAULT 2500 CHECK (carcass_markup_bps >= 0),
    door_panel_markup_bps       INTEGER NOT NULL DEFAULT 2500 CHECK (door_panel_markup_bps >= 0),
    component_markup_bps        INTEGER NOT NULL DEFAULT 2500 CHECK (component_markup_bps >= 0),
    handle_markup_bps           INTEGER NOT NULL DEFAULT 2500 CHECK (handle_markup_bps >= 0),
    extras_markup_bps           INTEGER NOT NULL DEFAULT 2500 CHECK (extras_markup_bps >= 0),
    fabrication_markup_bps      INTEGER NOT NULL DEFAULT 2500 CHECK (fabrication_markup_bps >= 0),
    install_markup_bps          INTEGER NOT NULL DEFAULT 2500 CHECK (install_markup_bps >= 0),
    delivery_markup_bps         INTEGER NOT NULL DEFAULT 2500 CHECK (delivery_markup_bps >= 0),
    joinery_commission_bps      INTEGER NOT NULL DEFAULT 0 CHECK (joinery_commission_bps >= 0),
    labour_cents_per_m2         INTEGER NOT NULL DEFAULT 2000 CHECK (labour_cents_per_m2 >= 0),
    consumables_cents_per_m2    INTEGER NOT NULL DEFAULT 1000 CHECK (consumables_cents_per_m2 >= 0),
    install_day_cost_cents      INTEGER NOT NULL DEFAULT 190000 CHECK (install_day_cost_cents >= 0),
    delivery_base_cents         INTEGER NOT NULL DEFAULT 95000 CHECK (delivery_base_cents >= 0),
    install_units_per_day       INTEGER NOT NULL DEFAULT 3 CHECK (install_units_per_day >= 1),
    delivery_units_per_trip     INTEGER NOT NULL DEFAULT 20 CHECK (delivery_units_per_trip >= 1),
    minimum_install_days_bps    INTEGER NOT NULL DEFAULT 5000 CHECK (minimum_install_days_bps >= 0),
    minimum_delivery_trips_bps  INTEGER NOT NULL DEFAULT 5000 CHECK (minimum_delivery_trips_bps >= 0),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT quote_pricing_settings_quote_company_fk
        FOREIGN KEY (quote_id, company_id)
        REFERENCES quotes(id, company_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS quote_pricing_settings_company_id_idx
    ON quote_pricing_settings(company_id);

DROP TRIGGER IF EXISTS quote_pricing_settings_set_updated_at ON quote_pricing_settings;
CREATE TRIGGER quote_pricing_settings_set_updated_at
BEFORE UPDATE ON quote_pricing_settings
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

INSERT INTO project_pricing_settings (
    company_id,
    project_id,
    vat_rate_bps,
    default_markup_bps,
    carcass_markup_bps,
    door_panel_markup_bps,
    component_markup_bps,
    handle_markup_bps,
    extras_markup_bps,
    fabrication_markup_bps,
    install_markup_bps,
    delivery_markup_bps,
    joinery_commission_bps,
    labour_cents_per_m2,
    consumables_cents_per_m2,
    install_day_cost_cents,
    delivery_base_cents,
    install_units_per_day,
    delivery_units_per_trip,
    minimum_install_days_bps,
    minimum_delivery_trips_bps,
    created_at,
    updated_at
)
SELECT
    p.company_id,
    p.id,
    COALESCE(ps.vat_rate_bps, 1500),
    COALESCE(ps.default_markup_bps, 2500),
    COALESCE(ps.carcass_markup_bps, 2500),
    COALESCE(ps.door_panel_markup_bps, 2500),
    COALESCE(ps.component_markup_bps, 2500),
    COALESCE(ps.handle_markup_bps, 2500),
    COALESCE(ps.extras_markup_bps, 2500),
    COALESCE(ps.fabrication_markup_bps, 2500),
    COALESCE(ps.install_markup_bps, 2500),
    COALESCE(ps.delivery_markup_bps, 2500),
    COALESCE(ps.joinery_commission_bps, 0),
    COALESCE(ps.labour_cents_per_m2, 2000),
    COALESCE(ps.consumables_cents_per_m2, 1000),
    COALESCE(ps.install_day_cost_cents, 190000),
    COALESCE(ps.delivery_base_cents, 95000),
    COALESCE(ps.install_units_per_day, 3),
    COALESCE(ps.delivery_units_per_trip, 20),
    COALESCE(ps.minimum_install_days_bps, 5000),
    COALESCE(ps.minimum_delivery_trips_bps, 5000),
    p.created_at,
    p.updated_at
FROM projects p
LEFT JOIN pricing_settings ps
    ON ps.company_id = p.company_id
ON CONFLICT (project_id) DO NOTHING;

INSERT INTO quote_pricing_settings (
    company_id,
    quote_id,
    vat_rate_bps,
    default_markup_bps,
    carcass_markup_bps,
    door_panel_markup_bps,
    component_markup_bps,
    handle_markup_bps,
    extras_markup_bps,
    fabrication_markup_bps,
    install_markup_bps,
    delivery_markup_bps,
    joinery_commission_bps,
    labour_cents_per_m2,
    consumables_cents_per_m2,
    install_day_cost_cents,
    delivery_base_cents,
    install_units_per_day,
    delivery_units_per_trip,
    minimum_install_days_bps,
    minimum_delivery_trips_bps,
    created_at,
    updated_at
)
SELECT
    q.company_id,
    q.id,
    pps.vat_rate_bps,
    pps.default_markup_bps,
    pps.carcass_markup_bps,
    pps.door_panel_markup_bps,
    pps.component_markup_bps,
    pps.handle_markup_bps,
    pps.extras_markup_bps,
    pps.fabrication_markup_bps,
    pps.install_markup_bps,
    pps.delivery_markup_bps,
    pps.joinery_commission_bps,
    pps.labour_cents_per_m2,
    pps.consumables_cents_per_m2,
    pps.install_day_cost_cents,
    pps.delivery_base_cents,
    pps.install_units_per_day,
    pps.delivery_units_per_trip,
    pps.minimum_install_days_bps,
    pps.minimum_delivery_trips_bps,
    q.created_at,
    q.updated_at
FROM quotes q
JOIN project_pricing_settings pps
    ON pps.project_id = q.project_id
   AND pps.company_id = q.company_id
ON CONFLICT (quote_id) DO NOTHING;

COMMENT ON TABLE project_pricing_settings IS 'Project-scoped pricing defaults copied from company settings when the project is created.';
COMMENT ON TABLE quote_pricing_settings IS 'Quote-scoped pricing settings copied from project defaults when the quote is created and used for quote pricing calculations.';
