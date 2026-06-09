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
- Project and quote pricing settings read: `pricing:read`
- Project and quote pricing settings update: `pricing:update`

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
PATCH /api/v1/quotes/{quote_id}/status
POST  /api/v1/quotes/{quote_id}/revisions
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

Quote responses include `unit_count`, status, quote number, and revision fields so UIs can render quote cards without extra unit queries:

```json
{
  "id": "quote-uuid",
  "company_id": "company-uuid",
  "project_id": "project-uuid",
  "name": "Kitchen Quote v1",
  "notes": "Client wants matte white doors",
  "status": "sent",
  "quote_number": "Q-001",
  "revision": 1,
  "previous_revision_id": null,
  "previous_revision_quote_number": null,
  "previous_revision_revision": null,
  "unit_count": 5,
  "created_at": "2026-06-01T10:30:00Z",
  "updated_at": "2026-06-01T10:30:00Z"
}
```

Status values:

- `draft`: The quote is still being prepared and is safe to edit.
- `ready`: The quote is ready for review or sending.
- `sent`: The quote has been sent to the client.
- `accepted`: The client has accepted this quote.
- `rejected`: The client has rejected this quote.
- `revised`: The quote has been superseded by later client changes.
- `expired`: The quote is no longer valid.

`POST /api/v1/projects/{project_id}/quotes` creates quotes as `draft`, with the next project quote number and revision `1`.

Status update payload:

```json
{
  "status": "ready"
}
```

Status changes are permissive in this version so cabinetmakers can reflect the real job conversation without workflow lock-in.

Creating a revision:

```http
POST /api/v1/quotes/{quote_id}/revisions
```

The API copies the source quote header, units, custom panel configuration, selected extras, and quote pricing settings. The new quote keeps the same `quote_number`, increments `revision`, links `previous_revision_id`, and starts as `draft`. The source quote is not changed, so a sent or accepted record remains visible as it was.

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

## Project and Quote Pricing Settings

```http
GET   /api/v1/projects/{project_id}/pricing-settings
PATCH /api/v1/projects/{project_id}/pricing-settings
GET   /api/v1/quotes/{quote_id}/pricing-settings
PATCH /api/v1/quotes/{quote_id}/pricing-settings
```

Project pricing settings are copied from company pricing defaults when a project
is created. Quote pricing settings are copied from the project's current pricing
defaults when a quote is created. Updating company settings only changes future
project snapshots, and updating project settings only changes future quote
snapshots. Existing project and quote pricing settings are not rewritten by
parent default changes.

Request payload (`PATCH`):

```json
{
  "vat_rate_bps": 1500,
  "default_markup_bps": 2500,
  "carcass_markup_bps": 2500,
  "door_panel_markup_bps": 2500,
  "component_markup_bps": 2500,
  "handle_markup_bps": 2500,
  "extras_markup_bps": 2500,
  "fabrication_markup_bps": 2500,
  "install_markup_bps": 2500,
  "delivery_markup_bps": 2500,
  "joinery_commission_bps": 0,
  "labour_cents_per_m2": 2000,
  "consumables_cents_per_m2": 1000,
  "install_day_cost_cents": 190000,
  "delivery_base_cents": 95000,
  "install_units_per_day": 3,
  "delivery_units_per_trip": 20,
  "minimum_install_days_bps": 5000,
  "minimum_delivery_trips_bps": 5000
}
```

Project response:

```json
{
  "company_id": "company-uuid",
  "project_id": "project-uuid",
  "vat_rate_bps": 1500,
  "default_markup_bps": 2500,
  "created_at": "2026-06-01T10:30:00Z",
  "updated_at": "2026-06-01T10:30:00Z"
}
```

Quote response uses the same fields and replaces `project_id` with `quote_id`.

## Project Pricing Summary

```http
GET /api/v1/projects/{project_id}/pricing
```

Permission: `pricing:read`

The endpoint builds a live project pricing summary by combining:

- Project quotes and units.
- Quote-selected extras.
- Active price-list items (`effective_to IS NULL`) if an active price list exists.
- Project pricing defaults for project metadata.
- Each quote's own pricing settings for quote calculations.

Response shape:

```json
{
  "project_id": "project-uuid",
  "project_name": "Smith Kitchen",
  "active_price_list_id": "price-list-uuid",
  "currency_code": "ZAR",
  "vat_rate_bps": 1500,
  "markup_bps": 2500,
  "pricing_settings": {
    "company_id": "company-uuid",
    "project_id": "project-uuid",
    "vat_rate_bps": 1500,
    "default_markup_bps": 2500,
    "carcass_markup_bps": 2500,
    "door_panel_markup_bps": 2500,
    "component_markup_bps": 2500,
    "handle_markup_bps": 2500,
    "extras_markup_bps": 2500,
    "fabrication_markup_bps": 2500,
    "install_markup_bps": 2500,
    "delivery_markup_bps": 2500,
    "joinery_commission_bps": 0,
    "labour_cents_per_m2": 2000,
    "consumables_cents_per_m2": 1000,
    "install_day_cost_cents": 190000,
    "delivery_base_cents": 95000,
    "install_units_per_day": 3,
    "delivery_units_per_trip": 20,
    "minimum_install_days_bps": 5000,
    "minimum_delivery_trips_bps": 5000,
    "created_at": "2026-06-01T10:30:00Z",
    "updated_at": "2026-06-01T10:30:00Z"
  },
  "is_complete": true,
  "subtotal_cents": 346783,
  "cost_total_cents": 346783,
  "sell_before_vat_cents": 433479,
  "vat_cents": 65021,
  "grand_total_cents": 498000,
  "profit_cents": 86696,
  "bucket_totals": [
    {
      "bucket": "material",
      "cost_total_cents": 120000,
      "sell_total_cents": 180000,
      "profit_cents": 60000
    }
  ],
  "quotes": [
    {
      "quote_id": "quote-uuid",
      "quote_name": "Kitchen Quote v1",
      "quote_status": "sent",
      "quote_number": "Q-001",
      "revision": 1,
      "previous_revision_id": null,
      "previous_revision_quote_number": null,
      "previous_revision_revision": null,
      "vat_rate_bps": 1500,
      "markup_bps": 2500,
      "pricing_settings": {
        "company_id": "company-uuid",
        "quote_id": "quote-uuid",
        "vat_rate_bps": 1500,
        "default_markup_bps": 2500,
        "created_at": "2026-06-01T10:30:00Z",
        "updated_at": "2026-06-01T10:30:00Z"
      },
      "is_complete": true,
      "missing_items": [],
      "subtotal_cents": 346783,
      "cost_total_cents": 346783,
      "sell_before_vat_cents": 433479,
      "vat_cents": 65021,
      "grand_total_cents": 498000,
      "profit_cents": 86696,
      "bucket_totals": [],
      "lines": [
        {
          "item_type": "board",
          "item_key": "board::board-uuid",
          "price_component": "sqm",
          "bucket": "material",
          "description": "Carcass material: PG White (16mm)",
          "qty": 3.42,
          "uom": "m2",
          "unit_price_cents": 10000,
          "unit_cost_cents": 10000,
          "cost_total_cents": 34200,
          "markup_bps": 2500,
          "sell_total_cents": 42750,
          "line_total_cents": 42750,
          "profit_cents": 8550,
          "missing": false
        }
      ]
    }
  ]
}
```

`subtotal_cents` is retained for backward compatibility and is the base cost
subtotal. `sell_before_vat_cents` is the sell subtotal before VAT.

When a required item has no active price entry, it is returned in
`missing_items`, cost/sell totals are omitted for that line, and `is_complete`
is `false`.

Line `bucket` values group the spreadsheet-derived pricing categories:
`material`, `component`, `handle`, `labour`, `consumable`, `extra`,
`installation`, `delivery`, and `commission`.

## Frontend Integration Notes

- Project list can be loaded once via `GET /projects` and filtered with `search`.
- Opening a project should call `GET /projects/{project_id}/quotes`.
- Opening a quote should call `GET /quotes/{quote_id}/units`.
- Quote cards and workspace headers should show `status`, `quote_number`, and `revision`; use `PATCH /quotes/{quote_id}/status` for status controls.
- Use `POST /quotes/{quote_id}/revisions` when client changes require a new editable revision of a sent or accepted quote.
- Panels tab can load and save quote panel config via `GET/PUT /quotes/{quote_id}/custom-panels`.
- Cutting list tab can call `GET /quotes/{quote_id}/cutting-list`.
- Extras tab can load and save quote-selected extras via `GET/PUT /quotes/{quote_id}/extras`.
- Pricing tab can load project totals via `GET /projects/{project_id}/pricing` and format all cent values with the returned `currency_code`.
- Quote defaults are designed for fast unit creation UX: set defaults once on quote, then apply during add-unit flows.
