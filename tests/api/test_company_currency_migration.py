from pathlib import Path


MIGRATION_0012 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0012_company_currency.sql"


def test_company_currency_migration_adds_local_currency_to_companies():
    sql = MIGRATION_0012.read_text()

    assert "ADD COLUMN IF NOT EXISTS currency_code TEXT" in sql
    assert "SET currency_code = 'ZAR'" in sql
    assert "ALTER COLUMN currency_code SET DEFAULT 'ZAR'" in sql
    assert "ALTER COLUMN currency_code SET NOT NULL" in sql
    assert "companies_currency_code_check" in sql
    assert "'^[A-Z]{3}$'" in sql
    assert "sqlite" not in sql.lower()
