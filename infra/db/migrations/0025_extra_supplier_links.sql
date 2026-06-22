ALTER TABLE extras
ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL;

UPDATE extras e
SET supplier_id = s.id
FROM suppliers s
WHERE e.supplier_id IS NULL
  AND e.supplier <> ''
  AND s.company_id = e.company_id
  AND lower(trim(s.name)) = lower(trim(e.supplier));

CREATE INDEX IF NOT EXISTS extras_supplier_id_idx ON extras(supplier_id);

COMMENT ON COLUMN extras.supplier_id IS 'Optional selected supplier for extra catalog rows. Null means no supplier is assigned.';
