from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row


PASSWORD_ITERATIONS = 390_000
SESSION_DAYS = 7


class AuthError(Exception):
    pass


class EmailAlreadyRegistered(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    company_id: str
    company_name: str
    name: str
    email: str
    role: str


@dataclass(frozen=True)
class AuthSession:
    access_token: str
    expires_at: datetime
    user: AuthenticatedUser


class AuthStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")

    def register_company_owner(
        self,
        *,
        company_name: str,
        name: str,
        email: str,
        password: str,
    ) -> AuthSession:
        normalized_email = normalize_email(email)
        password_hash = hash_password(password)
        company_slug = _company_slug(company_name)

        try:
            with self._connect() as conn:
                with conn.transaction():
                    company = conn.execute(
                        """
                        INSERT INTO companies (name, slug)
                        VALUES (%s, %s)
                        RETURNING id::text, name
                        """,
                        (company_name.strip(), company_slug),
                    ).fetchone()
                    user = conn.execute(
                        """
                        INSERT INTO users (company_id, email, name, password_hash, role)
                        VALUES (%s, %s, %s, %s, 'owner')
                        RETURNING
                            id::text,
                            company_id::text,
                            email::text,
                            name,
                            role
                        """,
                        (company["id"], normalized_email, name.strip(), password_hash),
                    ).fetchone()
                    auth_user = _user_from_rows(user, company)
                    return self._create_session(conn, auth_user)
        except psycopg.errors.UniqueViolation as exc:
            raise EmailAlreadyRegistered("Email is already registered") from exc

    def login(self, *, email: str, password: str) -> AuthSession:
        normalized_email = normalize_email(email)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    u.id::text,
                    u.company_id::text,
                    c.name AS company_name,
                    u.email::text,
                    u.name,
                    u.role,
                    u.password_hash,
                    u.is_active
                FROM users u
                JOIN companies c ON c.id = u.company_id
                WHERE u.email = %s
                """,
                (normalized_email,),
            ).fetchone()

            if not row or not row["is_active"] or not verify_password(password, row["password_hash"]):
                raise InvalidCredentials("Invalid email or password")

            return self._create_session(conn, _user_from_row(row))

    def get_user_for_token(self, token: str) -> AuthenticatedUser | None:
        token_hash = hash_token(token)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    u.id::text,
                    u.company_id::text,
                    c.name AS company_name,
                    u.email::text,
                    u.name,
                    u.role
                FROM auth_sessions s
                JOIN users u ON u.id = s.user_id
                JOIN companies c ON c.id = u.company_id
                WHERE s.token_hash = %s
                  AND s.revoked_at IS NULL
                  AND s.expires_at > now()
                  AND u.is_active = true
                """,
                (token_hash,),
            ).fetchone()
            if not row:
                return None

            conn.execute(
                "UPDATE auth_sessions SET last_seen_at = now() WHERE token_hash = %s",
                (token_hash,),
            )
            return _user_from_row(row)

    def revoke_session(self, token: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = now()
                WHERE token_hash = %s
                  AND revoked_at IS NULL
                """,
                (hash_token(token),),
            )

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for auth database access")
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _create_session(self, conn, user: AuthenticatedUser) -> AuthSession:
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(days=SESSION_DAYS)
        conn.execute(
            """
            INSERT INTO auth_sessions (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user.id, hash_token(token), expires_at),
        )
        return AuthSession(access_token=token, expires_at=expires_at, user=user)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "$".join(
        [
            "pbkdf2_sha256",
            str(PASSWORD_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(salt.encode("ascii")),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(
        base64.urlsafe_b64encode(digest).decode("ascii"),
        expected,
    )


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _company_slug(company_name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", company_name.strip().lower()).strip("-")
    if not base:
        base = "company"
    return f"{base}-{secrets.token_hex(3)}"


def _user_from_rows(user_row, company_row) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user_row["id"],
        company_id=user_row["company_id"],
        company_name=company_row["name"],
        name=user_row["name"],
        email=user_row["email"],
        role=user_row["role"],
    )


def _user_from_row(row) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=row["id"],
        company_id=row["company_id"],
        company_name=row["company_name"],
        name=row["name"],
        email=row["email"],
        role=row["role"],
    )
