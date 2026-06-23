# Cutlists API Contract

The cutlists API currently exposes preview generation for cabinet units.

Base path:

```http
/api/v1/cutlists
```

Auth header:

```http
Authorization: Bearer <access_token>
```

## Permissions

- Preview: `cutlists:preview`

The API returns `401` for missing or invalid tokens and `403` when the authenticated role lacks `cutlists:preview`.

## Endpoint

### `POST /api/v1/cutlists/preview`

Request:

```json
{
  "units": [
    {
      "unit_number": 1,
      "unit_type": "Base Door",
      "height": 780,
      "width": 900,
      "depth": 560,
      "board_type_id": "board-uuid",
      "extra_params": {
        "num_doors": 2,
        "num_shelves": 1
      }
    }
  ]
}
```

`unit_type` accepts any non-empty string (up to 120 chars). Built-in defaults are:

- `Base Draw`
- `Base Door`
- `Wall Door`
- `Tall Door`

Custom unit type keys are supported for company-specific rulesets.

`board_type_id` must reference a board visible to the authenticated user's company. The API resolves formula thickness from that board type and does not accept raw unit thickness in preview requests.

Response:

```json
{
  "carcass": [
    {
      "unit_number": 1,
      "desc": "Side",
      "length": 748,
      "width": 544,
      "qty": 2
    }
  ],
  "panels": [
    {
      "unit_number": 1,
      "desc": "Door",
      "length": 777,
      "width": 447,
      "qty": 2
    }
  ],
  "hardware": [],
  "extras": [],
  "runtime_rows": [
    {
      "unit_number": 1,
      "section": "panel",
      "desc": "Door",
      "length": 777,
      "width": 447,
      "qty": 2,
      "edge_long_1": true,
      "edge_long_2": true,
      "edge_short_1": true,
      "edge_short_2": true
    }
  ],
  "runtime_mode": "ruleset",
  "unit_sources": [
    {
      "unit_number": 1,
      "unit_type_key": "Base Door",
      "source": "ruleset",
      "ruleset_id": "ruleset-uuid",
      "unit_config_id": "unit-config-uuid",
      "note": null
    }
  ],
  "validation_warnings": [],
  "readiness": {
    "cutlist_valid": true,
    "warning_count": 0
  }
}
```

If generated rows are not usable, `validation_warnings` identifies the affected unit or quote-level row while leaving the row in the schedule:

```json
{
  "severity": "warning",
  "source": "unit",
  "unit_number": 4,
  "section": "carcass",
  "row_desc": "Drawer Side",
  "reason": "Width must be greater than 0 mm."
}
```

## Runtime Behavior

Ruleset-based runtime evaluation is controlled by environment variable:

- `CUTLIST_USE_DB_RULESETS=true` (or `1`, `yes`, `on`) enables DB ruleset runtime.
- Any other value keeps the legacy strategy engine for preview generation.

When the ruleset runtime is enabled, each unit resolves in this order:

1. Company-owned active unit config, then global active default unit config.
2. Company-owned active ruleset, then global active default ruleset. Only one company ruleset per unit type can be active; active company revisions are read-only and must be copied to a draft revision before changes.
3. If ruleset/config is missing or evaluation fails, that unit falls back to legacy runtime output.

`runtime_mode` values:

- `ruleset`: all units used ruleset runtime.
- `drawer_system`: all units used configured metal drawer system runtime.
- `legacy`: all units used legacy runtime.
- `mixed`: some units used rulesets and some fell back to legacy.

`unit_sources` explains which path each unit used and includes fallback notes when applicable. Metal drawer system rows use `source: "drawer_system"` when the selected drawer hardware has `drawer_system_kind: "metal"`.

Drawer runner metadata from the selected slide is copied into the cutting
formula context. Rules can read `slide_length`, `slide_side_length`,
`slide_side_clearance_total`, `slide_mount_type`, `slide_product_family`,
`slide_required_depth_mm`, and `slide_box_width_deduction_mm`. When
`slide_box_width_deduction_mm` is zero, legacy drawer width calculation still
uses `2 * slide_side_clearance_total`.

For configured metal drawer systems, normal timber drawer-side, front/back, and
base drawer-box parts are suppressed. The cut schedule keeps the ordinary
carcass and drawer-front rows, then adds the selected system's
`drawer_system_config.panel_formulas` rows. Formula rows can target `carcass`,
`panel`, or `extra_panel`; hardware/accessory rows are emitted by the hardware
pick-list from `drawer_system_config.hardware_items`.

Units can select library-backed C/J channel profiles and full-length profile
handles through `extra_params` handle IDs:

```json
{
  "top_j_channel_handle_id": "handle-j-uuid",
  "middle_c_channel_handle_id": "handle-c-uuid",
  "between_lower_c_channel_handle_id": "handle-c-uuid",
  "base_door_top_j_channel_handle_id": "handle-j-uuid",
  "tall_vertical_channel_handle_id": "handle-c-or-j-uuid",
  "handle_id": "full-length-profile-handle-uuid",
  "full_length_handle_orientation": "length"
}
```

The selected IDs must reference Handles library rows. `handle_type`,
`supplier_id`, display-only `supplier_name`, and `front_reduction_mm` are read
from the handle item; unit payloads do not carry profile finish, supplier, code,
allowance, or reduction fields.

Built-in drawer support is fixed to Base 1/2/3 Draw units:

- Base 1 Draw: `top_j_channel_handle_id`.
- Base 2 Draw: `top_j_channel_handle_id` and `middle_c_channel_handle_id`.
- Base 3 Draw: `top_j_channel_handle_id` and `between_lower_c_channel_handle_id`.

Drawer channels reduce the affected drawer-front heights. Base Door top
J-channels reduce door-front height. Tall vertical channels reduce door/front
width. Full-length profile handles use `full_length_handle_orientation`:
`length` cuts the profile to derived door-front height and reduces front width;
`width` cuts the profile to derived door-front width and reduces front height.

Profile hardware rows use the selected handle library item. The row `W` value is
the required profile cut length: unit width for horizontal channels, unit height
for tall vertical channels, and derived door-front height or width for
full-length profile handles.
