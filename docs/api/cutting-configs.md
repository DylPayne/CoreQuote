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

## Unit Configs

```http
GET /api/v1/cutting/unit-configs?include_archived=false
GET /api/v1/cutting/unit-configs/{unit_config_id}
POST /api/v1/cutting/unit-configs
PATCH /api/v1/cutting/unit-configs/{unit_config_id}
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
  "status": "active",
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

## Cutting Rulesets

```http
GET   /api/v1/cutting/rulesets?unit_type_key=Base%20Door&include_archived=false
POST  /api/v1/cutting/rulesets
GET   /api/v1/cutting/rulesets/{ruleset_id}
PATCH /api/v1/cutting/rulesets/{ruleset_id}
```

List responses omit `rows` so the frontend can render ruleset tabs cheaply. Get, create, and update responses include `rows`.

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

The `PATCH` endpoint replaces the ruleset's rows with the submitted `rows` array inside one database transaction. This is intentional for the frontend grid: save the current draft as one coherent ruleset instead of issuing row-by-row updates.
Each update also snapshots the prior ruleset state (including rows) into `cutting_ruleset_history` so edits do not overwrite historical definitions.

## Frontend Integration Notes

- Use `GET /unit-configs` to build the unit-type navigation and to show global versus company-owned configs.
- Use `GET /rulesets?unit_type_key=...` for the ruleset list beside each unit type.
- Use `GET /rulesets/{id}` when the user opens the editor.
- The editor can model the four edge toggles directly from `edge_long_1`, `edge_long_2`, `edge_short_1`, and `edge_short_2`.
- Save the editor with `PATCH /rulesets/{id}` and the full row array.
- To create a new company ruleset for a unit type, post a full ruleset payload with `unit_type_key` and `rows`. Rulesets are not lineage-linked.
