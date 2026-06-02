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

### Suppliers

Resource: `suppliers`

```json
{
  "name": "Grass ZA",
  "code": "GRASS-ZA",
  "contact_name": "Sales",
  "email": "sales@example.com",
  "phone": "",
  "notes": ""
}
```

Suppliers represent the company/distributor an item is bought from. They are
separate from product brands. For example, a Grass Dynapro slide has product
brand `Grass` and supplier `Grass ZA`.

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

### Item Supplier Links

Item supplier links connect a catalog item to a supplier-specific SKU and order
unit. Each item can have multiple supplier links, but only one preferred link per
`(item_type, item_ref_id, price_component)`.

```http
GET    /api/v1/libraries/item-suppliers?item_type=slide&item_ref_id=slide-uuid
POST   /api/v1/libraries/item-suppliers
GET    /api/v1/libraries/item-suppliers/{item_supplier_id}
PATCH  /api/v1/libraries/item-suppliers/{item_supplier_id}
DELETE /api/v1/libraries/item-suppliers/{item_supplier_id}
```

Payload:

```json
{
  "item_type": "slide",
  "item_ref_id": "slide-uuid",
  "supplier_id": "supplier-uuid",
  "supplier_sku": "F130107820204",
  "supplier_description": "Dynapro Undermount F/Ext 500mm",
  "price_component": "unit",
  "order_uom": "pairs",
  "is_preferred": true,
  "notes": ""
}
```

Responses include `supplier_name` and the active supplier-cost summary when one
exists:

```json
{
  "active_supplier_item_cost_id": "supplier-cost-uuid",
  "active_list_price_cents": 68498,
  "active_discount_bps": 3000,
  "active_unit_cost_cents": 47949,
  "active_currency_code": "ZAR"
}
```

### Supplier Item Costs

Supplier item costs are versioned buying costs. They do not directly change
quote totals until they are generated into price-list items.

```http
GET  /api/v1/libraries/item-suppliers/{item_supplier_id}/costs?include_history=false
POST /api/v1/libraries/item-suppliers/{item_supplier_id}/costs
POST /api/v1/libraries/item-suppliers/{item_supplier_id}/costs/upsert
GET  /api/v1/libraries/item-suppliers/{item_supplier_id}/costs/{cost_id}
```

Payload:

```json
{
  "list_price_cents": 68498,
  "discount_bps": 3000,
  "unit_cost_cents": 47949,
  "currency_code": "ZAR",
  "source": "spreadsheet",
  "source_ref": "DRAWSLIDES!A19:D19",
  "effective_from": null
}
```

`discount_bps` is stored in basis points. `3000` means 30.00%. `unit_cost_cents`
is the net cost used when generating a price list row.

### Pricing Settings

```http
GET   /api/v1/libraries/pricing-settings
PATCH /api/v1/libraries/pricing-settings
```

Payload:

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

Rates are stored in basis points. `1500` means 15.00%, and `2500` means
25.00%. Monetary settings are stored in cents in the company currency.

Detailed pricing uses the active price list as base cost inputs, then applies
these bucket-specific settings:

- `carcass_markup_bps` for carcass board material and related base material.
- `door_panel_markup_bps` for doors, drawer fronts, flaps, and visible panels.
- `component_markup_bps` for slides, hinges, and flap mechanisms.
- `handle_markup_bps` for handles.
- `extras_markup_bps` for selected quote extras.
- `fabrication_markup_bps` for labour and fabrication allowances.
- `install_markup_bps` and `delivery_markup_bps` for operational charges.
- `joinery_commission_bps` for joinery and visible-panel sell totals before VAT.

`minimum_install_days_bps` and `minimum_delivery_trips_bps` represent decimal
quantities in basis points. `5000` means `0.5`.

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
  "source_supplier_item_cost_id": null,
  "cost_source": "manual",
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

### Generate Price List From Supplier Costs

```http
POST /api/v1/libraries/price-lists/{price_list_id}/generate-from-supplier-costs
```

Payload:

```json
{
  "selection_mode": "preferred_then_cheapest",
  "item_types": ["slide", "hinge"],
  "preserve_manual_overrides": true
}
```

`selection_mode` controls which active supplier cost is copied into the price
list when multiple supplier costs exist for one item:

- `preferred_then_cheapest`: use a preferred supplier cost if present, otherwise the cheapest active cost.
- `preferred_only`: generate only items with a preferred supplier cost.
- `cheapest`: use the cheapest active supplier cost.

Generated rows use:

- `item_key` as `<item_type>::<item_ref_id>`;
- `source_supplier_item_cost_id` pointing to the supplier cost row;
- `cost_source` set to `supplier`;
- `unit_price_cents` copied from the supplier cost `unit_cost_cents`.

When `preserve_manual_overrides` is true, existing active rows whose
`cost_source` is not `supplier` are left unchanged.

Response:

```json
{
  "price_list_id": "price-list-uuid",
  "selection_mode": "preferred_then_cheapest",
  "generated_count": 42,
  "created_count": 40,
  "updated_count": 2,
  "unchanged_count": 0,
  "skipped_override_count": 0,
  "missing_price_count": 0
}
```

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
