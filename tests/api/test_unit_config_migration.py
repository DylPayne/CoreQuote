from pathlib import Path


MIGRATION_0005 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0005_unit_configs_cutting_rulesets.sql"
MIGRATION_0006 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0006_inline_cutting_rule_edges.sql"
MIGRATION_0020 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0020_production_metadata.sql"
MIGRATION_0021 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0021_board_type_grain_policy.sql"
MIGRATION_0022 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0022_one_active_company_cutting_ruleset.sql"
MIGRATION_0030 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0030_wall_front_overhang_defaults.sql"
MIGRATION_0007 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0007_simplify_default_unit_types.sql"
MIGRATION_0008 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0008_cutting_ruleset_history.sql"
MIGRATION_0017 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0017_default_non_drawer_cutting_formulas.sql"


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


def test_production_metadata_migration_is_postgres_jsonb_and_company_scoped_sources():
    sql = MIGRATION_0020.read_text()

    assert "ALTER TABLE quotes" in sql
    assert "ADD COLUMN IF NOT EXISTS production_metadata JSONB NOT NULL DEFAULT '{}'::jsonb" in sql
    assert "ALTER TABLE quote_units" in sql
    assert "CHECK (jsonb_typeof(production_metadata) = 'object')" in sql
    assert "Quote-scoped workshop production instructions by material role" in sql
    assert "Unit-scoped workshop production instruction overrides by material role" in sql


def test_wall_front_overhang_default_migration_is_quote_scoped_jsonb():
    sql = MIGRATION_0030.read_text()

    assert "ALTER TABLE quotes" in sql
    assert "ADD COLUMN IF NOT EXISTS wall_front_overhang_default JSONB NOT NULL DEFAULT" in sql
    assert '"enabled":false' in sql
    assert '"amount_mm":20' in sql
    assert '"edge":"bottom"' in sql
    assert "CHECK (jsonb_typeof(wall_front_overhang_default) = 'object')" in sql
    assert "Quote-level default for handle-free wall-unit front overhang geometry" in sql


def test_board_type_grain_policy_migration_defaults_existing_boards_to_required():
    sql = MIGRATION_0021.read_text()

    assert "ALTER TABLE board_types" in sql
    assert "ADD COLUMN IF NOT EXISTS grain_policy TEXT NOT NULL DEFAULT 'required'" in sql
    assert "CHECK (grain_policy IN ('none', 'optional', 'required'))" in sql
    assert "Controls whether workshop grain direction applies to this board type" in sql


def test_company_ruleset_activation_migration_limits_one_active_ruleset_per_type():
    sql = MIGRATION_0022.read_text()

    assert "ROW_NUMBER() OVER" in sql
    assert "PARTITION BY company_id, unit_type_key" in sql
    assert "SET status = 'archived'" in sql
    assert "cutting_rulesets_one_active_company_key_idx" in sql
    assert "WHERE company_id IS NOT NULL AND status = 'active'" in sql


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


def test_default_non_drawer_formula_migration_matches_spreadsheet_defaults():
    sql = MIGRATION_0017.read_text()

    assert "'Base Draw'" not in sql
    assert "variant_config = unit_configs.variant_config || desired_defaults.variant_config_patch" in sql
    assert "('Wall Door'::text, '{\"default_shelves\":2}'::jsonb)" in sql
    assert "('Tall Door'::text, '{\"default_shelves\":5}'::jsonb)" in sql
    assert "('Wall Door'::text, 20, 'carcass', 'Base', 'w', 'd', '1', '')" in sql
    assert "('Wall Door'::text, 30, 'carcass', 'Top', 'w', 'd', '1', '')" in sql
    assert "('Wall Door'::text, 100, 'panel', 'Door', 'h - panel_gap_mm + 20', '(w / num_doors) - panel_gap_mm', 'num_doors', 'num_doors > 0')" in sql
    assert "('Tall Door'::text, 30, 'carcass', 'Top', 'w', 'd', '1', '')" in sql
