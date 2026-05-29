from pathlib import Path


MIGRATION_0005 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0005_unit_configs_cutting_rulesets.sql"
MIGRATION_0006 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0006_inline_cutting_rule_edges.sql"


def test_unit_config_migration_is_postgres_first():
    sql = MIGRATION_0005.read_text()

    assert "JSONB" in sql
    assert "TIMESTAMPTZ" in sql
    assert "gen_random_uuid()" in sql
    assert "sqlite" not in sql.lower()


def test_unit_config_migration_supports_global_and_company_configs():
    sql = MIGRATION_0005.read_text()

    assert "company_id              UUID REFERENCES companies" in sql
    assert "WHERE company_id IS NULL" in sql
    assert "unit_configs_one_active_global_key_idx" in sql
    assert "unit_configs_one_active_company_key_idx" in sql
    assert "version                 INTEGER NOT NULL DEFAULT 1" in sql


def test_cutting_rules_store_edges_as_rule_row_columns():
    sql = MIGRATION_0005.read_text()

    assert "edge_long_1         BOOLEAN NOT NULL DEFAULT false" in sql
    assert "edge_long_2         BOOLEAN NOT NULL DEFAULT false" in sql
    assert "edge_short_1        BOOLEAN NOT NULL DEFAULT false" in sql
    assert "edge_short_2        BOOLEAN NOT NULL DEFAULT false" in sql
    assert "CREATE TABLE IF NOT EXISTS cutting_rule_row_edges" not in sql


def test_inline_edge_migration_migrates_and_removes_old_edge_table():
    sql = MIGRATION_0006.read_text()

    assert "ADD COLUMN IF NOT EXISTS edge_long_1" in sql
    assert "FROM cutting_rule_row_edges" in sql
    assert "DROP TABLE IF EXISTS cutting_rule_row_edges" in sql
