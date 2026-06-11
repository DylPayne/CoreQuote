from __future__ import annotations

from typing import Any

from corequote_api.projects_quotes import WorkspaceStore


class _Cursor:
    def __init__(self, row: dict[str, Any] | None = None):
        self.row = row or {}

    def fetchone(self) -> dict[str, Any]:
        return self.row


class _RecordingConn:
    def __init__(self):
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _Cursor:
        self.calls.append((sql, params))
        if "INSERT INTO quotes" in sql and "RETURNING id::text" in sql:
            return _Cursor({"id": "quote-copy"})
        return _Cursor()


class _RecordingStore(WorkspaceStore):
    def __init__(self):
        super().__init__(database_url="postgresql://unused")
        self.inserted_quote_pricing_settings: tuple[str, str, dict[str, int]] | None = None

    def _insert_quote_pricing_settings(self, conn, company_id: str, quote_id: str, settings: dict[str, int]) -> None:
        self.inserted_quote_pricing_settings = (company_id, quote_id, settings)


def test_insert_quote_copy_copies_payload_units_extras_and_pricing_without_source_updates():
    store = _RecordingStore()
    conn = _RecordingConn()
    source = {
        "id": "quote-source",
        "project_id": "project-1",
        "name": "Kitchen Quote",
        "notes": "Original notes",
        "default_carcass_board_type_id": "board-carcass",
        "default_door_board_type_id": "board-door",
        "default_panel_board_type_id": "board-panel",
        "default_slide_id": "slide-1",
        "default_hinge_id": "hinge-1",
        "default_base_handle_id": "handle-base",
        "default_wall_handle_id": "handle-wall",
        "default_tall_handle_id": "handle-tall",
        "default_drawer_handle_id": "handle-drawer",
        "unit_defaults": {"Base Door": {"height": 780, "depth": 580}},
        "custom_panels": {
            "presets": {"base_side_panel": {"enabled": True, "qty": 2, "board_type_id": "board-panel"}},
            "manual": [{"label": "Sink filler", "length": 720, "width": 80, "qty": 1, "board_type_id": "board-panel"}],
            "auto": {},
        },
    }
    pricing_settings = {"vat_rate_bps": 1500, "default_markup_bps": 3000}

    new_quote_id = store._insert_quote_copy(
        conn,
        company_id="company-1",
        source=source,
        name="Kitchen Quote (Copy)",
        quote_number="Q-002",
        revision=1,
        previous_revision_id=None,
        pricing_settings=pricing_settings,
    )

    assert new_quote_id == "quote-copy"
    quote_sql, quote_params = conn.calls[0]
    assert "INSERT INTO quotes" in quote_sql
    assert quote_params[:8] == (
        "company-1",
        "project-1",
        "Kitchen Quote (Copy)",
        "Original notes",
        "draft",
        "Q-002",
        1,
        None,
    )
    assert quote_params[-2].obj == source["unit_defaults"]
    assert quote_params[-1].obj == source["custom_panels"]

    unit_copy = next((call for call in conn.calls if "INSERT INTO quote_units" in call[0]), None)
    assert unit_copy is not None
    assert "FROM quote_units" in unit_copy[0]
    assert "WHERE company_id = %s" in unit_copy[0]
    assert "AND quote_id = %s" in unit_copy[0]
    assert unit_copy[1] == ("quote-copy", "company-1", "quote-source")

    extras_copy = next((call for call in conn.calls if "INSERT INTO quote_extras" in call[0]), None)
    assert extras_copy is not None
    assert "FROM quote_extras" in extras_copy[0]
    assert "WHERE company_id = %s" in extras_copy[0]
    assert "AND quote_id = %s" in extras_copy[0]
    assert extras_copy[1] == ("quote-copy", "company-1", "quote-source")

    assert store.inserted_quote_pricing_settings == ("company-1", "quote-copy", pricing_settings)
    assert all("UPDATE " not in sql for sql, _params in conn.calls)


def test_insert_quote_copy_preserves_revision_link_when_requested():
    store = _RecordingStore()
    conn = _RecordingConn()
    source = {
        "id": "quote-source",
        "project_id": "project-1",
        "name": "Kitchen Quote",
        "notes": "",
        "default_carcass_board_type_id": None,
        "default_door_board_type_id": None,
        "default_panel_board_type_id": None,
        "default_slide_id": None,
        "default_hinge_id": None,
        "default_base_handle_id": None,
        "default_wall_handle_id": None,
        "default_tall_handle_id": None,
        "default_drawer_handle_id": None,
        "unit_defaults": {},
        "custom_panels": {},
    }

    store._insert_quote_copy(
        conn,
        company_id="company-1",
        source=source,
        name="Kitchen Quote v2",
        quote_number="Q-001",
        revision=2,
        previous_revision_id="quote-source",
        pricing_settings={"vat_rate_bps": 1500},
    )

    assert conn.calls[0][1][:8] == (
        "company-1",
        "project-1",
        "Kitchen Quote v2",
        "",
        "draft",
        "Q-001",
        2,
        "quote-source",
    )
