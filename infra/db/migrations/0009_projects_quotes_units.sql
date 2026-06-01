CREATE TABLE IF NOT EXISTS projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0),
    client      TEXT NOT NULL DEFAULT '',
    address     TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS projects_id_company_id_idx
    ON projects(id, company_id);
CREATE INDEX IF NOT EXISTS projects_company_created_idx
    ON projects(company_id, created_at DESC);

DROP TRIGGER IF EXISTS projects_set_updated_at ON projects;
CREATE TRIGGER projects_set_updated_at
BEFORE UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS quotes (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id                      UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    project_id                      UUID NOT NULL,
    name                            TEXT NOT NULL CHECK (length(trim(name)) > 0),
    notes                           TEXT NOT NULL DEFAULT '',
    default_carcass_board_type_id   UUID REFERENCES board_types(id) ON DELETE SET NULL,
    default_door_board_type_id      UUID REFERENCES board_types(id) ON DELETE SET NULL,
    default_panel_board_type_id     UUID REFERENCES board_types(id) ON DELETE SET NULL,
    default_slide_id                UUID REFERENCES slides(id) ON DELETE SET NULL,
    default_hinge_id                UUID REFERENCES hinges(id) ON DELETE SET NULL,
    default_base_handle_id          UUID REFERENCES handles(id) ON DELETE SET NULL,
    default_wall_handle_id          UUID REFERENCES handles(id) ON DELETE SET NULL,
    default_tall_handle_id          UUID REFERENCES handles(id) ON DELETE SET NULL,
    default_drawer_handle_id        UUID REFERENCES handles(id) ON DELETE SET NULL,
    unit_defaults                   JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(unit_defaults) = 'object'),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT quotes_project_company_fk
        FOREIGN KEY (project_id, company_id)
        REFERENCES projects(id, company_id)
        ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS quotes_id_company_id_idx
    ON quotes(id, company_id);
CREATE INDEX IF NOT EXISTS quotes_company_project_created_idx
    ON quotes(company_id, project_id, created_at DESC);

DROP TRIGGER IF EXISTS quotes_set_updated_at ON quotes;
CREATE TRIGGER quotes_set_updated_at
BEFORE UPDATE ON quotes
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

CREATE TABLE IF NOT EXISTS quote_units (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id              UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    quote_id                UUID NOT NULL,
    unit_number             INTEGER NOT NULL CHECK (unit_number > 0),
    unit_type_key           TEXT NOT NULL CHECK (length(trim(unit_type_key)) > 0),
    height                  INTEGER NOT NULL CHECK (height > 0),
    width                   INTEGER NOT NULL CHECK (width > 0),
    depth                   INTEGER NOT NULL CHECK (depth > 0),
    thickness               INTEGER NOT NULL DEFAULT 16 CHECK (thickness > 0),
    carcass_board_type_id   UUID REFERENCES board_types(id) ON DELETE SET NULL,
    door_board_type_id      UUID REFERENCES board_types(id) ON DELETE SET NULL,
    extra_params            JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(extra_params) = 'object'),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT quote_units_quote_company_fk
        FOREIGN KEY (quote_id, company_id)
        REFERENCES quotes(id, company_id)
        ON DELETE CASCADE,
    CONSTRAINT quote_units_quote_unit_number_unique UNIQUE (quote_id, unit_number)
);

CREATE INDEX IF NOT EXISTS quote_units_company_quote_unit_number_idx
    ON quote_units(company_id, quote_id, unit_number ASC);

DROP TRIGGER IF EXISTS quote_units_set_updated_at ON quote_units;
CREATE TRIGGER quote_units_set_updated_at
BEFORE UPDATE ON quote_units
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

COMMENT ON TABLE projects IS 'Company-scoped project headers for quote workflows.';
COMMENT ON TABLE quotes IS 'Company-scoped quote headers under projects, with per-quote defaults for materials and hardware.';
COMMENT ON TABLE quote_units IS 'Company-scoped unit rows that belong to a quote and preserve explicit unit ordering through unit_number.';
