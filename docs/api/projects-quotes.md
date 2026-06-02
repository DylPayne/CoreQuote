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
- Project pricing summary read: `pricing:read`

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

## Quote Cutting List

```http
GET /api/v1/quotes/{quote_id}/cutting-list
```

Permission: `quotes:read`

This endpoint builds a live cutting list from the persisted quote units. It uses the same runtime engine as `POST /api/v1/cutlists/preview`, including ruleset runtime when `CUTLIST_USE_DB_RULESETS` is enabled.

The `extras` collection also includes quote-level custom panel rows (for example side panels/fillers, kickers, pelmets, and manual panel rows) generated from the saved quote panel configuration.

Response shape:

```json
{
  "quote_id": "quote-uuid",
  "carcass": [
    { "unit_number": 1, "desc": "Side", "length": 748, "width": 564, "qty": 2 }
  ],
  "panels": [
    { "unit_number": 1, "desc": "Door", "length": 777, "width": 297, "qty": 2 }
  ],
  "hardware": [],
  "extras": [
    { "unit_number": 0, "desc": "Kicker", "length": 1760, "width": 100, "qty": 1 }
  ],
  "runtime_rows": [
    {
      "unit_number": 0,
      "desc": "Kicker",
      "length": 1760,
      "width": 100,
      "qty": 1,
      "section": "extra_panel",
      "board_type_id": "board-uuid"
    }
  ],
  "runtime_mode": "legacy",
  "unit_sources": []
}
```

## Quote Extras Selection

```http
GET /api/v1/quotes/{quote_id}/extras
PUT /api/v1/quotes/{quote_id}/extras
```

Permissions:

- Read: `quotes:read`
- Replace selection: `quotes:write`

Request payload for `PUT`:

```json
{
  "items": [
    { "extra_id": "extra-uuid-1", "quantity": 2 },
    { "extra_id": "extra-uuid-2", "quantity": 1 }
  ]
}
```

Behavior notes:

- `PUT` is replace-all for the quote selection.
- Duplicate `extra_id` rows are merged server-side.
- `quantity` must be a positive integer.
- Extra IDs must be visible in the current company.

Response shape (`GET` and `PUT`):

```json
{
  "quote_id": "quote-uuid",
  "items": [
    { "extra_id": "extra-uuid-1", "quantity": 2 },
    { "extra_id": "extra-uuid-2", "quantity": 1 }
  ]
}
```

## Quote Custom Panels

```http
GET /api/v1/quotes/{quote_id}/custom-panels
PUT /api/v1/quotes/{quote_id}/custom-panels
```

Permissions:

- Read: `quotes:read`
- Replace configuration: `quotes:write`

`PUT` stores quote-level panel configuration used by cutting-list extras and pricing board usage.

Request payload for `PUT`:

```json
{
  "presets": {
    "base_side_panel": { "qty": 1, "board_type_id": "board-uuid" },
    "wall_side_filler": { "qty": 1, "board_type_id": null }
  },
  "manual": [
    { "name": "Feature End", "length": 2300, "width": 300, "qty": 1, "board_type_id": "board-uuid" }
  ],
  "auto": {
    "kicker_board_type_id": "board-uuid",
    "pelmet_board_type_id": "board-uuid",
    "kicker_return_count": 1,
    "kicker_return_depth_mm": 560,
    "kicker_override_on": false,
    "kicker_override_qty": 0,
    "kicker_override_length": 0,
    "kicker_override_width": 100,
    "pelmet_override_on": false,
    "pelmet_override_qty": 0,
    "pelmet_override_length": 0,
    "pelmet_override_width": 330
  }
}
```

Behavior notes:

- `kicker_return_count` and `kicker_return_depth_mm` add optional kicker return segments on top of total base-run width.
- Manual rows with non-positive length, width, or qty are ignored at save time.
- Any supplied `board_type_id` must be visible to the current company.

Response shape (`GET` and `PUT`):

```json
{
  "quote_id": "quote-uuid",
  "custom_panels": {
    "presets": {},
    "manual": [],
    "auto": {}
  },
  "computed_rows": [
    { "desc": "Kicker", "length": 1760, "width": 100, "qty": 1, "board_type_id": "board-uuid" }
  ]
}
```

## Project Pricing Summary

```http
GET /api/v1/projects/{project_id}/pricing
```

Permission: `pricing:read`

The endpoint builds a live project pricing summary by combining:

- Project quotes and units.
- Quote-selected extras.
- Active price-list items (`effective_to IS NULL`) if an active price list exists.
- Pricing settings (`vat_rate_bps`, `default_markup_bps`).

Response shape:

```json
{
  "project_id": "project-uuid",
  "project_name": "Smith Kitchen",
  "active_price_list_id": "price-list-uuid",
  "currency_code": "ZAR",
  "vat_rate_bps": 1500,
  "markup_bps": 2500,
  "is_complete": true,
  "subtotal_cents": 346783,
  "sell_before_vat_cents": 433479,
  "vat_cents": 65021,
  "grand_total_cents": 498000,
  "quotes": [
    {
      "quote_id": "quote-uuid",
      "quote_name": "Kitchen Quote v1",
      "is_complete": true,
      "missing_items": [],
      "subtotal_cents": 346783,
      "sell_before_vat_cents": 433479,
      "vat_cents": 65021,
      "grand_total_cents": 498000,
      "lines": []
    }
  ]
}
```

When a required item has no active price entry, it is returned in `missing_items`, line totals are omitted for that line, and `is_complete` is `false`.

## Frontend Integration Notes

- Project list can be loaded once via `GET /projects` and filtered with `search`.
- Opening a project should call `GET /projects/{project_id}/quotes`.
- Opening a quote should call `GET /quotes/{quote_id}/units`.
- Panels tab can load and save quote panel config via `GET/PUT /quotes/{quote_id}/custom-panels`.
- Cutting list tab can call `GET /quotes/{quote_id}/cutting-list`.
- Extras tab can load and save quote-selected extras via `GET/PUT /quotes/{quote_id}/extras`.
- Pricing tab can load project totals via `GET /projects/{project_id}/pricing` and format all cent values with the returned `currency_code`.
- Quote defaults are designed for fast unit creation UX: set defaults once on quote, then apply during add-unit flows.
