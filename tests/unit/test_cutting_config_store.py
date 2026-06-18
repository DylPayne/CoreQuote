from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from corequote_api.cutting_configs import CuttingConfigStore


class _Result:
    def __init__(self, rows: list[dict[str, Any]] | None = None):
        self.rows = rows or []

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows

    def fetchone(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None


class _CapturingConnection:
    def __init__(
        self,
        *,
        active_rulesets: list[dict[str, Any]] | None = None,
        active_unit_configs: list[dict[str, Any]] | None = None,
    ):
        self.active_unit_configs = active_unit_configs or []
        self.active_rulesets = active_rulesets or []
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> _Result:
        self.calls.append((sql, tuple(params)))
        if "SELECT" in sql and "FROM cutting_rulesets" in sql:
            return _Result(self.active_rulesets or [])
        if "SELECT" in sql and "FROM unit_configs" in sql:
            return _Result(self.active_unit_configs)
        return _Result()


class _SnapshottingStore(CuttingConfigStore):
    def __init__(self):
        super().__init__(database_url="postgresql://example")
        self.snapshots: list[tuple[dict[str, Any], str]] = []

    def _with_rows(self, conn, ruleset: dict) -> dict:
        return {**ruleset, "rows": []}

    def _snapshot_ruleset(self, conn, ruleset: dict[str, Any], snapshot_reason: str) -> None:
        self.snapshots.append((ruleset, snapshot_reason))


def test_archive_other_active_company_rulesets_snapshots_and_archives_existing_active_rulesets():
    existing_ruleset = {
        "id": "ruleset-1",
        "company_id": "company-1",
        "unit_config_id": "unit-config-1",
        "unit_type_key": "Base Door",
        "name": "Older active ruleset",
        "description": "",
        "status": "active",
        "version": 1,
        "is_default": True,
        "created_at": "2026-06-17T12:00:00Z",
        "updated_at": "2026-06-17T12:00:00Z",
    }
    conn = _CapturingConnection(active_rulesets=[existing_ruleset])
    store = _SnapshottingStore()

    store._archive_other_active_company_rulesets(
        conn,
        company_id="company-1",
        unit_type_key="Base Door",
        exclude_ruleset_id="ruleset-2",
    )

    assert store.snapshots == [({**existing_ruleset, "rows": []}, "auto_archive_for_active_ruleset")]
    update_sql, update_params = conn.calls[-1]
    assert "UPDATE cutting_rulesets" in update_sql
    assert "SET status = 'archived'" in update_sql
    assert "is_default = false" in update_sql
    assert "id <> %s" in update_sql
    assert update_params == ("company-1", "Base Door", "ruleset-2")


def test_archive_other_active_company_unit_configs_archives_existing_active_setup():
    conn = _CapturingConnection()
    store = _SnapshottingStore()

    store._archive_other_active_company_unit_configs(
        conn,
        company_id="company-1",
        unit_type_key="Base Door",
        exclude_unit_config_id="unit-config-2",
    )

    update_sql, update_params = conn.calls[-1]
    assert "UPDATE unit_configs" in update_sql
    assert "SET status = 'archived'" in update_sql
    assert "is_default = false" in update_sql
    assert "id <> %s" in update_sql
    assert update_params == ("company-1", "Base Door", "unit-config-2")


def test_ruleset_history_rows_store_config_only_without_persistence_metadata():
    row_timestamp = datetime(2026, 6, 18, 8, 0, tzinfo=UTC)

    assert CuttingConfigStore._ruleset_history_rows(
        [
            {
                "id": "row-1",
                "sort_order": 1,
                "section": "panel",
                "description": "Door",
                "length_formula": "h",
                "width_formula": "w / 2",
                "qty_formula": "num_doors",
                "condition_formula": "num_doors > 0",
                "grain_direction": "length",
                "can_rotate": False,
                "edge_long_1": True,
                "edge_long_2": False,
                "edge_short_1": True,
                "edge_short_2": False,
                "meta": {"source": "test"},
                "created_at": row_timestamp,
                "updated_at": row_timestamp,
            }
        ]
    ) == [
        {
            "sort_order": 1,
            "section": "panel",
            "description": "Door",
            "length_formula": "h",
            "width_formula": "w / 2",
            "qty_formula": "num_doors",
            "condition_formula": "num_doors > 0",
            "grain_direction": "length",
            "can_rotate": False,
            "edge_long_1": True,
            "edge_long_2": False,
            "edge_short_1": True,
            "edge_short_2": False,
            "meta": {"source": "test"},
        }
    ]
