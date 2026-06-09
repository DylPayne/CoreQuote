---
title: "Phase 2: Add real-job output package test"
milestone: "Phase 2 — Real Quote Outputs"
labels: "phase-2-outputs,type-test,codex-ready,needs-real-job-test,ui,backend,pdf-export,production,pricing"
---

## Real-world job supported

Before Phase 2 is considered complete, the team needs proof that one realistic cabinetry job can produce a client quote and workshop package that are both usable.

## User flow

1. A tester opens the Phase 1 real-job quote.
2. The tester confirms readiness is complete.
3. The tester generates the customer quote PDF.
4. The tester generates the workshop schedule and supporting summaries.
5. The tester reviews the outputs as both client and workshop user.

## Scope included

- Define expected Phase 2 outputs for the shared real-job scenario.
- Verify customer PDF hides internal costs and shows correct totals.
- Verify workshop schedule includes cut rows and warnings where relevant.
- Verify material summary and hardware pick list are present.
- Record any output quality issues as follow-up issues.

## Scope excluded

- Automated visual regression testing unless added by the implementation work.
- Public quote links.
- Email delivery.
- Payment or acceptance workflow.

## Acceptance criteria

- The scenario produces a customer PDF.
- The scenario produces a workshop package or schedule.
- Totals in the PDF match the on-screen quote total.
- Internal costs/profit are not visible in the client PDF.
- Material and hardware summaries are available for the same quote.

## Real cabinetry test scenario

Use "Smith Kitchen Phase 2": the same job from Phase 1, with completed boards, prices, handles, visible panels, delivery, installation, VAT, terms, and expiry date.

## Definition of done

- The test scenario is documented and has been run once manually.
- Output artifacts are reviewed for readability and correctness.
- Any gaps found during review have follow-up issues.
- Phase 2 cannot be closed until this issue passes.

## Suggested technical notes

- Store sample output files only if the repo wants fixtures; otherwise attach them to the GitHub issue.
- Consider a later automated smoke test that creates a quote and verifies export endpoints return files.
- Use the same scenario data across PDF and workshop output checks.

## Risks/regressions to watch

- Passing backend export tests without checking the actual PDF layout.
- Letting totals drift between screen and PDF.
- Testing a quote that is too simple to reveal output issues.
- Forgetting workshop usability while focusing on client presentation.
