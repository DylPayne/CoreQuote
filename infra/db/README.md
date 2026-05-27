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

## Auth And Tenancy Model

- Each `user` belongs to exactly one `company`.
- The first registered user for a new company is created with the `owner` role.
- Bearer tokens are opaque server-side session tokens. Only a SHA-256 token hash is stored in Postgres.
- Company-owned business tables should include `company_id` and every future API query should scope by the authenticated user's `company_id`.
- Existing quote data is company-scoped through `projects.company_id`; quote queries should always join through `projects`.

Frontend clients should treat the auth API contract in `docs/api/auth.md` as the source of truth.
