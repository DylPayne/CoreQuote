from pathlib import Path


MIGRATION_0019 = Path(__file__).resolve().parents[2] / "infra" / "db" / "migrations" / "0019_effective_pricing_indexes.sql"


def test_effective_pricing_migration_adds_lookup_indexes_and_comments():
    sql = MIGRATION_0019.read_text()

    assert "price_lists_active_effective_idx" in sql
    assert "price_list_items_effective_lookup_idx" in sql
    assert "supplier_item_costs_effective_lookup_idx" in sql
    assert "exclusive timestamp" in sql.lower()
    assert "sqlite" not in sql.lower()
