ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS currency_code TEXT;

UPDATE companies
SET currency_code = 'ZAR'
WHERE currency_code IS NULL
   OR btrim(currency_code) = '';

UPDATE companies
SET currency_code = upper(btrim(currency_code));

ALTER TABLE companies
    ALTER COLUMN currency_code SET DEFAULT 'ZAR',
    ALTER COLUMN currency_code SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'companies_currency_code_check'
          AND conrelid = 'companies'::regclass
    ) THEN
        ALTER TABLE companies
            ADD CONSTRAINT companies_currency_code_check
            CHECK (currency_code ~ '^[A-Z]{3}$');
    END IF;
END;
$$;

COMMENT ON COLUMN companies.currency_code IS
    'ISO 4217 currency code used when displaying and editing company quote pricing.';
