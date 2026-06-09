---
title: "Phase 1: Show missing price guidance"
milestone: "Phase 1 — Trustworthy Quote Flow"
labels: "phase-1-trust,type-feature,codex-ready,ui,backend,pricing"
---

## Real-world job supported

An estimator sees a quote total that is too low because some boards, hardware, handles, or extras have no price. They need to know exactly what to fix.

## User flow

1. The estimator opens quote pricing.
2. Missing items are grouped in one clear list.
3. Each missing item says what is missing and where it is used.
4. The estimator can navigate to the matching library/pricing area.
5. After adding the price, the quote pricing updates and the warning clears.

## Scope included

- Missing price summary for selected quote and project pricing.
- Group missing items by board, slide, hinge, handle, extra, labour, delivery, or installation where applicable.
- Show item name, component, unit of measure, and affected quote.
- Link users toward the correct library/pricing screen.
- Ensure missing prices affect readiness.

## Scope excluded

- Supplier price import.
- Automatic price suggestions.
- Bulk price editing.
- Historical price comparison.

## Acceptance criteria

- Missing price rows are visible without reading line-item details one by one.
- The user can identify the exact library item needing a price.
- Missing prices are reflected in the readiness checklist.
- Complete pricing still shows cost, sell, VAT, profit, and total.
- UI copy says "Add a price for..." rather than exposing raw item keys.

## Real cabinetry test scenario

Create a quote with a board, one slide, one hinge, and one handle. Remove the handle price from the active price list. Confirm the quote shows the handle as missing and points the estimator to the price list entry to add.

## Definition of done

- Missing price guidance is visible at quote level and project pricing level.
- Tests cover missing board and missing hardware prices.
- Existing pricing totals do not double-count or hide missing lines.
- Readiness checks consume the same missing-price signal.

## Suggested technical notes

- Extend pricing summary responses with a missing price collection if line items are not enough.
- Use stable item references so the UI can route to the relevant library tab later.
- Keep the existing detailed line table for estimator confidence.

## Risks/regressions to watch

- Treating missing costs as zero without warning.
- Duplicating missing items many times for repeated units.
- Breaking existing pricing summary calculations.
- Making the user hunt through long library tables manually.
