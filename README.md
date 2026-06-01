# CoreQuote

CoreQuote is a FastAPI + React cabinetry quoting and cutlist system for kitchen, built-in, and board-based joinery workflows.

It combines:

- project and quote management,
- unit-by-unit cabinet configuration,
- board and hardware libraries,
- cutlist generation,
- component counting,
- and PDF output.

## Status

CoreQuote is actively developed as:

- API: FastAPI (`apps/api`)
- Frontend: React + Vite (`apps/web`)
- Shared logic: `corequote_core` package (`packages/corequote-core`)
- Database: PostgreSQL with SQL migrations (`infra/db/migrations`)

Legacy surfaces:

- `apps/streamlit` is deprecated and not a current product development target.
- SQLite (`packages/corequote-core/corequote_core/database.py`, `data/corequote.db`, `data/slides.csv`) is deprecated and migration-only.

## Repository Layout

```text
CoreQuote/
├── apps/
│   ├── api/                              # FastAPI application
│   │   └── corequote_api/
│   ├── web/                              # React + Vite frontend
│   └── streamlit/                        # Deprecated legacy UI
├── packages/
│   └── corequote-core/
│       └── corequote_core/               # Shared domain/business logic
├── infra/
│   └── db/
│       ├── migrations/                   # PostgreSQL SQL migrations
│       ├── apply_migrations.py           # Migration runner
│       └── import_sqlite_libraries.py    # Legacy import helper
├── docs/
│   └── api/                              # API contracts
├── tests/
│   ├── api/
│   └── unit/
├── compose.yml                           # Local Postgres service
└── README.md
```

## Prerequisites

- Python 3.14+
- Node.js 20+
- Docker (for local Postgres)
- `uv` (recommended) or `pip` + virtualenv

## Quick Start

1. Clone and enter the repo.

```bash
git clone https://github.com/DylPayne/CoreQuote.git
cd CoreQuote
```

2. Install Python dependencies.

```bash
uv sync
```

Alternative setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

3. Configure environment.

```bash
cp .env.example .env
```

4. Start local Postgres.

```bash
docker compose up -d postgres
```

5. Apply database migrations.

```bash
DATABASE_URL=postgresql://corequote:corequote_dev_password@localhost:5433/corequote_dev \
uv run python infra/db/apply_migrations.py
```

6. Install frontend dependencies.

```bash
cd apps/web
npm install
cd ../..
```

## Run Locally

Start the API from the repository root:

```bash
uv run uvicorn corequote_api.main:app --app-dir apps/api --reload --port 8000
```

Start the frontend in a second terminal:

```bash
cd apps/web
npm run dev
```

By default, the frontend targets `http://localhost:8000`. Override with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Local Test Login

For frontend QA with seeded local data:

- Company: `CoreQuote Test Co`
- Name: `Test Owner`
- Email: `test.owner@corequote.local`
- Password: `CoreQuoteTestPass123!`

If login fails, verify the API is connected to your local Postgres database.

## Testing

Run the full suite:

```bash
uv run pytest
```

Focused runs:

```bash
uv run pytest tests/unit
uv run pytest tests/api
```

## API Notes

- API base path: `/api/v1`
- Auth contract: `docs/api/auth.md`
- RBAC contract: `docs/api/rbac.md`
- Libraries API: `docs/api/libraries.md`
- Cutlists API: `docs/api/cutlists.md`

Bearer auth is required for protected endpoints:

```http
Authorization: Bearer <access_token>
```

## Database and Migrations

- Product database is PostgreSQL.
- Migrations are forward-only SQL files in `infra/db/migrations`.
- The migration runner tracks applied files in `schema_migrations`.
- Legacy SQLite import exists only for explicit migration support.

See: `infra/db/README.md`.

## Development Guidelines

- Keep API code in `apps/api`, frontend code in `apps/web`, and shared logic in `packages/corequote-core/corequote_core`.
- Use shared frontend primitives in `apps/web/src/components/ui`.
- Scope company-owned data by authenticated `company_id`.
- Add or update tests with behavior changes.

## License

No license file is currently included.
