# Smith Kitchen Phase 3 Fast Entry Scenario

Issue: [#65](https://github.com/DylPayne/CoreQuote/issues/65)

Parent epic: [#44](https://github.com/DylPayne/CoreQuote/issues/44)

Use this scenario as the shared Phase 3 product acceptance test for accelerated
quote entry. It proves that duplicate quote, bulk unit entry, reorder, and bulk
apply flows can recreate the Smith Kitchen job faster without weakening
readiness, pricing, cutlist, material summary, hardware pick-list, or output
review confidence.

## Local Stack

Run the real local stack before manual testing:

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

## Source Scenario

Start from the completed [Smith Kitchen Phase 1](smith-kitchen-phase-1.md) or
[Smith Kitchen Phase 2](smith-kitchen-phase-2.md) scenario, or create an
equivalent ready quote with these required details:

| Area | Required setup |
| --- | --- |
| Project | Smith Kitchen project for client `Sam Smith` at `12 Oak Street` |
| Quote | Ready baseline quote with quote number/revision visible |
| Units | Two base door units, one base drawer unit, two wall door units, and one tall door unit |
| Boards | Carcass, door/drawer, and visible panel boards selected and priced |
| Hardware | Default slide, hinge, base handle, wall handle, tall handle, and drawer handle selected and priced |
| Visible panels | Base side panel pair, wall side filler, kicker, and any generated wall pelmet have resolved boards |
| Services | Delivery and installation pricing are included |
| Pricing | VAT is enabled, missing price guidance is clear, and the final quote has no missing prices |
| Outputs | Customer PDF, workshop schedule, material summary, and hardware pick list are ready to generate |

Use the same pricing settings as the Phase 1/2 Smith Kitchen scenarios unless a
product issue explicitly asks for different commercial assumptions:

| Setting | Value |
| --- | ---: |
| VAT | 15.00% |
| Default markup | 25.00% |
| Installation day cost | 1900.00 |
| Units per install day | 12 |
| Minimum install days | 0.50 |
| Delivery base | 950.00 |
| Delivery units per trip | 20 |
| Minimum deliveries | 0.50 |

## Fast Entry Workflow

1. Open the ready Smith Kitchen baseline quote.
2. Use `Duplicate quote` to create the Phase 3 working quote. If the test needs
   to validate revisions instead of duplicate quotes, create a revision from the
   copied quote before output review.
3. Rename the quote to `Smith Kitchen Phase 3 Fast Entry <date>`.
4. Open `Bulk Unit Entry` and create or confirm these six rows in order:

| # | Unit type | Width | Height | Depth | Extra params |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | Base Door | 600 mm | 780 mm | 580 mm | 1 door, 1 shelf |
| 2 | Base Door | 600 mm | 780 mm | 580 mm | 1 door, 1 shelf |
| 3 | Base Draw | 900 mm | 780 mm | 580 mm | 3 drawers |
| 4 | Wall Door | 600 mm | 720 mm | 330 mm | 1 door, 1 shelf |
| 5 | Wall Door | 600 mm | 720 mm | 330 mm | 1 door, 1 shelf |
| 6 | Tall Door | 600 mm | 2100 mm | 580 mm | 1 door, 4 shelves |

5. Save the bulk grid.
6. Use the unit table reorder controls to move one unit down and then back up,
   confirming the final order still matches the table above.
7. Select all six units, open `Bulk apply`, and apply the quote-default carcass
   and door boards unless the test intentionally needs unit-level overrides.
8. Open `Panels`, `Pricing`, `Readiness`, and `Review outputs`.
9. Mark the quote Ready only after all readiness checks pass.
10. Record timing, repeated steps avoided, downstream output state, and any
    follow-up issues linked to #44.

## Pass/Fail Criteria

The scenario passes only when all of these are true:

| Area | Expected result |
| --- | --- |
| Quote | Phase 3 quote is a duplicate or revision of the ready baseline and has its own visible quote number/revision |
| Units | Six units are present in the expected order after the bulk grid save and reorder round trip |
| Bulk apply | Selected defaults/overrides persist across all selected units |
| Visible panels | Base side panel pair, wall side filler, kicker, and any automatic wall pelmet have resolved boards |
| Readiness | Summary is `Ready for review`, warning count is `0`, and error count is `0` |
| Quote status | `Mark Ready` succeeds and the quote status badge shows `Ready` |
| Pricing | Client total is populated, delivery and installation are included, VAT is greater than zero, and missing prices are `0` |
| Cutting list | Workshop cutting rows are generated with positive dimensions and no cutlist warnings |
| Material summary | Material summary is ready with carcass, door/drawer, and visible-panel material usage |
| Hardware pick list | Hardware pick list is ready with expected slide, hinge, and handle quantities |
| Output review | Client PDF, workshop schedule, material summary, and hardware pick-list actions are enabled |

## Friction Signals

Record practical speed evidence each time the scenario is run:

| Signal | Baseline one-unit-at-a-time flow | Phase 3 fast-entry target |
| --- | --- | --- |
| Unit entry | Six individual unit forms and saves | One bulk-grid save for the six-unit schedule |
| Shared defaults | Repeated board/hardware checks per unit when correcting setup | One selected-unit bulk apply operation |
| Reordering | Manual delete/recreate or edit-heavy correction if order drifts | Reorder controls update sequence directly |
| Quote variant | Re-enter project/quote setup for alternatives | Duplicate quote or revision preserves trusted setup |
| Downstream review | Same readiness/output checks after manual entry | Same readiness/output checks after accelerated entry |

Capture approximate elapsed time from choosing the baseline quote to confirming
`Review outputs`, the number of screens/forms used, repeated edits avoided, and
any remaining friction that should become a follow-up issue.

## Relevant Automated Coverage

The manual scenario remains the acceptance evidence for #65. These automated
tests cover the Phase 3 feature contracts and the downstream Smith Kitchen
output package:

```bash
uv run pytest tests/api/test_projects_quotes.py
uv run pytest tests/unit/test_projects_quotes_copying.py
uv run pytest tests/unit/test_real_job_output_package.py
npm run build
```

## Manual Run Log

Add a dated entry whenever the scenario is run against the real local stack.

| Date | Environment | Result | Timing and friction notes | Downstream evidence | Follow-ups |
| --- | --- | --- | --- | --- | --- |
| 2026-06-11 | Local Postgres on `localhost:5433`, FastAPI on `127.0.0.1:8001`, React/Vite on `127.0.0.1:5174`, Playwright MCP, local test owner account | Pass | Approximately 7 minutes from selecting the ready baseline quote to output-review verification. Used duplicate quote, one quote edit, one bulk-grid save, one reorder down/up round trip, one selected-unit bulk apply, readiness review, and output review. Avoided six individual unit forms, repeated board selection edits, and re-entering project/quote pricing defaults. | Duplicated `Smith Kitchen Phase 1` into `Smith Kitchen Phase 3 Fast Entry 2026-06-11`; confirmed six units, 45 workshop rows, 70 material pieces, 22.01 m2 material area, 23 hardware quantity, 9 estimated sheets, 3 hardware/material lines, client total `R 9 362,46`, missing prices `0`, cutlist warnings `0`, readiness warnings/errors `0`, and all four output actions ready. Postgres read-only inspection confirmed `status` `ready`, `Q-002` revision `1`, six units, visible panel setup, VAT, markup, delivery, and installation settings persisted. | None filed; no Phase 3 product gap was found in this run. |

## Manual Evidence Checklist

For review, attach or summarize evidence for:

- Browser flow through duplicate quote, bulk unit entry, reorder, bulk apply,
  readiness, and output review.
- Console state from the frontend smoke test, including any warnings or errors.
- Read-only database inspection proving the copied quote persisted with the
  expected status, unit count, panels, and pricing settings.
- Any follow-up GitHub issues linked to #44.
