from __future__ import annotations

import os
from pathlib import Path

import psycopg


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def apply_migrations(database_url: str | None = None) -> list[str]:
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required to apply database migrations")

    applied_now: list[str] = []
    with psycopg.connect(url) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version     TEXT PRIMARY KEY,
                applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.commit()

        applied = {
            row[0]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration.name in applied:
                continue

            with conn.transaction():
                conn.execute(migration.read_text())
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (migration.name,),
                )
            applied_now.append(migration.name)

    return applied_now


if __name__ == "__main__":
    migrations = apply_migrations()
    if migrations:
        for migration in migrations:
            print(f"Applied {migration}")
    else:
        print("No pending migrations")
