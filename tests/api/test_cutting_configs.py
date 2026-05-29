from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from corequote_api.auth import AuthenticatedUser
from corequote_api.cutting_configs import CuttingConfigNotFound
from corequote_api.main import app
from corequote_api.routers import auth, cutting_configs


client = TestClient(app)
NOW = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)


class FakeAuthStore:
    def __init__(self, *, role: str = "owner"):
        self.user = AuthenticatedUser(
            id="user-1",
            company_id="company-1",
            company_name="Core Cabinets",
            name="Dylan Payne",
            email="dylan@example.com",
            role=role,
        )

    def get_user_for_token(self, token: str) -> AuthenticatedUser | None:
        if token == "test-token":
            return self.user
        return None


class FakeCuttingConfigStore:
    def __init__(self):
        self.created_unit_config_payload: tuple[str, dict] | None = None
        self.updated_unit_config_payload: tuple[str, str, dict] | None = None
        self.created_payload: tuple[str, dict] | None = None
        self.updated_payload: tuple[str, str, dict] | None = None
        self.list_rulesets_filter: tuple[str, str | None, bool] | None = None

    def list_unit_configs(self, company_id: str, include_archived: bool = False):
        return [
            unit_config("global-base-door", company_id=None, unit_type_key="Base 2 Door", is_default=True),
            unit_config("company-base-door", company_id=company_id, unit_type_key="Base 2 Door", label="Company Base Door"),
        ]

    def get_unit_config(self, company_id: str, unit_config_id: str):
        if unit_config_id == "missing":
            raise CuttingConfigNotFound()
        return unit_config(unit_config_id, company_id=None, is_default=True)

    def create_unit_config(self, company_id: str, payload: dict):
        self.created_unit_config_payload = (company_id, payload)
        return unit_config("created-unit-config", company_id=company_id, unit_type_key=payload["unit_type_key"], label=payload["label"])

    def update_unit_config(self, company_id: str, unit_config_id: str, payload: dict):
        self.updated_unit_config_payload = (company_id, unit_config_id, payload)
        return unit_config(unit_config_id, company_id=company_id, unit_type_key=payload["unit_type_key"], label=payload["label"])

    def list_rulesets(self, company_id: str, unit_type_key: str | None = None, include_archived: bool = False):
        self.list_rulesets_filter = (company_id, unit_type_key, include_archived)
        return [
            ruleset("global-ruleset", company_id=None, unit_type_key=unit_type_key or "Base 2 Door", include_rows=False),
            ruleset("company-ruleset", company_id=company_id, unit_type_key=unit_type_key or "Base 2 Door", include_rows=False),
        ]

    def get_ruleset(self, company_id: str, ruleset_id: str):
        if ruleset_id == "missing":
            raise CuttingConfigNotFound()
        return ruleset(ruleset_id, company_id=company_id, include_rows=True)

    def create_ruleset(self, company_id: str, payload: dict):
        self.created_payload = (company_id, payload)
        return ruleset("created-ruleset", company_id=company_id, unit_type_key=payload["unit_type_key"], include_rows=True)

    def update_ruleset(self, company_id: str, ruleset_id: str, payload: dict):
        self.updated_payload = (company_id, ruleset_id, payload)
        return ruleset(ruleset_id, company_id=company_id, unit_type_key=payload["unit_type_key"], include_rows=True)


def test_unit_configs_list_includes_global_and_company_visible_configs():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    try:
        response = client.get("/api/v1/cutting/unit-configs", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [row["id"] for row in body] == ["global-base-door", "company-base-door"]
    assert body[0]["company_id"] is None
    assert body[1]["company_id"] == "company-1"
    assert body[0]["variant_config"]["num_doors"] == 2


def test_ruleset_detail_returns_rows_with_inline_edge_flags():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    try:
        response = client.get("/api/v1/cutting/rulesets/company-ruleset", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["rows"][0]["description"] == "Door"
    assert body["rows"][0]["edge_long_1"] is True
    assert body["rows"][0]["edge_short_2"] is True


def test_create_ruleset_requires_cutlist_write_and_passes_frontend_payload():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    payload = ruleset_payload()
    try:
        response = client.post("/api/v1/cutting/rulesets", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert store.created_payload == ("company-1", payload)
    assert response.json()["company_id"] == "company-1"


def test_create_unit_config_requires_cutlist_write_and_passes_payload():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    payload = unit_config_payload(unit_type_key="Combined Door Drawer", label="Combined Door Drawer")
    try:
        response = client.post("/api/v1/cutting/unit-configs", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert store.created_unit_config_payload == ("company-1", payload)
    assert response.json()["unit_type_key"] == "Combined Door Drawer"


def test_update_unit_config_replaces_company_owned_shape():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    payload = unit_config_payload(unit_type_key="Custom Wall Unit", label="Custom Wall Unit")
    try:
        response = client.patch("/api/v1/cutting/unit-configs/company-unit-config", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.updated_unit_config_payload == ("company-1", "company-unit-config", payload)


def test_update_ruleset_replaces_rows_for_grid_saves():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    payload = ruleset_payload(name="Edited Base Door")
    try:
        response = client.patch("/api/v1/cutting/rulesets/company-ruleset", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.updated_payload == ("company-1", "company-ruleset", payload)


def test_viewer_cannot_create_ruleset():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    try:
        response = client.post("/api/v1/cutting/rulesets", json=ruleset_payload(), headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: cutlists:write"}


def test_viewer_cannot_create_unit_config():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    try:
        response = client.post("/api/v1/cutting/unit-configs", json=unit_config_payload(), headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: cutlists:write"}


def test_ruleset_list_supports_unit_type_filter_for_frontend_tabs():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    try:
        response = client.get(
            "/api/v1/cutting/rulesets?unit_type_key=Base%202%20Door&include_archived=true",
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.list_rulesets_filter == ("company-1", "Base 2 Door", True)
    assert "rows" not in response.json()[0]


def test_missing_ruleset_returns_404():
    store = FakeCuttingConfigStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[cutting_configs.get_cutting_config_store] = lambda: store
    try:
        response = client.get("/api/v1/cutting/rulesets/missing", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def unit_config(
    item_id: str,
    *,
    company_id: str | None,
    unit_type_key: str = "Base 2 Door",
    label: str = "Base 2 Door",
    is_default: bool = False,
) -> dict:
    return {
        "id": item_id,
        "company_id": company_id,
        "unit_type_key": unit_type_key,
        "label": label,
        "category": "base",
        "variant_type": "door",
        "version": 1,
        "status": "active",
        "is_default": is_default,
        "variant_config": {"num_doors": 2, "default_shelves": 1, "shelf_setback": 20, "panel_gap_mm": 3},
        "default_height": 780,
        "default_width": 600,
        "default_depth": 580,
        "height_min": 300,
        "height_max": 2400,
        "width_min": 150,
        "width_max": 1200,
        "depth_min": 150,
        "depth_max": 700,
        "created_at": NOW,
        "updated_at": NOW,
    }


def ruleset(
    item_id: str,
    *,
    company_id: str | None,
    unit_type_key: str = "Base 2 Door",
    include_rows: bool,
) -> dict:
    result = {
        "id": item_id,
        "company_id": company_id,
        "unit_config_id": "unit-config-1",
        "unit_type_key": unit_type_key,
        "name": "Company Base Door",
        "description": "Door rules",
        "status": "draft",
        "version": 1,
        "is_default": False,
        "created_at": NOW,
        "updated_at": NOW,
    }
    if include_rows:
        result["rows"] = [
            {
                "id": "row-1",
                "sort_order": 10,
                "section": "panel",
                "description": "Door",
                "length_formula": "h - panel_gap_mm",
                "width_formula": "(w / num_doors) - panel_gap_mm",
                "qty_formula": "num_doors",
                "condition_formula": "num_doors > 0",
                "grain_direction": "length",
                "can_rotate": False,
                "edge_long_1": True,
                "edge_long_2": True,
                "edge_short_1": True,
                "edge_short_2": True,
                "meta": {},
                "created_at": NOW,
                "updated_at": NOW,
            }
        ]
    return result


def ruleset_payload(*, name: str = "Company Base Door") -> dict:
    return {
        "unit_config_id": "unit-config-1",
        "unit_type_key": "Base 2 Door",
        "name": name,
        "description": "Door rules",
        "status": "draft",
        "version": 1,
        "is_default": False,
        "rows": [
            {
                "sort_order": 10,
                "section": "panel",
                "description": "Door",
                "length_formula": "h - panel_gap_mm",
                "width_formula": "(w / num_doors) - panel_gap_mm",
                "qty_formula": "num_doors",
                "condition_formula": "num_doors > 0",
                "grain_direction": "length",
                "can_rotate": False,
                "edge_long_1": True,
                "edge_long_2": True,
                "edge_short_1": True,
                "edge_short_2": True,
                "meta": {},
            }
        ],
    }


def unit_config_payload(*, unit_type_key: str = "Custom Unit", label: str = "Custom Unit") -> dict:
    return {
        "unit_type_key": unit_type_key,
        "label": label,
        "category": "custom",
        "variant_type": "custom",
        "version": 1,
        "status": "active",
        "is_default": False,
        "variant_config": {"panel_gap_mm": 3},
        "default_height": 780,
        "default_width": 600,
        "default_depth": 560,
        "height_min": 300,
        "height_max": 2400,
        "width_min": 150,
        "width_max": 1200,
        "depth_min": 150,
        "depth_max": 700,
    }


def auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}
