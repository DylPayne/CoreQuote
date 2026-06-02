from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from corequote_api.auth import AuthenticatedUser
from corequote_api.companies import Company, CompanyConflict, CompanyNotFound
from corequote_api.main import app
from corequote_api.routers import auth, companies


client = TestClient(app)


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


class FakeCompanyStore:
    def __init__(self):
        now = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)
        self.company = Company(
            id="company-1",
            name="Core Cabinets",
            slug="core-cabinets-a1b2c3",
            created_at=now,
            updated_at=now,
            currency_code="ZAR",
        )
        self.created_name: str | None = None
        self.updated_payload: tuple[str, str | None, str | None] | None = None
        self.deleted_id: str | None = None
        self.conflict_on_delete = False

    def create_company(self, *, name: str) -> Company:
        self.created_name = name
        return Company(
            id="company-2",
            name=name.strip(),
            slug="new-shop-d4e5f6",
            created_at=self.company.created_at,
            updated_at=self.company.updated_at,
            currency_code="ZAR",
        )

    def get_company(self, company_id: str) -> Company:
        if company_id != self.company.id:
            raise CompanyNotFound()
        return self.company

    def update_company(
        self,
        *,
        company_id: str,
        name: str | None = None,
        currency_code: str | None = None,
    ) -> Company:
        if company_id != self.company.id:
            raise CompanyNotFound()
        self.updated_payload = (company_id, name, currency_code)
        self.company = Company(
            id=self.company.id,
            name=name.strip() if name is not None else self.company.name,
            slug=self.company.slug,
            created_at=self.company.created_at,
            updated_at=self.company.updated_at,
            currency_code=currency_code if currency_code is not None else self.company.currency_code,
        )
        return self.company

    def delete_company(self, company_id: str) -> None:
        if self.conflict_on_delete:
            raise CompanyConflict("Company cannot be deleted while related records exist")
        if company_id != self.company.id:
            raise CompanyNotFound()
        self.deleted_id = company_id


def test_create_company_requires_company_admin_permission():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="member")
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/companies",
            json={"name": "New Shop"},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert store.created_name is None


def test_create_company_returns_created_company():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore()
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/companies",
            json={"name": "New Shop"},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert store.created_name == "New Shop"
    assert response.json()["name"] == "New Shop"
    assert response.json()["slug"] == "new-shop-d4e5f6"
    assert response.json()["currency_code"] == "ZAR"


def test_list_companies_returns_current_company_only():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="member")
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.get(
            "/api/v1/companies",
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [company["id"] for company in response.json()] == ["company-1"]
    assert response.json()[0]["currency_code"] == "ZAR"


def test_get_company_hides_other_companies():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore()
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.get(
            "/api/v1/companies/company-2",
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Company not found"}


def test_update_company_renames_current_company():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore()
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/companies/company-1",
            json={"name": "Core Cabinets Ltd"},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["name"] == "Core Cabinets Ltd"
    assert response.json()["slug"] == "core-cabinets-a1b2c3"
    assert response.json()["currency_code"] == "ZAR"
    assert store.updated_payload == ("company-1", "Core Cabinets Ltd", None)


def test_update_company_changes_currency_for_owner():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/companies/company-1",
            json={"currency_code": "usd"},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["currency_code"] == "USD"
    assert store.updated_payload == ("company-1", None, "USD")


def test_update_company_currency_requires_owner_role():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="admin")
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/companies/company-1",
            json={"currency_code": "USD"},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Only company owners can change company currency"}
    assert store.updated_payload is None


def test_update_company_requires_a_field():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/companies/company-1",
            json={},
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {"detail": "At least one company field is required"}
    assert store.updated_payload is None


def test_delete_company_returns_409_when_related_records_exist():
    store = FakeCompanyStore()
    store.conflict_on_delete = True
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore()
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.delete(
            "/api/v1/companies/company-1",
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {"detail": "Company cannot be deleted while related records exist"}


def test_delete_company_returns_204():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore()
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.delete(
            "/api/v1/companies/company-1",
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""
    assert store.deleted_id == "company-1"


def test_delete_company_requires_owner_role():
    store = FakeCompanyStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="admin")
    app.dependency_overrides[companies.get_company_store] = lambda: store
    try:
        response = client.delete(
            "/api/v1/companies/company-1",
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: companies:delete"}
    assert store.deleted_id is None
