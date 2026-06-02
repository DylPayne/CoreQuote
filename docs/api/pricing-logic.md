# Detailed Pricing Logic

This document records the pricing behavior derived from the spreadsheet in
`docs/guidelines` and the app-native model used to implement it. The workbook is
a reference for business intent only; CoreQuote does not import workbook data or
mirror spreadsheet formulas cell-by-cell.

## Spreadsheet Flow Observed

Pricing in the workbook is split across a few major areas:

- Numbered unit sheets price each cabinet unit from board area, components,
  handles, legs, consumables, and labour.
- `INPUT!Z2` sums the numbered unit sheet prices into the joinery cabinet total.
- `QUOTE!P17` applies a commission factor to joinery and visible-panel sell
  prices, but not to delivery or installation.
- `PANELS` prices visible panels and fabrication work separately from normal
  cabinet units.
- `COSTING` groups material, component, handle, panel, fabrication,
  installation, delivery, and extra costs, then calculates sell values and
  profit checks.
- `QUOTE` presents the customer-facing pre-VAT subtotal, VAT, and grand total.

## App Pricing Model

CoreQuote treats pricing as a live company-scoped calculation from the current
quote state, active price list, and pricing settings.

The active price list stores base costs. Pricing settings store sell-side
multipliers and operational rates. The calculation returns both cost and sell
values so estimators can see margin, missing prices, and the source of each
total.

## Pricing Settings

Detailed pricing uses these company settings:

- `vat_rate_bps`: VAT applied after all sell totals.
- `default_markup_bps`: backward-compatible default used as a fallback.
- `carcass_markup_bps`: carcass board and related base material markup.
- `door_panel_markup_bps`: doors, drawer fronts, flaps, and visible panels.
- `component_markup_bps`: slides, hinges, and flap mechanisms.
- `handle_markup_bps`: handles and handle profile material.
- `extras_markup_bps`: quote-selected extras and bespoke items.
- `fabrication_markup_bps`: labour, fabrication, CNC, and solid wood work.
- `install_markup_bps`: installation labour markup.
- `delivery_markup_bps`: delivery markup.
- `joinery_commission_bps`: commission applied to joinery and visible-panel
  sell totals before VAT.
- `labour_cents_per_m2`: unit assembly labour base cost by carcass area.
- `consumables_cents_per_m2`: consumables base cost by carcass area.
- `install_day_cost_cents`: base installation cost per day.
- `delivery_base_cents`: base delivery cost per delivery unit.
- `install_units_per_day`: cabinet count used to estimate installation days.
- `delivery_units_per_trip`: cabinet count used to estimate delivery units.
- `minimum_install_days_bps`: minimum install duration, stored as a decimal day
  in basis points. `5000` means `0.5`.
- `minimum_delivery_trips_bps`: minimum delivery units, stored as a decimal in
  basis points. `5000` means `0.5`.

## Quote Calculation

Each quote calculation produces grouped pricing lines with:

- `bucket`: material, component, handle, labour, consumable, installation,
  delivery, extra, commission, or tax.
- `cost_total_cents`: base cost before markup.
- `sell_total_cents`: sell value after markup and any commission when relevant.
- `profit_cents`: sell minus cost.
- `markup_bps`: markup used for that line.
- `qty`, `uom`, and optional active price information.
- `missing`: true when a required base price is absent.

The calculation keeps legacy response totals for existing callers:

- `subtotal_cents`: cost subtotal before markup.
- `sell_before_vat_cents`: sell subtotal before VAT.
- `vat_cents`: VAT on sell subtotal.
- `grand_total_cents`: sell subtotal plus VAT.

## Rules Preserved From The Spreadsheet

- Cabinet material is priced by area and selected board type.
- Carcass material and door/panel material can use separate markups.
- Component, handle, extras, fabrication, installation, and delivery markup
  buckets are independent.
- Installation uses a cabinet-count rule with a minimum duration.
- Delivery uses a cabinet-count rule with a minimum delivery unit.
- Joinery commission is applied to joinery and visible-panel sell totals, not to
  delivery or installation.
- VAT is applied last.

## Rules Not Copied Directly

- Workbook lookup tables are replaced by explicit PostgreSQL catalog and price
  list rows.
- Spreadsheet dynamic-array and `INDIRECT` aggregation is replaced by runtime
  cutlist rows and structured quote/unit state.
- Supplier discounts are stored in supplier item costs. Price-list rows copy the
  selected supplier net cost so quote totals remain stable until regenerated.
- Spreadsheet `ROUNDUP(..., -1)` behavior for extras is not copied by default.
  Extras use the active price list cost and the extras markup.
- The workbook's conversion artifacts such as `#REF!` and dummy Excel UDFs are
  ignored.

## Frontend Requirements

The pricing tab should show:

- total cost, sell before VAT, VAT, grand total, and profit;
- complete or missing-price status;
- quote totals with cost/sell/profit columns;
- grouped line details by bucket;
- clear missing price rows that tell the estimator which price-list item is
  required.

The library pricing settings screen should expose the detailed settings without
cramping the form. Group controls by tax/defaults, material markups, operational
rates, and delivery/installation assumptions.
