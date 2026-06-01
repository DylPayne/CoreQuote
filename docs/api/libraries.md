# Libraries API Contract

The libraries API exposes the inventory and pricing libraries that currently live in the Streamlit app and SQLite database. Every endpoint requires a bearer token and scopes data to `current_user.company_id`.

Base path:

```http
/api/v1/libraries
```

Auth header:

```http
Authorization: Bearer <access_token>
```

## Permissions

Catalog inventory endpoints use:

- Read: `catalog:read`
- Create/update/delete: `catalog:write`

Pricing endpoints use:

- Read: `pricing:read`
- Create/update/delete: `pricing:update`

The API returns `401` for missing or invalid tokens, `403` for missing permissions, `404` when a row is not visible to the user's company, and `409` for duplicate rows or rows still referenced by other data.

## Catalog Libraries

Each catalog library supports:

```http
GET    /api/v1/libraries/{resource}
POST   /api/v1/libraries/{resource}
GET    /api/v1/libraries/{resource}/{id}
PATCH  /api/v1/libraries/{resource}/{id}
DELETE /api/v1/libraries/{resource}/{id}
```

`PATCH` currently expects the full editable payload for that resource.

### Boards

Resource: `boards`

```json
{
  "brand": "PG Bison",
  "material": "MelaWood",
  "thickness": 16,
  "length_mm": 2750,
  "width_mm": 1830,
  "costing_mode": "sheet"
}
```

`costing_mode` is `sheet` or `sqm`.

### Slides

Resource: `slides`

```json
{
  "brand": "Grass",
  "model": "Dynapro",
  "code": "DYN-500",
  "length": 500,
  "side_length": 500,
  "side_clearance_total": 26,
  "side_height_uplift": 0
}
```

### Hinges

Resource: `hinges`

```json
{
  "brand": "Blum",
  "model": "Clip Top",
  "code": "BL-110",
  "opening_angle_deg": 110
}
```

### Handles

Resource: `handles`

```json
{
  "name": "Slim Bar 160",
  "supplier": "Hafele",
  "code": "HB-160"
}
```

### Extra Categories

Resource: `extra-categories`

```json
{
  "name": "Appliances"
}
```

### Extras

Resource: `extras`

```json
{
  "name": "Stove",
  "category_id": "extra-category-uuid",
  "supplier": "Defy",
  "code": "DFY-600",
  "notes": ""
}
```

Responses include `category_name` so the frontend can render the library table without an extra lookup.

## Pricing Libraries

### Pricing Settings

```http
GET   /api/v1/libraries/pricing-settings
PATCH /api/v1/libraries/pricing-settings
```

Payload:

```json
{
  "vat_rate_bps": 1500,
  "default_markup_bps": 2500
}
```

Rates are stored in basis points. `1500` means 15.00%, and `2500` means 25.00%.

### Price Lists

```http
GET    /api/v1/libraries/price-lists
POST   /api/v1/libraries/price-lists
GET    /api/v1/libraries/price-lists/active
GET    /api/v1/libraries/price-lists/{price_list_id}
PATCH  /api/v1/libraries/price-lists/{price_list_id}
DELETE /api/v1/libraries/price-lists/{price_list_id}
```

Payload:

```json
{
  "name": "Default Price List",
  "status": "active",
  "effective_from": null,
  "effective_to": null
}
```

`status` is `draft`, `active`, or `archived`.

Only one price list may be `active` per company. Use `GET /api/v1/libraries/price-lists/active` when quoting screens need the currently active list.

### Price List Items

```http
GET    /api/v1/libraries/price-lists/{price_list_id}/items?include_history=false
POST   /api/v1/libraries/price-lists/{price_list_id}/items
POST   /api/v1/libraries/price-lists/{price_list_id}/items/upsert
GET    /api/v1/libraries/price-lists/{price_list_id}/items/{item_id}
PATCH  /api/v1/libraries/price-lists/{price_list_id}/items/{item_id}
DELETE /api/v1/libraries/price-lists/{price_list_id}/items/{item_id}
```

Payload:

```json
{
  "item_type": "slide",
  "item_ref_id": "slide-uuid",
  "item_key": null,
  "price_component": "unit",
  "uom": "pairs",
  "unit_price_cents": 12500,
  "effective_from": null
}
```

`item_type` is `board`, `slide`, `hinge`, `handle`, or `extra`.

At least one of `item_ref_id` or `item_key` is required.

- Preferred: send `item_ref_id` (the library row UUID). The API validates the item belongs to the current company and derives `item_key` automatically as `<item_type>::<item_ref_id>`.
- Backward-compatible: send `item_key` directly for legacy natural keys or imported data.

`price_component` identifies the specific cost component for an item. Common components are:

- `unit` for slides, hinges, handles, and extras.
- `sheet`, `sqm`, `edging_m`, and `labour_board` for boards.

By default, list endpoints return only active prices, where `effective_to` is `null`. Pass `include_history=true` to include replaced or retired prices.

Updating a price item does not overwrite the old price. The API closes the old row by setting `effective_to`, inserts a new active row, and returns the new row. The response includes:

```json
{
  "id": "new-price-row-uuid",
  "replaces_id": "old-price-row-uuid",
  "effective_from": "2026-05-28T12:00:00Z",
  "effective_to": null,
  "is_active": true
}
```

Deleting a price item retires the active row by setting `effective_to`; it does not remove historical pricing.

### Upsert Convenience Endpoint

Use `POST /api/v1/libraries/price-lists/{price_list_id}/items/upsert` when the UI should save a price without checking first whether an active row already exists.

- If an active row exists for the same `(item_type, item_key, price_component)`, the API versions it and returns the replacement row.
- If no active row exists, the API creates a new row.

## Response Shape

Create, get, and update responses return the submitted fields plus:

```json
{
  "id": "row-uuid",
  "created_at": "2026-05-28T12:00:00Z",
  "updated_at": "2026-05-28T12:00:00Z"
}
```

Deletes return `204 No Content`.
