from __future__ import annotations

import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import dict_row


class CompanyError(Exception):
    pass


class CompanyNotFound(CompanyError):
    pass


class CompanyConflict(CompanyError):
    pass


@dataclass(frozen=True)
class Company:
    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class CompanyStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")

    def create_company(self, *, name: str) -> Company:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO companies (name, slug)
                    VALUES (%s, %s)
                    RETURNING id::text, name, slug, created_at, updated_at
                    """,
                    (name.strip(), _company_slug(name)),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise CompanyConflict("Company slug is already in use") from exc

        return _company_from_row(row)

    def get_company(self, company_id: str) -> Company:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id::text, name, slug, created_at, updated_at
                FROM companies
                WHERE id = %s
                """,
                (company_id,),
            ).fetchone()

        if not row:
            raise CompanyNotFound("Company not found")
        return _company_from_row(row)

    def update_company(self, *, company_id: str, name: str) -> Company:
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE companies
                SET name = %s
                WHERE id = %s
                RETURNING id::text, name, slug, created_at, updated_at
                """,
                (name.strip(), company_id),
            ).fetchone()

        if not row:
            raise CompanyNotFound("Company not found")
        return _company_from_row(row)

    def delete_company(self, company_id: str) -> None:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    DELETE FROM companies
                    WHERE id = %s
                    RETURNING id::text
                    """,
                    (company_id,),
                ).fetchone()
        except psycopg.errors.ForeignKeyViolation as exc:
            raise CompanyConflict("Company cannot be deleted while related records exist") from exc

        if not row:
            raise CompanyNotFound("Company not found")

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for company database access")
        return psycopg.connect(self.database_url, row_factory=dict_row)


def _company_slug(company_name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", company_name.strip().lower()).strip("-")
    if not base:
        base = "company"
    return f"{base}-{secrets.token_hex(3)}"


def _company_from_row(row) -> Company:
    return Company(
        id=row["id"],
        name=row["name"],
        slug=row["slug"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
