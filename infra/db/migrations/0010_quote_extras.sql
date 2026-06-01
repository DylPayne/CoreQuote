CREATE TABLE IF NOT EXISTS quote_extras (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    quote_id    UUID NOT NULL,
    extra_id    UUID NOT NULL REFERENCES extras(id) ON DELETE RESTRICT,
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT quote_extras_quote_company_fk
        FOREIGN KEY (quote_id, company_id)
        REFERENCES quotes(id, company_id)
        ON DELETE CASCADE,
    CONSTRAINT quote_extras_quote_extra_unique UNIQUE (quote_id, extra_id)
);

CREATE INDEX IF NOT EXISTS quote_extras_company_quote_idx
    ON quote_extras(company_id, quote_id, created_at ASC);

DROP TRIGGER IF EXISTS quote_extras_set_updated_at ON quote_extras;
CREATE TRIGGER quote_extras_set_updated_at
BEFORE UPDATE ON quote_extras
FOR EACH ROW
EXECUTE FUNCTION corequote_set_updated_at();

COMMENT ON TABLE quote_extras IS 'Company-scoped selected extras and quantities per quote.';
