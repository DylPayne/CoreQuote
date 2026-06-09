---
title: "Phase 1: Add real-job readiness test scenario"
milestone: "Phase 1 — Trustworthy Quote Flow"
labels: "phase-1-trust,type-test,codex-ready,needs-real-job-test,ui,backend,pricing,production"
---

## Real-world job supported

Before Phase 1 is considered usable, the team needs one repeatable cabinetry job that proves the quote flow catches incomplete setup and reaches a trusted ready state.

## User flow

1. A tester follows a documented kitchen quote scenario.
2. The tester intentionally leaves setup gaps.
3. The app shows readiness warnings.
4. The tester fixes the gaps.
5. The quote reaches Ready with sensible totals and schedules.

## Scope included

- Define a repeatable small kitchen scenario.
- Include units, boards, one slide, one hinge, handles, visible panels, delivery, installation, and VAT.
- Document expected readiness warnings for incomplete setup.
- Document expected ready-state behavior after fixes.
- Use this scenario as a product acceptance test for Phase 1 issues.

## Scope excluded

- Automated browser test implementation unless needed by the feature work.
- Exact commercial price benchmarking.
- PDF or export verification, which belongs to Phase 2.

## Acceptance criteria

- The scenario can be followed by another contributor without extra context.
- It covers at least one base drawer, one base door, one wall unit, visible panel rows, and quote pricing.
- It includes an intentionally missing board or price step.
- It defines what "ready" means for the scenario.
- Phase 1 issues can reference this scenario as shared acceptance evidence.

## Real cabinetry test scenario

Use "Smith Kitchen Phase 1": two base door units, one base drawer unit, two wall units, one tall unit, one base side panel pair, one wall side filler, one kicker, delivery, and half-day installation.

## Definition of done

- Scenario steps are documented in the repo or attached to this issue.
- Expected warnings and final ready state are written down.
- The scenario has been manually run once against the app before closing Phase 1.
- Follow-up issues are created for any discovered product gaps.

## Suggested technical notes

- This may become a Playwright smoke test later.
- Keep values realistic but not dependent on proprietary supplier pricing.
- Reference readiness check ids once the readiness service exists.

## Risks/regressions to watch

- A scenario that is too small to reveal real workflow issues.
- A scenario that depends on fragile seed data.
- Treating the test as complete without running it in the UI.
- Letting the scenario drift away from actual cabinetry workflows.
