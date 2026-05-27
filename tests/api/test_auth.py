from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from corequote_api.auth import (
    AuthenticatedUser,
    AuthSession,
    EmailAlreadyRegistered,
    InvalidCredentials,
)
from corequote_api.main import app
from corequote_api.routers import auth


client = TestClient(app)


class FakeAuthStore:
    def __init__(self):
        self.user = AuthenticatedUser(
            id="user-1",
            company_id="company-1",
            company_name="Core Cabinets",
            name="Dylan Payne",
            email="dylan@example.com",
            role="owner",
        )
        self.revoked_token: str | None = None

    def register_company_owner(self, *, company_name: str, name: str, email: str, password: str) -> AuthSession:
        if email == "taken@example.com":
            raise EmailAlreadyRegistered()
        return self._session()

    def login(self, *, email: str, password: str) -> AuthSession:
        if email != "dylan@example.com" or password != "correct-horse-battery-staple":
            raise InvalidCredentials()
        return self._session()

    def get_user_for_token(self, token: str) -> AuthenticatedUser | None:
        if token == "test-token":
            return self.user
        return None

    def revoke_session(self, token: str) -> None:
        self.revoked_token = token

    def _session(self) -> AuthSession:
        return AuthSession(
            access_token="test-token",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            user=self.user,
        )


def test_register_creates_company_owner_session():
    store = FakeAuthStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "company_name": "Core Cabinets",
                "name": "Dylan Payne",
                "email": "dylan@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] == "test-token"
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": "user-1",
        "company_id": "company-1",
        "company_name": "Core Cabinets",
        "name": "Dylan Payne",
        "email": "dylan@example.com",
        "role": "owner",
    }


def test_register_returns_409_for_existing_email():
    store = FakeAuthStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "company_name": "Core Cabinets",
                "name": "Dylan Payne",
                "email": "taken@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {"detail": "Email is already registered"}


def test_login_creates_session():
    store = FakeAuthStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "dylan@example.com",
                "password": "correct-horse-battery-staple",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["access_token"] == "test-token"


def test_me_requires_valid_bearer_token():
    store = FakeAuthStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: store
    try:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["company_id"] == "company-1"


def test_me_returns_401_without_token():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_logout_revokes_session():
    store = FakeAuthStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert store.revoked_token == "test-token"
