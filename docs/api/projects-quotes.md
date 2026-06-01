# Projects, Quotes, and Units API Contract

This API replaces the legacy Streamlit project/quote/unit workflow with a PostgreSQL-first, tenant-scoped contract.

Base path:

```http
/api/v1
```

Auth header:

```http
Authorization: Bearer <access_token>
```

All rows are scoped to `current_user.company_id`.

## Permissions

- Project read: `projects:read`
- Project create/update/delete: `projects:write`
- Quote and unit read: `quotes:read`
- Quote and unit create/update/delete: `quotes:write`

The API returns:

- `401` for missing/invalid bearer sessions.
- `403` for missing permissions.
- `404` when a project/quote/unit is not visible to the current company.
- `422` for validation errors (for example invalid defaults or non-positive dimensions).
- `409` for write conflicts.

## Projects

```http
GET    /api/v1/projects?search=smith
POST   /api/v1/projects
GET    /api/v1/projects/{project_id}
PATCH  /api/v1/projects/{project_id}
DELETE /api/v1/projects/{project_id}
```

Request payload (`POST` / `PATCH`):

```json
{
  "name": "Smith Kitchen",
  "client": "John Smith",
  "address": "12 Oak Street",
  "description": "Kitchen renovation"
}
```

Response includes derived quote count:

```json
{
  "id": "project-uuid",
  "company_id": "company-uuid",
  "name": "Smith Kitchen",
  "client": "John Smith",
  "address": "12 Oak Street",
  "description": "Kitchen renovation",
  "quote_count": 2,
  "created_at": "2026-06-01T10:30:00Z",
  "updated_at": "2026-06-01T10:30:00Z"
}
```

## Quotes

```http
GET   /api/v1/projects/{project_id}/quotes
POST  /api/v1/projects/{project_id}/quotes
GET   /api/v1/quotes/{quote_id}
PATCH /api/v1/quotes/{quote_id}
DELETE /api/v1/quotes/{quote_id}
```

Request payload (`POST` / `PATCH`):

```json
{
  "name": "Kitchen Quote v1",
  "notes": "Client wants matte white doors",
  "default_carcass_board_type_id": "board-uuid",
  "default_door_board_type_id": "board-uuid",
  "default_panel_board_type_id": "board-uuid",
  "default_slide_id": "slide-uuid",
  "default_hinge_id": "hinge-uuid",
  "default_base_handle_id": "handle-uuid",
  "default_wall_handle_id": "handle-uuid",
  "default_tall_handle_id": "handle-uuid",
  "default_drawer_handle_id": "handle-uuid",
  "unit_defaults": {
    "Base Draw": { "height": 780, "depth": 580 },
    "Base Door": { "height": 780, "depth": 580 },
    "Wall Door": { "height": 720, "depth": 330 },
    "Tall Door": { "height": 2100, "depth": 580 }
  }
}
```

Quote responses include `unit_count` so UIs can render quote cards without extra unit queries.

## Quote Units

```http
GET    /api/v1/quotes/{quote_id}/units
POST   /api/v1/quotes/{quote_id}/units
PATCH  /api/v1/quotes/{quote_id}/units/{unit_id}
DELETE /api/v1/quotes/{quote_id}/units/{unit_id}
```

Request payload (`POST` / `PATCH`):

```json
{
  "unit_type_key": "Base Draw",
  "height": 780,
  "width": 900,
  "depth": 580,
  "thickness": 16,
  "carcass_board_type_id": "board-uuid",
  "door_board_type_id": "board-uuid",
  "extra_params": {
    "num_drawers": 3
  }
}
```

Response shape:

```json
{
  "id": "unit-uuid",
  "company_id": "company-uuid",
  "quote_id": "quote-uuid",
  "unit_number": 1,
  "unit_type_key": "Base Draw",
  "height": 780,
  "width": 900,
  "depth": 580,
  "thickness": 16,
  "carcass_board_type_id": "board-uuid",
  "door_board_type_id": "board-uuid",
  "extra_params": { "num_drawers": 3 },
  "created_at": "2026-06-01T10:30:00Z",
  "updated_at": "2026-06-01T10:30:00Z"
}
```

Unit numbering is sequential per quote. On delete, remaining units are automatically renumbered to keep a gapless order for UI display and cutlist workflows.

## Frontend Integration Notes

- Project list can be loaded once via `GET /projects` and filtered with `search`.
- Opening a project should call `GET /projects/{project_id}/quotes`.
- Opening a quote should call `GET /quotes/{quote_id}/units`.
- Quote defaults are designed for fast unit creation UX: set defaults once on quote, then apply during add-unit flows.
