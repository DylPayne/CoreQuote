from pathlib import Path


MIGRATION_0005 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0005_unit_configs_cutting_rulesets.sql"
MIGRATION_0006 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0006_inline_cutting_rule_edges.sql"
MIGRATION_0007 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0007_simplify_default_unit_types.sql"
MIGRATION_0008 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0008_cutting_ruleset_history.sql"


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


def test_simplified_default_units_migration_seeds_four_core_families():
    sql = MIGRATION_0007.read_text()

    assert "'Base Draw'" in sql
    assert "'Base Door'" in sql
    assert "'Wall Door'" in sql
    assert "'Tall Door'" in sql
    assert "'Tall Pantry'" in sql  # Archived from active defaults.


def test_simplified_default_units_migration_removes_pantry_specific_formula_paths():
    sql = MIGRATION_0007.read_text()

    assert '"is_pantry"' not in sql
    assert "CASE WHEN" not in sql
    assert "'h - panel_gap_mm'" in sql


def test_ruleset_history_migration_tracks_snapshot_rows():
    sql = MIGRATION_0008.read_text()

    assert "CREATE TABLE IF NOT EXISTS cutting_ruleset_history" in sql
    assert "rows            JSONB NOT NULL DEFAULT '[]'::jsonb" in sql
    assert "snapshot_reason TEXT NOT NULL DEFAULT 'update'" in sql
