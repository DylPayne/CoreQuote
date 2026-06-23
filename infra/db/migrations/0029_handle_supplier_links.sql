ALTER TABLE handles
    ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL;

UPDATE handles h
SET supplier_id = s.id
FROM suppliers s
WHERE h.supplier_id IS NULL
  AND h.company_id = s.company_id
  AND trim(h.supplier) <> ''
  AND lower(trim(h.supplier)) = lower(trim(s.name));

ALTER TABLE handles
    DROP CONSTRAINT IF EXISTS handles_company_id_name_supplier_code_key;

CREATE INDEX IF NOT EXISTS handles_supplier_id_idx ON handles(supplier_id);

CREATE UNIQUE INDEX IF NOT EXISTS handles_company_name_supplier_idx
    ON handles(company_id, name, COALESCE(supplier_id, '00000000-0000-0000-0000-000000000000'::uuid));

ALTER TABLE handles
    DROP COLUMN IF EXISTS supplier,
    DROP COLUMN IF EXISTS code;

COMMENT ON COLUMN handles.supplier_id IS 'Optional company-scoped supplier relationship for this handle/profile. Supplier SKUs live in item_suppliers.';
