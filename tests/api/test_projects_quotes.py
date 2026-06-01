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


def auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}
