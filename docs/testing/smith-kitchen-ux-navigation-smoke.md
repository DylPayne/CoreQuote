# Smith Kitchen UX Navigation Smoke Scenario

Issue: [#124](https://github.com/DylPayne/CoreQuote/issues/124)

Parent issue: [#118](https://github.com/DylPayne/CoreQuote/issues/118)

Use this scenario to validate the UX/navigation rework against a realistic
cabinetry quoting journey. The test is written for a non-technical estimator who
needs to set up common library data, build or review a quote, understand pricing,
prepare outputs, and avoid advanced rule tooling during normal daily work.

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

## Source Job

Start from a completed Smith Kitchen quote from the Phase 1 to Phase 5 product
scenarios, or create an equivalent kitchen quote with these job details:

| Area | Required setup |
| --- | --- |
| Project | Smith Kitchen UX Navigation for client `Sam Smith` at `12 Oak Street` |
| Quote | One visible quote with quote number/revision and a clear selected state |
| Units | Two base door units, one base drawer unit, two wall door units, and one tall door unit |
| Boards | Carcass, door/drawer, and visible-panel boards are available in setup libraries |
| Hardware | Default slide, hinge, base handle, wall handle, tall handle, and drawer handle are available |
| Visible panels | Base side panel pair, wall side filler, kicker, and any generated wall pelmet are reviewable |
| Pricing | One pass with missing-price guidance visible and one pass with all prices resolved |
| Outputs | Customer PDF, workshop schedule, material summary, and hardware pick list are reachable |
| Production | Production handoff is reachable from the quote workflow without exposing customer pricing in the workshop view |

Use existing company data if it already matches the scenario. If the run creates
temporary data, use clearly named Smith Kitchen UX records so later reviewers can
find or remove them.

## User Journey

The scenario passes when a tester can complete this journey without needing to
open `Advanced Cutlist Rules` or `Rule Tester`:

1. Open `Projects` from the everyday work area.
2. Find the Smith Kitchen project from the project list or search.
3. Open the project and confirm the project start point makes it clear how to
   create a new quote, select an existing quote, or review project pricing.
4. Select the Smith Kitchen quote and confirm the quote workflow reads like job
   tasks, not technical tabs: build quote, check quote, review price, outputs,
   and production handoff.
5. Open the unit-building area and confirm the six-unit schedule is visible or
   can be created from the same quote workflow.
6. Open the readiness/check area and confirm plain-language warnings explain the
   next action when setup is incomplete.
7. Open the pricing area while a price is intentionally missing and confirm the
   screen explains what cannot be priced and offers a clear path to pricing
   setup.
8. Resolve or switch to a fully priced quote, then confirm the priced state shows
   the quote total first, with detailed cost/profit rows secondary.
9. Open customer/workshop outputs and confirm output actions are grouped by the
   job task the user is trying to complete.
10. Open production handoff and confirm it is reachable after outputs without
    needing to understand cutlist rule internals.
11. Open `Setup Libraries` from the setup area and confirm the first screen
    points to setup checklist, board materials, hardware, suppliers/costs,
    handles/extras, and pricing setup.
12. Edit representative catalog rows and confirm supported edits open modal
    dialogs rather than unexpectedly showing an edit form at the bottom of the
    page. Cover at least board, hinge, handle, supplier, extra category, and
    extra edits when those rows exist.
13. Confirm imports, bulk edits, maintenance tables, `Advanced Cutlist Rules`,
    and `Rule Tester` are visible only as setup or advanced tools, not as the
    normal path for quoting a kitchen.

## Pricing Guidance Checks

Run both pricing states during the smoke:

| State | Expected user-facing result |
| --- | --- |
| Missing price | The pricing view says which material, hardware, or extra needs a price and offers `Open pricing setup` or equivalent setup guidance. The user should not need to know the internal price-list model. |
| Fully priced | The primary summary shows the customer-facing quote total, VAT state, missing prices at `0`, and a clear distinction between selected quote pricing and project pricing. Cost/profit detail remains available but secondary. |

## Navigation Pass Criteria

The navigation pass should confirm:

| Area | Expected result |
| --- | --- |
| Top-level navigation | Daily work, setup work, and advanced tools are visually distinct. |
| Projects | The opening state makes recent/open projects, creating projects, and quote selection obvious. |
| Quote workflow | The selected quote presents a sequential job workflow instead of a flat set of similarly weighted technical tabs. |
| Libraries | Common setup work is immediately visible; import, bulk-edit, and maintenance tools are progressively disclosed. |
| Catalog edits | Similar create/edit actions use modal dialogs wherever the implementation supports it. |
| Pricing | Quote totals and missing-price recovery are understandable to non-technical users. |
| Outputs | Customer and workshop outputs are reachable from the quote workflow. |
| Production | Workshop handoff is reachable after output review and does not require advanced cutlist pages. |
| Advanced tools | `Advanced Cutlist Rules` and `Rule Tester` stay available, but the normal quoting path does not push users there. |
| Mobile | At about 390 px wide, Projects, selected quote workflow, Setup Libraries, pricing, outputs, production, and advanced cutlist pages do not create horizontal page overflow. |

## Playwright Smoke Evidence

Capture the following evidence for each run:

- Desktop navigation path through Projects, selected project, selected quote,
  units, readiness/check, pricing, outputs, production, Setup Libraries, and
  Advanced.
- Mobile navigation path at about 390 px wide for the same core flow, with a
  horizontal overflow check on Projects, selected quote, Setup Libraries,
  pricing, outputs, production, Advanced Cutlist Rules, and Rule Tester.
- Modal evidence for representative catalog edits.
- Console/network errors or warnings observed after login.
- Any UX friction filed as a linked GitHub follow-up issue.

## Follow-Up Rule

Do not bury remaining friction in the run log. If the smoke finds a user-facing
navigation problem, confusing pricing copy, modal inconsistency, or mobile
overflow that should not block #124, create a follow-up issue linked to #118 and
note the issue number in the run log.

## Manual Run Log

Add a dated entry whenever the scenario is run against the real local stack.

| Date | Environment | Result | Key evidence | Follow-ups |
| --- | --- | --- | --- | --- |
| 2026-06-23 | Local Postgres on `localhost:5433`, FastAPI on `127.0.0.1:8019`, React/Vite on `127.0.0.1:5179`, Playwright MCP, local test owner account | Pass | Desktop smoke opened `Smith Kitchen Phase 1 20260610104559`, selected the ready `Smith Kitchen Phase 3 Fast Entry 2026-06-11` quote, and confirmed the quote workflow exposes build quote, check quote, review price, customer/workshop outputs, and production handoff without putting Rule Tester in the quote workspace. Pricing smoke also opened `Issue 34 Missing Price QA 1781080505703` and confirmed the missing-price state names 2 missing prices, offers `Open pricing setup`, and explains the missing handle and extra rows in quoting language; the ready Smith Kitchen quote showed the priced state with project-vs-quote pricing copy and detailed breakdown kept secondary. Setup Libraries showed setup checklist, board materials, hardware, suppliers/costs, handles/extras, pricing setup, and advanced/import tools separated from everyday tabs. Edit checks opened modal dialogs for board, hinge, handle, supplier, extra category, and extra rows. Mobile smoke at 390 px confirmed no page-level horizontal overflow on Projects, selected quote, quote pricing, outputs, production handoff, Setup Libraries, Advanced Cutlist Rules, and Rule Tester; document/body width stayed `375` and forced horizontal page scroll stayed `0`. Playwright console reported 0 warnings/errors after login, and observed API requests returned `200`. | None filed; no additional user-facing UX friction found in this pass. |
