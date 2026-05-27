from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class DatabaseHealth:
    ok: bool
    database: str
    message: str | None = None


def check_database_connection(database_url: str | None = None) -> DatabaseHealth:
    url = database_url or os.environ.get("DATABASE_URL")
    database = _database_name(url)
    if not url:
        return DatabaseHealth(
            ok=False,
            database=database,
            message="DATABASE_URL is not configured",
        )

    try:
        import psycopg
    except ImportError:
        return DatabaseHealth(
            ok=False,
            database=database,
            message="Postgres driver is not installed",
        )

    try:
        with psycopg.connect(url, connect_timeout=2) as conn:
            with conn.cursor() as cursor:
                cursor.execute("select 1")
                cursor.fetchone()
    except Exception as exc:
        return DatabaseHealth(
            ok=False,
            database=database,
            message=f"Database connection failed: {exc.__class__.__name__}",
        )

    return DatabaseHealth(ok=True, database=database)


def _database_name(database_url: str | None) -> str:
    if not database_url:
        return "unknown"
    path = urlparse(database_url).path
    return path.lstrip("/") or "unknown"
