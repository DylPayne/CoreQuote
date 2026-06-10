---
title: "Phase 2: Export workshop cutting schedule"
milestone: "Phase 2 — Real Quote Outputs"
labels: "phase-2-outputs,type-feature,codex-ready,ui,backend,production,pdf-export"
---

## Real-world job supported

A workshop needs a clear cutting schedule that can be printed or shared without using the estimator screen.

## User flow

1. The estimator opens a Ready quote.
2. The estimator selects Workshop cutting schedule.
3. The app warns if any cutting rows are invalid.
4. The estimator exports the schedule.
5. The workshop receives grouped carcass, panel, and custom panel rows with project and quote context.

## Scope included

- Export cutting schedule to PDF or print-ready format.
- Include project name, client/site, quote number, revision, and export date.
- Include carcass rows, panel rows, custom panel rows, unit numbers, length, width, quantity, and board/material where known.
- Include validation warnings if export is allowed with warnings.
- Make the export available from the quote cutting list tab or output review screen.

## Scope excluded

- Cut optimization/nesting.
- Labels.
- Machine-specific export formats.
- Supplier purchase orders.

## Acceptance criteria

- Export includes all rows visible in the quote cutting list.
- Invalid rows are not silently exported as normal.
- Rows are grouped in a way a workshop can scan.
- The export clearly identifies the project, quote, and revision.
- The export does not include customer-facing price totals.

## Real cabinetry test scenario

Use a kitchen quote with one base drawer, one base door, two wall units, visible side panels, and a kicker. Export the workshop schedule and confirm the workshop can see what to cut by unit and panel group.

## Definition of done

- Workshop export works from a real quote.
- Cutlist validation warnings are represented.
- Manual QA verifies a multi-page schedule remains readable.
- Tests cover the export data shape and invalid-row handling.

## Suggested technical notes

- Reuse quote cutting list generation and validation outputs.
- Consider both PDF and CSV/XLSX later; start with the most useful first output.
- Keep workshop outputs separate from customer quote outputs.

## Risks/regressions to watch

- Export rows not matching on-screen cutlist rows.
- Losing custom panel rows.
- Making the schedule too dense to read.
- Treating warnings as success without clear messaging.
