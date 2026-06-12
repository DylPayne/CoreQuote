from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Any

from corequote_api import projects_quotes
from corequote_api.projects_quotes import WorkspaceStore, _quote_pricing_as_of


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


class _ProjectHistoryStore(WorkspaceStore):
    def __init__(self):
        super().__init__(database_url="postgresql://unused")
        self.active_price_calls: list[tuple[str, datetime | None]] = []
        self.price_lookup_calls: list[tuple[str | None, datetime | None]] = []

    def _connect(self):
        return _EmptyConnection()

    def get_project(self, company_id: str, project_id: str) -> dict:
        return {"id": project_id, "name": "Smith Kitchen"}

    def list_quotes(self, company_id: str, project_id: str) -> list[dict]:
        return [
            {
                "id": "quote-old",
                "name": "Smith Kitchen v1",
                "status": "sent",
                "quote_number": "Q-001",
                "revision": 1,
                "previous_revision_id": None,
                "previous_revision_quote_number": None,
                "previous_revision_revision": None,
                "created_at": datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
                "updated_at": datetime(2026, 5, 3, 10, 0, tzinfo=UTC),
            },
            {
                "id": "quote-new",
                "name": "Smith Kitchen v2",
                "status": "draft",
                "quote_number": "Q-001",
                "revision": 2,
                "previous_revision_id": "quote-old",
                "previous_revision_quote_number": "Q-001",
                "previous_revision_revision": 1,
                "created_at": datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
                "updated_at": datetime(2026, 6, 4, 10, 0, tzinfo=UTC),
            },
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
        self.active_price_calls.append((company_id, as_of))
        return "price-current" if as_of is None else f"price-{as_of.date().isoformat()}"

    def _get_price_lookup(
        self,
        conn,
        company_id: str,
        price_list_id: str | None,
        as_of: datetime | None = None,
    ) -> dict[tuple[str, str, str], dict]:
        self.price_lookup_calls.append((price_list_id, as_of))
        return {}

    def _load_company_item_lookups(self, conn, company_id: str) -> dict[str, dict[str, dict]]:
        return {"boards": {}, "slides": {}, "hinges": {}, "handles": {}, "extras": {}}


def test_project_pricing_uses_each_quote_timestamp_for_price_history(monkeypatch):
    store = _ProjectHistoryStore()

    def fake_price_quote(**kwargs):
        quote = kwargs["quote"]
        return {
            "quote_id": quote["id"],
            "quote_name": quote["name"],
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

    result = store.get_project_pricing("company-1", "project-1", runtime_service=None)

    old_as_of = datetime(2026, 5, 3, 10, 0, tzinfo=UTC)
    new_as_of = datetime(2026, 6, 4, 10, 0, tzinfo=UTC)
    assert store.active_price_calls == [
        ("company-1", None),
        ("company-1", old_as_of),
        ("company-1", new_as_of),
    ]
    assert store.price_lookup_calls == [
        ("price-2026-05-03", old_as_of),
        ("price-2026-06-04", new_as_of),
    ]
    assert [row["active_price_list_id"] for row in result["quotes"]] == [
        "price-2026-05-03",
        "price-2026-06-04",
    ]
    assert [row["pricing_as_of"] for row in result["quotes"]] == [old_as_of, new_as_of]


def test_quote_pricing_as_of_falls_back_to_created_at():
    created_at = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)

    assert _quote_pricing_as_of({"created_at": created_at, "updated_at": None}) == created_at
