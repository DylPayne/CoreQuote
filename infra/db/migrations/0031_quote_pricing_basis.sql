ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS pricing_as_of TIMESTAMPTZ;

COMMENT ON COLUMN quotes.pricing_as_of IS
    'Optional quote-level pricing basis timestamp. When set, quote pricing resolves active price rows as of this timestamp instead of the quote updated timestamp.';
