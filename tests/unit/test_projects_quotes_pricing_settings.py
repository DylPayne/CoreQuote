from __future__ import annotations

from contextlib import nullcontext

from corequote_api.projects_quotes import WorkspaceStore


class _FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def transaction(self):
        return nullcontext()


class _ProjectPricingStore(WorkspaceStore):
    def __init__(self):
        super().__init__(database_url="postgresql://unused")
        self.saved_payload: dict | None = None

    def _connect(self):
        return _FakeConnection()

    def _ensure_project_visible(self, conn, company_id: str, project_id: str) -> dict:
        return {"id": project_id}

    def _get_project_pricing_settings(self, conn, company_id: str, project_id: str) -> dict[str, int]:
        return {
            "vat_rate_bps": 1700,
            "default_markup_bps": 3200,
            "carcass_markup_bps": 2500,
            "door_panel_markup_bps": 2500,
            "component_markup_bps": 2500,
            "handle_markup_bps": 2500,
            "extras_markup_bps": 2500,
            "fabrication_markup_bps": 2500,
            "install_markup_bps": 2500,
            "delivery_markup_bps": 2500,
            "joinery_commission_bps": 0,
            "labour_cents_per_m2": 2400,
            "consumables_cents_per_m2": 1000,
            "install_day_cost_cents": 210000,
            "delivery_base_cents": 95000,
            "install_units_per_day": 4,
            "delivery_units_per_trip": 20,
            "minimum_install_days_bps": 5000,
            "minimum_delivery_trips_bps": 5000,
        }

    def _upsert_project_pricing_settings(self, conn, company_id: str, project_id: str, settings: dict[str, int]) -> dict:
        self.saved_payload = settings
        return {"company_id": company_id, "project_id": project_id, **settings}


class _QuotePricingStore(WorkspaceStore):
    def __init__(self):
        super().__init__(database_url="postgresql://unused")
        self.saved_payload: dict | None = None

    def _connect(self):
        return _FakeConnection()

    def _ensure_quote_visible(self, conn, company_id: str, quote_id: str) -> dict:
        return {"id": quote_id, "project_id": "project-1"}

    def _get_quote_pricing_settings_response(self, conn, company_id: str, quote_id: str, quote: dict) -> dict:
        return {
            "company_id": company_id,
            "quote_id": quote_id,
            "vat_rate_bps": 1500,
            "default_markup_bps": 2800,
            "carcass_markup_bps": 2500,
            "door_panel_markup_bps": 2500,
            "component_markup_bps": 2500,
            "handle_markup_bps": 2500,
            "extras_markup_bps": 2500,
            "fabrication_markup_bps": 2500,
            "install_markup_bps": 2500,
            "delivery_markup_bps": 2500,
            "joinery_commission_bps": 0,
            "labour_cents_per_m2": 2000,
            "consumables_cents_per_m2": 1000,
            "install_day_cost_cents": 190000,
            "delivery_base_cents": 95000,
            "install_units_per_day": 3,
            "delivery_units_per_trip": 16,
            "minimum_install_days_bps": 5000,
            "minimum_delivery_trips_bps": 5000,
            "created_at": None,
            "updated_at": None,
        }

    def _upsert_quote_pricing_settings(self, conn, company_id: str, quote_id: str, settings: dict[str, int]) -> dict:
        self.saved_payload = settings
        return {"company_id": company_id, "quote_id": quote_id, **settings}


def test_update_project_pricing_settings_preserves_existing_values_on_partial_patch():
    store = _ProjectPricingStore()

    result = store.update_project_pricing_settings("company-1", "project-1", {"vat_rate_bps": 1550})

    assert result["vat_rate_bps"] == 1550
    assert result["default_markup_bps"] == 3200
    assert result["labour_cents_per_m2"] == 2400
    assert store.saved_payload == {
        key: value
        for key, value in result.items()
        if key not in {"company_id", "project_id"}
    }


def test_update_quote_pricing_settings_preserves_existing_values_on_partial_patch():
    store = _QuotePricingStore()

    result = store.update_quote_pricing_settings("company-1", "quote-1", {"delivery_base_cents": 125000})

    assert result["delivery_base_cents"] == 125000
    assert result["default_markup_bps"] == 2800
    assert result["delivery_units_per_trip"] == 16
    assert store.saved_payload == {
        key: value
        for key, value in result.items()
        if key not in {"company_id", "quote_id"}
    }
