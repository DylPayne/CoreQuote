from fastapi.testclient import TestClient

from corequote_api.auth import AuthenticatedUser
from corequote_api.database import DatabaseHealth
from corequote_api.main import app
from corequote_api.routers import auth, health


client = TestClient(app)


class FakeAuthStore:
    def get_user_for_token(self, token: str) -> AuthenticatedUser | None:
        if token != "test-token":
            return None
        return AuthenticatedUser(
            id="user-1",
            company_id="company-1",
            company_name="Core Cabinets",
            name="Dylan Payne",
            email="dylan@example.com",
            role="estimator",
        )


def test_health_endpoints():
    assert client.get("/health/live").json() == {"status": "ok", "service": "corequote-api"}
    assert client.get("/health/ready").json() == {"status": "ok", "service": "corequote-api"}


def test_api_allows_local_frontend_cors_preflight():
    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Access-Control-Request-Headers": "authorization",
            "Access-Control-Request-Method": "GET",
            "Origin": "http://127.0.0.1:5174",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"


def test_database_health_endpoint_checks_connection():
    def checker() -> DatabaseHealth:
        return DatabaseHealth(ok=True, database="corequote_dev")

    app.dependency_overrides[health.get_database_checker] = lambda: checker
    try:
        response = client.get("/health/db")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "corequote-api",
        "database": "corequote_dev",
    }


def test_database_health_endpoint_returns_503_when_connection_fails():
    def checker() -> DatabaseHealth:
        return DatabaseHealth(
            ok=False,
            database="corequote_dev",
            message="Database connection failed: OperationalError",
        )

    app.dependency_overrides[health.get_database_checker] = lambda: checker
    try:
        response = client.get("/health/db")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "status": "error",
            "service": "corequote-api",
            "database": "corequote_dev",
            "message": "Database connection failed: OperationalError",
        }
    }


def test_cutlist_preview_uses_core_cutlist_logic():
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore()
    try:
        response = client.post(
            "/api/v1/cutlists/preview",
            json={
                "units": [
                    {
                        "unit_number": 1,
                        "unit_type": "Base Door",
                        "height": 780,
                        "width": 900,
                        "depth": 560,
                        "thickness": 16,
                        "extra_params": {"num_doors": 2, "num_shelves": 1},
                    }
                ]
            },
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert {"unit_number": 1, "desc": "Side", "length": 748, "width": 544, "qty": 2} in body["carcass"]
    assert {"unit_number": 1, "desc": "Door", "length": 777, "width": 447, "qty": 2} in body["panels"]


def test_cutlist_preview_requires_authentication():
    response = client.post(
        "/api/v1/cutlists/preview",
        json={
            "units": [
                {
                    "unit_number": 1,
                    "unit_type": "Base Door",
                    "height": 780,
                    "width": 900,
                    "depth": 560,
                    "thickness": 16,
                    "extra_params": {"num_doors": 2, "num_shelves": 1},
                }
            ]
        },
    )

    assert response.status_code == 401
