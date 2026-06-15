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
- Quote readiness read: `quotes:read`
- Workshop schedule PDF export: `quotes:read`
- Production handoff read: `production:read`
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
POST  /api/v1/quotes/{quote_id}/duplicate
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
  },
  "production_metadata": {
    "carcass": {
      "edge_banding": "",
      "grain_direction": "none",
      "rotation": "none",
      "notes": ""
    },
    "door_panel": {
      "edge_banding": "1mm ABS on exposed door and drawer-front edges",
      "grain_direction": "length",
      "rotation": "no_rotation",
      "notes": "Keep matched faces in unit order."
    },
    "visible_panel": {
      "edge_banding": "1mm ABS on all exposed panel edges",
      "grain_direction": "length",
      "rotation": "no_rotation",
      "notes": ""
    }
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

Duplicating a quote:

```http
POST /api/v1/quotes/{quote_id}/duplicate
```

Permission: `quotes:write`

The API creates a new editable `draft` quote in the same project. It copies the source quote defaults, production metadata, unit defaults, units, custom panel configuration, selected extras, and quote pricing settings. The duplicate receives the next project quote number, starts at revision `1`, and does not link `previous_revision_id`, so it behaves as a separate alternative rather than part of the original revision chain.

The source quote is not changed. Existing customer quote PDFs, workshop schedules, readiness state, pricing, and status remain traceable through the source quote number and revision.

Response: `201` with the normal quote response shape.

Creating a revision:

```http
POST /api/v1/quotes/{quote_id}/revisions
```

Permission: `quotes:write`

The API copies the source quote header, defaults, production metadata, units, custom panel configuration, selected extras, and quote pricing settings. The new quote keeps the same `quote_number`, increments `revision`, links `previous_revision_id`, and starts as `draft`. The source quote is not changed, so a sent or accepted record remains visible as it was.

## Quote Units

```http
GET    /api/v1/quotes/{quote_id}/units
POST   /api/v1/quotes/{quote_id}/units
POST   /api/v1/quotes/{quote_id}/units/{unit_id}/duplicate
PUT    /api/v1/quotes/{quote_id}/units/bulk
PATCH  /api/v1/quotes/{quote_id}/units/bulk-apply
PUT    /api/v1/quotes/{quote_id}/units/reorder
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
  "carcass_board_type_id": "board-uuid",
  "door_board_type_id": "board-uuid",
  "extra_params": {
    "num_drawers": 3
  },
  "production_metadata": {
    "carcass": {
      "edge_banding": "",
      "grain_direction": "none",
      "rotation": "none",
      "notes": ""
    },
    "door_panel": {
      "edge_banding": "2mm front edge, 1mm remaining edges",
      "grain_direction": "length",
      "rotation": "no_rotation",
      "notes": "Keep this island unit as the reference grain direction."
    },
    "visible_panel": {
      "edge_banding": "",
      "grain_direction": "none",
      "rotation": "none",
      "notes": ""
    }
  }
}
```

`thickness` is not accepted in unit create/update requests. The API resolves it from the unit `carcass_board_type_id`, falling back to the quote `default_carcass_board_type_id` when the unit does not override the carcass board. An effective carcass board is required.

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

Duplicating a unit:

```http
POST /api/v1/quotes/{quote_id}/units/{unit_id}/duplicate
```

Permission: `quotes:write`

The API copies the source unit on the same quote, including dimensions, effective thickness, board overrides, and `extra_params`. It assigns a new unit identity and the next `unit_number`. Later edits to the duplicate update only the duplicate row.

Response: `201` with the normal unit response shape.

Bulk saving units:

```http
PUT /api/v1/quotes/{quote_id}/units/bulk
```

Permission: `quotes:write`

Request payload:

```json
{
  "units": [
    {
      "unit_type_key": "Base Door",
      "height": 780,
      "width": 600,
      "depth": 580,
      "carcass_board_type_id": "board-uuid",
      "door_board_type_id": "board-uuid",
      "extra_params": {
        "num_doors": 2,
        "num_shelves": 1
      }
    },
    {
      "id": "existing-unit-uuid",
      "unit_type_key": "Base Draw",
      "height": 780,
      "width": 900,
      "depth": 580,
      "carcass_board_type_id": "board-uuid",
      "door_board_type_id": "board-uuid",
      "extra_params": {
        "num_drawers": 3
      }
    }
  ]
}
```

Rows without `id` create new units at the end of the quote order. Rows with `id` update existing units on the same quote. The batch validates quote visibility, unit visibility, dimensions, board defaults/overrides, and effective carcass thickness before any row is written, so invalid batches do not create partial units.

Response: `200` with the refreshed unit list in quote/workshop order.

Errors:

- `404` when the quote or an edited unit is not visible to the current company.
- `422` for invalid rows, with row-prefixed messages such as `units[2]: Carcass board is required`.
- `409` for write conflicts.

Bulk applying selected unit overrides:

```http
PATCH /api/v1/quotes/{quote_id}/units/bulk-apply
```

Permission: `quotes:write`

Request payload:

```json
{
  "unit_ids": ["unit-uuid-1", "unit-uuid-2"],
  "carcass_board_type_id": "board-uuid",
  "door_board_type_id": "board-uuid",
  "handle_id": "handle-uuid",
  "slide_id": "slide-uuid",
  "hinge_id": "hinge-uuid",
  "height": 780,
  "depth": 580
}
```

`unit_ids` must contain at least one visible unit on the quote and cannot contain duplicates. At least one apply field must be present. Optional board and hardware IDs may be `null` to clear the selected override and fall back to quote defaults.

Board and dimension fields apply to every selected unit. Hardware fields are stored as unit-level `extra_params` overrides and apply only to compatible unit families:

- `slide_id` applies to drawer units.
- `hinge_id` applies to door units.
- `handle_id` applies to drawer, base door, wall door, and tall door units.

Unsupported hardware fields are ignored for a selected unit rather than changing unrelated cabinet types. The API validates quote visibility, selected unit visibility, library item visibility, positive dimensions, board defaults/overrides, and effective carcass thickness before writing the batch.

Response: `200` with the refreshed unit list in quote/workshop order.

Errors:

- `404` when the quote, a selected unit, or a selected library item is not visible to the current company.
- `422` when the request has no apply fields, duplicate unit IDs, invalid dimensions, or invalid board/default combinations.
- `409` for write conflicts.

Reordering units:

```http
PUT /api/v1/quotes/{quote_id}/units/reorder
```

Permission: `quotes:write`

Request payload:

```json
{
  "unit_ids": ["unit-uuid-2", "unit-uuid-1", "unit-uuid-3"]
}
```

The payload must include every unit currently on the quote exactly once. The first ID receives `unit_number` 1, the second receives `unit_number` 2, and so on. Reordering changes the display/workshop order used by cutting lists, pricing, readiness, material summary, hardware pick list, and workshop outputs because those downstream views read the same persisted quote unit order.

Response: `200` with the refreshed unit list in the requested order.

Errors:

- `404` when the quote or a requested unit is not visible to the current company.
- `422` when the order omits existing quote units or includes duplicate unit IDs.
- `409` for write conflicts.

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
      "board_type_id": "board-uuid",
      "grain_direction": "none",
      "can_rotate": true
    }
  ],
  "runtime_mode": "legacy",
  "unit_sources": [],
  "validation_warnings": [
    {
      "severity": "warning",
      "source": "quote_panel",
      "unit_number": 0,
      "section": "extra_panel",
      "row_desc": "Kicker",
      "reason": "Choose a board for this quote-level panel."
    }
  ],
  "readiness": {
    "cutlist_valid": false,
    "warning_count": 1
  }
}
```

Cutlist validation runs after row generation. It warns on zero or negative length, width, or quantity, and on rows that cannot be tied to a usable board/material choice. The schedule rows remain visible so estimators can inspect and correct the source unit or quote-level panel.

## Quote Readiness

```http
GET /api/v1/quotes/{quote_id}/readiness
```

Permission: `quotes:read`

This endpoint runs a live readiness checklist from the current quote, project,
units, board selections, cutting-list output, price list, and quote totals. It
returns business-facing check messages and stable check IDs/actions that can be
reused by future export or send buttons.

Response shape:

```json
{
  "quote_id": "quote-uuid",
  "status": "needs_attention",
  "is_ready": false,
  "summary_title": "Needs attention before review",
  "summary_message": "2 readiness checks need attention before this quote is ready for review.",
  "warning_count": 2,
  "error_count": 0,
  "checks": [
    {
      "id": "unit_boards",
      "severity": "warning",
      "title": "Choose boards for the quote",
      "message": "1 cabinet without a carcass board cannot be trusted for pricing or cutting yet.",
      "action_label": "Review board choices",
      "action_target": "units"
    },
    {
      "id": "missing_prices",
      "severity": "warning",
      "title": "Add missing prices",
      "message": "1 required price missing from the active price list, so totals are not ready for review.",
      "action_label": "Open price list",
      "action_target": "libraries-pricing"
    }
  ]
}
```

Readiness checks currently use these stable IDs:

- `project_details`
- `unit_count`
- `default_boards`
- `unit_boards`
- `cutlist_rows`
- `missing_prices`
- `quote_totals`
- `hardware_pick_list`
- `required_outputs`

`action_target` maps to frontend workspace actions: `project`, `quote`,
`units`, `panels`, `cutting-lists`, `pricing`, or `outputs`. The
`libraries-pricing` target opens Libraries > Pricing so missing active price
lists and missing price rows can be fixed without parsing copy. The current UI
uses `outputs` to open the quote output review screen.

Errors:

- `401` for missing/invalid bearer sessions.
- `403` for roles without `quotes:read`.
- `404` when the quote is not visible to the current company.

Frontend integration notes:

- Load this endpoint when a quote is selected and after edits to project
  details, quote setup, units, panels, extras, or pricing settings.
- Treat `is_ready` as the reusable status for future export/send workflows.
- Use `checks[].action_target` for direct workspace navigation; do not parse
  message text.

## Quote Output Review

```http
GET /api/v1/quotes/{quote_id}/output-review
```

Permission: `pricing:read`

This endpoint builds the quote-level review screen used before generating
client or workshop outputs. It combines readiness, pricing confidence,
cutting-list status, material summary, hardware pick-list status, and the
available output actions.

Response excerpt:

```json
{
  "quote_id": "quote-uuid",
  "quote_name": "Kitchen Quote",
  "project_id": "project-uuid",
  "project_name": "Main Kitchen",
  "quote_status": "draft",
  "quote_number": "Q-001",
  "revision": 1,
  "currency_code": "USD",
  "client_quote_total_cents": 498000,
  "pricing_missing_price_count": 1,
  "cutlist_row_count": 24,
  "cutlist_warning_count": 1,
  "readiness": {
    "quote_id": "quote-uuid",
    "status": "needs_attention",
    "is_ready": false,
    "summary_title": "Needs attention before review",
    "summary_message": "2 readiness checks need attention before this quote is ready for review.",
    "warning_count": 2,
    "error_count": 0,
    "checks": []
  },
  "client_quote": {
    "id": "client_quote",
    "label": "Client quote",
    "status": "needs_attention",
    "severity": "warning",
    "message": "Resolve readiness warnings before generating the client quote."
  },
  "internal_pricing": {
    "id": "internal_pricing",
    "label": "Internal pricing confidence",
    "status": "needs_attention",
    "severity": "warning",
    "message": "Review missing prices before trusting internal margin and totals."
  },
  "actions": [
    {
      "id": "client_quote_pdf",
      "group": "client",
      "label": "Client quote",
      "description": "Customer PDF with sell totals only. Internal costs and profit stay hidden.",
      "enabled": false,
      "warning": "Resolve readiness warnings before generating the client quote.",
      "hides_internal_costs": true,
      "action_target": "pricing"
    },
    {
      "id": "workshop_schedule",
      "group": "workshop",
      "label": "Workshop schedule",
      "description": "Cutting and production schedule for the workshop.",
      "enabled": true,
      "warning": "Cutting-list warnings will be included in the workshop schedule.",
      "hides_internal_costs": false,
      "action_target": "cutting-lists"
    }
  ]
}
```

The full response also includes `workshop_schedule`, `material_status`,
`hardware_status`, `material_summary`, and `hardware_pick_list` using the same
schemas as the project pricing response.

Errors:

- `401` for missing/invalid bearer sessions.
- `403` for roles without `pricing:read`.
- `404` when the quote is not visible to the current company.
- `422` when quote data cannot be evaluated.

Frontend integration notes:

- Load this endpoint when the estimator opens the quote's `Review outputs` tab.
- Render `actions` in separate Client quote and Workshop package groups.
- Treat `actions[].enabled` as the generate/readiness state. Show
  `actions[].warning` before any export action even when export remains enabled
  with warnings.
- The `client_quote_pdf` action has `hides_internal_costs: true`; client UI must
  not show cost, profit, or internal margin beside that action.
- Use `actions[].action_target` for navigation to the source area that can fix a
  warning or inspect the output detail.

## Production Handoff

```http
GET /api/v1/quotes/{quote_id}/production-handoff
```

Permission: `production:read`

This endpoint builds the workshop production packet from the live quote review
context. It reuses the current cutting-list rows, cutlist warnings, material
summary, hardware pick list, quote metadata, project metadata, and board library
lookup. It does not return customer quote totals, internal cost, sell price,
profit, margin, or markup fields.

Rows are grouped for board-first workshop flow by board/material, thickness,
material role, unit, and cutlist section. Quote-level custom panel rows are
included with `source_type: "quote_panel"` and `unit_number: 0`.

Production metadata is workshop-only and is not added to customer quote totals
or customer PDF contracts. It can be recorded on the quote by material role, on
individual units by material role, or on custom panel rows. Unit metadata
overrides quote defaults for matching roles, and custom panel metadata overrides
the quote `visible_panel` defaults for that generated row. Cutting ruleset edge
flags are rendered as `edge_sides`; saved edge-banding text, grain direction,
rotation guidance, and production notes are shown beside each affected part.
Door/drawer panels and visible quote panels produce row warnings when required
edge or grain details are missing.

The response also includes `board_requirements`, a production-facing material
ordering review derived from the same rows and material summary. It groups by
board/material, thickness, and material role, includes quote-level custom panel
part IDs, and labels all sheet counts as estimates because CoreQuote has not
optimized nesting. When sheet dimensions are available, each requirement row
includes estimated sheet area and an estimated waste allowance percentage based
on sheet area minus part area. Missing board choices, unavailable board records,
missing sheet dimensions, invalid part dimensions, or incomplete material data
appear in `board_requirements.warnings` before export.

Response excerpt:

```json
{
  "quote_id": "quote-uuid",
  "quote_name": "Workshop Handoff",
  "quote_status": "ready",
  "quote_number": "Q-001",
  "revision": 1,
  "project_id": "project-uuid",
  "project_name": "Smith Kitchen Phase 5 Workshop Handoff",
  "row_count": 3,
  "group_count": 2,
  "label_count": 3,
  "warning_count": 0,
  "groups": [
    {
      "group_key": "board-uuid::16::White::carcass::1::carcass",
      "board_type_id": "board-uuid",
      "board_name": "PG White (16mm)",
      "brand": "PG",
      "material": "White",
      "thickness": 16,
      "sheet_length_mm": 2750,
      "sheet_width_mm": 1830,
      "material_role": "carcass",
      "role_label": "Carcass",
      "unit_number": 1,
      "unit_label": "Unit 1",
      "section": "carcass",
      "section_label": "Carcass",
      "row_count": 1,
      "piece_count": 2,
      "warning_count": 0,
      "part_ids": ["Q-001-R1-U01-CAR-SIDE-748X564-01"],
      "rows": [
        {
          "part_id": "Q-001-R1-U01-CAR-SIDE-748X564-01",
          "source_type": "unit",
          "unit_number": 1,
          "unit_label": "Unit 1",
          "section": "carcass",
          "material_role": "carcass",
          "board_type_id": "board-uuid",
          "board_name": "PG White (16mm)",
          "desc": "Side",
          "length": 748,
          "width": 564,
          "quantity": 2,
          "edge_sides": [],
          "edge_sides_label": "None",
          "edge_banding": "",
          "grain_direction": "none",
          "grain_label": "Unspecified",
          "can_rotate": true,
          "rotation": "allow_rotation",
          "rotation_label": "Can rotate",
          "production_notes": "",
          "warning_count": 0,
          "warning_messages": []
        }
      ]
    }
  ],
  "material_summary": {
    "groups": [
      {
        "board_type_id": "board-uuid",
        "material_role": "carcass",
        "board_name": "PG White (16mm)",
        "piece_count": 2,
        "area_m2": 0.84,
        "estimated_sheets": 1,
        "part_ids": ["Q-001-R1-U01-CAR-SIDE-748X564-01"]
      }
    ],
    "warnings": [],
    "total_area_m2": 0.84,
    "total_piece_count": 2,
    "total_edge_m": 0,
    "total_estimated_sheets": 1
  },
  "board_requirements": {
    "estimate_label": "Sheet counts are estimates only; CoreQuote has not optimized board nesting.",
    "groups": [
      {
        "requirement_key": "board-uuid::16::White::carcass",
        "board_type_id": "board-uuid",
        "board_name": "PG White (16mm)",
        "brand": "PG",
        "material": "White",
        "thickness": 16,
        "sheet_length_mm": 2750,
        "sheet_width_mm": 1830,
        "material_role": "carcass",
        "role_label": "Carcass",
        "row_count": 1,
        "piece_count": 2,
        "area_m2": 0.84,
        "edge_m": 0,
        "sheet_area_m2": 5.0325,
        "estimated_sheets": 1,
        "estimated_sheet_area_m2": 5.0325,
        "waste_area_m2": 4.1925,
        "waste_percent": 83.31,
        "sheet_estimate_label": "1 estimated sheet (area estimate, not optimized nesting).",
        "waste_allowance_label": "Estimated waste allowance 83.3% from sheet area minus part area.",
        "part_ids": ["Q-001-R1-U01-CAR-SIDE-748X564-01"],
        "source_labels": ["Unit 1"],
        "warning_count": 0,
        "warning_messages": []
      }
    ],
    "warnings": [],
    "total_area_m2": 0.84,
    "total_piece_count": 2,
    "total_edge_m": 0,
    "total_estimated_sheets": 1,
    "total_estimated_sheet_area_m2": 5.0325,
    "total_waste_area_m2": 4.1925,
    "warning_count": 0
  },
  "hardware_pick_list": {
    "items": [
      {
        "part_id": "Q-001-R1-HW-HINGE-HINGE-1",
        "item_type": "hinge",
        "item_name": "Blum Clip top",
        "quantity": 4,
        "uom": "pcs",
        "unit_numbers": [1],
        "related_part_ids": ["Q-001-R1-U01-CAR-SIDE-748X564-01"]
      }
    ],
    "warnings": [],
    "total_item_count": 1,
    "total_quantity": 4
  },
  "labels": [
    {
      "part_id": "Q-001-R1-U01-CAR-SIDE-748X564-01",
      "label": "Q-001-R1-U01-CAR-SIDE-748X564-01 · Side · 748 x 564 mm",
      "source_type": "unit",
      "unit_number": 1,
      "section": "carcass",
      "desc": "Side",
      "dimensions_label": "748 x 564 mm",
      "material_label": "PG White (16mm)",
      "quantity": 2,
      "warning_count": 0,
      "edge_sides_label": "None",
      "grain_label": "Unspecified",
      "rotation_label": "Can rotate"
    }
  ]
}
```

Stable part identifiers are deterministic from quote number, revision, source
type, unit/quote-panel source, section, description, dimensions, and a repeat
index. The same `part_id` appears in grouped cutting rows, material summary
`part_ids`, related hardware rows, and labels.

Errors:

- `401` for missing/invalid bearer sessions.
- `403` for roles without `production:read`.
- `404` when the quote is not visible to the current company.
- `422` when the cutting-list context cannot be built.

Frontend integration notes:

- Load this endpoint when a workshop user opens the quote `Production` tab.
- Refresh it after changes to quote board defaults, units, custom panels, or
  selected extras.
- Treat the response as production-safe. Do not add pricing, customer totals,
  cost, profit, margin, or markup fields to this view.
- Render `board_requirements.estimate_label`, `sheet_estimate_label`, and
  `waste_allowance_label` exactly as estimate copy. Do not present sheet counts
  as optimized nesting or final supplier board counts.

## Customer Quote PDF

```http
GET /api/v1/quotes/{quote_id}/customer-quote.pdf
```

Permission: `pricing:read`

Returns an `application/pdf` attachment for the customer-facing quote. The
filename is generated from the quote name, quote number, and revision, for
example:

```http
Content-Disposition: attachment; filename="Smith-Kitchen-Quote-v1-Q-001-rev-1.pdf"
```

The export uses the same live readiness and pricing context as
`GET /quotes/{quote_id}/output-review`. Generation is allowed only when the
`client_quote_pdf` output action is enabled. If readiness or pricing blocks
export, the API returns the same warning text surfaced in output review.

Customer PDF contents:

- Company name, a logo placeholder, current user name/email as contact details,
  and the company currency.
- Client name, site address, project name, quote name, quote number, revision,
  issue date, and expiry date.
- Customer summary rows for cabinetry, visible panels, hardware/extras,
  installation, delivery, VAT, and grand total where those values are present.
- Terms and notes from `quote.notes`, or a default validity note when notes are
  blank.

Internal cost, profit, and margin fields are not copied into the customer PDF
document model and must not be rendered in the file.

Errors:

- `401` for missing/invalid bearer sessions.
- `403` for roles without `pricing:read`.
- `404` when the quote is not visible to the current company.
- `422` when readiness, missing prices, or another pricing/setup issue blocks
  customer PDF generation.

Frontend integration notes:

- Load `output-review` when the estimator opens `Review outputs`; use the
  `client_quote_pdf` action state to enable the download button.
- On click, request this endpoint as a blob and use the response
  `Content-Disposition` filename when available.
- If the PDF request returns `422`, show the returned detail and refresh
  output review so readiness warnings stay current.

## Workshop Schedule PDF

```http
GET /api/v1/quotes/{quote_id}/workshop-schedule.pdf
```

Permission: `quotes:read`

Returns an `application/pdf` attachment for the workshop cutting schedule. The
filename is generated from the quote name, quote number, and revision, for
example:

```http
Content-Disposition: attachment; filename="workshop-Smith-Kitchen-Quote-v1-Q-001-rev-1.pdf"
```

The export uses the same live cutting-list context as
`GET /quotes/{quote_id}/cutting-list` and `GET /quotes/{quote_id}/output-review`.
Generation is allowed when the quote has at least one cutting row. Cutting-list
validation warnings do not block export; they are included in the PDF warning
section and affected rows are marked for checking.

Workshop schedule PDF contents:

- Company name, project name, client/site, quote name, quote number, revision,
  and export date.
- Grouped carcass, panel, custom panel, hardware, and other cutting-list rows
  when present.
- Unit number, description, length, width, quantity, board/material where known,
  and a row status.
- Validation warning text for invalid dimensions or missing/unavailable board
  selections.

Customer-facing price totals, internal costs, profit, and margin fields are not
rendered in this export.

Errors:

- `401` for missing/invalid bearer sessions.
- `403` for roles without `quotes:read`.
- `404` when the quote is not visible to the current company.
- `422` when there are no schedule rows to export.

Frontend integration notes:

- The output review `workshop_schedule` action downloads this endpoint as a
  blob when `enabled` is true.
- If `warning` is present, keep the download action visible and show a route
  back to the cutting-list source so the estimator can inspect invalid rows.
- Use the response `Content-Disposition` filename when available.

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
    "base_side_panel": {
      "qty": 1,
      "board_type_id": "board-uuid",
      "production_metadata": {
        "edge_banding": "1mm ABS on exposed side edge",
        "grain_direction": "length",
        "rotation": "no_rotation",
        "notes": ""
      }
    },
    "wall_side_filler": {
      "qty": 1,
      "board_type_id": null,
      "production_metadata": {
        "edge_banding": "",
        "grain_direction": "none",
        "rotation": "none",
        "notes": ""
      }
    }
  },
  "manual": [
    {
      "name": "Feature End",
      "length": 2300,
      "width": 300,
      "qty": 1,
      "board_type_id": "board-uuid",
      "production_metadata": {
        "edge_banding": "1mm ABS all exposed edges",
        "grain_direction": "length",
        "rotation": "no_rotation",
        "notes": "Visible end panel."
      }
    }
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
    "pelmet_override_width": 330,
    "production_metadata": {
      "edge_banding": "1mm ABS on visible kicker and pelmet edges",
      "grain_direction": "length",
      "rotation": "no_rotation",
      "notes": ""
    }
  }
}
```

Behavior notes:

- `kicker_return_count` and `kicker_return_depth_mm` add optional kicker return segments on top of total base-run width.
- Manual rows with non-positive length, width, or qty are ignored at save time.
- Any supplied `board_type_id` must be visible to the current company.
- `production_metadata` is optional on presets, manual rows, and auto rows. Missing
  metadata defaults to empty edge notes, `grain_direction: "none"`, and
  `rotation: "none"` before the production handoff applies quote-level defaults.

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
- Price-list items current at each quote's pricing timestamp if an active price list exists.
- Project pricing defaults for project metadata.
- Each quote's own pricing settings for quote calculations.

Each quote summary includes `active_price_list_id` and `pricing_as_of`. Price
rows are selected where `effective_from <= pricing_as_of` and `effective_to` is
either null or later than `pricing_as_of`. This keeps older revisions
explainable after a supplier-cost refresh creates newer price rows.

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
  "missing_prices": [],
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
      "active_price_list_id": "price-list-uuid",
      "pricing_as_of": "2026-06-01T10:30:00Z",
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
      "cutlist_warnings": [],
      "missing_prices": [
        {
          "item_type": "handle",
          "item_type_label": "Handle",
          "item_key": "handle::handle-uuid",
          "item_ref_id": "handle-uuid",
          "price_component": "unit",
          "component": "Unit price",
          "bucket": "handle",
          "item_name": "Bar pull",
          "uom": "pcs",
          "quantity": 3,
          "used_in": ["Handle"],
          "usage_label": "Handle",
          "affected_quote_id": "quote-uuid",
          "affected_quote_name": "Kitchen Quote v1",
          "library_area": "pricing",
          "action_label": "Add a price for Bar pull",
          "message": "Add a price for Bar pull using Unit price in the pricing library.",
          "library_target": "pricing",
          "library_target_label": "Pricing",
          "catalog_target": "handles",
          "catalog_target_label": "Handle library",
          "guidance_action_label": "Open Pricing",
          "guidance_message": "Handle library already appears on the quote. Open Pricing and add Unit price for Bar pull to the active price list. If this price comes from suppliers, add the supplier cost first and generate prices."
        }
      ],
      "material_summary": {
        "groups": [
          {
            "board_type_id": "board-uuid",
            "material_role": "carcass",
            "role_label": "Carcass material",
            "board_name": "PG White (16mm)",
            "brand": "PG",
            "material": "White",
            "thickness": 16,
            "length_mm": 2750,
            "width_mm": 1830,
            "costing_mode": "sqm",
            "piece_count": 8,
            "area_m2": 3.42,
            "edge_m": 7.5,
            "sheet_area_m2": 5.0325,
            "estimated_sheets": 1,
            "price_component": "sqm",
            "pricing_qty": 3.42,
            "pricing_uom": "m2",
            "cost_total_cents": 34200,
            "sell_total_cents": 42750,
            "missing_price": false
          }
        ],
        "warnings": [],
        "total_area_m2": 3.42,
        "total_piece_count": 8,
        "total_edge_m": 7.5,
        "total_estimated_sheets": 1
      },
      "hardware_pick_list": {
        "items": [
          {
            "item_type": "slide",
            "type_label": "Slides",
            "item_key": "slide::slide-uuid",
            "item_ref_id": "slide-uuid",
            "item_name": "Grass Dynapro",
            "supplier": "Grass",
            "code": "S500",
            "quantity": 3,
            "uom": "pairs",
            "unit_numbers": [1],
            "used_in": ["Unit 1 drawers"],
            "usage_label": "Unit 1 drawers"
          },
          {
            "item_type": "extra",
            "type_label": "Extras",
            "item_key": "extra::extra-uuid",
            "item_ref_id": "extra-uuid",
            "item_name": "Waste removal",
            "supplier": "Core",
            "code": "WR1",
            "quantity": 1,
            "uom": "pcs",
            "unit_numbers": [],
            "used_in": ["Quote extra"],
            "usage_label": "Quote extra"
          }
        ],
        "warnings": [
          {
            "severity": "warning",
            "code": "missing_handle_selection",
            "item_type": "handle",
            "unit_number": 1,
            "item_ref_id": null,
            "message": "Choose a drawer handle for Unit 1 drawers."
          }
        ],
        "total_item_count": 2,
        "total_quantity": 4
      },
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
`missing_items` for backward compatibility and in `missing_prices` as
estimator-facing guidance. Each `missing_prices` row identifies the library
item type, stable item reference, price component, unit of measure, quantity,
where it is used, the affected quote, the price-list target (`library_target`),
and the related catalog target (`catalog_target`) when the missing price belongs
to a board, slide, hinge, handle, or extra. Use `guidance_message` and
`guidance_action_label` for user-facing copy that distinguishes a missing price
from a missing catalog item. Cost/sell totals are omitted for the matching line,
and `is_complete` is `false`. Project pricing responses also include a top-level
`missing_prices` array containing the missing price guidance for all included
quotes. `is_complete` is also `false` when `cutlist_warnings` is not empty.

Each quote also includes `material_summary` for internal review/workshop
handoff. It is aggregated from the same runtime cutlist rows used for pricing,
grouped by board type, role, and thickness. Sheet counts are estimates, not
nested or optimized board counts. Missing board selections, unavailable board
records, or missing sheet dimensions appear in `material_summary.warnings`.
Customer-facing quote PDFs include summarized customer amounts only; they do not
include internal material cost, profit, margin, or line-level pricing detail.

Each quote also includes `hardware_pick_list` for workshop or purchasing review.
It groups slide, hinge, handle, and selected quote-extra quantities by catalog
item, preserves stable `item_ref_id` values for future supplier ordering, and
lists affected unit labels where available. Slide and hinge `supplier` values
come from their catalog brand; handle and extra `supplier` values come from the
supplier field. The pick list intentionally excludes price, sell, profit, and
margin fields. Missing slide, hinge, handle, or stale catalog choices appear in
`hardware_pick_list.warnings` and affect quote readiness.

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
- Pricing UI should show `missing_prices` before detailed line items and use `guidance_action_label`, `guidance_message`, `library_target`, and `catalog_target` instead of exposing raw item keys.
- Quote pricing review should show `material_summary` groups and warnings before detailed line items. Treat `estimated_sheets` as an estimate; `null` means sheet dimensions are missing.
- Quote pricing or output review should show `hardware_pick_list` groups and warnings for internal/workshop use. Do not mix its rows with client-facing margin, profit, or sell-price display.
- Quote defaults are designed for fast unit creation UX: set defaults once on quote, then apply during add-unit flows.
