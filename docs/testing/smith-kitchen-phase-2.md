# Smith Kitchen Phase 2 Output Package Scenario

Issue: [#43](https://github.com/DylPayne/CoreQuote/issues/43)

Use this scenario as the shared Phase 2 product acceptance test for a realistic
small kitchen output package. It extends the Phase 1 readiness scenario and
proves that one Ready quote can produce a customer quote PDF, workshop cutting
schedule, material summary, and hardware pick list from the same quote data.

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

Start from the completed [Smith Kitchen Phase 1](smith-kitchen-phase-1.md)
scenario, or create an equivalent quote with these required Phase 2 additions:

| Area | Required setup |
| --- | --- |
| Quote | `Smith Kitchen Phase 2`, client `Sam Smith`, site `12 Oak Street`, quote number/revision visible |
| Units | Two base door units, one base drawer unit, two wall door units, and one tall door unit |
| Boards | Carcass, door/drawer, and visible panel boards selected and priced |
| Hardware | Default slide, hinge, base handle, wall handle, tall handle, and drawer handle selected and priced |
| Visible panels | Base side panel pair, wall side filler, kicker, and any generated wall pelmet have resolved boards |
| Services | Delivery and installation pricing are included |
| Pricing | VAT is enabled, missing price guidance is clear, and the final Ready quote has no missing prices |
| Terms | Quote notes include payment terms and the PDF shows an expiry date |

Use the same pricing settings as Phase 1 unless a product issue explicitly asks
for different commercial assumptions:

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

## Expected Output Package

The scenario passes only when all of these are true:

| Output | Expected result |
| --- | --- |
| Readiness | `Ready for review`, `is_ready` is `true`, and warning/error counts are zero |
| Customer PDF | Downloads successfully, shows client/project/quote metadata, terms, expiry date, VAT, subtotal, and grand total |
| Customer PDF privacy | Internal cost, margin, profit, workshop rows, and supplier picking detail are not visible |
| Customer total | PDF grand total matches the on-screen quote total from pricing/output review |
| Workshop schedule | Downloads successfully with carcass, panel, and custom panel cut rows grouped for workshop review |
| Workshop warnings | The completed scenario should have no warnings; if warnings appear, they must be visible in the schedule and logged as a gap |
| Material summary | Shows carcass, door/drawer, and visible panel material groups with piece counts, area, sheet estimate, and no warnings |
| Hardware pick list | Shows slides, hinges, base handles, wall handles, tall handles, drawer handles, and selected extras with quantities and no warnings |
| Output actions | Client PDF, workshop schedule, material summary, and hardware pick list actions are enabled |

Expected hardware quantities for the default six-unit setup:

| Item | Quantity |
| --- | ---: |
| Drawer slide pairs | 3 |
| Hinges | 12 |
| Base handles | 2 |
| Wall handles | 2 |
| Tall handles | 1 |
| Drawer handles | 3 |

## Manual Review Steps

1. Open `Projects` and select the completed `Smith Kitchen Phase 2` quote.
2. Open `Readiness` and confirm all checks pass.
3. Open `Pricing` and record the quote grand total.
4. Open `Review outputs`.
5. Confirm all four output actions are enabled.
6. Download the customer quote PDF.
7. Review the PDF as the client and confirm only sell totals, VAT, terms, expiry, and quote metadata are visible.
8. Download the workshop schedule PDF.
9. Review the schedule as the workshop and confirm cut rows are readable, grouped, and include warnings only if the app shows warnings.
10. Review material summary and hardware pick list in the app.
11. Record any readability, correctness, or workflow gap as a GitHub follow-up linked to #43.

## Automated Regression

`tests/unit/test_real_job_output_package.py` keeps a deterministic copy of this
scenario at the core-output layer. It verifies that the same quote/cutlist data:

- prices completely with VAT, delivery, installation, boards, hardware, and extras;
- reaches Ready with no readiness warnings;
- enables all output review actions;
- builds a customer PDF document whose total matches the pricing grand total;
- excludes internal cost, profit, and margin fields from the customer document;
- builds a workshop schedule with carcass, panel, and custom panel rows;
- provides material summary and hardware pick-list data for the same quote.

Run it with:

```bash
uv run pytest tests/unit/test_real_job_output_package.py
```

## Manual Run Log

Add a dated entry whenever the scenario is run against the real local stack.

| Date | Environment | Result | Notes |
| --- | --- | --- | --- |
| Pending | Local Postgres, FastAPI, React server | Pending | Run the manual review steps before using this as release evidence for Phase 2 closure. |

## Automated Run Log

| Date | Environment | Result | Notes |
| --- | --- | --- | --- |
| 2026-06-11 | Core-output pytest regression | Pass | `uv run pytest tests/unit/test_real_job_output_package.py` passed; no output package gaps found in the deterministic Smith Kitchen Phase 2 fixture. |
