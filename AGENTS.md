# AGENTS.md

Guidance for AI agents working in this repository.

## Project Overview

CoreQuote is a FastAPI + React cabinetry quoting and cutlist system for kitchen, built-in, and board-based joinery workflows. It combines project and quote management, cabinet unit configuration, board and hardware libraries, cutting list generation, component counting, and PDF output.

The current codebase is a Python project with:

- React UI in `apps/web`.
- FastAPI API layer in `apps/api`.
- Reusable business logic in `packages/corequote-core/corequote_core`.
- PostgreSQL persistence managed through migrations in `infra/db/migrations`.
- Tests in `tests/unit` and `tests/api`.

Deprecated legacy surfaces:

- `apps/streamlit` is deprecated and no longer used. Do not add features, fixes, styling changes, or new workflows there unless the user explicitly asks for legacy migration support.
- SQLite persistence in `packages/corequote-core/corequote_core/database.py`, `data/corequote.db`, and `data/slides.csv` is deprecated and no longer used for product development. Do not extend SQLite schemas, helpers, seed data, or tests. New persistence work must be designed for PostgreSQL first.

## Setup Commands

Preferred setup with uv:

```bash
uv sync
```

Alternative setup with venv and pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run the React frontend:

```bash
cd apps/web
npm run dev
```

TODO: Confirm the intended local FastAPI run command before relying on it for development workflows.

## Testing Commands

Run the full test suite:

```bash
uv run pytest
```

Alternative when using an activated virtual environment:

```bash
pytest
```

Run focused tests while developing:

```bash
uv run pytest tests/unit
uv run pytest tests/api
```

Always run the relevant tests before finishing. For changes to shared business logic, run the full suite unless there is a clear reason not to.

## Code Style

- Follow the existing Python style in the touched files.
- Keep functions small and behavior explicit.
- Prefer typed datamodels and existing helper functions over ad hoc dictionaries or string manipulation.
- Keep React UI code in `apps/web`, API code in `apps/api`, and reusable business logic in `packages/corequote-core/corequote_core`.
- Do not introduce a new formatter, linter, framework, or architectural pattern without approval.
- TODO: Add the canonical formatter/linter command if the project adopts one.

## Frontend Styling

- Keep frontend styling global and token-driven. Colours, typography, spacing density, radii, shadows, and shared control sizing should come from global theme/style variables and shared primitives.
- Keep the React frontend visually and structurally uniform by composing UI from shared shadcn-style primitives in `apps/web/src/components/ui`.
- Do not hand-style raw `button`, `input`, `select`, table, alert, card, badge, or navigation controls inside feature code when a shared primitive exists. If a new UI pattern is needed, add or extend a reusable primitive first, then consume it from the feature.
- Do not hardcode one-off visual styling inside individual components when the same decision belongs in the app-wide design system.
- Local component classes should be limited to layout, responsive placement, and content-specific structure unless there is a clear reason to extend the shared primitives.

## Database and Migration Rules

- The product database is PostgreSQL. Design schema and persistence behavior for PostgreSQL first.
- Database migrations live in `infra/db/migrations` and are applied with `infra/db/apply_migrations.py`.
- Do not add new SQLite tables, migrations, helpers, or tests. SQLite files and `apps/streamlit` are legacy migration references only.
- Do not hand-edit `data/corequote.db` unless the user explicitly asks for legacy data recovery.
- Do not run destructive database commands, data wipes, bulk updates, or migration rewrites without explicit confirmation.
- Keep schema changes small, backwards-compatible where possible, and covered by tests when they affect business behavior.
- Explain any migration strategy before implementing it.

## API and Database Development

- Use a test-driven development workflow for API and database work: add or update focused tests first, implement the smallest change that satisfies them, then run the relevant tests before finishing.
- Protect new API endpoints with bearer authentication and the central role-based permission helpers unless the endpoint is explicitly public.
- Scope all company-owned database reads and writes by the authenticated user's `company_id`.
- Document every new or changed API contract in `docs/api` with request/response examples, auth requirements, permissions, error responses, and frontend integration notes.
- Keep database migrations forward-only, reviewable, and paired with tests that cover the affected API or persistence behavior.

## Git Workflow

- Always run `git status --short --branch` before editing.
- Never work directly on `main` or `master`.
- Create a focused feature branch for each task.
- Keep commits and file changes small, coherent, and reviewable.
- Do not revert, overwrite, or clean up user changes unless explicitly asked.
- Review diffs before finishing.
- If generated files or local data change unexpectedly, investigate before including them.

## Change Management

- Keep changes scoped to the user request.
- Do not add dependencies without explicit approval.
- Do not change architecture, persistence strategy, deployment strategy, or public interfaces without explaining the plan first.
- Add or update tests for business logic changes.
- Prefer focused tests for narrow changes and broader regression tests for shared calculation, pricing, persistence, or API behavior.
- Never hardcode secrets, tokens, credentials, private keys, or environment-specific values.
- Use environment variables or existing configuration patterns for sensitive or machine-specific settings.

## Deployment Safety

- Do not run deployment commands without explicit confirmation.
- Do not run AWS, cloud, production, or remote infrastructure commands without explicit confirmation.
- Do not run destructive commands without explicit confirmation. This includes commands that delete files, reset Git state, wipe databases, modify production data, or alter deployed infrastructure.
- Treat commands involving `rm`, `git reset`, `git clean`, database deletion, AWS CLI, Terraform, Docker deployment, or production credentials as confirmation-required.
- If a command could affect data or infrastructure outside the local working tree, stop and ask first.

## Final Response Format

When finishing a task, respond with:

- A short summary of what changed.
- The tests or checks run, with results.
- Any commands intentionally not run and why.
- Any remaining TODOs, risks, or follow-up recommendations.
- Relevant file paths using absolute paths when possible.

Keep the final response concise and focused on what the reviewer needs to know.
