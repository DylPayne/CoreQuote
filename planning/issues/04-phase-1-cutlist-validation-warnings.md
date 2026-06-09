---
title: "Phase 1: Warn about invalid cutting schedule rows"
milestone: "Phase 1 — Trustworthy Quote Flow"
labels: "phase-1-trust,type-feature,codex-ready,ui,backend,production"
---

## Real-world job supported

A workshop must not receive a cutting schedule with zero-length parts, missing board choices, or impossible dimensions.

## User flow

1. The estimator opens the cutting list tab for a quote.
2. The app shows warning messages above the schedule if rows are not usable.
3. Each warning explains the affected unit or custom panel.
4. The estimator fixes dimensions, boards, or unit setup before exporting.

## Scope included

- Validate generated cutlist rows for zero or negative length, width, or quantity.
- Warn when a cutlist row cannot be tied to a usable board/material.
- Show affected unit number and row description.
- Include warnings in quote readiness.
- Keep the schedule visible so the estimator can inspect it.

## Scope excluded

- Full cut optimization.
- Label printing.
- Board nesting layout.
- Changing formula/ruleset behavior unless needed to surface the warning.

## Acceptance criteria

- Zero-length rows are clearly marked.
- Negative or zero quantity rows are clearly marked.
- Missing board/material choices are clearly marked.
- Warnings identify the affected unit or quote-level panel.
- Workshop export work in Phase 2 can block or warn based on these checks.

## Real cabinetry test scenario

Create a base drawer unit with a slide/default setup that produces zero drawer side dimensions. Confirm the cutting list shows a warning before the user exports the schedule.

## Definition of done

- Cutlist validation runs whenever the quote cutting list is displayed.
- Readiness checklist includes cutlist validation status.
- Tests cover at least one zero-dimension row and one valid row.
- Existing valid cutting lists continue to display normally.

## Suggested technical notes

- Add a validation layer after cutlist generation rather than burying warnings inside formulas.
- Return severity, unit number, row description, and reason.
- Keep generated rows unchanged so users can still inspect the source issue.

## Risks/regressions to watch

- Blocking valid edge cases such as intentional zero-quantity conditional rows after filtering.
- Producing warnings that are too technical for estimators.
- Hiding invalid rows instead of making them visible.
- Slowing down quote loading for large projects.
