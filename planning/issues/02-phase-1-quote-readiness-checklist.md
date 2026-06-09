---
title: "Phase 1: Add quote readiness checklist"
milestone: "Phase 1 — Trustworthy Quote Flow"
labels: "phase-1-trust,type-feature,codex-ready,ui,backend,pricing,production"
---

## Real-world job supported

Before sending a quote or cutting parts, an estimator needs one clear answer: is this quote complete enough to trust?

## User flow

1. The estimator opens a quote.
2. A readiness panel shows what is complete and what still needs attention.
3. The estimator clicks a warning to jump to the area that needs fixing.
4. When all required checks pass, the quote can be marked Ready.

## Scope included

- Readiness panel in the quote workspace.
- Checks for client/project details, unit count, default boards, unit boards, missing prices, invalid cutlist rows, quote totals, and required outputs.
- Clear pass/warning/error display.
- Links or actions that take the user to the relevant tab.
- Readiness status usable by future export/send workflows.

## Scope excluded

- Blocking all work until every warning is fixed.
- Client quote PDF generation.
- Workshop export generation.
- Automated supplier lookup.

## Acceptance criteria

- A new quote with no units shows helpful setup tasks.
- A quote with missing boards shows a specific warning.
- A quote with missing prices shows a specific warning.
- A quote with invalid cutlist rows shows a specific warning.
- A complete quote can show Ready without exposing internal implementation details.
- Readiness wording explains the business problem, not the technical cause.

## Real cabinetry test scenario

Create a kitchen quote with one base drawer unit, no carcass board, and no board prices. Confirm the readiness panel says what is missing. Add the required board and price, regenerate the checks, and confirm the quote becomes ready for review.

## Definition of done

- Readiness checks run from current quote data.
- The checklist appears in a predictable place in the quote workspace.
- Each failed check has a direct next action.
- Tests cover at least missing boards, missing prices, no units, and invalid cutlist rows.
- The checklist is ready to be reused by export buttons in Phase 2.

## Suggested technical notes

- Prefer a single quote-readiness service or helper that can be reused by UI and export endpoints.
- Return structured check ids, severity, title, message, and suggested action.
- Keep warnings separate from blocking errors so the product can mature without trapping users.

## Risks/regressions to watch

- Readiness logic drifting away from pricing and cutlist logic.
- Too many warnings making the panel noisy.
- False confidence when checks pass but outputs are still incomplete.
- Hiding advanced issues that matter to production.
