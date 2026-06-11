from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from corequote_api.auth import AuthenticatedUser
from corequote_api.main import app
from corequote_api.projects_quotes import WorkspaceNotFound, WorkspaceValidationError
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
    def __init__(self, *, project_pricing_payload: dict | None = None, quote_output_review_payload: dict | None = None):
        self.project_pricing_payload = project_pricing_payload
        self.quote_output_review_payload = quote_output_review_payload
        self.created_project_payload: tuple[str, dict] | None = None
        self.updated_project_payload: tuple[str, str, dict] | None = None
        self.deleted_project: tuple[str, str] | None = None
        self.created_quote_payload: tuple[str, str, dict] | None = None
        self.updated_quote_payload: tuple[str, str, dict] | None = None
        self.updated_quote_status_payload: tuple[str, str, str] | None = None
        self.created_quote_revision: tuple[str, str] | None = None
        self.deleted_quote: tuple[str, str] | None = None
        self.created_unit_payload: tuple[str, str, dict] | None = None
        self.updated_unit_payload: tuple[str, str, str, dict] | None = None
        self.deleted_unit: tuple[str, str, str] | None = None
        self.replaced_quote_extras_payload: tuple[str, str, list[dict]] | None = None
        self.replaced_quote_custom_panels_payload: tuple[str, str, dict] | None = None
        self.requested_cutting_list: tuple[str, str] | None = None
        self.requested_quote_readiness: tuple[str, str] | None = None
        self.requested_quote_output_review: tuple[str, str] | None = None
        self.generated_customer_quote_pdf: tuple[str, str, dict] | None = None
        self.generated_workshop_schedule_pdf: tuple[str, str, dict] | None = None
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

    def update_quote_status(self, company_id: str, quote_id: str, status: str) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.updated_quote_status_payload = (company_id, quote_id, status)
        return quote(quote_id, project_id="project-1", status=status, unit_count=2)

    def create_quote_revision(self, company_id: str, quote_id: str) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.created_quote_revision = (company_id, quote_id)
        return quote(
            "quote-2",
            project_id="project-1",
            name="Kitchen Quote v2",
            quote_number="Q-001",
            revision=2,
            previous_revision_id=quote_id,
            previous_revision_quote_number="Q-001",
            previous_revision_revision=1,
            status="draft",
            unit_count=2,
        )

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

    def get_quote_readiness(self, company_id: str, quote_id: str, runtime_service=None) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.requested_quote_readiness = (company_id, quote_id)
        return quote_readiness(quote_id)

    def get_quote_output_review(self, company_id: str, quote_id: str, runtime_service=None) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.requested_quote_output_review = (company_id, quote_id)
        return self.quote_output_review_payload or quote_output_review(quote_id)

    def generate_customer_quote_pdf(self, company_id: str, quote_id: str, *, company: dict, runtime_service=None) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        if quote_id == "not-ready":
            raise WorkspaceValidationError("Resolve readiness warnings before generating the client quote.")
        self.generated_customer_quote_pdf = (company_id, quote_id, company)
        return {
            "filename": "Smith-Kitchen-Quote-v1-Q-001-rev-1.pdf",
            "content": b"%PDF-1.3 customer quote",
        }

    def generate_workshop_schedule_pdf(self, company_id: str, quote_id: str, *, company: dict, runtime_service=None) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        if quote_id == "empty":
            raise WorkspaceValidationError("Add cabinet units before generating the workshop schedule.")
        self.generated_workshop_schedule_pdf = (company_id, quote_id, company)
        return {
            "filename": "workshop-Smith-Kitchen-Quote-v1-Q-001-rev-1.pdf",
            "content": b"%PDF-1.3 workshop schedule",
        }

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
        return self.project_pricing_payload or project_pricing(project_id)

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
    assert response.json()[0]["status"] == "draft"
    assert response.json()[0]["quote_number"] == "Q-001"
    assert response.json()[0]["revision"] == 1


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


def test_update_quote_status_from_workspace():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/quotes/quote-1/status",
            json={"status": "sent"},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert response.json()["quote_number"] == "Q-001"
    assert response.json()["revision"] == 1
    assert store.updated_quote_status_payload == ("company-1", "quote-1", "sent")


def test_update_quote_status_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/quotes/quote-1/status",
            json={"status": "sent"},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}
    assert store.updated_quote_status_payload is None


def test_create_quote_revision_links_to_previous_quote():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/quotes/quote-1/revisions", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "quote-2"
    assert body["status"] == "draft"
    assert body["quote_number"] == "Q-001"
    assert body["revision"] == 2
    assert body["previous_revision_id"] == "quote-1"
    assert body["previous_revision_quote_number"] == "Q-001"
    assert body["previous_revision_revision"] == 1
    assert store.created_quote_revision == ("company-1", "quote-1")


def test_create_quote_revision_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/quotes/quote-1/revisions", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}
    assert store.created_quote_revision is None


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


def test_get_quote_readiness_returns_structured_checks():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/quotes/quote-1/readiness", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["quote_id"] == "quote-1"
    assert body["status"] == "needs_attention"
    assert body["checks"][0]["id"] == "unit_count"
    assert body["checks"][0]["action_target"] == "units"
    assert store.requested_quote_readiness == ("company-1", "quote-1")


def test_get_quote_readiness_returns_404_if_quote_not_visible():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/quotes/missing/readiness", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Quote not found"}
    assert store.requested_quote_readiness is None


def test_get_quote_output_review_returns_actions_and_statuses():
    payload = quote_output_review(
        "quote-1",
        actions=[
            {
                "id": "client_quote_pdf",
                "group": "client",
                "label": "Client quote",
                "description": "Customer PDF with sell totals only. Internal costs and profit stay hidden.",
                "enabled": False,
                "warning": "Resolve readiness warnings before generating the client quote.",
                "hides_internal_costs": True,
                "action_target": "pricing",
            },
            {
                "id": "workshop_schedule",
                "group": "workshop",
                "label": "Workshop schedule",
                "description": "Cutting and production schedule for the workshop.",
                "enabled": False,
                "warning": "Fix cutting-list warnings before generating the workshop schedule.",
                "hides_internal_costs": False,
                "action_target": "cutting-lists",
            },
        ],
    )
    store = FakeWorkspaceStore(quote_output_review_payload=payload)
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/quotes/quote-1/output-review", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["quote_id"] == "quote-1"
    assert body["client_quote"]["status"] == "needs_attention"
    assert body["internal_pricing"]["status"] == "needs_attention"
    assert body["actions"][0]["label"] == "Client quote"
    assert body["actions"][0]["enabled"] is False
    assert body["actions"][0]["hides_internal_costs"] is True
    assert store.requested_quote_output_review == ("company-1", "quote-1")


def test_get_quote_output_review_requires_pricing_read_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/quotes/quote-1/output-review", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:read"}
    assert store.requested_quote_output_review is None


def test_download_customer_quote_pdf_returns_pdf_attachment():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store

    try:
        response = client.get("/api/v1/quotes/quote-1/customer-quote.pdf", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="Smith-Kitchen-Quote-v1-Q-001-rev-1.pdf"'
    assert response.content.startswith(b"%PDF")
    assert store.generated_customer_quote_pdf == (
        "company-1",
        "quote-1",
        {
            "name": "CoreQuote Test Co",
            "contact_name": "Test Owner",
            "contact_email": "test.owner@corequote.local",
        },
    )


def test_download_customer_quote_pdf_surfaces_readiness_blockers():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store

    try:
        response = client.get("/api/v1/quotes/not-ready/customer-quote.pdf", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Resolve readiness warnings before generating the client quote."}


def test_download_customer_quote_pdf_requires_pricing_read_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store

    try:
        response = client.get("/api/v1/quotes/quote-1/customer-quote.pdf", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:read"}
    assert store.generated_customer_quote_pdf is None


def test_download_workshop_schedule_pdf_returns_pdf_attachment():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store

    try:
        response = client.get("/api/v1/quotes/quote-1/workshop-schedule.pdf", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="workshop-Smith-Kitchen-Quote-v1-Q-001-rev-1.pdf"'
    assert response.content.startswith(b"%PDF")
    assert store.generated_workshop_schedule_pdf == (
        "company-1",
        "quote-1",
        {
            "name": "CoreQuote Test Co",
            "contact_name": "Test Owner",
            "contact_email": "test.owner@corequote.local",
        },
    )


def test_download_workshop_schedule_pdf_surfaces_empty_schedule_blocker():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store

    try:
        response = client.get("/api/v1/quotes/empty/workshop-schedule.pdf", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Add cabinet units before generating the workshop schedule."}


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


def test_get_project_pricing_returns_missing_price_guidance():
    payload = project_pricing(
        "project-1",
        is_complete=False,
        missing_prices=[
            missing_price(
                item_type="handle",
                item_type_label="Handle",
                item_key="handle::handle-1",
                item_ref_id="handle-1",
                price_component="unit",
                component="Unit price",
                bucket="handle",
                item_name="Bar pull",
                affected_quote_id="quote-1",
                affected_quote_name="Kitchen Quote",
                quantity=3,
                uom="pcs",
                used_in=["Handle"],
                usage_label="Handle",
                action_label="Add a price for Bar pull",
                message="Add a price for Bar pull using Unit price in the pricing library.",
            )
        ],
        quote_missing_prices=[
            missing_price(
                item_type="handle",
                item_type_label="Handle",
                item_key="handle::handle-1",
                item_ref_id="handle-1",
                price_component="unit",
                component="Unit price",
                bucket="handle",
                item_name="Bar pull",
                affected_quote_id="quote-1",
                affected_quote_name="Kitchen Quote",
                quantity=3,
                uom="pcs",
                used_in=["Handle"],
                usage_label="Handle",
                action_label="Add a price for Bar pull",
                message="Add a price for Bar pull using Unit price in the pricing library.",
            )
        ],
    )
    store = FakeWorkspaceStore(project_pricing_payload=payload)
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/projects/project-1/pricing", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["is_complete"] is False
    assert body["missing_prices"][0]["action_label"] == "Add a price for Bar pull"
    assert body["missing_prices"][0]["affected_quote_name"] == "Kitchen Quote"
    assert body["quotes"][0]["missing_prices"][0]["item_ref_id"] == "handle-1"


def test_get_project_pricing_returns_quote_material_summary():
    payload = project_pricing("project-1", material_summary=material_summary())
    store = FakeWorkspaceStore(project_pricing_payload=payload)
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/projects/project-1/pricing", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    summary = response.json()["quotes"][0]["material_summary"]
    assert summary["total_area_m2"] == 1.42
    assert summary["total_estimated_sheets"] is None
    assert summary["groups"][0]["role_label"] == "Carcass material"
    assert summary["groups"][0]["estimated_sheets"] == 1
    assert summary["warnings"][0]["code"] == "missing_board_dimensions"
    assert summary["warnings"][0]["message"] == "Add sheet length and width for Egger Oak look (18mm) to estimate sheets."


def test_get_project_pricing_returns_quote_hardware_pick_list():
    payload = project_pricing("project-1", hardware_pick_list=hardware_pick_list())
    store = FakeWorkspaceStore(project_pricing_payload=payload)
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/projects/project-1/pricing", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    pick_list = response.json()["quotes"][0]["hardware_pick_list"]
    assert pick_list["total_item_count"] == 2
    assert pick_list["total_quantity"] == 7
    assert pick_list["items"][0]["item_type"] == "slide"
    assert pick_list["items"][0]["supplier"] == "Grass"
    assert pick_list["items"][0]["code"] == "S500"
    assert pick_list["items"][0]["used_in"] == ["Unit 1 drawers"]
    assert pick_list["warnings"][0]["code"] == "missing_handle_selection"


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


def test_project_pricing_settings_partial_patch_only_sends_changed_fields():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/projects/project-1/pricing-settings",
            json={"vat_rate_bps": 1550},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.updated_project_pricing_settings_payload == ("company-1", "project-1", {"vat_rate_bps": 1550})


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


def test_quote_pricing_settings_partial_patch_only_sends_changed_fields():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/quotes/quote-1/pricing-settings",
            json={"delivery_base_cents": 125000},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.updated_quote_pricing_settings_payload == ("company-1", "quote-1", {"delivery_base_cents": 125000})


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
    status: str = "draft",
    quote_number: str = "Q-001",
    revision: int = 1,
    previous_revision_id: str | None = None,
    previous_revision_quote_number: str | None = None,
    previous_revision_revision: int | None = None,
    unit_count: int = 0,
) -> dict:
    return {
        "id": item_id,
        "company_id": "company-1",
        "project_id": project_id,
        "name": name,
        "notes": notes,
        "status": status,
        "quote_number": quote_number,
        "revision": revision,
        "previous_revision_id": previous_revision_id,
        "previous_revision_quote_number": previous_revision_quote_number,
        "previous_revision_revision": previous_revision_revision,
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


def quote_readiness(quote_id: str) -> dict:
    return {
        "quote_id": quote_id,
        "status": "needs_attention",
        "is_ready": False,
        "summary_title": "Needs attention before review",
        "summary_message": "1 readiness check needs attention before this quote is ready for review.",
        "warning_count": 1,
        "error_count": 0,
        "checks": [
            {
                "id": "unit_count",
                "severity": "warning",
                "title": "Add cabinet units",
                "message": "This quote has no cabinets yet, so there is nothing to price, cut, or review.",
                "action_label": "Add units",
                "action_target": "units",
            }
        ],
    }


def quote_output_review(quote_id: str, *, actions: list[dict] | None = None) -> dict:
    return {
        "quote_id": quote_id,
        "quote_name": "Kitchen Quote",
        "project_id": "project-1",
        "project_name": "Main Kitchen",
        "quote_status": "draft",
        "quote_number": "Q-001",
        "revision": 1,
        "currency_code": "USD",
        "readiness": quote_readiness(quote_id),
        "client_quote": {
            "id": "client_quote",
            "label": "Client quote",
            "status": "needs_attention",
            "severity": "warning",
            "message": "Resolve readiness warnings before generating the client quote.",
        },
        "internal_pricing": {
            "id": "internal_pricing",
            "label": "Internal pricing confidence",
            "status": "needs_attention",
            "severity": "warning",
            "message": "Review missing prices before trusting internal margin and totals.",
        },
        "workshop_schedule": {
            "id": "workshop_schedule",
            "label": "Workshop schedule",
            "status": "needs_attention",
            "severity": "warning",
            "message": "Fix cutting-list warnings before workshop handoff.",
        },
        "material_status": {
            "id": "material_summary",
            "label": "Material summary",
            "status": "ready",
            "severity": "pass",
            "message": "Material summary is ready for review.",
        },
        "hardware_status": {
            "id": "hardware_pick_list",
            "label": "Hardware pick list",
            "status": "ready",
            "severity": "pass",
            "message": "Hardware pick list is ready for review.",
        },
        "material_summary": material_summary(),
        "hardware_pick_list": hardware_pick_list(),
        "actions": actions
        or [
            {
                "id": "client_quote_pdf",
                "group": "client",
                "label": "Client quote",
                "description": "Customer PDF with sell totals only. Internal costs and profit stay hidden.",
                "enabled": False,
                "warning": "Resolve readiness warnings before generating the client quote.",
                "hides_internal_costs": True,
                "action_target": "pricing",
            },
            {
                "id": "workshop_schedule",
                "group": "workshop",
                "label": "Workshop schedule",
                "description": "Cutting and production schedule for the workshop.",
                "enabled": False,
                "warning": "Fix cutting-list warnings before generating the workshop schedule.",
                "hides_internal_costs": False,
                "action_target": "cutting-lists",
            },
            {
                "id": "material_summary",
                "group": "workshop",
                "label": "Material summary",
                "description": "Board quantities and estimated sheets for internal ordering.",
                "enabled": True,
                "warning": None,
                "hides_internal_costs": False,
                "action_target": "pricing",
            },
            {
                "id": "hardware_pick_list",
                "group": "workshop",
                "label": "Hardware pick list",
                "description": "Slides, hinges, handles, and extras to pick for production.",
                "enabled": True,
                "warning": None,
                "hides_internal_costs": False,
                "action_target": "pricing",
            },
        ],
    }


def project_pricing(
    project_id: str,
    *,
    is_complete: bool = True,
    missing_prices: list[dict] | None = None,
    quote_missing_prices: list[dict] | None = None,
    material_summary: dict | None = None,
    hardware_pick_list: dict | None = None,
) -> dict:
    return {
        "project_id": project_id,
        "project_name": "Main Kitchen",
        "active_price_list_id": "price-list-1",
        "currency_code": "USD",
        "vat_rate_bps": 1500,
        "markup_bps": 2500,
        "pricing_settings": pricing_settings(project_id=project_id),
        "is_complete": is_complete,
        "missing_prices": missing_prices or [],
        "subtotal_cents": 346783,
        "cost_total_cents": 346783,
        "sell_before_vat_cents": 433479,
        "vat_cents": 65021,
        "grand_total_cents": 498000,
        "profit_cents": 86696,
        "bucket_totals": [],
        "quotes": [
            {
                "quote_id": "quote-1",
                "quote_name": "Kitchen Quote",
                "quote_status": "draft",
                "quote_number": "Q-001",
                "revision": 1,
                "previous_revision_id": None,
                "previous_revision_quote_number": None,
                "previous_revision_revision": None,
                "vat_rate_bps": 1500,
                "markup_bps": 2500,
                "pricing_settings": pricing_settings(quote_id="quote-1"),
                "is_complete": is_complete,
                "missing_items": [],
                "material_summary": material_summary or {"groups": [], "warnings": [], "total_area_m2": 0, "total_piece_count": 0, "total_edge_m": 0, "total_estimated_sheets": None},
                "hardware_pick_list": hardware_pick_list or {"items": [], "warnings": [], "total_item_count": 0, "total_quantity": 0},
                "missing_prices": quote_missing_prices or [],
                "subtotal_cents": 346783,
                "cost_total_cents": 346783,
                "sell_before_vat_cents": 433479,
                "vat_cents": 65021,
                "grand_total_cents": 498000,
                "profit_cents": 86696,
                "bucket_totals": [],
                "lines": [],
            }
        ],
    }


def hardware_pick_list() -> dict:
    return {
        "items": [
            {
                "item_type": "slide",
                "type_label": "Slides",
                "item_key": "slide::slide-1",
                "item_ref_id": "slide-1",
                "item_name": "Grass Dynapro",
                "supplier": "Grass",
                "code": "S500",
                "quantity": 3,
                "uom": "pairs",
                "unit_numbers": [1],
                "used_in": ["Unit 1 drawers"],
                "usage_label": "Unit 1 drawers",
            },
            {
                "item_type": "extra",
                "type_label": "Extras",
                "item_key": "extra::extra-1",
                "item_ref_id": "extra-1",
                "item_name": "Waste removal",
                "supplier": "Core",
                "code": "WR1",
                "quantity": 4,
                "uom": "pcs",
                "unit_numbers": [],
                "used_in": ["Quote extra"],
                "usage_label": "Quote extra",
            },
        ],
        "warnings": [
            {
                "severity": "warning",
                "code": "missing_handle_selection",
                "item_type": "handle",
                "unit_number": 1,
                "item_ref_id": None,
                "message": "Choose a drawer handle for Unit 1 drawers.",
            }
        ],
        "total_item_count": 2,
        "total_quantity": 7,
    }


def material_summary() -> dict:
    return {
        "groups": [
            {
                "board_type_id": "board-1",
                "material_role": "carcass",
                "role_label": "Carcass material",
                "board_name": "PG White melamine (16mm)",
                "brand": "PG",
                "material": "White melamine",
                "thickness": 16,
                "length_mm": 2440,
                "width_mm": 1220,
                "costing_mode": "sheet",
                "piece_count": 2,
                "area_m2": 1.0,
                "edge_m": 3.0,
                "sheet_area_m2": 2.9768,
                "estimated_sheets": 1,
                "price_component": "sheet",
                "pricing_qty": 1,
                "pricing_uom": "sheet",
                "cost_total_cents": 50000,
                "sell_total_cents": 62500,
                "missing_price": False,
            },
            {
                "board_type_id": "board-2",
                "material_role": "door_panel",
                "role_label": "Door and drawer material",
                "board_name": "Egger Oak look (18mm)",
                "brand": "Egger",
                "material": "Oak look",
                "thickness": 18,
                "length_mm": None,
                "width_mm": None,
                "costing_mode": "sheet",
                "piece_count": 2,
                "area_m2": 0.42,
                "edge_m": 0,
                "sheet_area_m2": None,
                "estimated_sheets": None,
                "price_component": "sheet",
                "pricing_qty": 0,
                "pricing_uom": "sheet",
                "cost_total_cents": 0,
                "sell_total_cents": 0,
                "missing_price": False,
            },
        ],
        "warnings": [
            {
                "severity": "warning",
                "code": "missing_board_dimensions",
                "material_role": "door_panel",
                "role_label": "Door and drawer material",
                "unit_number": 0,
                "row_desc": "Egger Oak look (18mm)",
                "board_type_id": "board-2",
                "message": "Add sheet length and width for Egger Oak look (18mm) to estimate sheets.",
            }
        ],
        "total_area_m2": 1.42,
        "total_piece_count": 4,
        "total_edge_m": 3.0,
        "total_estimated_sheets": None,
    }


def missing_price(**overrides) -> dict:
    payload = {
        "item_type": "board",
        "item_type_label": "Board",
        "item_key": "board::board-1",
        "item_ref_id": "board-1",
        "price_component": "sqm",
        "component": "Square metre price",
        "bucket": "material",
        "item_name": "PG White (16mm)",
        "uom": "m2",
        "quantity": 1,
        "used_in": ["Carcass material"],
        "usage_label": "Carcass material",
        "affected_quote_id": "quote-1",
        "affected_quote_name": "Kitchen Quote",
        "library_area": "pricing",
        "action_label": "Add a price for PG White (16mm)",
        "message": "Add a price for PG White (16mm) using Square metre price in the pricing library.",
    }
    payload.update(overrides)
    return payload


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
