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
      "thickness": 16,
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
2. Company-owned active ruleset, then global active default ruleset.
3. If ruleset/config is missing or evaluation fails, that unit falls back to legacy runtime output.

`runtime_mode` values:

- `ruleset`: all units used ruleset runtime.
- `legacy`: all units used legacy runtime.
- `mixed`: some units used rulesets and some fell back to legacy.

`unit_sources` explains which path each unit used and includes fallback notes when applicable.
