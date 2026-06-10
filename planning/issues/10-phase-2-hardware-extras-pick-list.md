---
title: "Phase 2: Add hardware and extras pick list"
milestone: "Phase 2 — Real Quote Outputs"
labels: "phase-2-outputs,type-feature,codex-ready,ui,backend,production"
---

## Real-world job supported

The workshop or purchasing person needs a list of slides, hinges, handles, and extras required for the quote.

## User flow

1. The estimator opens quote outputs.
2. The hardware pick list groups required components by type.
3. The user sees supplier/code, quantity, and affected units where available.
4. The list can be exported or included in the workshop package.

## Scope included

- Hardware/components summary for slides, hinges, handles, and selected extras.
- Include supplier, code/SKU, item name, quantity, and unit association where known.
- Include missing component warnings.
- Include the pick list in workshop/internal outputs.

## Scope excluded

- Supplier purchase order creation.
- Stock tracking.
- Barcode scanning.
- Delivery tracking.

## Acceptance criteria

- Drawer units contribute slide quantities where configured.
- Door units contribute hinge quantities where configured.
- Handles and quote extras appear when selected.
- Missing component choices are visible and affect readiness.
- The pick list can be used without exposing pricing margin.

## Real cabinetry test scenario

Use a quote with one three-drawer base unit, two two-door base units, two wall units, handles, and one extra item. Confirm the pick list shows slides, hinges, handles, and the extra with quantities.

## Definition of done

- Pick list appears in the quote output review or workshop export.
- Tests cover at least slides, hinges, handles, and extras.
- Manual QA confirms quantities match the real-job scenario.
- Missing component setup is reflected in readiness.

## Suggested technical notes

- Reuse pricing/component counting logic where possible.
- Separate quantity calculation from price calculation so the list can be used even before final pricing.
- Keep item ids available for future supplier ordering.

## Risks/regressions to watch

- Counting handles or hinges incorrectly across unit types.
- Ignoring quote-level extras.
- Making pricing required before a pick list can be useful.
- Duplicating logic between pricing and production outputs.
