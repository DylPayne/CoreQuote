from fastapi.testclient import TestClient

from corequote_api.auth import AuthenticatedUser
from corequote_api.database import DatabaseHealth
from corequote_api.main import app
from corequote_api.routers import auth, cutlists, health


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


class FakeCutlistRuntimeService:
    def __init__(self, result: dict):
        self.result = result
        self.calls: list[dict] = []

    def build_preview(self, *, company_id: str, units: list[dict], use_db_rulesets: bool) -> dict:
        self.calls.append(
            {
                "company_id": company_id,
                "units": units,
                "use_db_rulesets": use_db_rulesets,
            }
        )
        return self.result


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
    assert body["hardware"] == []
    assert body["extras"] == []
    assert body["runtime_mode"] == "legacy"
    assert body["unit_sources"] == [
        {
            "unit_number": 1,
            "unit_type_key": "Base Door",
            "source": "legacy",
            "ruleset_id": None,
            "unit_config_id": None,
            "note": None,
        }
    ]


def test_cutlist_preview_uses_ruleset_runtime_when_feature_flag_enabled(monkeypatch):
    runtime_service = FakeCutlistRuntimeService(
        result={
            "carcass": [{"unit_number": 1, "desc": "Company Side", "length": 748, "width": 544, "qty": 2}],
            "panels": [{"unit_number": 1, "desc": "Door", "length": 777, "width": 447, "qty": 2}],
            "hardware": [],
            "extras": [],
            "runtime_rows": [
                {
                    "unit_number": 1,
                    "section": "carcass",
                    "desc": "Company Side",
                    "length": 748,
                    "width": 544,
                    "qty": 2,
                    "edge_long_1": False,
                    "edge_long_2": False,
                    "edge_short_1": False,
                    "edge_short_2": False,
                }
            ],
            "runtime_mode": "ruleset",
            "unit_sources": [
                {
                    "unit_number": 1,
                    "unit_type_key": "Base Door",
                    "source": "ruleset",
                    "ruleset_id": "company-ruleset",
                    "unit_config_id": "company-config",
                    "note": None,
                }
            ],
        }
    )
    monkeypatch.setenv("CUTLIST_USE_DB_RULESETS", "true")
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore()
    app.dependency_overrides[cutlists.get_cutlist_runtime_service] = lambda: runtime_service
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
        monkeypatch.delenv("CUTLIST_USE_DB_RULESETS", raising=False)

    assert response.status_code == 200
    assert response.json()["runtime_mode"] == "ruleset"
    assert runtime_service.calls[0]["company_id"] == "company-1"
    assert runtime_service.calls[0]["use_db_rulesets"] is True


def test_cutlist_preview_accepts_custom_unit_type_strings(monkeypatch):
    runtime_service = FakeCutlistRuntimeService(
        result={
            "carcass": [],
            "panels": [],
            "hardware": [],
            "extras": [],
            "runtime_rows": [],
            "runtime_mode": "legacy",
            "unit_sources": [
                {
                    "unit_number": 1,
                    "unit_type_key": "Corner Door",
                    "source": "legacy",
                    "ruleset_id": None,
                    "unit_config_id": None,
                    "note": None,
                }
            ],
        }
    )
    monkeypatch.setenv("CUTLIST_USE_DB_RULESETS", "true")
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore()
    app.dependency_overrides[cutlists.get_cutlist_runtime_service] = lambda: runtime_service
    try:
        response = client.post(
            "/api/v1/cutlists/preview",
            json={
                "units": [
                    {
                        "unit_number": 1,
                        "unit_type": "Corner Door",
                        "height": 780,
                        "width": 900,
                        "depth": 560,
                        "thickness": 16,
                        "extra_params": {"num_doors": 2},
                    }
                ]
            },
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()
        monkeypatch.delenv("CUTLIST_USE_DB_RULESETS", raising=False)

    assert response.status_code == 200
    assert response.json()["unit_sources"][0]["unit_type_key"] == "Corner Door"
    assert runtime_service.calls[0]["units"][0]["unit_type"] == "Corner Door"


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
