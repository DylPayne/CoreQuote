from __future__ import annotations

import csv
from datetime import UTC, datetime
from io import StringIO

from fastapi.testclient import TestClient

from corequote_api.auth import AuthenticatedUser
from corequote_api.main import app
from corequote_api.projects_quotes import WorkspaceNotFound, WorkspaceStore, WorkspaceValidationError, _quote_pricing_as_of
from corequote_api.projects_quotes_payloads import _clean_unit_payload
from corequote_api.routers import auth, projects_quotes


client = TestClient(app)
NOW = datetime(2026, 6, 1, 10, 30, tzinfo=UTC)
DEFAULT_PRODUCTION_METADATA = {
    "carcass": {"edge_banding": "", "grain_direction": "none", "rotation": "none", "notes": ""},
    "door_panel": {"edge_banding": "", "grain_direction": "none", "rotation": "none", "notes": ""},
    "visible_panel": {"edge_banding": "", "grain_direction": "none", "rotation": "none", "notes": ""},
}


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
    def __init__(
        self,
        *,
        project_pricing_payload: dict | None = None,
        quote_output_review_payload: dict | None = None,
        quote_production_handoff_payload: dict | None = None,
        quote_readiness_payload: dict | None = None,
    ):
        self.project_pricing_payload = project_pricing_payload
        self.quote_output_review_payload = quote_output_review_payload
        self.quote_production_handoff_payload = quote_production_handoff_payload
        self.quote_readiness_payload = quote_readiness_payload
        self.created_project_payload: tuple[str, dict] | None = None
        self.updated_project_payload: tuple[str, str, dict] | None = None
        self.deleted_project: tuple[str, str] | None = None
        self.created_quote_payload: tuple[str, str, dict] | None = None
        self.updated_quote_payload: tuple[str, str, dict] | None = None
        self.updated_quote_status_payload: tuple[str, str, str] | None = None
        self.duplicated_quote: tuple[str, str] | None = None
        self.created_quote_revision: tuple[str, str] | None = None
        self.deleted_quote: tuple[str, str] | None = None
        self.created_unit_payload: tuple[str, str, dict] | None = None
        self.duplicated_unit: tuple[str, str, str] | None = None
        self.bulk_saved_units: tuple[str, str, list[dict]] | None = None
        self.bulk_applied_unit_overrides: tuple[str, str, dict] | None = None
        self.reordered_units: tuple[str, str, list[str]] | None = None
        self.updated_unit_payload: tuple[str, str, str, dict] | None = None
        self.deleted_unit: tuple[str, str, str] | None = None
        self.replaced_quote_extras_payload: tuple[str, str, list[dict]] | None = None
        self.replaced_quote_custom_panels_payload: tuple[str, str, dict] | None = None
        self.requested_cutting_list: tuple[str, str] | None = None
        self.requested_quote_readiness: tuple[str, str] | None = None
        self.requested_quote_output_review: tuple[str, str] | None = None
        self.requested_quote_production_handoff: tuple[str, str] | None = None
        self.generated_customer_quote_pdf: tuple[str, str, dict] | None = None
        self.generated_workshop_schedule_pdf: tuple[str, str, dict] | None = None
        self.generated_production_handoff_export: tuple[str, str, str] | None = None
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

    def duplicate_quote(self, company_id: str, quote_id: str) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.duplicated_quote = (company_id, quote_id)
        return quote(
            "quote-copy",
            project_id="project-1",
            name="Kitchen Quote (Copy)",
            quote_number="Q-002",
            revision=1,
            previous_revision_id=None,
            previous_revision_quote_number=None,
            previous_revision_revision=None,
            status="draft",
            unit_count=2,
        )

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
        payload = _clean_unit_payload(payload)
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

    def duplicate_unit(self, company_id: str, quote_id: str, unit_id: str) -> dict:
        if quote_id == "missing" or unit_id == "missing":
            raise WorkspaceNotFound("Unit not found")
        self.duplicated_unit = (company_id, quote_id, unit_id)
        return unit(
            "unit-2",
            quote_id=quote_id,
            unit_number=2,
            unit_type_key="Base Door",
            width=600,
            height=780,
            depth=580,
            thickness=16,
            carcass_board_type_id="board-1",
            door_board_type_id="board-2",
            extra_params={"num_doors": 2, "num_shelves": 1},
        )

    def bulk_save_units(self, company_id: str, quote_id: str, payloads: list[dict]) -> list[dict]:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        if any(row.get("id") == "missing" for row in payloads):
            raise WorkspaceNotFound("Unit not found")
        if any(row.get("unit_type_key") == "Invalid setup" for row in payloads):
            raise WorkspaceValidationError("units[1]: Carcass board is required")
        payloads = [{"id": row.get("id"), **_clean_unit_payload(row)} for row in payloads]
        self.bulk_saved_units = (company_id, quote_id, payloads)
        return [
            unit(
                row.get("id") or f"unit-{index}",
                quote_id=quote_id,
                unit_number=index,
                unit_type_key=row["unit_type_key"],
                width=row["width"],
                height=row["height"],
                depth=row["depth"],
                carcass_board_type_id=row.get("carcass_board_type_id"),
                door_board_type_id=row.get("door_board_type_id"),
                extra_params=row.get("extra_params", {}),
            )
            for index, row in enumerate(payloads, start=1)
        ]

    def bulk_apply_unit_overrides(self, company_id: str, quote_id: str, payload: dict) -> list[dict]:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        if "missing" in payload.get("unit_ids", []):
            raise WorkspaceNotFound("Unit not found")
        if set(payload) == {"unit_ids"}:
            raise WorkspaceValidationError("Select at least one field to apply")
        if payload.get("height") == 1:
            raise WorkspaceValidationError("Unit 1: height must be a positive integer")
        self.bulk_applied_unit_overrides = (company_id, quote_id, payload)
        return [
            unit(
                unit_id,
                quote_id=quote_id,
                unit_number=index,
                unit_type_key="Base Door" if unit_id != "unit-drawer" else "Base Draw",
                width=600,
                height=payload.get("height", 780),
                depth=payload.get("depth", 580),
                carcass_board_type_id=payload.get("carcass_board_type_id"),
                door_board_type_id=payload.get("door_board_type_id"),
                extra_params={
                    key: value
                    for key, value in {
                        "handle_id": payload.get("handle_id"),
                        "slide_id": payload.get("slide_id") if unit_id == "unit-drawer" else None,
                        "hinge_id": payload.get("hinge_id") if unit_id != "unit-drawer" else None,
                    }.items()
                    if value
                },
            )
            for index, unit_id in enumerate(payload.get("unit_ids", []), start=1)
        ]

    def reorder_units(self, company_id: str, quote_id: str, unit_ids: list[str]) -> list[dict]:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        if "missing" in unit_ids:
            raise WorkspaceNotFound("Unit not found")
        if "partial" in unit_ids:
            raise WorkspaceValidationError("Reorder payload must include every quote unit exactly once")
        self.reordered_units = (company_id, quote_id, unit_ids)
        return [
            unit(unit_id, quote_id=quote_id, unit_number=index, unit_type_key="Base Door", width=600)
            for index, unit_id in enumerate(unit_ids, start=1)
        ]

    def update_unit(self, company_id: str, quote_id: str, unit_id: str, payload: dict) -> dict:
        if quote_id == "missing" or unit_id == "missing":
            raise WorkspaceNotFound("Unit not found")
        payload = _clean_unit_payload(payload)
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
        return self.quote_readiness_payload or quote_readiness(quote_id)

    def get_quote_output_review(self, company_id: str, quote_id: str, runtime_service=None) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        self.requested_quote_output_review = (company_id, quote_id)
        return self.quote_output_review_payload or quote_output_review(quote_id)

    def get_quote_production_handoff(self, company_id: str, quote_id: str, runtime_service=None) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        if quote_id == "invalid-production":
            raise WorkspaceValidationError("Add cabinet units before building the production handoff.")
        self.requested_quote_production_handoff = (company_id, quote_id)
        return self.quote_production_handoff_payload or quote_production_handoff(quote_id)

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

    def generate_production_handoff_export(self, company_id: str, quote_id: str, *, export_format: str, runtime_service=None) -> dict:
        if quote_id == "missing":
            raise WorkspaceNotFound("Quote not found")
        if quote_id == "empty":
            raise WorkspaceValidationError("Add production rows before exporting the production handoff.")
        self.generated_production_handoff_export = (company_id, quote_id, export_format)
        if export_format == "xlsx":
            return {
                "filename": "production-Smith-Kitchen-Q-001-rev-1.xlsx",
                "content": b"PK\x03\x04 production workbook",
            }
        return {
            "filename": "production-Smith-Kitchen-Q-001-rev-1.csv",
            "content": (
                "Project,Quote,Quote Number,Revision,Source,Unit,Part ID,Warning State\n"
                "Main Kitchen,Kitchen Quote,Q-001,1,Unit,Unit 1,Q-001-R1-U01-CAR-SIDE-748X564-01,Ready\n"
            ).encode("utf-8"),
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


def test_duplicate_quote_creates_editable_copy_with_new_quote_number():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/quotes/quote-1/duplicate", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "quote-copy"
    assert body["name"] == "Kitchen Quote (Copy)"
    assert body["status"] == "draft"
    assert body["quote_number"] == "Q-002"
    assert body["revision"] == 1
    assert body["previous_revision_id"] is None
    assert body["unit_count"] == 2
    assert store.duplicated_quote == ("company-1", "quote-1")


def test_duplicate_quote_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/quotes/quote-1/duplicate", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}
    assert store.duplicated_quote is None


def test_duplicate_quote_returns_404_for_hidden_quote():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/quotes/missing/duplicate", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Quote not found"}
    assert store.duplicated_quote is None


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


def test_create_unit_cleans_drawer_split_payload():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = unit_payload(unit_type_key="Base Draw", width=600)
    payload["extra_params"] = {
        "num_drawers": "3",
        "drawer_split_mode": "manual",
        "drawer_face_heights": ["194", 194, 383],
        "drawer_face_ratios": [1, 1, 2],
    }
    try:
        response = client.post("/api/v1/quotes/quote-1/units", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert store.created_unit_payload == (
        "company-1",
        "quote-1",
        {
            **payload,
            "extra_params": {
                "num_drawers": 3,
                "drawer_split_mode": "manual",
                "drawer_face_heights": [194, 194, 383],
            },
        },
    )
    assert response.json()["extra_params"] == {
        "num_drawers": 3,
        "drawer_split_mode": "manual",
        "drawer_face_heights": [194, 194, 383],
    }


def test_create_unit_rejects_manual_drawer_split_total_mismatch():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = unit_payload(unit_type_key="Base Draw", width=600)
    payload["extra_params"] = {
        "num_drawers": 3,
        "drawer_split_mode": "manual",
        "drawer_face_heights": [194, 194, 300],
    }
    try:
        response = client.post("/api/v1/quotes/quote-1/units", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "drawer_face_heights total must equal 771 mm"}
    assert store.created_unit_payload is None


def test_duplicate_unit_uses_nested_quote_scope_and_returns_copy():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/quotes/quote-1/units/unit-1/duplicate", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "unit-2"
    assert body["unit_number"] == 2
    assert body["unit_type_key"] == "Base Door"
    assert body["width"] == 600
    assert body["carcass_board_type_id"] == "board-1"
    assert body["door_board_type_id"] == "board-2"
    assert body["extra_params"] == {"num_doors": 2, "num_shelves": 1}
    assert store.duplicated_unit == ("company-1", "quote-1", "unit-1")


def test_duplicate_unit_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/quotes/quote-1/units/unit-1/duplicate", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}
    assert store.duplicated_unit is None


def test_duplicate_unit_returns_404_if_unit_not_visible():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.post("/api/v1/quotes/quote-1/units/missing/duplicate", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Unit not found"}
    assert store.duplicated_unit is None


def test_bulk_save_units_accepts_create_and_edit_rows():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = {
        "units": [
            {"id": "unit-1", **unit_payload(unit_type_key="Base Door", width=600)},
            {**unit_payload(unit_type_key="Base Draw", width=900), "extra_params": {"num_drawers": 3}},
            {**unit_payload(unit_type_key="Wall Door", width=600), "extra_params": {"num_doors": 2, "num_shelves": 1}},
        ]
    }
    try:
        response = client.put("/api/v1/quotes/quote-1/units/bulk", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [(row["id"], row["unit_number"], row["unit_type_key"], row["width"]) for row in body] == [
        ("unit-1", 1, "Base Door", 600),
        ("unit-2", 2, "Base Draw", 900),
        ("unit-3", 3, "Wall Door", 600),
    ]
    assert store.bulk_saved_units == (
        "company-1",
        "quote-1",
        [
            {"id": "unit-1", **unit_payload(unit_type_key="Base Door", width=600)},
            {"id": None, **unit_payload(unit_type_key="Base Draw", width=900), "extra_params": {"num_drawers": 3}},
            {"id": None, **unit_payload(unit_type_key="Wall Door", width=600), "extra_params": {"num_doors": 2, "num_shelves": 1}},
        ],
    )


def test_bulk_save_units_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.put(
            "/api/v1/quotes/quote-1/units/bulk",
            json={"units": [unit_payload()]},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}
    assert store.bulk_saved_units is None


def test_bulk_save_units_returns_422_for_invalid_row_dimensions():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    invalid_row = unit_payload()
    invalid_row["width"] = 0
    try:
        response = client.put(
            "/api/v1/quotes/quote-1/units/bulk",
            json={"units": [invalid_row]},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert store.bulk_saved_units is None


def test_bulk_save_units_returns_404_for_invalid_quote_or_unit_access():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = {"units": [{"id": "missing", **unit_payload()}]}
    try:
        response = client.put("/api/v1/quotes/quote-1/units/bulk", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Unit not found"}
    assert store.bulk_saved_units is None


def test_bulk_save_units_surfaces_row_specific_setup_errors():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = {
        "units": [
            unit_payload(unit_type_key="Base Door", width=600),
            unit_payload(unit_type_key="Invalid setup", width=900),
        ]
    }
    try:
        response = client.put("/api/v1/quotes/quote-1/units/bulk", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "units[1]: Carcass board is required"}
    assert store.bulk_saved_units is None


def test_bulk_apply_unit_overrides_updates_selected_units():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = {
        "unit_ids": ["unit-1", "unit-drawer"],
        "carcass_board_type_id": "board-2",
        "handle_id": "handle-2",
        "slide_id": "slide-2",
        "hinge_id": "hinge-2",
        "height": 800,
        "depth": 560,
    }
    try:
        response = client.patch("/api/v1/quotes/quote-1/units/bulk-apply", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [(row["id"], row["height"], row["depth"], row["carcass_board_type_id"]) for row in body] == [
        ("unit-1", 800, 560, "board-2"),
        ("unit-drawer", 800, 560, "board-2"),
    ]
    assert body[0]["extra_params"] == {"handle_id": "handle-2", "hinge_id": "hinge-2"}
    assert body[1]["extra_params"] == {"handle_id": "handle-2", "slide_id": "slide-2"}
    assert store.bulk_applied_unit_overrides == ("company-1", "quote-1", payload)


def test_bulk_apply_unit_overrides_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/quotes/quote-1/units/bulk-apply",
            json={"unit_ids": ["unit-1"], "depth": 560},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}
    assert store.bulk_applied_unit_overrides is None


def test_bulk_apply_unit_overrides_returns_404_for_invalid_unit_access():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/quotes/quote-1/units/bulk-apply",
            json={"unit_ids": ["unit-1", "missing"], "depth": 560},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Unit not found"}
    assert store.bulk_applied_unit_overrides is None


def test_bulk_apply_unit_overrides_requires_at_least_one_field():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/quotes/quote-1/units/bulk-apply",
            json={"unit_ids": ["unit-1"]},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Select at least one field to apply"}
    assert store.bulk_applied_unit_overrides is None


def test_bulk_apply_unit_overrides_surfaces_validation_failures():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/quotes/quote-1/units/bulk-apply",
            json={"unit_ids": ["unit-1"], "height": 1},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Unit 1: height must be a positive integer"}
    assert store.bulk_applied_unit_overrides is None


def test_reorder_units_persists_requested_workshop_order():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    payload = {"unit_ids": ["unit-3", "unit-1", "unit-2"]}
    try:
        response = client.put("/api/v1/quotes/quote-1/units/reorder", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [(row["id"], row["unit_number"]) for row in body] == [
        ("unit-3", 1),
        ("unit-1", 2),
        ("unit-2", 3),
    ]
    assert store.reordered_units == ("company-1", "quote-1", payload["unit_ids"])


def test_reorder_units_requires_quotes_write_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.put(
            "/api/v1/quotes/quote-1/units/reorder",
            json={"unit_ids": ["unit-1", "unit-2"]},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: quotes:write"}
    assert store.reordered_units is None


def test_reorder_units_returns_404_for_invalid_unit_access():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.put(
            "/api/v1/quotes/quote-1/units/reorder",
            json={"unit_ids": ["unit-1", "missing"]},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Unit not found"}
    assert store.reordered_units is None


def test_reorder_units_surfaces_row_order_validation_errors():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.put(
            "/api/v1/quotes/quote-1/units/reorder",
            json={"unit_ids": ["unit-1", "partial"]},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Reorder payload must include every quote unit exactly once"}
    assert store.reordered_units is None


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


def test_get_quote_readiness_allows_libraries_pricing_action_target():
    readiness = quote_readiness("quote-1")
    readiness["checks"] = [
        {
            "id": "missing_prices",
            "severity": "warning",
            "title": "Activate a price list",
            "message": "Open Libraries > Pricing and make one price list active before trusting quote totals.",
            "action_label": "Open price lists",
            "action_target": "libraries-pricing",
        }
    ]
    store = FakeWorkspaceStore(quote_readiness_payload=readiness)
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/quotes/quote-1/readiness", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["checks"][0]["action_target"] == "libraries-pricing"
    assert response.json()["checks"][0]["action_label"] == "Open price lists"


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


def test_get_quote_production_handoff_returns_client_safe_grouped_packet():
    payload = quote_production_handoff("quote-1")
    payload["client_quote_total_cents"] = 999999
    payload["material_summary"]["groups"][0]["cost_total_cents"] = 120000
    payload["board_requirements"]["groups"][0]["cost_total_cents"] = 120000
    store = FakeWorkspaceStore(quote_production_handoff_payload=payload)
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/quotes/quote-1/production-handoff", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["quote_id"] == "quote-1"
    assert body["quote_number"] == "Q-001"
    assert body["groups"][0]["board_name"] == "PG White (16mm)"
    assert body["groups"][0]["rows"][0]["part_id"] == "Q-001-R1-U01-CAR-SIDE-748X564-01"
    assert body["material_summary"]["groups"][0]["part_ids"] == ["Q-001-R1-U01-CAR-SIDE-748X564-01"]
    assert body["board_requirements"]["estimate_label"] == "Sheet counts are estimates only; CoreQuote has not optimized board nesting."
    assert body["board_requirements"]["groups"][0]["part_ids"] == ["Q-001-R1-U01-CAR-SIDE-748X564-01"]
    assert body["board_requirements"]["groups"][0]["sheet_estimate_label"] == "1 estimated sheet (area estimate, not optimized nesting)."
    assert body["hardware_pick_list"]["items"][0]["related_part_ids"] == ["Q-001-R1-U01-CAR-SIDE-748X564-01"]
    assert "client_quote_total_cents" not in body
    assert "cost_total_cents" not in body["material_summary"]["groups"][0]
    assert "cost_total_cents" not in body["board_requirements"]["groups"][0]
    assert store.requested_quote_production_handoff == ("company-1", "quote-1")


def test_get_quote_production_handoff_requires_production_read_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/quotes/quote-1/production-handoff", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: production:read"}
    assert store.requested_quote_production_handoff is None


def test_get_quote_production_handoff_surfaces_cutlist_blockers():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store
    try:
        response = client.get("/api/v1/quotes/invalid-production/production-handoff", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Add cabinet units before building the production handoff."}


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


def test_download_production_handoff_csv_returns_attachment_and_uses_company_scope():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store

    try:
        response = client.get("/api/v1/quotes/quote-1/production-handoff.csv", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == 'attachment; filename="production-Smith-Kitchen-Q-001-rev-1.csv"'
    rows = list(csv.DictReader(StringIO(response.content.decode("utf-8"))))
    assert rows[0]["Part ID"] == "Q-001-R1-U01-CAR-SIDE-748X564-01"
    assert store.generated_production_handoff_export == ("company-1", "quote-1", "csv")


def test_download_production_handoff_xlsx_returns_workbook_attachment():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store

    try:
        response = client.get("/api/v1/quotes/quote-1/production-handoff.xlsx", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert response.headers["content-disposition"] == 'attachment; filename="production-Smith-Kitchen-Q-001-rev-1.xlsx"'
    assert response.content.startswith(b"PK")
    assert store.generated_production_handoff_export == ("company-1", "quote-1", "xlsx")


def test_download_production_handoff_export_requires_production_read_permission():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store

    try:
        response = client.get("/api/v1/quotes/quote-1/production-handoff.csv", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: production:read"}
    assert store.generated_production_handoff_export is None


def test_download_production_handoff_export_returns_404_if_quote_not_visible():
    store = FakeWorkspaceStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[projects_quotes.get_workspace_store] = lambda: store

    try:
        response = client.get("/api/v1/quotes/missing/production-handoff.xlsx", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Quote not found"}
    assert store.generated_production_handoff_export is None


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
    assert body["missing_prices"][0]["library_target"] == "pricing"
    assert body["missing_prices"][0]["catalog_target"] == "handles"
    assert "supplier cost first" in body["missing_prices"][0]["guidance_message"]
    assert body["quotes"][0]["missing_prices"][0]["item_ref_id"] == "handle-1"
    assert body["quotes"][0]["missing_prices"][0]["guidance_action_label"] == "Open Pricing"


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


class RecordingPricingConn:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql: str, params: tuple):
        self.calls.append((sql, params))
        return self

    def fetchone(self):
        return {"id": "price-list-1"}

    def fetchall(self):
        return [
            {
                "item_type": "handle",
                "item_key": "handle::handle-1",
                "price_component": "unit",
                "uom": "pcs",
                "unit_price_cents": 12000,
                "price_list_item_id": "price-item-1",
                "source_supplier_item_cost_id": None,
                "cost_source": "manual",
                "effective_from": datetime(2026, 5, 1, tzinfo=UTC),
                "effective_to": None,
            }
        ]


def test_quote_pricing_as_of_prefers_quote_updated_at():
    created_at = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
    updated_at = datetime(2026, 6, 1, 10, 30, tzinfo=UTC)

    assert _quote_pricing_as_of({"created_at": created_at, "updated_at": updated_at}) == updated_at


def test_workspace_price_lookup_respects_effective_date_and_company_scope():
    store = WorkspaceStore(database_url="postgresql://unused")
    conn = RecordingPricingConn()
    as_of = datetime(2026, 6, 12, 8, 0, tzinfo=UTC)

    lookup = store._get_price_lookup(conn, "company-1", "price-list-1", as_of)

    sql, params = conn.calls[0]
    assert "company_id = %s" in sql
    assert "effective_from <= %s" in sql
    assert "(effective_to IS NULL OR effective_to > %s)" in sql
    assert params == ("company-1", "price-list-1", as_of, as_of)
    assert lookup[("handle", "handle::handle-1", "unit")]["unit_price_cents"] == 12000


def test_workspace_active_price_list_respects_effective_date_and_company_scope():
    store = WorkspaceStore(database_url="postgresql://unused")
    conn = RecordingPricingConn()
    as_of = datetime(2026, 6, 12, 8, 0, tzinfo=UTC)

    assert store._get_active_price_list_id(conn, "company-1", as_of) == "price-list-1"

    sql, params = conn.calls[0]
    assert "company_id = %s" in sql
    assert "status = 'active'" in sql
    assert "(effective_from IS NULL OR effective_from <= %s)" in sql
    assert "(effective_to IS NULL OR effective_to >= %s)" in sql
    assert params == ("company-1", as_of.date(), as_of.date())


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
        "production_metadata": DEFAULT_PRODUCTION_METADATA,
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
        "production_metadata": DEFAULT_PRODUCTION_METADATA,
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
        "production_metadata": DEFAULT_PRODUCTION_METADATA,
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
        "production_metadata": DEFAULT_PRODUCTION_METADATA,
    }


def quote_custom_panels_state() -> dict:
    return {
        "presets": {
            "base_side_panel": {"qty": 1, "board_type_id": None, "production_metadata": DEFAULT_PRODUCTION_METADATA["visible_panel"]},
            "wall_side_filler": {"qty": 1, "board_type_id": None, "production_metadata": DEFAULT_PRODUCTION_METADATA["visible_panel"]},
        },
        "manual": [
            {
                "name": "Feature End",
                "length": 2300,
                "width": 300,
                "qty": 1,
                "board_type_id": None,
                "production_metadata": DEFAULT_PRODUCTION_METADATA["visible_panel"],
            },
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
            "production_metadata": DEFAULT_PRODUCTION_METADATA["visible_panel"],
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


def quote_production_handoff(quote_id: str) -> dict:
    part_id = "Q-001-R1-U01-CAR-SIDE-748X564-01"
    row = {
        "part_id": part_id,
        "project_id": "project-1",
        "project_name": "Main Kitchen",
        "quote_id": quote_id,
        "quote_name": "Kitchen Quote",
        "quote_number": "Q-001",
        "revision": 1,
        "source_type": "unit",
        "unit_number": 1,
        "unit_label": "Unit 1",
        "unit_type_key": "Base Door",
        "section": "carcass",
        "section_label": "Carcass",
        "material_role": "carcass",
        "role_label": "Carcass",
        "board_type_id": "board-1",
        "board_name": "PG White (16mm)",
        "brand": "PG",
        "material": "White",
        "thickness": 16,
        "sheet_length_mm": 2750,
        "sheet_width_mm": 1830,
        "desc": "Side",
        "length": 748,
        "width": 564,
        "quantity": 2,
        "warning_count": 0,
        "warning_messages": [],
    }
    return {
        "quote_id": quote_id,
        "quote_name": "Kitchen Quote",
        "quote_status": "ready",
        "quote_number": "Q-001",
        "revision": 1,
        "project_id": "project-1",
        "project_name": "Main Kitchen",
        "row_count": 1,
        "group_count": 1,
        "label_count": 1,
        "warning_count": 0,
        "groups": [
            {
                "group_key": "board-1::16::White::carcass::1::carcass",
                "board_type_id": "board-1",
                "board_name": "PG White (16mm)",
                "brand": "PG",
                "material": "White",
                "thickness": 16,
                "sheet_length_mm": 2750,
                "sheet_width_mm": 1830,
                "material_role": "carcass",
                "role_label": "Carcass",
                "unit_number": 1,
                "unit_label": "Unit 1",
                "section": "carcass",
                "section_label": "Carcass",
                "row_count": 1,
                "piece_count": 2,
                "warning_count": 0,
                "part_ids": [part_id],
                "rows": [row],
            }
        ],
        "rows": [row],
        "material_summary": {
            "groups": [
                {
                    "board_type_id": "board-1",
                    "material_role": "carcass",
                    "role_label": "Carcass",
                    "board_name": "PG White (16mm)",
                    "brand": "PG",
                    "material": "White",
                    "thickness": 16,
                    "length_mm": 2750,
                    "width_mm": 1830,
                    "piece_count": 2,
                    "area_m2": 0.84,
                    "edge_m": 0,
                    "estimated_sheets": 1,
                    "part_ids": [part_id],
                }
            ],
            "warnings": [],
            "total_area_m2": 0.84,
            "total_piece_count": 2,
            "total_edge_m": 0,
            "total_estimated_sheets": 1,
        },
        "board_requirements": {
            "estimate_label": "Sheet counts are estimates only; CoreQuote has not optimized board nesting.",
            "groups": [
                {
                    "requirement_key": "board-1::carcass",
                    "board_type_id": "board-1",
                    "board_name": "PG White (16mm)",
                    "brand": "PG",
                    "material": "White",
                    "thickness": 16,
                    "sheet_length_mm": 2750,
                    "sheet_width_mm": 1830,
                    "material_role": "carcass",
                    "role_label": "Carcass",
                    "row_count": 1,
                    "piece_count": 2,
                    "area_m2": 0.84,
                    "edge_m": 0,
                    "sheet_area_m2": 5.0325,
                    "estimated_sheets": 1,
                    "estimated_sheet_area_m2": 5.0325,
                    "waste_area_m2": 4.1925,
                    "waste_percent": 83.31,
                    "sheet_estimate_label": "1 estimated sheet (area estimate, not optimized nesting).",
                    "waste_allowance_label": "Estimated waste allowance 83.3% from sheet area minus part area.",
                    "part_ids": [part_id],
                    "source_labels": ["Unit 1"],
                    "warning_count": 0,
                    "warning_messages": [],
                }
            ],
            "warnings": [],
            "total_area_m2": 0.84,
            "total_piece_count": 2,
            "total_edge_m": 0,
            "total_estimated_sheets": 1,
            "total_estimated_sheet_area_m2": 5.0325,
            "total_waste_area_m2": 4.1925,
            "warning_count": 0,
        },
        "hardware_pick_list": {
            "items": [
                {
                    "part_id": "Q-001-R1-HW-HINGE-HINGE-1",
                    "item_type": "hinge",
                    "type_label": "Hinges",
                    "item_key": "hinge::hinge-1",
                    "item_ref_id": "hinge-1",
                    "item_name": "Blum Clip top",
                    "supplier": "Blum",
                    "code": "H110",
                    "quantity": 4,
                    "uom": "pcs",
                    "unit_numbers": [1],
                    "used_in": ["Unit 1 doors"],
                    "usage_label": "Unit 1 doors",
                    "related_part_ids": [part_id],
                }
            ],
            "warnings": [],
            "total_item_count": 1,
            "total_quantity": 4,
        },
        "labels": [
            {
                "part_id": part_id,
                "label": f"{part_id} · Side · 748 x 564 mm",
                "source_type": "unit",
                "unit_number": 1,
                "unit_label": "Unit 1",
                "section": "carcass",
                "desc": "Side",
                "dimensions_label": "748 x 564 mm",
                "material_label": "PG White (16mm)",
                "quantity": 2,
                "warning_count": 0,
            }
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
    item_type = overrides.get("item_type", "board")
    item_name = overrides.get("item_name", "PG White (16mm)")
    component = overrides.get("component", "Square metre price")
    catalog_target, catalog_target_label = {
        "board": ("boards", "Board library"),
        "slide": ("slides", "Slide library"),
        "hinge": ("hinges", "Hinge library"),
        "handle": ("handles", "Handle library"),
        "extra": ("extras", "Extra library"),
    }.get(item_type, (None, None))
    payload = {
        "item_type": item_type,
        "item_type_label": "Board",
        "item_key": "board::board-1",
        "item_ref_id": "board-1",
        "price_component": "sqm",
        "component": component,
        "bucket": "material",
        "item_name": item_name,
        "uom": "m2",
        "quantity": 1,
        "used_in": ["Carcass material"],
        "usage_label": "Carcass material",
        "affected_quote_id": "quote-1",
        "affected_quote_name": "Kitchen Quote",
        "library_area": "pricing",
        "action_label": "Add a price for PG White (16mm)",
        "message": "Add a price for PG White (16mm) using Square metre price in the pricing library.",
        "library_target": "pricing",
        "library_target_label": "Pricing",
        "catalog_target": catalog_target,
        "catalog_target_label": catalog_target_label,
        "guidance_action_label": "Open Pricing",
        "guidance_message": (
            f"{catalog_target_label or 'Catalog'} already appears on the quote. Open Pricing and add {component} for {item_name} "
            "to the active price list. If this price comes from suppliers, add the supplier cost first and generate prices."
        ),
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
