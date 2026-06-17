# Smith Kitchen Phase 5 Workshop Handoff Scenario

Issue: [#94](https://github.com/DylPayne/CoreQuote/issues/94)

Parent epic: [#46](https://github.com/DylPayne/CoreQuote/issues/46)

Use this scenario as the shared Phase 5 product acceptance test for a realistic
workshop handoff. It extends the Smith Kitchen Phase 2 output package and proves
that a production user can cut, edge, label, order board, pick hardware, review
warnings, and export CSV/XLSX data without seeing customer totals, internal
cost, profit, margin, or markup.

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

Start from a completed [Smith Kitchen Phase 2](smith-kitchen-phase-2.md) quote,
or create an equivalent quote with these required values:

| Area | Required setup |
| --- | --- |
| Project | `Smith Kitchen Phase 5 Workshop Handoff`, client `Sam Smith`, site `12 Oak Street` |
| Quote | Ready Smith Kitchen quote with visible quote number and revision |
| Units | Two base door units, one base drawer unit, two wall door units, and one tall door unit |
| Boards | Carcass, door/drawer, and visible panel boards selected, priced, and available in the board library |
| Hardware | Default slide, hinge, base handle, wall handle, tall handle, and drawer handle selected and priced |
| Visible panels | Base side panel pair, wall side filler, kicker, and any generated wall pelmet have resolved boards |
| Services | Delivery, installation, and site protection remain priced in quote outputs but absent from workshop production packet totals |
| Pricing | VAT is enabled and the quote has no missing prices before production review |

Use the same pricing settings and library fixture assumptions as Phase 2/4 unless
a follow-up issue intentionally changes them.

## Production Setup

Add or confirm these workshop-specific instructions before the final pass:

| Scope | Edge-banding | Grain and rotation | Notes |
| --- | --- | --- | --- |
| Door/drawer panel default | `1mm ABS on all exposed door and drawer-front edges` | Length grain, no rotation | Keep door labels matched to the unit number |
| Drawer unit override | `1mm ABS on all drawer-front edges` | Width grain, no rotation | Stack drawer-front labels from top to bottom |
| Visible panel default | `1mm ABS on all exposed visible-panel edges` | Length grain, no rotation | Label finished face before cutting |
| Wall pelmet row override | `1mm ABS on front long edge only` | Width grain, no rotation | Run pelmet grain continuously across the wall units |

For the warning checkpoint, temporarily remove the visible-panel edge-banding or
grain instruction, open the production handoff, and confirm the affected
quote-level panel row is marked for review. Restore the instruction before the
final pass.

## Expected Workshop Packet

The scenario passes only when all of these are true:

| Area | Expected result |
| --- | --- |
| Production grouping | Rows are grouped by board/material, thickness, material role, unit, and section; the six-unit Smith Kitchen fixture produces 13 groups from 22 deterministic cutting rows |
| Stable part IDs | Part IDs remain stable after reload and use quote number, revision, source, section, part, dimensions, and repeat index |
| Carcass parts | Carcass rows use the carcass board, positive dimensions, positive quantities, and no production warnings |
| Door/drawer panels | Door rows show length grain and no rotation; drawer-front rows show the drawer-unit width-grain override |
| Visible panels | Base side panel pair, wall side filler, kicker, and wall pelmet appear as quote-level production rows |
| Kicker/pelmet/filler rows | Kicker, wall side filler, and wall pelmet rows keep visible-panel board selection, edge instructions, grain/rotation notes, and label-ready part IDs |
| Labels | Label count equals cutting row count, every label uses an existing part ID, and warning state is visible on labels |
| Material totals | Material summary and board requirements agree on piece count, area, estimated sheets, and quote-level visible-panel part IDs |
| Board requirements | Sheet counts are labelled as estimates and are not presented as optimized nesting |
| Hardware pick list | Slide, hinge, base/wall/tall/drawer handles, and site protection are present with expected quantities |
| Warning review | Missing edge/grain/rotation data creates visible warnings; the final pass has zero cutting, production, material, board-requirement, and hardware warnings |
| CSV export | CSV downloads with workshop-facing columns, stable part IDs, edge/grain/rotation notes, warning state, and no pricing fields |
| XLSX export | Workbook includes Cutting Schedule, Material Summary, Board Requirements, Hardware Pick List, Labels, and Warnings sheets |
| Privacy | Customer total, internal cost, sell total, profit, margin, markup, and price-list line amounts are absent from production UI and exports |

Expected hardware quantities for the default Smith Kitchen setup:

| Item | Quantity |
| --- | ---: |
| Drawer slide pairs | 3 |
| Hinges | 12 |
| Base handles | 2 |
| Wall handles | 2 |
| Tall handles | 1 |
| Drawer handles | 3 |
| Site protection | 1 |

## Manual Review Steps

1. Open `Projects` and select the completed `Smith Kitchen Phase 5 Workshop Handoff` quote.
2. Open `Readiness` and confirm the quote is ready with zero warnings and zero errors.
3. Open `Review outputs` and confirm the workshop schedule, production CSV, production workbook, material summary, and hardware pick-list actions are enabled.
4. Open `Production`.
5. Record row count, group count, label count, warning count, board requirement count, and hardware item count.
6. Confirm the visible quote-level rows include `Base side panel pair`, `Wall side filler`, `Kicker`, and `Wall pelmet`.
7. Confirm a door row, drawer-front row, and wall pelmet row show the expected edge-banding, grain, rotation, and production notes.
8. Confirm label part IDs match production row part IDs.
9. Review board requirements and confirm sheet counts are clearly labelled as estimates.
10. Review hardware pick list quantities against the table above.
11. Search the production view for `total`, `cost`, `sell`, `profit`, `margin`, and `markup`; none should expose customer or internal pricing data.
12. Download production CSV and XLSX.
13. Open the CSV and XLSX and confirm the expected sheets/columns, quote-level panel rows, labels, warnings sheet, and absence of pricing fields.
14. Record any issue that could cause an incorrect cut, edge, label, board order, or hardware pick as a GitHub follow-up linked to #94 and #46.

## Automated Regression

`tests/unit/test_smith_kitchen_phase5_workshop_handoff.py` extends the
deterministic Smith Kitchen Phase 2 fixture with Phase 5 production metadata. It
verifies row/group/label counts, stable part IDs, visible-panel rows, edge and
grain notes, board requirements, hardware quantities, warning-free final output,
CSV/XLSX export shape, and production-output privacy.

Run it with:

```bash
uv run pytest tests/unit/test_smith_kitchen_phase5_workshop_handoff.py
```

## Manual Run Log

Add a dated entry whenever the scenario is run against the real local stack.

| Date | Environment | Result | Key evidence | Follow-ups |
| --- | --- | --- | --- | --- |
| 2026-06-15 | Local Postgres on `localhost:5433`, FastAPI on `127.0.0.1:8002`, React/Vite on `127.0.0.1:5174`, Playwright MCP, local test owner account | Smoke pass; final scenario pass pending | Opened existing ready `Smith Kitchen Phase 3 Fast Entry 2026-06-11` quote, selected `Production`, confirmed `13 groups`, `45 rows`, `45 labels`, `15 warnings`, visible grain/edge warning review, board requirements `22.01 m2`, `9 est. sheets`, `70 pieces`, hardware pick list `3 lines` and `23 items`, downloaded CSV and XLSX exports, saw production handoff/export network requests return `200`, and saw no browser console warnings or errors. | Complete the final no-warning Phase 5 run after entering the production metadata in this scenario; no new follow-up issue filed from this smoke. |

## Automated Run Log

| Date | Environment | Result | Notes |
| --- | --- | --- | --- |
| 2026-06-15 | Core-output pytest regression | Pass | `uv run pytest tests/unit/test_smith_kitchen_phase5_workshop_handoff.py` passed and verified Phase 5 production grouping, labels, board requirements, hardware quantities, warning-free exports, and pricing privacy. |
