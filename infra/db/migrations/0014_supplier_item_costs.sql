CREATE TABLE IF NOT EXISTS brands (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, name)
);

CREATE INDEX IF NOT EXISTS brands_company_id_idx ON brands(company_id);

DROP TRIGGER IF EXISTS brands_set_updated_at ON brands;
CREATE TRIGGER brands_set_updated_at
BEFORE UPDATE ON brands
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

INSERT INTO brands (company_id, name)
SELECT DISTINCT company_id, trim(brand)
FROM board_types
WHERE trim(brand) <> ''
ON CONFLICT (company_id, name) DO NOTHING;

INSERT INTO brands (company_id, name)
SELECT DISTINCT company_id, trim(brand)
FROM slides
WHERE trim(brand) <> ''
ON CONFLICT (company_id, name) DO NOTHING;

INSERT INTO brands (company_id, name)
SELECT DISTINCT company_id, trim(brand)
FROM hinges
WHERE trim(brand) <> ''
ON CONFLICT (company_id, name) DO NOTHING;

ALTER TABLE board_types
    ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES brands(id) ON DELETE SET NULL;

ALTER TABLE slides
    ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES brands(id) ON DELETE SET NULL;

ALTER TABLE hinges
    ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES brands(id) ON DELETE SET NULL;

UPDATE board_types item
SET brand_id = brand.id
FROM brands brand
WHERE item.brand_id IS NULL
  AND brand.company_id = item.company_id
  AND brand.name = trim(item.brand);

UPDATE slides item
SET brand_id = brand.id
FROM brands brand
WHERE item.brand_id IS NULL
  AND brand.company_id = item.company_id
  AND brand.name = trim(item.brand);

UPDATE hinges item
SET brand_id = brand.id
FROM brands brand
WHERE item.brand_id IS NULL
  AND brand.company_id = item.company_id
  AND brand.name = trim(item.brand);

CREATE INDEX IF NOT EXISTS board_types_brand_id_idx ON board_types(brand_id);
CREATE INDEX IF NOT EXISTS slides_brand_id_idx ON slides(brand_id);
CREATE INDEX IF NOT EXISTS hinges_brand_id_idx ON hinges(brand_id);

CREATE TABLE IF NOT EXISTS suppliers (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id    UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    name          TEXT NOT NULL,
    code          TEXT NOT NULL DEFAULT '',
    contact_name  TEXT NOT NULL DEFAULT '',
    email         TEXT NOT NULL DEFAULT '',
    phone         TEXT NOT NULL DEFAULT '',
    notes         TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, name)
);

CREATE INDEX IF NOT EXISTS suppliers_company_id_idx ON suppliers(company_id);

DROP TRIGGER IF EXISTS suppliers_set_updated_at ON suppliers;
CREATE TRIGGER suppliers_set_updated_at
BEFORE UPDATE ON suppliers
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS item_suppliers (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id            UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    item_type             TEXT NOT NULL CHECK (item_type IN ('board', 'slide', 'hinge', 'handle', 'extra')),
    item_ref_id           UUID NOT NULL,
    supplier_id           UUID NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    supplier_sku          TEXT NOT NULL DEFAULT '',
    supplier_description  TEXT NOT NULL DEFAULT '',
    price_component       TEXT NOT NULL DEFAULT 'unit',
    order_uom             TEXT NOT NULL DEFAULT 'pcs',
    is_preferred          BOOLEAN NOT NULL DEFAULT false,
    notes                 TEXT NOT NULL DEFAULT '',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, item_type, item_ref_id, supplier_id, supplier_sku, price_component)
);

CREATE INDEX IF NOT EXISTS item_suppliers_company_id_idx ON item_suppliers(company_id);
CREATE INDEX IF NOT EXISTS item_suppliers_item_idx ON item_suppliers(company_id, item_type, item_ref_id);
CREATE INDEX IF NOT EXISTS item_suppliers_supplier_id_idx ON item_suppliers(supplier_id);

DROP INDEX IF EXISTS item_suppliers_one_preferred_per_item_idx;
CREATE UNIQUE INDEX item_suppliers_one_preferred_per_item_idx
    ON item_suppliers (company_id, item_type, item_ref_id, price_component)
    WHERE is_preferred;

DROP TRIGGER IF EXISTS item_suppliers_set_updated_at ON item_suppliers;
CREATE TRIGGER item_suppliers_set_updated_at
BEFORE UPDATE ON item_suppliers
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS supplier_item_costs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id            UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    item_supplier_id      UUID NOT NULL REFERENCES item_suppliers(id) ON DELETE CASCADE,
    list_price_cents      INTEGER NOT NULL DEFAULT 0 CHECK (list_price_cents >= 0),
    discount_bps          INTEGER NOT NULL DEFAULT 0 CHECK (discount_bps >= 0 AND discount_bps <= 10000),
    unit_cost_cents       INTEGER NOT NULL CHECK (unit_cost_cents >= 0),
    currency_code         TEXT NOT NULL DEFAULT 'ZAR' CHECK (currency_code ~ '^[A-Z]{3}$'),
    source                TEXT NOT NULL DEFAULT 'manual',
    source_ref            TEXT NOT NULL DEFAULT '',
    effective_from        TIMESTAMPTZ NOT NULL DEFAULT now(),
    effective_to          TIMESTAMPTZ,
    replaces_id           UUID REFERENCES supplier_item_costs(id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS supplier_item_costs_company_id_idx ON supplier_item_costs(company_id);
CREATE INDEX IF NOT EXISTS supplier_item_costs_item_supplier_id_idx ON supplier_item_costs(item_supplier_id);
CREATE INDEX IF NOT EXISTS supplier_item_costs_history_idx
    ON supplier_item_costs (item_supplier_id, effective_from DESC);

DROP INDEX IF EXISTS supplier_item_costs_one_active_per_item_supplier_idx;
CREATE UNIQUE INDEX supplier_item_costs_one_active_per_item_supplier_idx
    ON supplier_item_costs (item_supplier_id)
    WHERE effective_to IS NULL;

DROP TRIGGER IF EXISTS supplier_item_costs_set_updated_at ON supplier_item_costs;
CREATE TRIGGER supplier_item_costs_set_updated_at
BEFORE UPDATE ON supplier_item_costs
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

ALTER TABLE price_list_items
    ADD COLUMN IF NOT EXISTS source_supplier_item_cost_id UUID REFERENCES supplier_item_costs(id) ON DELETE SET NULL;

ALTER TABLE price_list_items
    ADD COLUMN IF NOT EXISTS cost_source TEXT NOT NULL DEFAULT 'manual';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'price_list_items_cost_source_check'
    ) THEN
        ALTER TABLE price_list_items
            ADD CONSTRAINT price_list_items_cost_source_check
            CHECK (cost_source IN ('manual', 'supplier', 'override', 'import'));
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS price_list_items_source_supplier_item_cost_id_idx
    ON price_list_items(source_supplier_item_cost_id);

COMMENT ON TABLE brands IS 'Company-scoped product brands or manufacturers, separate from suppliers.';
COMMENT ON TABLE suppliers IS 'Company-scoped supplier/distributor records.';
COMMENT ON TABLE item_suppliers IS 'Links a catalog item to a supplier-specific SKU, UOM, and preferred-source flag.';
COMMENT ON TABLE supplier_item_costs IS 'Versioned buying costs from suppliers. Price lists copy from these rows to form quoting snapshots.';
COMMENT ON COLUMN board_types.brand_id IS 'Normalized brand reference. The brand text column remains for API compatibility.';
COMMENT ON COLUMN slides.brand_id IS 'Normalized brand reference. The brand text column remains for API compatibility.';
COMMENT ON COLUMN hinges.brand_id IS 'Normalized brand reference. The brand text column remains for API compatibility.';
COMMENT ON COLUMN item_suppliers.price_component IS 'Price component generated into price_list_items, such as unit, sheet, or sqm.';
COMMENT ON COLUMN item_suppliers.order_uom IS 'Supplier order unit of measure, copied to generated price list items.';
COMMENT ON COLUMN supplier_item_costs.list_price_cents IS 'Supplier list price before discount in the company currency.';
COMMENT ON COLUMN supplier_item_costs.discount_bps IS 'Supplier discount represented in basis points. 3000 means 30.00%.';
COMMENT ON COLUMN supplier_item_costs.unit_cost_cents IS 'Net buying cost after discount in the company currency.';
COMMENT ON COLUMN price_list_items.source_supplier_item_cost_id IS 'Supplier cost row used to generate this price-list item, if any.';
COMMENT ON COLUMN price_list_items.cost_source IS 'manual, supplier, override, or import source marker for price-list generation.';
