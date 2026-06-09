---
title: "Phase 2: Add material and board summary"
milestone: "Phase 2 — Real Quote Outputs"
labels: "phase-2-outputs,type-feature,codex-ready,ui,backend,production,pricing"
---

## Real-world job supported

Before ordering material or trusting a quote, a cabinetmaker needs to know roughly how much board, edging, and visible panel material the job uses.

## User flow

1. The estimator opens quote outputs or pricing.
2. The material summary groups board usage by board type, thickness, and role.
3. The estimator sees total area, sheet count estimate where possible, and related cost/sell values.
4. The summary can be included in workshop/internal outputs.

## Scope included

- Board/material summary for a quote.
- Group by carcass board, door/panel board, custom panel board, and thickness.
- Show area totals and quantities where available.
- Include sheet estimate if board dimensions exist.
- Include in internal quote review or workshop export.

## Scope excluded

- Full nesting/waste optimization.
- Supplier ordering workflow.
- Automatic stock availability.
- Board offcut management.

## Acceptance criteria

- A quote with multiple board types shows separate material groups.
- Board area totals are visible.
- Missing board dimensions or board selections produce clear warnings.
- Summary uses the same source rows as pricing/cutlist where practical.
- Customer-facing quote PDF does not show internal material cost unless explicitly enabled later.

## Real cabinetry test scenario

Create a kitchen quote using white melamine carcass board and oak-look door/panel board. Confirm the summary separates carcass material from visible panels and estimates sheet needs from board size.

## Definition of done

- Material summary appears in the output review or quote workspace.
- Tests cover grouping by board type and missing board data.
- Manual QA confirms totals are plausible for the real-job scenario.
- The summary can be reused by production handoff work.

## Suggested technical notes

- Aggregate from generated cutlist/runtime rows and custom panel rows.
- Store or pass board dimensions, thickness, and costing mode with summary rows.
- Keep estimates labelled as estimates until optimization exists.

## Risks/regressions to watch

- Double-counting door/panel rows.
- Mixing carcass and visible panel materials without explanation.
- Presenting sheet estimates as optimized board counts.
- Divergence between material summary and pricing totals.
