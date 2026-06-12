# Smith Kitchen Phase 4 Library Refresh Scenario

Issue: [#78](https://github.com/DylPayne/CoreQuote/issues/78)

Parent epic: [#45](https://github.com/DylPayne/CoreQuote/issues/45)

Use this scenario as the shared Phase 4 product acceptance test for setting up
the Smith Kitchen libraries from import data, refreshing prices, and proving the
downstream quote outputs still behave like a real cabinetry job.

## Fixture

The sanitized CSV fixture lives in
`docs/testing/fixtures/smith-kitchen-phase-4-library-refresh/`.

Import or preview the files in this order:

| Step | File | Resource | Purpose |
| ---: | --- | --- | --- |
| 1 | `suppliers.csv` | Suppliers | Adds board, hardware, and internal extras suppliers |
| 2 | `boards.csv` | Boards | Adds carcass, door, and visible-panel boards |
| 3 | `slides.csv` | Slides | Adds one 500 mm drawer slide pair |
| 4 | `hinges.csv` | Hinges | Adds one 110 degree concealed hinge |
| 5 | `handles.csv` | Handles | Adds base, wall, tall, and drawer handles |
| 6 | `extra_categories.csv` | Extra categories | Adds the site extras category |
| 7 | `extras.csv` | Extras | Adds a site protection allowance |
| 8 | `supplier_item_costs.csv` | Supplier item costs | Links catalog items to supplier costs |
| 9 | `price_list_items.csv` | Price list rows | Creates active sell prices for the quote |

Create or select an active price list before previewing `price_list_items.csv`.

## Included Data

| Area | Included rows |
| --- | --- |
| Boards | `CoreBoard White melamine 16mm`, `CoreBoard Matt white door board 18mm`, `CoreBoard Matt white visible panel 18mm` |
| Hardware | `Grass Dynapro soft close` slide, `Blum 110 degree soft close` hinge |
| Handles | `Base pull`, `Wall pull`, `Tall pull`, `Drawer pull` |
| Extras | `Site protection` in `Site extras` |
| Prices | Active ZAR prices for all boards, slide, hinge, handles, and site protection |
| Pricing assumptions | 15.00% VAT and 25.00% default markup, matching the Phase 1/2 Smith Kitchen scenarios |

The fixture uses example suppliers and non-proprietary prices. Email addresses
use `example.invalid`, and no client, supplier, or workbook secrets are present.

## Quote Path

After importing the fixture, create the Smith Kitchen quote from the Phase 1/2
scenario:

- project `Smith Kitchen Phase 4 Library Refresh`;
- client `Sam Smith`;
- address `12 Oak Street`;
- two base door units, one base drawer unit, two wall units, and one tall unit;
- quote defaults set to the imported carcass, door, visible-panel board, slide,
  hinge, and four handle choices;
- quote extras include `Site protection`;
- visible panels include a base side panel pair, wall side filler, and kicker.

The scenario passes only when:

| Area | Expected result |
| --- | --- |
| Readiness | `Ready for review`, zero warnings, zero errors |
| Pricing | Missing prices are `0`, VAT is greater than zero, and the grand total is greater than sell before VAT |
| Material summary | Carcass, door/drawer, and visible-panel groups use the imported CoreBoard rows |
| Hardware pick list | Slide, hinge, base/wall/tall/drawer handles, and site protection are present |
| Customer PDF | Renders successfully and totals match the pricing summary |
| Workshop schedule | Renders successfully with the imported board labels on cutting rows |
| Price refresh stability | A later active price refresh can change new pricing without mutating the original pricing summary evidence |

## Automated Coverage

`tests/unit/test_smith_kitchen_phase4_fixture.py` previews the fixture files in
the same order, resolves natural keys across catalog rows, prices the Smith
Kitchen Phase 2 quote with the imported rows, verifies readiness, material
summary, hardware pick list, customer PDF, workshop schedule, and checks that a
later price refresh does not mutate the original pricing summary.

Run it with:

```bash
uv run pytest tests/unit/test_smith_kitchen_phase4_fixture.py
```

## Workbook Ambiguity

The supplier workbook reference contains useful business intent, but the Phase 4
fixture intentionally does not recreate workbook formulas cell by cell. The
fixture records these explicit assumptions instead:

| Ambiguity | Fixture decision |
| --- | --- |
| Board prices can be sheet or square-metre based | Use sheet prices for all three board rows |
| Supplier discounts vary by supplier sheet | Use 0% discount and put net cost directly in `Unit Cost` |
| Handles can be grouped by cabinet type or one generic handle | Use separate base, wall, tall, and drawer handle rows |
| Delivery and installation may be quote services rather than catalog extras | Keep delivery/install in pricing settings and model only site protection as an extra |

If later workbook review finds a different production assumption, open a
follow-up issue linked to #78 rather than silently changing this fixture.

## Manual Run Log

Add a dated entry whenever the scenario is run against the real local stack.

| Date | Environment | Result | Key path verified | Follow-ups |
| --- | --- | --- | --- | --- |
| 2026-06-12 | Local Postgres on `localhost:5433`, FastAPI on `127.0.0.1:8001`, React/Vite on `127.0.0.1:5175`, Playwright MCP, local test owner account | Pass | Applied the committed fixture CSVs through the real API into the active `Supplier Cost Import` price list: suppliers 3 skipped after an earlier partial attempt, boards 3 created, slides 1 created, hinges 1 created, handles 4 created, extra category 1 created, extra 1 created, supplier costs 10 created, and active price rows 10 created with 0 failed rows. Libraries UI showed setup checklist `9/9 ready`; UI preview of `price_list_items.csv` returned 10 rows, 0 new, 0 updates, 10 skips, 0 duplicates, and 0 blocked; Playwright network showed `POST /api/v1/libraries/imports/preview` 200 and no console errors. API log also showed an isolated `Smith Kitchen Phase 4 Library Refresh` quote flow returning 200 for readiness, output review, customer PDF, and workshop schedule; Postgres read-only confirmed quote `ca6ddf24-0269-4c8b-b8b0-cab6033f9878` is `ready` with 6 units, 1 quote extra, 3 imported CoreBoard rows, 1 slide, 1 hinge, 4 handles, 1 site-protection extra, and 10 active price rows. Automated regression `tests/unit/test_smith_kitchen_phase4_fixture.py` verifies the imported fixture drives Smith Kitchen readiness, pricing, material summary, hardware pick list, customer PDF, workshop schedule, and quote-total stability. | None filed; the run found and fixed the brand-backed catalog import `brand_id` apply bug in this PR. |
