CREATE TABLE IF NOT EXISTS board_types (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id                      UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    brand                           TEXT NOT NULL,
    material                        TEXT NOT NULL,
    thickness                       INTEGER NOT NULL CHECK (thickness > 0),
    length_mm                       INTEGER NOT NULL CHECK (length_mm > 0),
    width_mm                        INTEGER NOT NULL CHECK (width_mm > 0),
    costing_mode                    TEXT NOT NULL DEFAULT 'sheet' CHECK (costing_mode IN ('sheet', 'sqm')),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, brand, material, thickness, length_mm, width_mm)
);

CREATE INDEX IF NOT EXISTS board_types_company_id_idx ON board_types(company_id);

DROP TRIGGER IF EXISTS board_types_set_updated_at ON board_types;
CREATE TRIGGER board_types_set_updated_at
BEFORE UPDATE ON board_types
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS slides (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id                  UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    brand                       TEXT NOT NULL,
    model                       TEXT NOT NULL,
    code                        TEXT NOT NULL DEFAULT '',
    length                      INTEGER NOT NULL CHECK (length >= 0),
    side_length                 INTEGER NOT NULL CHECK (side_length >= 0),
    side_clearance_total        INTEGER NOT NULL CHECK (side_clearance_total >= 0),
    side_height_uplift          INTEGER NOT NULL DEFAULT 0 CHECK (side_height_uplift >= 0),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, brand, model, code)
);

CREATE INDEX IF NOT EXISTS slides_company_id_idx ON slides(company_id);

DROP TRIGGER IF EXISTS slides_set_updated_at ON slides;
CREATE TRIGGER slides_set_updated_at
BEFORE UPDATE ON slides
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS hinges (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    brand               TEXT NOT NULL,
    model               TEXT NOT NULL,
    code                TEXT NOT NULL DEFAULT '',
    opening_angle_deg   INTEGER NOT NULL CHECK (opening_angle_deg >= 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, brand, model, code)
);

CREATE INDEX IF NOT EXISTS hinges_company_id_idx ON hinges(company_id);

DROP TRIGGER IF EXISTS hinges_set_updated_at ON hinges;
CREATE TRIGGER hinges_set_updated_at
BEFORE UPDATE ON hinges
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS handles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    name        TEXT NOT NULL,
    supplier    TEXT NOT NULL DEFAULT '',
    code        TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, name, supplier, code)
);

CREATE INDEX IF NOT EXISTS handles_company_id_idx ON handles(company_id);

DROP TRIGGER IF EXISTS handles_set_updated_at ON handles;
CREATE TRIGGER handles_set_updated_at
BEFORE UPDATE ON handles
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS extra_categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, name)
);

CREATE INDEX IF NOT EXISTS extra_categories_company_id_idx ON extra_categories(company_id);

DROP TRIGGER IF EXISTS extra_categories_set_updated_at ON extra_categories;
CREATE TRIGGER extra_categories_set_updated_at
BEFORE UPDATE ON extra_categories
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS extras (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id   UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    name         TEXT NOT NULL,
    category_id  UUID NOT NULL REFERENCES extra_categories(id) ON DELETE RESTRICT,
    supplier     TEXT NOT NULL DEFAULT '',
    code         TEXT NOT NULL DEFAULT '',
    notes        TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, name, category_id, supplier, code)
);

CREATE INDEX IF NOT EXISTS extras_company_id_idx ON extras(company_id);
CREATE INDEX IF NOT EXISTS extras_category_id_idx ON extras(category_id);

DROP TRIGGER IF EXISTS extras_set_updated_at ON extras;
CREATE TRIGGER extras_set_updated_at
BEFORE UPDATE ON extras
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS price_lists (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    name            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    effective_from  DATE,
    effective_to    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS price_lists_company_id_idx ON price_lists(company_id);
CREATE INDEX IF NOT EXISTS price_lists_company_status_idx ON price_lists(company_id, status);

DROP TRIGGER IF EXISTS price_lists_set_updated_at ON price_lists;
CREATE TRIGGER price_lists_set_updated_at
BEFORE UPDATE ON price_lists
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS price_list_items (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id        UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    price_list_id     UUID NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
    item_type         TEXT NOT NULL CHECK (item_type IN ('board', 'slide', 'hinge', 'handle', 'extra')),
    item_ref_id       UUID,
    item_key          TEXT NOT NULL,
    uom               TEXT NOT NULL,
    unit_price_cents  INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (price_list_id, item_type, item_key)
);

CREATE INDEX IF NOT EXISTS price_list_items_company_id_idx ON price_list_items(company_id);
CREATE INDEX IF NOT EXISTS price_list_items_price_list_id_idx ON price_list_items(price_list_id);

DROP TRIGGER IF EXISTS price_list_items_set_updated_at ON price_list_items;
CREATE TRIGGER price_list_items_set_updated_at
BEFORE UPDATE ON price_list_items
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

COMMENT ON TABLE board_types IS 'Company-scoped board inventory library.';
COMMENT ON TABLE slides IS 'Company-scoped drawer slide inventory library.';
COMMENT ON TABLE hinges IS 'Company-scoped hinge inventory library.';
COMMENT ON TABLE handles IS 'Company-scoped handle inventory library.';
COMMENT ON TABLE extra_categories IS 'Company-scoped categories for extras.';
COMMENT ON TABLE extras IS 'Company-scoped extras inventory library.';
COMMENT ON TABLE price_lists IS 'Company-scoped pricing library headers.';
COMMENT ON TABLE price_list_items IS 'Company-scoped pricing library line items.';
