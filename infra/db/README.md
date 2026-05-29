# CoreQuote Database

This folder stores database-owned objects that should live in source control, not only in pgAdmin.

## Migrations

Migrations live in `infra/db/migrations` and are applied in filename order.

Run them against the local Docker Postgres database:

```bash
DATABASE_URL=postgresql://corequote:corequote_dev_password@localhost:5433/corequote_dev \
uv run python infra/db/apply_migrations.py
```

The runner records applied files in `schema_migrations` so repeated runs are safe.

## Legacy SQLite Library Import

SQLite and Streamlit are deprecated and are not product development targets. This importer exists only to migrate old local library rows into Postgres when explicitly needed.

Legacy Streamlit library rows can be imported into a specific company with:

```bash
DATABASE_URL=postgresql://corequote:corequote_dev_password@localhost:5433/corequote_dev \
uv run python infra/db/import_sqlite_libraries.py \
  --company-id <company-uuid> \
  --sqlite-path data/corequote.db
```

The importer is repeatable. It upserts catalog rows by their company-scoped natural keys, maps old SQLite integer IDs to new UUIDs, rewrites ID-based price item keys such as `board::1::sheet` and `extra::1` to imported UUID rows, and separates board price components such as `sheet`, `sqm`, `edging_m`, and `labour_board`.

## Auth And Tenancy Model

- Each `user` belongs to exactly one `company`.
- The first registered user for a new company is created with the `owner` role.
- Valid user roles are `owner`, `admin`, `manager`, `estimator`, `production`, `viewer`, and legacy `member`.
- Bearer tokens are opaque server-side session tokens. Only a SHA-256 token hash is stored in Postgres.
- Company-owned business tables should include `company_id` and every future API query should scope by the authenticated user's `company_id`.
- Existing quote data is company-scoped through `projects.company_id`; quote queries should always join through `projects`.
- Company library tables for boards, slides, hinges, handles, extras, and price lists are created by `0003_company_libraries.sql`.
- Versioned pricing and company pricing defaults are created by `0004_versioned_pricing.sql`.

Frontend clients should treat the auth API contract in `docs/api/auth.md`, the RBAC contract in `docs/api/rbac.md`, and the libraries contract in `docs/api/libraries.md` as the source of truth.
