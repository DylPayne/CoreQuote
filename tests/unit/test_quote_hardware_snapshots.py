from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Any

from corequote_api import projects_quotes
from corequote_api.projects_quotes import WorkspaceStore
from corequote_core.hardware_pick_list import build_hardware_pick_list


class _EmptyCursor:
    def fetchall(self) -> list[dict[str, Any]]:
        return []


class _EmptyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def transaction(self):
        return nullcontext()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _EmptyCursor:
        return _EmptyCursor()


class _StatusFreezeConnection:
    def __init__(self):
        self.update_params: tuple[Any, ...] | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def transaction(self):
        return nullcontext()

    def execute(self, sql: str, params: tuple[Any, ...] = ()):
        if "UPDATE quotes" in sql:
            self.update_params = params
        return self

    def fetchone(self) -> dict[str, Any]:
        return {"id": "quote-1"}


class _StatusFreezeStore(WorkspaceStore):
    def __init__(self, *, quote: dict[str, Any], snapshot: dict[str, Any] | None):
        super().__init__(database_url="postgresql://unused")
        self.conn = _StatusFreezeConnection()
        self.quote = quote
        self.snapshot = snapshot
        self.capture_calls = 0
        self.locked_for_update = False

    def _connect(self):
        return self.conn

    def _ensure_quote_visible(self, conn, company_id: str, quote_id: str, *, for_update: bool = False) -> dict:
        self.locked_for_update = for_update
        return self.quote

    def _list_units_for_quote(self, conn, company_id: str, quote_id: str) -> list[dict]:
        return [{"id": "unit-1", "unit_type_key": "Base Draw", "extra_params": {"num_drawers": 3}}]

    def _list_quote_extras_for_quote(self, conn, company_id: str, quote_id: str) -> list[dict]:
        return []

    def _build_hardware_catalog_snapshot(self, conn, company_id: str, quote: dict[str, Any], units: list[dict], quote_extras: list[dict]) -> dict[str, Any]:
        self.capture_calls += 1
        assert units[0]["id"] == "unit-1"
        return self.snapshot or {}

    def get_quote(self, company_id: str, quote_id: str) -> dict:
        update_params = self.conn.update_params or ("draft", None)
        wrapped_snapshot = update_params[1]
        return {
            **self.quote,
            "id": quote_id,
            "status": update_params[0],
            "hardware_catalog_snapshot": getattr(wrapped_snapshot, "obj", None),
        }


class _ProjectSnapshotStore(WorkspaceStore):
    def __init__(self, *, snapshot: dict[str, Any], live_slide: dict[str, Any]):
        super().__init__(database_url="postgresql://unused")
        self.snapshot = snapshot
        self.live_slide = live_slide

    def _connect(self):
        return _EmptyConnection()

    def get_project(self, company_id: str, project_id: str) -> dict:
        return {"id": project_id, "name": "Smith Kitchen"}

    def list_quotes(self, company_id: str, project_id: str) -> list[dict]:
        return [
            {
                "id": "quote-1",
                "name": "Smith Kitchen",
                "status": "sent",
                "quote_number": "Q-001",
                "revision": 1,
                "previous_revision_id": None,
                "previous_revision_quote_number": None,
                "previous_revision_revision": None,
                "hardware_catalog_snapshot": self.snapshot,
                "created_at": datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
                "updated_at": datetime(2026, 5, 3, 10, 0, tzinfo=UTC),
            }
        ]

    def _get_company_currency_code(self, conn, company_id: str) -> str:
        return "ZAR"

    def _get_project_pricing_settings_response(self, conn, company_id: str, project_id: str, project: dict) -> dict:
        return {"company_id": company_id, "project_id": project_id, "vat_rate_bps": 1500, "default_markup_bps": 2500}

    def _get_quote_pricing_settings_map(
        self,
        conn,
        company_id: str,
        quotes: list[dict],
        project_settings: dict,
    ) -> dict[str, dict]:
        return {
            quote["id"]: {"company_id": company_id, "quote_id": quote["id"], "vat_rate_bps": 1500, "default_markup_bps": 2500}
            for quote in quotes
        }

    def _get_active_price_list_id(self, conn, company_id: str, as_of: datetime | None = None) -> str:
        return "price-list-1"

    def _get_price_lookup(
        self,
        conn,
        company_id: str,
        price_list_id: str | None,
        as_of: datetime | None = None,
    ) -> dict[tuple[str, str, str], dict]:
        return {}

    def _load_company_item_lookups(self, conn, company_id: str) -> dict[str, dict[str, dict]]:
        return {"boards": {}, "slides": {"slide-1": self.live_slide}, "hinges": {}, "handles": {}, "extras": {}}


def test_status_freeze_captures_hardware_catalog_snapshot():
    snapshot = {
        "version": 1,
        "items": {
            "slides": [{"id": "slide-1", "brand": "Grass", "model": "Dynapro", "accessory_config": {"accessories": []}}],
            "hinges": [],
            "handles": [],
            "extras": [],
        },
    }
    store = _StatusFreezeStore(
        quote={"id": "quote-1", "status": "draft", "hardware_catalog_snapshot": None},
        snapshot=snapshot,
    )

    result = store.update_quote_status("company-1", "quote-1", "ready")

    assert store.locked_for_update is True
    assert store.capture_calls == 1
    assert store.conn.update_params is not None
    assert store.conn.update_params[0] == "ready"
    assert store.conn.update_params[1].obj == snapshot
    assert result["hardware_catalog_snapshot"] == snapshot


def test_status_draft_clears_hardware_catalog_snapshot():
    existing_snapshot = {"version": 1, "items": {"slides": [], "hinges": [], "handles": [], "extras": []}}
    store = _StatusFreezeStore(
        quote={"id": "quote-1", "status": "ready", "hardware_catalog_snapshot": existing_snapshot},
        snapshot=None,
    )

    result = store.update_quote_status("company-1", "quote-1", "draft")

    assert store.capture_calls == 0
    assert store.conn.update_params is not None
    assert store.conn.update_params[0] == "draft"
    assert store.conn.update_params[1] is None
    assert result["hardware_catalog_snapshot"] is None


def test_frozen_quote_hardware_snapshot_keeps_old_accessory_bundle():
    store = WorkspaceStore(database_url="postgresql://unused")
    snapshot = {
        "version": 1,
        "items": {
            "slides": [
                {
                    "id": "slide-1",
                    "brand": "Grass",
                    "model": "Dynapro",
                    "code": "OLD",
                    "accessory_config": {
                        "accessories": [{"item_type": "extra", "item_ref_id": "extra-lock", "quantity": 1}]
                    },
                }
            ],
            "hinges": [],
            "handles": [],
            "extras": [{"id": "extra-lock", "name": "Old locking device", "supplier": "Grass", "code": "OLD-LOCK"}],
        },
    }
    live_lookups = {
        "boards": {},
        "slides": {
            "slide-1": {
                "id": "slide-1",
                "brand": "Grass",
                "model": "Dynapro",
                "code": "NEW",
                "accessory_config": {
                    "accessories": [{"item_type": "extra", "item_ref_id": "extra-lock", "quantity": 9}]
                },
            }
        },
        "hinges": {},
        "handles": {},
        "extras": {"extra-lock": {"id": "extra-lock", "name": "New locking device", "supplier": "Grass", "code": "NEW-LOCK"}},
    }
    quote = {"status": "sent", "default_slide_id": "slide-1", "hardware_catalog_snapshot": snapshot}

    lookups = store._hardware_lookups_for_quote(quote, live_lookups)
    result = build_hardware_pick_list(
        quote=quote,
        units=[{"unit_number": 1, "unit_type_key": "Base Draw", "height": 720, "extra_params": {"num_drawers": 3}}],
        quote_extras=[],
        slide_lookup=lookups["slides"],
        hinge_lookup=lookups["hinges"],
        handle_lookup=lookups["handles"],
        extra_lookup=lookups["extras"],
    )

    items = {item["item_key"]: item for item in result["items"]}
    assert items["slide::slide-1"]["code"] == "OLD"
    assert items["extra::extra-lock"]["quantity"] == 3
    assert items["extra::extra-lock"]["code"] == "OLD-LOCK"


def test_project_pricing_routes_frozen_quotes_through_hardware_snapshot(monkeypatch):
    snapshot = {
        "version": 1,
        "items": {
            "slides": [{"id": "slide-1", "brand": "Grass", "model": "Frozen", "accessory_config": {"accessories": []}}],
            "hinges": [],
            "handles": [],
            "extras": [],
        },
    }
    live_slide = {"id": "slide-1", "brand": "Grass", "model": "Live", "accessory_config": {"accessories": []}}
    store = _ProjectSnapshotStore(snapshot=snapshot, live_slide=live_slide)
    captured: dict[str, dict[str, dict]] = {}

    def fake_price_quote(**kwargs):
        captured["slide_lookup"] = kwargs["slide_lookup"]
        return {
            "quote_id": kwargs["quote"]["id"],
            "quote_name": kwargs["quote"]["name"],
            "is_complete": True,
            "missing_items": [],
            "missing_prices": [],
            "material_summary": {},
            "hardware_pick_list": {},
            "subtotal_cents": 1000,
            "cost_total_cents": 800,
            "sell_before_vat_cents": 1000,
            "vat_cents": 150,
            "grand_total_cents": 1150,
            "profit_cents": 200,
            "bucket_totals": [],
            "lines": [],
        }

    monkeypatch.setattr(projects_quotes, "_price_quote", fake_price_quote)

    store.get_project_pricing("company-1", "project-1", runtime_service=None)

    assert captured["slide_lookup"]["slide-1"]["model"] == "Frozen"
