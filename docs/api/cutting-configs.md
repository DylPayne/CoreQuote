# Cutting Configs API Contract

The cutting configs API exposes global and company-owned cabinet unit definitions and cutting rulesets. It is designed for the React frontend's ruleset editor: list unit types, choose a ruleset, edit formula rows in a grid, toggle edge flags, and save the ruleset atomically.

Base path:

```http
/api/v1/cutting
```

Auth header:

```http
Authorization: Bearer <access_token>
```

## Permissions

- Read endpoints use `cutlists:read`.
- Create and update endpoints use `cutlists:write`.

Global defaults have `company_id: null` and are visible to every company. Company-owned rows use the authenticated user's `company_id`. The API returns `404` when a requested config or ruleset is not visible to the user's company.

## Ownership And Lifecycle

- Built-in templates are global rows with `company_id: null`. They are read-only through company API writes and should be copied into a company draft revision before customization.
- Company draft revisions are editable rows scoped to the authenticated user's company. Quote cutlists do not use drafts.
- Active company revisions are the company-specific runtime override. Active revisions are read-only; changes require creating a new draft revision.
- Archived company revisions are read-only historical rows and are not used by quote cutlists.
- Each company can have only one active unit config and one active ruleset per `unit_type_key`.
- When a company unit config or ruleset is activated, the API automatically archives any other active company revision for that same `unit_type_key` and clears its default flag.
- If no active company ruleset exists for a unit type, quote cutlists use the active built-in default ruleset when DB ruleset runtime is enabled.

## Unit Configs

```http
GET /api/v1/cutting/unit-configs?include_archived=false
GET /api/v1/cutting/unit-configs/{unit_config_id}
POST /api/v1/cutting/unit-configs
PATCH /api/v1/cutting/unit-configs/{unit_config_id}
POST /api/v1/cutting/unit-configs/{unit_config_id}/revisions
```

Response:

```json
{
  "id": "unit-config-uuid",
  "company_id": null,
  "unit_type_key": "Base Door",
  "label": "Base Door",
  "category": "base",
  "variant_type": "door",
  "version": 1,
  "status": "active",
  "is_default": true,
  "variant_config": {
    "num_doors": 2,
    "default_shelves": 1,
    "shelf_setback": 20,
    "panel_gap_mm": 3
  },
  "default_height": 780,
  "default_width": 600,
  "default_depth": 580,
  "height_min": 300,
  "height_max": 2400,
  "width_min": 150,
  "width_max": 1200,
  "depth_min": 150,
  "depth_max": 700,
  "created_at": "2026-05-29T12:00:00Z",
  "updated_at": "2026-05-29T12:00:00Z"
}
```

Create/update payload:

```json
{
  "unit_type_key": "Custom Corner Unit",
  "label": "Custom Corner Unit",
  "category": "custom",
  "variant_type": "custom",
  "version": 1,
  "status": "draft",
  "is_default": false,
  "variant_config": {
    "panel_gap_mm": 3
  },
  "default_height": 780,
  "default_width": 600,
  "default_depth": 560,
  "height_min": 300,
  "height_max": 2400,
  "width_min": 150,
  "width_max": 1200,
  "depth_min": 150,
  "depth_max": 700
}
```

`PATCH /unit-configs/{unit_config_id}` only edits company-owned draft revisions. Sending `status: "active"` activates that draft and archives any previous active company unit config for the same `unit_type_key`.

`POST /unit-configs/{unit_config_id}/revisions` copies a visible built-in or company unit config into a new company-owned draft revision. The API assigns the next company version for that unit type.

## Cutting Rulesets

```http
GET   /api/v1/cutting/rulesets?unit_type_key=Base%20Door&include_archived=false
POST  /api/v1/cutting/rulesets
GET   /api/v1/cutting/rulesets/{ruleset_id}
PATCH /api/v1/cutting/rulesets/{ruleset_id}
POST  /api/v1/cutting/rulesets/{ruleset_id}/revisions
```

List responses omit `rows` so the frontend can render ruleset tabs cheaply. Get, create, and update responses include `rows`.

Runtime selection for a unit type is:

1. Active company ruleset for that `unit_type_key`.
2. Active built-in template where `company_id` is `null` and `is_default` is `true`.
3. Legacy cutlist strategy fallback if no ruleset can be resolved or a ruleset fails at runtime.

Create/update payload:

```json
{
  "unit_config_id": "unit-config-uuid",
  "unit_type_key": "Base Door",
  "name": "Company Base Door",
  "description": "Standard company base-door cutting logic.",
  "status": "draft",
  "version": 1,
  "is_default": false,
  "rows": [
    {
      "sort_order": 10,
      "section": "panel",
      "description": "Door",
      "length_formula": "h - panel_gap_mm",
      "width_formula": "(w / num_doors) - panel_gap_mm",
      "qty_formula": "num_doors",
      "condition_formula": "num_doors > 0",
      "grain_direction": "length",
      "can_rotate": false,
      "edge_long_1": true,
      "edge_long_2": true,
      "edge_short_1": true,
      "edge_short_2": true,
      "meta": {}
    }
  ]
}
```

The `PATCH` endpoint replaces the draft ruleset's rows with the submitted `rows` array inside one database transaction. This is intentional for the frontend grid: save the current draft as one coherent ruleset instead of issuing row-by-row updates.
`PATCH` only edits company-owned draft revisions. Active and archived company rulesets return `409` and must be copied to a new draft revision before changes.
Each update snapshots the prior draft state (including rows) into `cutting_ruleset_history` so edits do not overwrite historical definitions.
When a company ruleset draft is activated, any previously active company ruleset for the same unit type is snapshotted and archived in the same transaction.

`POST /rulesets/{ruleset_id}/revisions` copies a visible built-in or company ruleset, including all rows, into a new company-owned draft revision. The API assigns the next company version for that unit type.

## Frontend Integration Notes

- Use `GET /unit-configs` to build the unit-type navigation and to show global versus company-owned configs.
- Use `GET /rulesets?unit_type_key=...` for the ruleset list beside each unit type.
- Use `GET /rulesets/{id}` when the user opens the editor.
- The editor can model the four edge toggles directly from `edge_long_1`, `edge_long_2`, `edge_short_1`, and `edge_short_2`.
- Save draft ruleset revisions with `PATCH /rulesets/{id}` and the full row array.
- To customize a built-in template or change an active company ruleset, call `POST /rulesets/{id}/revisions`, then edit the returned draft.
- To start a blank company ruleset, post a draft payload with starter rows and keep `status: "draft"` until it has been tested.
- For company-only unit types, create the unit config and starter ruleset as drafts, test them, then activate the draft ruleset. If the draft ruleset references a draft company unit config, the frontend should activate that unit config at the same time.
- Show which ruleset is used for quotes by applying the runtime selection order above to the ruleset list.
