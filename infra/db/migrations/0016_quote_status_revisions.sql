ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'draft';

ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS quote_number TEXT;

ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;

ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS previous_revision_id UUID REFERENCES quotes(id) ON DELETE SET NULL;

WITH ranked AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY company_id, project_id
            ORDER BY created_at ASC, id ASC
        ) AS quote_index
    FROM quotes
    WHERE quote_number IS NULL
       OR length(trim(quote_number)) = 0
)
UPDATE quotes q
SET quote_number = 'Q-' || lpad(ranked.quote_index::text, 3, '0')
FROM ranked
WHERE q.id = ranked.id;

ALTER TABLE quotes
ALTER COLUMN quote_number SET NOT NULL;

ALTER TABLE quotes
DROP CONSTRAINT IF EXISTS quotes_status_chk;

ALTER TABLE quotes
ADD CONSTRAINT quotes_status_chk
CHECK (status IN ('draft', 'ready', 'sent', 'accepted', 'rejected', 'revised', 'expired'));

ALTER TABLE quotes
DROP CONSTRAINT IF EXISTS quotes_quote_number_not_blank_chk;

ALTER TABLE quotes
ADD CONSTRAINT quotes_quote_number_not_blank_chk
CHECK (length(trim(quote_number)) > 0);

ALTER TABLE quotes
DROP CONSTRAINT IF EXISTS quotes_revision_positive_chk;

ALTER TABLE quotes
ADD CONSTRAINT quotes_revision_positive_chk
CHECK (revision > 0);

CREATE UNIQUE INDEX IF NOT EXISTS quotes_company_project_number_revision_idx
    ON quotes(company_id, project_id, quote_number, revision);

CREATE INDEX IF NOT EXISTS quotes_previous_revision_id_idx
    ON quotes(previous_revision_id);

COMMENT ON COLUMN quotes.status IS
'Cabinetmaker-facing quote status: draft, ready, sent, accepted, rejected, revised, or expired.';

COMMENT ON COLUMN quotes.quote_number IS
'Stable project-facing quote number shared by revisions of the same quote.';

COMMENT ON COLUMN quotes.revision IS
'Visible revision number for a quote number, starting at 1.';

COMMENT ON COLUMN quotes.previous_revision_id IS
'Optional link to the quote revision this row was created from.';
