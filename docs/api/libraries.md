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

## Setup Checklist

```http
GET /api/v1/libraries/setup-checklist
```

Permission: `pricing:read`.

This endpoint returns a company-scoped checklist for the Libraries first-run and
maintenance flow. It does not create or update any setup data; it only reads the
current company's catalog counts, supplier-cost links, active price list, saved
pricing settings, and quote defaults.

Example response:

```json
{
  "status": "needs_attention",
  "summary_title": "Library setup needs attention",
  "summary_message": "3 setup items still need attention before the Smith Kitchen library refresh is fully ready.",
  "complete_count": 6,
  "total_count": 9,
  "items": [
    {
      "id": "boards",
      "label": "Boards",
      "status": "complete",
      "count": 3,
      "message": "Board choices are available for carcasses, doors, and panels.",
      "action_label": "Review boards",
      "action_target": "boards"
    },
    {
      "id": "active-price-list",
      "label": "Active price list",
      "status": "warning",
      "count": 0,
      "message": "An active price list exists, but it does not have active prices yet.",
      "action_label": "Add prices",
      "action_target": "pricing"
    }
  ]
}
```

Checklist item `status` is one of `complete`, `missing`, `warning`, or
`action_needed`. `action_target` points the React app to the setup area that can
fix or review the item: `pricing`, `boards`, `slides`, `hinges`, `suppliers`,
`handles`, `extra-categories`, `extras`, or `projects`.

The checklist is intentionally business-facing. For example, it explains that
quote defaults live on quotes rather than asking the user to understand database
tables.

## Import Preview

```http
POST /api/v1/libraries/imports/preview
```

Permission: `pricing:update`.

This endpoint parses CSV, TSV, or XLSX library rows and returns a dry-run
classification. It does not create, update, or delete library data. Use the
apply endpoint below when the user explicitly commits the reviewed import.

Supported `resource` values:

- `boards`
- `slides`
- `hinges`
- `handles`
- `suppliers`
- `extra_categories`
- `extras`
- `supplier_item_costs`
- `price_list_items`

Request:

```json
{
  "resource": "boards",
  "source_format": "csv",
  "filename": "boards.csv",
  "sheet_name": null,
  "content": "Brand,Material,Thickness,Length,Width,Costing Mode\nPG Bison,MelaWood,16,2750,1830,sheet\n",
  "column_mapping": {
    "thickness": "Thickness"
  },
  "price_list_id": null
}
```

For `xlsx`, send `content` as base64-encoded workbook bytes and optionally set
`sheet_name`. For `price_list_items`, `price_list_id` selects the price list to
preview against; when omitted, the API uses the company's active price list.
For `supplier_item_costs` and `price_list_items`, natural-key catalog matching
can use `Brand`, `Material` or `Name`, `Code`, `Category`, and `Supplier`
columns. Include `Supplier` for handle and extra rows when the catalog item uses
supplier as part of its identity.

Response:

```json
{
  "resource": "boards",
  "source_format": "csv",
  "sheet_name": null,
  "columns": ["Brand", "Material", "Thickness", "Length", "Width", "Costing Mode"],
  "mapped_fields": [
    {
      "field": "brand",
      "label": "Brand",
      "source_column": "Brand",
      "required": true
    }
  ],
  "summary": {
    "total_rows": 2,
    "create_count": 1,
    "update_count": 0,
    "skipped_count": 0,
    "duplicate_count": 0,
    "blocked_count": 1
  },
  "rows": [
    {
      "row_number": 2,
      "status": "create",
      "identity": "board:pg bison:melawood:16:2750:1830",
      "message": "This row will be created when the import is applied.",
      "payload": {
        "brand": "PG Bison",
        "material": "MelaWood",
        "thickness": 16,
        "length_mm": 2750,
        "width_mm": 1830,
        "costing_mode": "sheet"
      },
      "problems": []
    }
  ]
}
```

Row `status` is one of:

- `create`: no matching row exists in the current company library.
- `update`: a matching row exists, but the imported values differ.
- `skipped`: a blank row or an unchanged existing row.
- `duplicate`: an earlier row in the same file has the same identity.
- `blocked`: required data, references, units, dimensions, currency, or prices
  need correction before the row can be applied.

Each problem includes `field`, `code`, `severity`, `message`, and `suggestion`
so the frontend can show plain validation feedback without parsing exception
text. Preview lookups are scoped to the authenticated user's `company_id`,
including supplier, category, catalog item, supplier-cost, and price-list
references.

## Import Apply

```http
POST /api/v1/libraries/imports/apply
```

Permission: `pricing:update`.

This endpoint re-runs the same server-side validation as import preview, then
commits the import inside one PostgreSQL transaction. Rows classified as
`create` or `update` are written, `skipped` rows are left unchanged, and rows
classified as `blocked` or `duplicate` are recorded as failed without writing
that row. Unexpected database failures roll back the whole apply operation.

Request:

```json
{
  "resource": "boards",
  "source_format": "csv",
  "filename": "boards.csv",
  "sheet_name": null,
  "source_ref": "Supplier price list June",
  "content": "Brand,Material,Thickness,Length,Width,Costing Mode\nPG Bison,MelaWood,16,2750,1830,sqm\n",
  "column_mapping": {},
  "price_list_id": null
}
```

Response:

```json
{
  "batch_id": "import-batch-uuid",
  "resource": "boards",
  "source_format": "csv",
  "summary": {
    "total_rows": 3,
    "created_count": 1,
    "updated_count": 1,
    "skipped_count": 0,
    "failed_count": 1
  },
  "rows": [
    {
      "row_number": 2,
      "status": "updated",
      "identity": "board:pg bison:melawood:16:2750:1830",
      "message": "Updated library row.",
      "target_id": "board-uuid",
      "problems": []
    },
    {
      "row_number": 3,
      "status": "failed",
      "identity": "board:pg bison:melawood:16:2750:1830",
      "message": "This row looks like row 2 in the same import.",
      "target_id": "",
      "problems": [
        {
          "field": "identity",
          "code": "duplicate_in_file",
          "severity": "warning",
          "message": "Another import row already uses board:pg bison:melawood:16:2750:1830.",
          "suggestion": "Keep one copy of this item before applying the import."
        }
      ]
    }
  ]
}
```

Apply row `status` is one of `created`, `updated`, `skipped`, or `failed`.
Successful apply operations create audit rows in `library_import_batches` and
`library_import_rows`, including the authenticated user, company, source file
metadata, `source_ref`, content hash, normalized payload, row outcome, target
row id, and structured validation problems.

Validation errors return `422`, duplicate/race conflicts return `409`, and
company-scoped missing references return `404` or `422` depending on whether
the missing row was the target or supporting data. In these error cases the
transaction rolls back and no import rows are applied.

## Catalog Libraries

Each catalog library supports:

```http
GET    /api/v1/libraries/{resource}?search=melawood&recent_days=30
POST   /api/v1/libraries/{resource}
GET    /api/v1/libraries/{resource}/{id}
PATCH  /api/v1/libraries/{resource}/{id}
DELETE /api/v1/libraries/{resource}/{id}
```

`PATCH` currently expects the full editable payload for that resource.

List endpoints are company-scoped and accept:

- `search`: case-insensitive match across the human-readable fields for that resource.
- `recent_days`: rows updated in the last 1 to 365 days.
- `category_id`: extras only, limits rows to one extra category.

### Catalog Bulk Update

```http
PATCH /api/v1/libraries/catalog/bulk-update
```

Requires `catalog:write`. The endpoint only updates explicitly selected row
IDs, never a whole filtered result set.

Payload:

```json
{
  "resource": "handles",
  "item_ids": ["handle-uuid-1", "handle-uuid-2"],
  "updates": {
    "supplier": "Hafele"
  },
  "confirm": false
}
```

Use `confirm: false` to preview. Re-send the same selected IDs and updates with
`confirm: true` to apply.

Supported fields:

- `boards`: `costing_mode`
- `slides`: `brand`, `code`
- `hinges`: `brand`, `code`
- `handles`: `supplier`, `code`
- `extras`: `category_id`, `supplier`, `code`, `notes`
- `suppliers`: `contact_name`, `email`, `phone`, `notes`, `default_discount_bps`

Response:

```json
{
  "resource": "handles",
  "confirm": false,
  "requested_count": 2,
  "matched_count": 2,
  "updated_count": 0,
  "failed_count": 0,
  "summary_message": "Preview ready for 2 selected rows.",
  "rows": [
    {
      "item_id": "handle-uuid-1",
      "label": "Slim Bar (Hafele)",
      "status": "preview",
      "message": "Will update 1 field.",
      "changed_fields": ["supplier"]
    }
  ]
}
```

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
  "notes": "",
  "default_discount_bps": 3000
}
```

Suppliers represent the company/distributor an item is bought from. They are
separate from product brands. For example, a Grass Dynapro slide has product
brand `Grass` and supplier `Grass ZA`.

`default_discount_bps` stores the supplier's default discount in basis points.
`3000` means `30.00%`. The frontend uses this value as the default discount
when adding new supplier item costs.

To set a supplier discount and optionally apply it to every active cost row for
that supplier:

```http
POST /api/v1/libraries/suppliers/{supplier_id}/discount
```

Request:

```json
{
  "discount_bps": 3000,
  "apply_to_active_costs": true,
  "source": "supplier-discount",
  "source_ref": "libraries-ui",
  "effective_from": null
}
```

Response:

```json
{
  "supplier_id": "supplier-uuid",
  "discount_bps": 3000,
  "matched_item_supplier_count": 12,
  "updated_cost_count": 10,
  "unchanged_cost_count": 2,
  "skipped_without_active_cost_count": 0
}
```

When `apply_to_active_costs` is `true`, existing supplier costs current at
`effective_from` are versioned. The old current cost receives `effective_to`,
and the replacement cost keeps the same list price and currency while
recalculating `unit_cost_cents` from the new discount.

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
GET    /api/v1/libraries/item-suppliers?item_type=slide&item_ref_id=slide-uuid&search=dynapro&recent_days=30&has_active_cost=true
POST   /api/v1/libraries/item-suppliers
GET    /api/v1/libraries/item-suppliers/{item_supplier_id}
PATCH  /api/v1/libraries/item-suppliers/{item_supplier_id}
DELETE /api/v1/libraries/item-suppliers/{item_supplier_id}
```

List filters are:

- `item_type`: one of `board`, `slide`, `hinge`, `handle`, or `extra`.
- `item_ref_id`: the catalog row UUID.
- `supplier_id`: the supplier UUID.
- `search`: case-insensitive match across supplier name, SKU, description, component, order UOM, notes, and item type.
- `has_active_cost`: `true` for links with an active supplier cost or `false` for links missing one.
- `recent_days`: rows where the supplier link or active cost changed in the last 1 to 365 days.

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
GET  /api/v1/libraries/item-suppliers/{item_supplier_id}/costs?include_history=false&as_of=2026-06-12T08:00:00Z
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

By default, list endpoints return supplier costs current at `now()`, where
`effective_from <= as_of` and `effective_to` is either null or later than
`as_of`. Pass `as_of` to inspect the cost that was or will be current at a
specific timestamp. Pass `include_history=true` to include current, future, and
retired costs. Responses include:

```json
{
  "is_active": true,
  "is_current": true,
  "effective_status": "current"
}
```

`is_active` means the row has no scheduled end (`effective_to` is null).
`is_current` means the row applies at the requested `as_of` timestamp.
`effective_status` is `current`, `future`, or `retired`.

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
25.00%. Monetary settings are stored in cents in the company currency. These
company settings are defaults for new projects; updating them does not rewrite
existing project or quote pricing settings.

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

Only one price list may be `active` per company. Use
`GET /api/v1/libraries/price-lists/active` when quoting screens need the
currently active list. Add `as_of=2026-06-12T08:00:00Z` to resolve the active
list for a quote or audit timestamp; `effective_from` and `effective_to` are
checked alongside `status`.

### Price List Items

```http
GET    /api/v1/libraries/price-lists/{price_list_id}/items?include_history=false&as_of=2026-06-12T08:00:00Z&search=hinge&item_type=hinge&effective_status=current&recent_days=30
POST   /api/v1/libraries/price-lists/{price_list_id}/items
POST   /api/v1/libraries/price-lists/{price_list_id}/items/upsert
PATCH  /api/v1/libraries/price-lists/{price_list_id}/items/bulk-update
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

By default, list endpoints return only prices current at `now()`, where
`effective_from <= as_of` and `effective_to` is either null or later than
`as_of`. Pass `as_of` to inspect another timestamp. Pass
`include_history=true` to include current, future, and retired prices.
List filters are:

- `search`: case-insensitive match across item type, item key, component, UOM, and source.
- `item_type`: one of `board`, `slide`, `hinge`, `handle`, or `extra`.
- `effective_status`: `current`, `future`, or `retired`.
- `recent_days`: rows updated in the last 1 to 365 days.

Updating a price item does not overwrite the old price. The API closes the row
current at the replacement timestamp by setting `effective_to`, inserts a new
row, and returns the replacement. The response includes:

```json
{
  "id": "new-price-row-uuid",
  "replaces_id": "old-price-row-uuid",
  "effective_from": "2026-05-28T12:00:00Z",
  "effective_to": null,
  "is_active": true,
  "is_current": true,
  "effective_status": "current"
}
```

`is_active` means the row has no scheduled end (`effective_to` is null).
`is_current` means the row applies at the requested `as_of` timestamp.
`effective_status` is `current`, `future`, or `retired`.

Deleting a price item retires the current or future row by setting
`effective_to`; it does not remove historical pricing.

### Price List Item Bulk Update

```http
PATCH /api/v1/libraries/price-lists/{price_list_id}/items/bulk-update
```

Requires `pricing:update`. The endpoint accepts selected price row IDs only.
It does not accept filter expressions as update targets. Current rows are
versioned the same way as the single-row update endpoint; retired and future
rows are reported as failed preview rows.

Payload:

```json
{
  "item_ids": ["price-row-uuid-1", "price-row-uuid-2"],
  "unit_price_cents": 13200,
  "uom": "pcs",
  "cost_source": "override",
  "confirm": false
}
```

At least one of `unit_price_cents`, `uom`, or `cost_source` is required.
`cost_source` can be set to `manual` or `override` through this endpoint.
Use `confirm: false` to preview and `confirm: true` to apply the same selected
row IDs and field changes.

Response shape matches catalog bulk update responses with
`resource: "price_list_items"` and row `status` values of `preview`, `updated`,
or `failed`.

### Generate Price List From Supplier Costs

```http
POST /api/v1/libraries/price-lists/{price_list_id}/generate-from-supplier-costs
```

Payload:

```json
{
  "selection_mode": "preferred_then_cheapest",
  "item_types": ["slide", "hinge"],
  "preserve_manual_overrides": true,
  "effective_from": null
}
```

`effective_from` is the timestamp when generated price rows become current. If
omitted or null, the refresh applies immediately. `selection_mode` controls
which supplier cost current at `effective_from` is copied into the price list
when multiple supplier costs exist for one item:

- `preferred_then_cheapest`: use a preferred supplier cost if present, otherwise the cheapest active cost.
- `preferred_only`: generate only items with a preferred supplier cost.
- `cheapest`: use the cheapest active supplier cost.

Generated rows use:

- `item_key` as `<item_type>::<item_ref_id>`;
- `source_supplier_item_cost_id` pointing to the supplier cost row;
- `cost_source` set to `supplier`;
- `unit_price_cents` copied from the supplier cost `unit_cost_cents`.

When `preserve_manual_overrides` is true, existing rows current at
`effective_from` whose
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

- If a row current at `effective_from` exists for the same `(item_type, item_key, price_component)`, the API versions it and returns the replacement row.
- If no current row exists, the API creates a new row.

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
