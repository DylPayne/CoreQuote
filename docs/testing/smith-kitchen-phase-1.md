# Smith Kitchen Phase 1 Readiness Scenario

Issue: [#37](https://github.com/DylPayne/CoreQuote/issues/37)

Use this scenario as the shared Phase 1 product acceptance test for a realistic
small kitchen quote. It proves that CoreQuote catches incomplete setup, guides
the estimator to fix it, and reaches a trusted Ready state with units, visible
panels, cutting rows, pricing, delivery, installation, and VAT.

## Local Stack

Run the real local stack before testing:

```bash
docker compose up -d postgres
DATABASE_URL=postgresql://corequote:corequote_dev_password@localhost:5433/corequote_dev \
uv run python infra/db/apply_migrations.py
uv run uvicorn corequote_api.main:app --app-dir apps/api --reload --port 8000
cd apps/web
npm run dev
```

Log in with the local test owner:

- Company: `CoreQuote Test Co`
- Email: `test.owner@corequote.local`
- Password: `CoreQuoteTestPass123!`

## Library Fixtures

Use existing rows if they are already present. Otherwise create rows with these
or equivalent values in `Libraries`.

| Area | Fixture | Values |
| --- | --- | --- |
| Boards | Carcass board | White melamine, 16 mm, 2750 x 1830 mm, sheet costing |
| Boards | Door board | Matt white MDF or melamine, 18 mm, 2750 x 1830 mm, sheet costing |
| Boards | Panel board | Matt white visible panel board, 18 mm, 2750 x 1830 mm, sheet costing |
| Slides | Drawer slide | One 500 mm drawer slide pair |
| Hinges | Door hinge | One 110 degree concealed hinge |
| Handles | Base handle | One pull handle for base doors |
| Handles | Wall handle | One pull handle for wall doors |
| Handles | Tall handle | One pull handle for tall doors |
| Handles | Drawer handle | One pull handle for drawers |

Create one active price list for the company. Add realistic, non-proprietary
`unit` prices for the slide, hinge, and each handle, and `sheet` prices for the
three boards. For the incomplete checkpoint, intentionally omit the drawer handle
price until the warning has been observed.

Use these quote pricing settings unless the company defaults already match them:

| Setting | Value | Scenario reason |
| --- | --- | --- |
| VAT | 15.00% | Confirms tax is included in final totals |
| Default markup | 25.00% | Keeps sell totals visibly above cost |
| Installation day cost | 1900.00 | Includes installation in pricing |
| Units per install day | 12 | Six units produce a half-day installation |
| Minimum install days | 0.50 | Confirms the half-day minimum is active |
| Delivery base | 950.00 | Includes delivery in pricing |
| Delivery units per trip | 20 | The kitchen fits in one small delivery allowance |
| Minimum deliveries | 0.50 | Confirms the delivery minimum is active |

## Project And Quote

Create a project:

| Field | Value |
| --- | --- |
| Project name | Smith Kitchen Phase 1 |
| Client | Sam Smith |
| Address | 12 Oak Street |
| Description | Phase 1 acceptance kitchen with units, panels, pricing, delivery, installation, and VAT. |

Create a quote:

| Field | Value |
| --- | --- |
| Quote name | Smith Kitchen Phase 1 |
| Notes | Real-job readiness scenario for Phase 1. |
| Carcass board | Carcass board fixture |
| Door board | Door board fixture |
| Panel board | Leave blank for the incomplete checkpoint |
| Default slide | Drawer slide fixture |
| Default hinge | Door hinge fixture |
| Base handle | Base handle fixture |
| Wall handle | Wall handle fixture |
| Tall handle | Tall handle fixture |
| Drawer handle | Drawer handle fixture |

Use the default dimensions unless a tester needs to confirm them explicitly:

| Unit family | Height | Depth |
| --- | ---: | ---: |
| Base Draw | 780 mm | 580 mm |
| Base Door | 780 mm | 580 mm |
| Wall Door | 720 mm | 330 mm |
| Tall Door | 2100 mm | 580 mm |

## Units

Add these six units in order:

| # | Unit type | Width | Height | Depth | Extra params |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | Base Door | 600 mm | 780 mm | 580 mm | 1 door, 1 shelf |
| 2 | Base Door | 600 mm | 780 mm | 580 mm | 1 door, 1 shelf |
| 3 | Base Draw | 900 mm | 780 mm | 580 mm | 3 drawers |
| 4 | Wall Door | 600 mm | 720 mm | 330 mm | 1 door, 1 shelf |
| 5 | Wall Door | 600 mm | 720 mm | 330 mm | 1 door, 1 shelf |
| 6 | Tall Door | 600 mm | 2100 mm | 580 mm | 1 door, 4 shelves |

Each unit should use the quote default carcass and door boards. This keeps the
test focused on quote-level readiness rather than unit override behavior.

## Visible Panels

Open `Panels`, save this setup, and keep the panel board blank for the incomplete
checkpoint:

| Panel control | Value |
| --- | --- |
| Base Side Panel | Qty 2, board defaults to panel board |
| Wall Side Filler | Qty 1, board defaults to panel board |
| Kicker board | Defaults to panel board |
| Kicker override | On |
| Kicker override qty | 1 |
| Kicker override length | 2100 mm |
| Kicker override width | 100 mm |

The computed custom rows should include a base side panel pair, one wall side
filler, and one kicker row. The current panel engine may also generate an
automatic `Wall Pelmet` row from the wall-unit run; that is acceptable when it
has positive dimensions and a resolved board.

## Incomplete Checkpoint

Before fixing the setup, verify the app blocks the quote from being treated as
ready:

1. Open `Readiness`.
2. Confirm the summary says `Needs attention before review`.
3. Confirm these check IDs warn:

| Check ID | Expected warning |
| --- | --- |
| `default_boards` | `Choose default boards`, because quote-level panel rows exist but the default panel board is blank |
| `missing_prices` | `Add missing prices`, because the drawer handle price has not been added to the active price list |
| `quote_totals` | `Build a quote total`, because totals cannot be trusted while required prices are missing |
| `required_outputs` | `Prepare review outputs`, because the quote does not yet have trusted pricing |

4. Open `Cutting Lists` and confirm custom rows are visible. If cutlist warnings
   appear for missing quote-panel material, they should point to the panel board
   gap.
5. Open `Pricing` and confirm the missing price guidance names the drawer handle
   and offers a pricing-library action.
6. Do not mark the quote Ready at this stage.

## Fixes

Fix the intentional gaps:

1. Edit the quote and select the panel board fixture as `Panel board`.
2. Open `Libraries`, add the missing active price-list `unit` price for the
   drawer handle, then return to the quote.
3. Open `Pricing` and reload the project pricing summary if needed.
4. Open `Readiness`.

## Ready State

The scenario passes only when all of these are true:

| Area | Expected result |
| --- | --- |
| Readiness summary | `Ready for review` |
| Readiness status | `status` is `ready`, `is_ready` is `true`, `warning_count` is `0`, and `error_count` is `0` |
| Passing check IDs | `project_details`, `unit_count`, `default_boards`, `unit_boards`, `cutlist_rows`, `missing_prices`, `quote_totals`, and `required_outputs` all pass |
| Units | Six cabinet units are shown: two base door units, one base drawer unit, two wall units, and one tall unit |
| Panels | Custom rows include the base side panel pair, wall side filler, and kicker; an automatic wall pelmet row is acceptable |
| Cutting list | Carcass, panel, and custom rows are generated with positive dimensions and no validation warnings |
| Pricing | Project and quote pricing show complete pricing with no missing price guidance |
| Delivery and installation | Pricing line items include delivery and installation service lines |
| VAT | VAT is greater than zero and the grand total is greater than sell before VAT |
| Quote status | The `Mark Ready` action succeeds and the quote status badge shows `Ready` |

Record any product gap discovered while running this scenario as a follow-up
GitHub issue linked to #37 before closing the phase work.

## Manual Run Log

Add a dated entry whenever the scenario is run against the real local stack.

| Date | Environment | Result | Notes |
| --- | --- | --- | --- |
| 2026-06-10 | Local Postgres, FastAPI, React server listening | API-backed readiness pass; browser click-through pending | Created `Smith Kitchen Phase 1 20260610104559`, observed incomplete warnings for `default_boards`, `missing_prices`, `quote_totals`, and `required_outputs`, fixed the panel board and drawer-handle price, reached `ready` with 0 warnings, 6 units, complete pricing, delivery/install lines, VAT, and Ready status. Playwright MCP browser validation was blocked by a locked browser profile. |
