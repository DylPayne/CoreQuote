from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from corequote_api.auth import AuthenticatedUser
from corequote_api.main import app
from corequote_api.projects_quotes import WorkspaceNotFound
from corequote_api.routers import auth, projects_quotes


client = TestClient(app)
NOW = datetime(2026, 6, 1, 10, 30, tzinfo=UTC)


class FakeAuthStore:
    def __init__(self, *, role: str = "owner"):
        self.user = AuthenticatedUser(
            id="user-1",
            company_id="company-1",
            company_name="CoreQuote Test Co",
            name="Test Owner",
            email="test.owner@corequote.local",
            role=role,
        )

    def get_user_for_token(self, token: str) -> AuthenticatedUser | None:
        if token == "test-token":
            return self.user
        return None


class FakeWorkspaceStore:
    def __init__(self):
        self.created_project_payload: tuple[str, dict] | None = None
        self.updated_project_payload: tuple[str, str, dict] | None = None
        self.deleted_project: tuple[str, str] | None = None
        self.created_quote_payload: tuple[str, str, dict] | None = None
        self.updated_quote_payload: tuple[str, str, dict] | None = None
        self.deleted_quote: tuple[str, str] | None = None
        self.created_unit_payload: tuple[str, str, dict] | None = None
        self.updated_unit_payload: tuple[str, str, str, dict] | None = None
        self.deleted_unit: tuple[str, str, str] | None = None
        self.replaced_quote_extras_payload: tuple[str, str, list[dict]] | None = None
        self.replaced_quote_custom_panels_payload: tuple[str, str, dict] | None = None
        self.requested_cutting_list: tuple[str, str] | None = None
        self.requested_quote_custom_panels: tuple[str, str] | None = None
        self.requested_project_pricing: tuple[str, str] | None = None
        self.requested_project_pricing_settings: tuple[str, str] | None = None
        self.updated_project_pricing_settings_payload: tuple[str, str, dict] | None = None
        self.requested_quote_pricing_settings: tuple[str, str] | None = None
        self.updated_quote_pricing_settings_payload: tuple[str, str, dict] | None = None

    def list_projects(self, company_id: str, search: str | None = None) -> list[dict]:
        return [project("project-1", quote_count=2)]

    def create_project(self, company_id: str, payload: dict) -> dict:
        self.created_project_payload = (company_id, payload)
        return project("project-2", name=payload["name"], quote_count=0)

    def get_project(self, company_id: str, project_id: str) -> dict:
        if project_id == "missing":
            raise WorkspaceNotFound("Project not found")
        return project(project_id, quote_count=1)

    def update_project(self, company_id: str, project_id: str, payload: dict) -> dict:
        if project_id == "missing":
            raise WorkspaceNotFound("Project not found")
        self.updated_project_payload = (company_id, project_id, payload)
        return project(project_id, name=payload["name"], quote_count=1)

    def delete_project(self, company_id: str, project_id: str) -> None:
        if project_id == "missing":
            raise WorkspaceNotFound("Project not found")
        self.deleted_project = (company_id, project_id)

    def list_quotes(self, company_id: str, project_id: str) -> list[dict]:
        if project_id == "missing":
            raise WorkspaceNotFound("Project not found")
        return [quote("quote-1", project_id=project_id, unit_count=3)]

    def create_quote(self, company_id: str, project_id: str, payload: dict) -> dict:
        if project_id == "missing":
            raise WorkspaceNotFound("Project not found")
        self.created_quote_payload = (company_id, project_id, payload)
        return quote("quote-2", project_id=project_id, name=payload["name"], notes=payload.get("notes", ""), unit_count=0)

    def get_quote(self, company_id: str, quote_id: str) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        return quote(quote_id, project_id="project-1", unit_count=2)

    def update_quote(self, company_id: str, quote_id: str, payload: dict) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.updated_quote_payload = (company_id, quote_id, payload)
        return quote(quote_id, project_id="project-1", name=payload["name"], notes=payload.get("notes", ""), unit_count=2)

    def delete_quote(self, company_id: str, quote_id: str) -> None:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.deleted_quote = (company_id, quote_id)

    def list_units(self, company_id: str, quote_id: str) -> list[dict]:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        return [unit("unit-1", quote_id=quote_id, unit_number=1)]

    def create_unit(self, company_id: str, quote_id: str, payload: dict) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.created_unit_payload = (company_id, quote_id, payload)
        return unit(
            "unit-2",
            quote_id=quote_id,
            unit_number=2,
            unit_type_key=payload["unit_type_key"],
            width=payload["width"],
            height=payload["height"],
            depth=payload["depth"],
            thickness=payload["thickness"],
            carcass_board_type_id=payload.get("carcass_board_type_id"),
            door_board_type_id=payload.get("door_board_type_id"),
            extra_params=payload.get("extra_params", {}),
        )

    def update_unit(self, company_id: str, quote_id: str, unit_id: str, payload: dict) -> dict:
        if quote_id == "missing" or unit_id == "missing":
            raise WorkspaceNotFound("Unit not found")
        self.updated_unit_payload = (company_id, quote_id, unit_id, payload)
        return unit(
            unit_id,
            quote_id=quote_id,
            unit_number=1,
            unit_type_key=payload["unit_type_key"],
            width=payload["width"],
            height=payload["height"],
            depth=payload["depth"],
            thickness=payload["thickness"],
            carcass_board_type_id=payload.get("carcass_board_type_id"),
            door_board_type_id=payload.get("door_board_type_id"),
            extra_params=payload.get("extra_params", {}),
        )

    def delete_unit(self, company_id: str, quote_id: str, unit_id: str) -> None:
        if quote_id == "missing" or unit_id == "missing":
            raise WorkspaceNotFound("Unit not found")
        self.deleted_unit = (company_id, quote_id, unit_id)

    def get_quote_cutting_list(self, company_id: str, quote_id: str, runtime_service=None) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.requested_cutting_list = (company_id, quote_id)
        return quote_cutting_list(quote_id)

    def list_quote_extras(self, company_id: str, quote_id: str) -> list[dict]:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        return [
            {"extra_id": "extra-1", "quantity": 2},
            {"extra_id": "extra-2", "quantity": 1},
        ]

    def replace_quote_extras(self, company_id: str, quote_id: str, items: list[dict]) -> list[dict]:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.replaced_quote_extras_payload = (company_id, quote_id, items)
        return items

    def get_quote_custom_panels(self, company_id: str, quote_id: str) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.requested_quote_custom_panels = (company_id, quote_id)
        return quote_custom_panels_response(quote_id)

    def replace_quote_custom_panels(self, company_id: str, quote_id: str, payload: dict) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.replaced_quote_custom_panels_payload = (company_id, quote_id, payload)
        return {
            "quote_id": quote_id,
            "custom_panels": payload,
            "computed_rows": quote_custom_panels_response(quote_id)["computed_rows"],
        }

    def get_project_pricing(self, company_id: str, project_id: str, runtime_service=None) -> dict:
        if project_id == "missing":
            raise WorkspaceNotFound("Project not found")
        self.requested_project_pricing = (company_id, project_id)
        return project_pricing(project_id)

    def get_project_pricing_settings(self, company_id: str, project_id: str) -> dict:
        if project_id == "missing":
            raise WorkspaceNotFound("Project not found")
        self.requested_project_pricing_settings = (company_id, project_id)
        return pricing_settings(project_id=project_id)

    def update_project_pricing_settings(self, company_id: str, project_id: str, payload: dict) -> dict:
        if project_id == "missing":
            raise WorkspaceNotFound("Project not found")
        self.updated_project_pricing_settings_payload = (company_id, project_id, payload)
        return pricing_settings(project_id=project_id, **payload)

    def get_quote_pricing_settings(self, company_id: str, quote_id: str) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.requested_quote_pricing_settings = (company_id, quote_id)
        return pricing_settings(quote_id=quote_id)

    def update_quote_pricing_settings(self, company_id: str, quote_id: str, payload: dict) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.updated_quote_pricing_settings_payload = (company_id, quote_id, payload)
        return pricing_settings(quote_id=quote_id, **payload)


def test_list_projects_returns_quote_counts():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/projects", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "project-1"
    assert body[0]["quote_count"] == 2


def test_create_project_requires_projects_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/projects", json=project_payload(), headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: projects:write"}
    assert store.created_project_payload is None


def test_create_project_passes_payload_to_store():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = project_payload(name="Hart House Kitchen")
    try:
        response = client.post("/api/v1/projects", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert store.created_project_payload == ("company-1", payload)
    assert response.json()["name"] == "Hart House Kitchen"


def test_list_quotes_returns_unit_counts():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/projects/project-1/quotes", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["unit_count"] == 3


def test_create_quote_returns_404_if_project_not_visible():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/projects/missing/quotes", json=quote_payload(), headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_create_quote_passes_payload_to_store():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = quote_payload(name="Kitchen Quote v1")
    try:
        response = client.post("/api/v1/projects/project-1/quotes", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert store.created_quote_payload == ("company-1", "project-1", payload)
    assert response.json()["name"] == "Kitchen Quote v1"


def test_update_quote_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch("/api/v1/quotes/quote-1", json=quote_payload(), headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}


def test_create_unit_and_update_unit_use_nested_quote_scope():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    create_payload = unit_payload(unit_type_key="Base Draw", width=900)
    update_payload = unit_payload(unit_type_key="Base Door", width=600)
    try:
        create_response = client.post("/api/v1/quotes/quote-1/units", json=create_payload, headers=auth_header())
        update_response = client.patch(
            "/api/v1/quotes/quote-1/units/unit-1",
            json=update_payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert store.created_unit_payload == ("company-1", "quote-1", create_payload)
    assert store.updated_unit_payload == ("company-1", "quote-1", "unit-1", update_payload)
    assert create_response.json()["unit_number"] == 2


def test_delete_unit_returns_204():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.delete("/api/v1/quotes/quote-1/units/unit-1", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert store.deleted_unit == ("company-1", "quote-1", "unit-1")


def test_get_quote_cutting_list_returns_cutlist_payload():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/quotes/quote-1/cutting-list", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["quote_id"] == "quote-1"
    assert response.json()["carcass"][0]["desc"] == "Side"
    assert store.requested_cutting_list == ("company-1", "quote-1")


def test_quote_extras_read_and_replace():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = {
        "items": [
            {"extra_id": "extra-1", "quantity": 3},
            {"extra_id": "extra-2", "quantity": 1},
        ]
    }
    try:
        read_response = client.get("/api/v1/quotes/quote-1/extras", headers=auth_header())
        replace_response = client.put("/api/v1/quotes/quote-1/extras", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert read_response.status_code == 200
    assert read_response.json()["quote_id"] == "quote-1"
    assert len(read_response.json()["items"]) == 2
    assert replace_response.status_code == 200
    assert replace_response.json()["items"] == payload["items"]
    assert store.replaced_quote_extras_payload == ("company-1", "quote-1", payload["items"])


def test_replace_quote_extras_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.put(
            "/api/v1/quotes/quote-1/extras",
            json={"items": [{"extra_id": "extra-1", "quantity": 2}]},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}


def test_quote_custom_panels_read_and_replace():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = quote_custom_panels_state()
    try:
        read_response = client.get("/api/v1/quotes/quote-1/custom-panels", headers=auth_header())
        replace_response = client.put("/api/v1/quotes/quote-1/custom-panels", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert read_response.status_code == 200
    assert read_response.json()["quote_id"] == "quote-1"
    assert len(read_response.json()["computed_rows"]) == 2
    assert replace_response.status_code == 200
    assert replace_response.json()["custom_panels"]["auto"]["kicker_return_count"] == 1
    assert store.requested_quote_custom_panels == ("company-1", "quote-1")
    assert store.replaced_quote_custom_panels_payload == ("company-1", "quote-1", payload)


def test_replace_quote_custom_panels_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.put(
            "/api/v1/quotes/quote-1/custom-panels",
            json=quote_custom_panels_state(),
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}


def test_get_project_pricing_requires_pricing_read_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/projects/project-1/pricing", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:read"}


def test_get_project_pricing_returns_project_totals():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/projects/project-1/pricing", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["project_id"] == "project-1"
    assert response.json()["grand_total_cents"] == 498000
    assert response.json()["quotes"][0]["quote_id"] == "quote-1"
    assert store.requested_project_pricing == ("company-1", "project-1")


def test_project_pricing_settings_read_and_update():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = pricing_settings_payload(vat_rate_bps=1550, default_markup_bps=3000)
    try:
        read_response = client.get("/api/v1/projects/project-1/pricing-settings", headers=auth_header())
        update_response = client.patch(
            "/api/v1/projects/project-1/pricing-settings",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert read_response.status_code == 200
    assert read_response.json()["project_id"] == "project-1"
    assert read_response.json()["vat_rate_bps"] == 1500
    assert update_response.status_code == 200
    assert update_response.json()["vat_rate_bps"] == 1550
    assert update_response.json()["default_markup_bps"] == 3000
    assert store.requested_project_pricing_settings == ("company-1", "project-1")
    assert store.updated_project_pricing_settings_payload == ("company-1", "project-1", payload)
    assert store.updated_quote_pricing_settings_payload is None


def test_project_pricing_settings_update_requires_pricing_update_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/projects/project-1/pricing-settings",
            json=pricing_settings_payload(vat_rate_bps=1550),
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}
    assert store.updated_project_pricing_settings_payload is None


def test_quote_pricing_settings_read_and_update():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = pricing_settings_payload(carcass_markup_bps=2750, delivery_base_cents=125000)
    try:
        read_response = client.get("/api/v1/quotes/quote-1/pricing-settings", headers=auth_header())
        update_response = client.patch(
            "/api/v1/quotes/quote-1/pricing-settings",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert read_response.status_code == 200
    assert read_response.json()["quote_id"] == "quote-1"
    assert read_response.json()["default_markup_bps"] == 2500
    assert update_response.status_code == 200
    assert update_response.json()["carcass_markup_bps"] == 2750
    assert update_response.json()["delivery_base_cents"] == 125000
    assert store.requested_quote_pricing_settings == ("company-1", "quote-1")
    assert store.updated_quote_pricing_settings_payload == ("company-1", "quote-1", payload)
    assert store.updated_project_pricing_settings_payload is None


def test_quote_pricing_settings_update_requires_pricing_update_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/quotes/quote-1/pricing-settings",
            json=pricing_settings_payload(vat_rate_bps=1550),
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}
    assert store.updated_quote_pricing_settings_payload is None


def project(item_id: str, *, name: str = "Main Kitchen", quote_count: int = 0) -> dict:
    return {
        "id": item_id,
        "company_id": "company-1",
        "name": name,
        "client": "John Smith",
        "address": "12 Oak Street",
        "description": "Kitchen renovation",
        "quote_count": quote_count,
        "created_at": NOW,
        "updated_at": NOW,
    }


def quote(
    item_id: str,
    *,
    project_id: str,
    name: str = "Kitchen Quote",
    notes: str = "",
    unit_count: int = 0,
) -> dict:
    return {
        "id": item_id,
        "company_id": "company-1",
        "project_id": project_id,
        "name": name,
        "notes": notes,
        "default_carcass_board_type_id": None,
        "default_door_board_type_id": None,
        "default_panel_board_type_id": None,
        "default_slide_id": None,
        "default_hinge_id": None,
        "default_base_handle_id": None,
        "default_wall_handle_id": None,
        "default_tall_handle_id": None,
        "default_drawer_handle_id": None,
        "unit_defaults": {
            "Base Draw": {"height": 780, "depth": 580},
            "Base Door": {"height": 780, "depth": 580},
            "Wall Door": {"height": 720, "depth": 330},
            "Tall Door": {"height": 2100, "depth": 580},
        },
        "unit_count": unit_count,
        "created_at": NOW,
        "updated_at": NOW,
    }


def unit(
    item_id: str,
    *,
    quote_id: str,
    unit_number: int,
    unit_type_key: str = "Base Draw",
    width: int = 900,
    height: int = 780,
    depth: int = 580,
    thickness: int = 16,
    carcass_board_type_id: str | None = None,
    door_board_type_id: str | None = None,
    extra_params: dict | None = None,
) -> dict:
    return {
        "id": item_id,
        "company_id": "company-1",
        "quote_id": quote_id,
        "unit_number": unit_number,
        "unit_type_key": unit_type_key,
        "height": height,
        "width": width,
        "depth": depth,
        "thickness": thickness,
        "carcass_board_type_id": carcass_board_type_id,
        "door_board_type_id": door_board_type_id,
        "extra_params": extra_params or {},
        "created_at": NOW,
        "updated_at": NOW,
    }


def project_payload(*, name: str = "Main Kitchen") -> dict:
    return {
        "name": name,
        "client": "John Smith",
        "address": "12 Oak Street",
        "description": "Kitchen renovation",
    }


def quote_payload(*, name: str = "Kitchen Quote") -> dict:
    return {
        "name": name,
        "notes": "Revision 1",
        "default_carcass_board_type_id": None,
        "default_door_board_type_id": None,
        "default_panel_board_type_id": None,
        "default_slide_id": None,
        "default_hinge_id": None,
        "default_base_handle_id": None,
        "default_wall_handle_id": None,
        "default_tall_handle_id": None,
        "default_drawer_handle_id": None,
        "unit_defaults": {
            "Base Draw": {"height": 780, "depth": 580},
            "Base Door": {"height": 780, "depth": 580},
        },
    }


def unit_payload(*, unit_type_key: str = "Base Draw", width: int = 900) -> dict:
    return {
        "unit_type_key": unit_type_key,
        "height": 780,
        "width": width,
        "depth": 580,
        "thickness": 16,
        "carcass_board_type_id": None,
        "door_board_type_id": None,
        "extra_params": {"num_drawers": 3},
    }


def quote_custom_panels_state() -> dict:
    return {
        "presets": {
            "base_side_panel": {"qty": 1, "board_type_id": None},
            "wall_side_filler": {"qty": 1, "board_type_id": None},
        },
        "manual": [
            {"name": "Feature End", "length": 2300, "width": 300, "qty": 1, "board_type_id": None},
        ],
        "auto": {
            "kicker_board_type_id": None,
            "pelmet_board_type_id": None,
            "kicker_return_count": 1,
            "kicker_return_depth_mm": 560,
            "kicker_override_on": False,
            "kicker_override_qty": 0,
            "kicker_override_length": 0,
            "kicker_override_width": 100,
            "pelmet_override_on": False,
            "pelmet_override_qty": 0,
            "pelmet_override_length": 0,
            "pelmet_override_width": 330,
        },
    }


def quote_custom_panels_response(quote_id: str) -> dict:
    return {
        "quote_id": quote_id,
        "custom_panels": quote_custom_panels_state(),
        "computed_rows": [
            {"desc": "Kicker", "length": 1760, "width": 100, "qty": 1, "board_type_id": None},
            {"desc": "Feature End", "length": 2300, "width": 300, "qty": 1, "board_type_id": None},
        ],
    }


def quote_cutting_list(quote_id: str) -> dict:
    return {
        "quote_id": quote_id,
        "carcass": [{"unit_number": 1, "desc": "Side", "length": 748, "width": 564, "qty": 2}],
        "panels": [{"unit_number": 1, "desc": "Door", "length": 777, "width": 297, "qty": 2}],
        "hardware": [],
        "extras": [],
        "runtime_rows": [],
        "runtime_mode": "legacy",
        "unit_sources": [{"unit_number": 1, "unit_type_key": "Base Door", "source": "legacy", "ruleset_id": None, "unit_config_id": None, "note": None}],
    }


def project_pricing(project_id: str) -> dict:
    return {
        "project_id": project_id,
        "project_name": "Main Kitchen",
        "active_price_list_id": "price-list-1",
        "currency_code": "USD",
        "vat_rate_bps": 1500,
        "markup_bps": 2500,
        "pricing_settings": pricing_settings(project_id=project_id),
        "is_complete": True,
        "subtotal_cents": 346783,
        "sell_before_vat_cents": 433479,
        "vat_cents": 65021,
        "grand_total_cents": 498000,
        "quotes": [
            {
                "quote_id": "quote-1",
                "quote_name": "Kitchen Quote",
                "vat_rate_bps": 1500,
                "markup_bps": 2500,
                "pricing_settings": pricing_settings(quote_id="quote-1"),
                "is_complete": True,
                "missing_items": [],
                "subtotal_cents": 346783,
                "sell_before_vat_cents": 433479,
                "vat_cents": 65021,
                "grand_total_cents": 498000,
                "lines": [],
            }
        ],
    }


def pricing_settings(
    *,
    project_id: str | None = None,
    quote_id: str | None = None,
    **overrides,
) -> dict:
    payload = {
        "company_id": "company-1",
        "vat_rate_bps": 1500,
        "default_markup_bps": 2500,
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
        "delivery_units_per_trip": 20,
        "minimum_install_days_bps": 5000,
        "minimum_delivery_trips_bps": 5000,
        "created_at": NOW,
        "updated_at": NOW,
    }
    if project_id is not None:
        payload["project_id"] = project_id
    if quote_id is not None:
        payload["quote_id"] = quote_id
    payload.update(overrides)
    return payload


def pricing_settings_payload(**overrides) -> dict:
    payload = pricing_settings(**overrides)
    payload.pop("company_id")
    payload.pop("created_at")
    payload.pop("updated_at")
    payload.pop("project_id", None)
    payload.pop("quote_id", None)
    return payload


def auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}
