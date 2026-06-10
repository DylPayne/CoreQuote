ALTER TABLE suppliers
    ADD COLUMN IF NOT EXISTS default_discount_bps INTEGER NOT NULL DEFAULT 0
    CHECK (default_discount_bps >= 0 AND default_discount_bps <= 10000);

COMMENT ON COLUMN suppliers.default_discount_bps IS
    'Default supplier discount represented in basis points. 3000 means 30.00%.';
