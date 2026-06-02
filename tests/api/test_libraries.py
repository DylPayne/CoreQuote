from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from corequote_api.auth import AuthenticatedUser
from corequote_api.libraries import LibraryConflict, LibraryNotFound, LibraryValidationError
from corequote_api.main import app
from corequote_api.routers import auth, libraries


client = TestClient(app)
NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


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


class FakeLibraryStore:
    def __init__(self):
        self.deleted: list[tuple[str, str]] = []
        self.price_item_deleted: tuple[str, str, str] | None = None
        self.active_price_list_requested = False
        self.pricing_settings_payload: dict | None = None
        self.created_payload: tuple[str, dict] | None = None
        self.updated_payload: tuple[str, str, dict] | None = None
        self.price_list_payload: dict | None = None
        self.price_item_payload: tuple[str, dict] | None = None

    def list_boards(self, company_id: str):
        return [board("board-1")]

    def create_board(self, company_id: str, payload: dict):
        self.created_payload = ("boards", payload)
        return board("board-2", brand=payload["brand"])

    def get_board(self, company_id: str, item_id: str):
        if not item_id.startswith("board-"):
            raise LibraryNotFound()
        return board(item_id)

    def update_board(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("boards", item_id, payload)
        return board(item_id, brand=payload["brand"])

    def delete_board(self, company_id: str, item_id: str):
        self.deleted.append(("boards", item_id))

    def list_slides(self, company_id: str):
        return [slide("slide-1")]

    def create_slide(self, company_id: str, payload: dict):
        self.created_payload = ("slides", payload)
        return slide("slide-2", brand=payload["brand"])

    def get_slide(self, company_id: str, item_id: str):
        return slide(item_id)

    def update_slide(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("slides", item_id, payload)
        return slide(item_id, brand=payload["brand"])

    def delete_slide(self, company_id: str, item_id: str):
        self.deleted.append(("slides", item_id))

    def list_hinges(self, company_id: str):
        return [hinge("hinge-1")]

    def create_hinge(self, company_id: str, payload: dict):
        self.created_payload = ("hinges", payload)
        return hinge("hinge-2", brand=payload["brand"])

    def get_hinge(self, company_id: str, item_id: str):
        return hinge(item_id)

    def update_hinge(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("hinges", item_id, payload)
        return hinge(item_id, brand=payload["brand"])

    def delete_hinge(self, company_id: str, item_id: str):
        self.deleted.append(("hinges", item_id))

    def list_handles(self, company_id: str):
        return [handle("handle-1")]

    def create_handle(self, company_id: str, payload: dict):
        self.created_payload = ("handles", payload)
        return handle("handle-2", name=payload["name"])

    def get_handle(self, company_id: str, item_id: str):
        return handle(item_id)

    def update_handle(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("handles", item_id, payload)
        return handle(item_id, name=payload["name"])

    def delete_handle(self, company_id: str, item_id: str):
        self.deleted.append(("handles", item_id))

    def list_extra_categories(self, company_id: str):
        return [extra_category("category-1")]

    def create_extra_category(self, company_id: str, payload: dict):
        self.created_payload = ("extra-categories", payload)
        return extra_category("category-2", name=payload["name"])

    def get_extra_category(self, company_id: str, item_id: str):
        return extra_category(item_id)

    def update_extra_category(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("extra-categories", item_id, payload)
        return extra_category(item_id, name=payload["name"])

    def delete_extra_category(self, company_id: str, item_id: str):
        self.deleted.append(("extra-categories", item_id))

    def list_extras(self, company_id: str):
        return [extra("extra-1")]

    def create_extra(self, company_id: str, payload: dict):
        self.created_payload = ("extras", payload)
        return extra("extra-2", name=payload["name"])

    def get_extra(self, company_id: str, item_id: str):
        return extra(item_id)

    def update_extra(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("extras", item_id, payload)
        return extra(item_id, name=payload["name"])

    def delete_extra(self, company_id: str, item_id: str):
        self.deleted.append(("extras", item_id))

    def get_pricing_settings(self, company_id: str):
        return {
            "company_id": company_id,
            "vat_rate_bps": 1500,
            "default_markup_bps": 2500,
            "created_at": NOW,
            "updated_at": NOW,
        }

    def update_pricing_settings(self, company_id: str, payload: dict):
        self.pricing_settings_payload = payload
        return {
            "company_id": company_id,
            **payload,
            "created_at": NOW,
            "updated_at": NOW,
        }

    def list_price_lists(self, company_id: str):
        return [price_list("price-list-1")]

    def get_active_price_list(self, company_id: str):
        self.active_price_list_requested = True
        return price_list("price-list-1")

    def create_price_list(self, company_id: str, payload: dict):
        self.price_list_payload = payload
        return price_list("price-list-2", name=payload["name"], status=payload["status"])

    def get_price_list(self, company_id: str, price_list_id: str):
        return price_list(price_list_id)

    def update_price_list(self, company_id: str, price_list_id: str, payload: dict):
        self.price_list_payload = payload
        return price_list(price_list_id, name=payload["name"], status=payload["status"])

    def delete_price_list(self, company_id: str, price_list_id: str):
        self.deleted.append(("price-lists", price_list_id))

    def list_price_list_items(self, company_id: str, price_list_id: str, include_history: bool = False):
        rows = [price_item("price-item-1", price_list_id)]
        if include_history:
            rows.append(price_item("price-item-old", price_list_id, effective_to=NOW))
        return rows

    def create_price_list_item(self, company_id: str, price_list_id: str, payload: dict):
        self.price_item_payload = (price_list_id, payload)
        if not payload.get("item_key") and not payload.get("item_ref_id"):
            raise LibraryValidationError("Either item_ref_id or item_key is required")
        item_key = payload.get("item_key") or f"{payload['item_type']}::{payload['item_ref_id']}"
        return price_item(
            "price-item-2",
            price_list_id,
            item_key=item_key,
            item_ref_id=payload.get("item_ref_id"),
            item_type=payload["item_type"],
            price_component=payload["price_component"],
            uom=payload["uom"],
            unit_price_cents=payload["unit_price_cents"],
        )

    def get_price_list_item(self, company_id: str, price_list_id: str, item_id: str):
        return price_item(item_id, price_list_id)

    def update_price_list_item(self, company_id: str, price_list_id: str, item_id: str, payload: dict):
        self.price_item_payload = (price_list_id, payload)
        if not payload.get("item_key") and not payload.get("item_ref_id"):
            raise LibraryValidationError("Either item_ref_id or item_key is required")
        item_key = payload.get("item_key") or f"{payload['item_type']}::{payload['item_ref_id']}"
        return price_item(
            "price-item-3",
            price_list_id,
            item_key=item_key,
            item_ref_id=payload.get("item_ref_id"),
            item_type=payload["item_type"],
            price_component=payload["price_component"],
            uom=payload["uom"],
            unit_price_cents=payload["unit_price_cents"],
            replaces_id=item_id,
        )

    def upsert_price_list_item(self, company_id: str, price_list_id: str, payload: dict):
        self.price_item_payload = (price_list_id, payload)
        if not payload.get("item_key") and not payload.get("item_ref_id"):
            raise LibraryValidationError("Either item_ref_id or item_key is required")
        item_key = payload.get("item_key") or f"{payload['item_type']}::{payload['item_ref_id']}"
        return price_item(
            "price-item-upsert",
            price_list_id,
            item_key=item_key,
            item_ref_id=payload.get("item_ref_id"),
            item_type=payload["item_type"],
            price_component=payload["price_component"],
            uom=payload["uom"],
            unit_price_cents=payload["unit_price_cents"],
        )

    def delete_price_list_item(self, company_id: str, price_list_id: str, item_id: str):
        self.price_item_deleted = (company_id, price_list_id, item_id)


def board(item_id: str, *, brand: str = "PG Bison") -> dict:
    return {
        "id": item_id,
        "brand": brand,
        "material": "MelaWood",
        "thickness": 16,
        "length_mm": 2750,
        "width_mm": 1830,
        "costing_mode": "sheet",
        "created_at": NOW,
        "updated_at": NOW,
    }


def slide(item_id: str, *, brand: str = "Grass") -> dict:
    return {
        "id": item_id,
        "brand": brand,
        "model": "Dynapro",
        "code": "DYN-500",
        "length": 500,
        "side_length": 500,
        "side_clearance_total": 26,
        "side_height_uplift": 0,
        "created_at": NOW,
        "updated_at": NOW,
    }


def hinge(item_id: str, *, brand: str = "Blum") -> dict:
    return {
        "id": item_id,
        "brand": brand,
        "model": "Clip Top",
        "code": "BL-110",
        "opening_angle_deg": 110,
        "created_at": NOW,
        "updated_at": NOW,
    }


def handle(item_id: str, *, name: str = "Slim Bar") -> dict:
    return {
        "id": item_id,
        "name": name,
        "supplier": "Hafele",
        "code": "HB-160",
        "created_at": NOW,
        "updated_at": NOW,
    }


def extra_category(item_id: str, *, name: str = "Appliances") -> dict:
    return {"id": item_id, "name": name, "created_at": NOW, "updated_at": NOW}


def extra(item_id: str, *, name: str = "Stove") -> dict:
    return {
        "id": item_id,
        "name": name,
        "category_id": "category-1",
        "category_name": "Appliances",
        "supplier": "Defy",
        "code": "DFY-600",
        "notes": "",
        "created_at": NOW,
        "updated_at": NOW,
    }


def price_list(item_id: str, *, name: str = "Default Price List", status: str = "active") -> dict:
    return {
        "id": item_id,
        "name": name,
        "status": status,
        "effective_from": None,
        "effective_to": None,
        "created_at": NOW,
        "updated_at": NOW,
    }


def price_item(
    item_id: str,
    price_list_id: str,
    *,
    item_key: str = "slide::Grass::Dynapro::DYN-500::500",
    item_ref_id: str | None = None,
    item_type: str = "slide",
    price_component: str = "unit",
    uom: str = "pairs",
    unit_price_cents: int = 12500,
    effective_to: datetime | None = None,
    replaces_id: str | None = None,
) -> dict:
    return {
        "id": item_id,
        "price_list_id": price_list_id,
        "item_type": item_type,
        "item_ref_id": item_ref_id,
        "item_key": item_key,
        "price_component": price_component,
        "uom": uom,
        "unit_price_cents": unit_price_cents,
        "effective_from": NOW,
        "effective_to": effective_to,
        "replaces_id": replaces_id,
        "is_active": effective_to is None,
        "created_at": NOW,
        "updated_at": NOW,
    }


CATALOG_CASES = [
    (
        "boards",
        {"brand": "Sonae", "material": "MDF", "thickness": 18, "length_mm": 2440, "width_mm": 1220, "costing_mode": "sqm"},
        "brand",
        "Sonae",
    ),
    (
        "slides",
        {
            "brand": "Blum",
            "model": "Movento",
            "code": "MOV-500",
            "length": 500,
            "side_length": 500,
            "side_clearance_total": 26,
            "side_height_uplift": 0,
        },
        "brand",
        "Blum",
    ),
    (
        "hinges",
        {"brand": "Hettich", "model": "Sensys", "code": "HS-110", "opening_angle_deg": 110},
        "brand",
        "Hettich",
    ),
    ("handles", {"name": "Cup Pull", "supplier": "Hafele", "code": "CP-96"}, "name", "Cup Pull"),
    ("extra-categories", {"name": "Lighting"}, "name", "Lighting"),
    (
        "extras",
        {"name": "LED Strip", "category_id": "category-1", "supplier": "Veti", "code": "LED-5M", "notes": "Warm white"},
        "name",
        "LED Strip",
    ),
]


@pytest.mark.parametrize(("resource", "payload", "field", "value"), CATALOG_CASES)
def test_catalog_library_crud(resource: str, payload: dict, field: str, value: str):
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        list_response = client.get(f"/api/v1/libraries/{resource}", headers=auth_header())
        create_response = client.post(f"/api/v1/libraries/{resource}", json=payload, headers=auth_header())
        created_id = create_response.json()["id"]
        get_response = client.get(f"/api/v1/libraries/{resource}/{created_id}", headers=auth_header())
        patch_response = client.patch(f"/api/v1/libraries/{resource}/{created_id}", json=payload, headers=auth_header())
        delete_response = client.delete(f"/api/v1/libraries/{resource}/{created_id}", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert create_response.status_code == 201
    assert create_response.json()[field] == value
    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()[field] == value
    assert delete_response.status_code == 204
    assert store.deleted[-1] == (resource, created_id)


def test_catalog_write_requires_catalog_write_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/libraries/handles",
            json={"name": "Cup Pull", "supplier": "Hafele", "code": "CP-96"},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: catalog:write"}


def test_catalog_get_returns_404_when_row_is_not_visible():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get("/api/v1/libraries/boards/missing-board", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_price_list_crud_requires_pricing_permissions():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {"name": "Trade 2026", "status": "draft", "effective_from": None, "effective_to": None}
    try:
        list_response = client.get("/api/v1/libraries/price-lists", headers=auth_header())
        create_response = client.post("/api/v1/libraries/price-lists", json=payload, headers=auth_header())
        price_list_id = create_response.json()["id"]
        get_response = client.get(f"/api/v1/libraries/price-lists/{price_list_id}", headers=auth_header())
        patch_response = client.patch(
            f"/api/v1/libraries/price-lists/{price_list_id}",
            json={"name": "Trade 2026 Active", "status": "active", "effective_from": None, "effective_to": None},
            headers=auth_header(),
        )
        delete_response = client.delete(f"/api/v1/libraries/price-lists/{price_list_id}", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert create_response.status_code == 201
    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "active"
    assert delete_response.status_code == 204
    assert store.deleted[-1] == ("price-lists", price_list_id)


def test_get_active_price_list():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get("/api/v1/libraries/price-lists/active", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == "price-list-1"
    assert store.active_price_list_requested


def test_estimator_cannot_update_price_lists():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/libraries/price-lists",
            json={"name": "Trade 2026", "status": "draft"},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}


def test_pricing_settings_read_and_update():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        read_response = client.get("/api/v1/libraries/pricing-settings", headers=auth_header())
        update_response = client.patch(
            "/api/v1/libraries/pricing-settings",
            json={"vat_rate_bps": 1550, "default_markup_bps": 3000},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert read_response.status_code == 200
    assert read_response.json()["vat_rate_bps"] == 1500
    assert update_response.status_code == 200
    assert update_response.json()["vat_rate_bps"] == 1550
    assert update_response.json()["default_markup_bps"] == 3000
    assert store.pricing_settings_payload["vat_rate_bps"] == 1550
    assert store.pricing_settings_payload["default_markup_bps"] == 3000
    assert store.pricing_settings_payload["carcass_markup_bps"] == 2500


def test_pricing_settings_update_requires_pricing_update_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/libraries/pricing-settings",
            json={"vat_rate_bps": 1550, "default_markup_bps": 3000},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}


def test_price_list_item_crud():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "slide",
        "item_ref_id": None,
        "item_key": "slide::Blum::Movento::MOV-500::500",
        "price_component": "unit",
        "uom": "pairs",
        "unit_price_cents": 14500,
    }
    try:
        list_response = client.get("/api/v1/libraries/price-lists/price-list-1/items", headers=auth_header())
        history_response = client.get(
            "/api/v1/libraries/price-lists/price-list-1/items?include_history=true",
            headers=auth_header(),
        )
        create_response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items",
            json=payload,
            headers=auth_header(),
        )
        item_id = create_response.json()["id"]
        get_response = client.get(f"/api/v1/libraries/price-lists/price-list-1/items/{item_id}", headers=auth_header())
        patch_response = client.patch(
            f"/api/v1/libraries/price-lists/price-list-1/items/{item_id}",
            json={**payload, "unit_price_cents": 15500},
            headers=auth_header(),
        )
        delete_response = client.delete(
            f"/api/v1/libraries/price-lists/price-list-1/items/{item_id}",
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert [row["is_active"] for row in list_response.json()] == [True]
    assert len(history_response.json()) == 2
    assert create_response.status_code == 201
    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["unit_price_cents"] == 15500
    assert patch_response.json()["id"] != item_id
    assert patch_response.json()["replaces_id"] == item_id
    assert patch_response.json()["is_active"] is True
    assert delete_response.status_code == 204
    assert store.price_item_deleted == ("company-1", "price-list-1", item_id)


def test_price_list_item_upsert_with_item_ref_id():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "board",
        "item_ref_id": "board-1",
        "price_component": "sheet",
        "uom": "sheet",
        "unit_price_cents": 359900,
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items/upsert",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item_key"] == "board::board-1"
    assert response.json()["item_ref_id"] == "board-1"
    assert response.json()["price_component"] == "sheet"
    assert store.price_item_payload == ("price-list-1", {**payload, "effective_from": None, "item_key": None})


def test_price_list_item_create_with_item_ref_id():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "extra",
        "item_ref_id": "extra-1",
        "price_component": "unit",
        "uom": "pcs",
        "unit_price_cents": 9900,
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["item_key"] == "extra::extra-1"
    assert response.json()["item_ref_id"] == "extra-1"
    assert store.price_item_payload == ("price-list-1", {**payload, "effective_from": None, "item_key": None})


def test_price_list_item_write_rejects_missing_item_identity():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "slide",
        "price_component": "unit",
        "uom": "pairs",
        "unit_price_cents": 14900,
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Either item_ref_id or item_key is required"}


def auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}
