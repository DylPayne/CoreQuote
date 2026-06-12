CREATE TABLE IF NOT EXISTS library_import_batches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    resource        TEXT NOT NULL CHECK (resource IN (
        'boards',
        'slides',
        'hinges',
        'handles',
        'suppliers',
        'extra_categories',
        'extras',
        'supplier_item_costs',
        'price_list_items'
    )),
    source_format   TEXT NOT NULL CHECK (source_format IN ('csv', 'tsv', 'xlsx')),
    filename        TEXT NOT NULL DEFAULT '',
    sheet_name      TEXT,
    source_ref      TEXT NOT NULL DEFAULT '',
    price_list_id   UUID REFERENCES price_lists(id) ON DELETE SET NULL,
    content_sha256  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed')),
    total_rows      INTEGER NOT NULL DEFAULT 0 CHECK (total_rows >= 0),
    created_count   INTEGER NOT NULL DEFAULT 0 CHECK (created_count >= 0),
    updated_count   INTEGER NOT NULL DEFAULT 0 CHECK (updated_count >= 0),
    skipped_count   INTEGER NOT NULL DEFAULT 0 CHECK (skipped_count >= 0),
    failed_count    INTEGER NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS library_import_batches_company_created_idx
    ON library_import_batches(company_id, created_at DESC);

CREATE INDEX IF NOT EXISTS library_import_batches_user_id_idx
    ON library_import_batches(user_id);

CREATE TABLE IF NOT EXISTS library_import_rows (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id         UUID NOT NULL REFERENCES library_import_batches(id) ON DELETE CASCADE,
    company_id       UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    row_number       INTEGER NOT NULL CHECK (row_number > 0),
    row_status       TEXT NOT NULL CHECK (row_status IN ('created', 'updated', 'skipped', 'failed')),
    import_identity  TEXT NOT NULL DEFAULT '',
    target_table     TEXT NOT NULL DEFAULT '',
    target_id        UUID,
    message          TEXT NOT NULL DEFAULT '',
    payload          JSONB NOT NULL DEFAULT '{}'::jsonb,
    problems         JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS library_import_rows_batch_id_idx
    ON library_import_rows(batch_id, row_number);

CREATE INDEX IF NOT EXISTS library_import_rows_company_created_idx
    ON library_import_rows(company_id, created_at DESC);

COMMENT ON TABLE library_import_batches IS 'Audit header for library imports applied by a company user.';
COMMENT ON TABLE library_import_rows IS 'Per-row audit outcomes for a library import batch.';
COMMENT ON COLUMN library_import_batches.content_sha256 IS 'SHA-256 hash of the submitted import content for source traceability without duplicating uploaded files.';
COMMENT ON COLUMN library_import_batches.source_ref IS 'User-visible source reference such as supplier price sheet, email, or spreadsheet tab.';
COMMENT ON COLUMN library_import_rows.payload IS 'Normalized row payload that was applied or rejected.';
COMMENT ON COLUMN library_import_rows.problems IS 'Structured validation problems for failed import rows.';
