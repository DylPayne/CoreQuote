---
title: "Phase 2: Add quote package review screen"
milestone: "Phase 2 — Real Quote Outputs"
labels: "phase-2-outputs,type-feature,codex-ready,ui,backend,pdf-export,production,pricing"
---

## Real-world job supported

Before sending or printing anything, the estimator needs one review screen that shows what will go to the client and what will go to the workshop.

## User flow

1. The estimator opens a quote and selects Review outputs.
2. The screen shows readiness status.
3. The screen shows customer quote summary, internal pricing confidence, workshop schedule status, material summary, and hardware pick list status.
4. The estimator chooses which output to generate.

## Scope included

- Output review screen or tab for a quote.
- Clear separation between Client quote and Workshop package.
- Show readiness warnings before export.
- Show available output actions for customer PDF, workshop schedule, material summary, and hardware list.
- Explain which outputs hide internal costs.

## Scope excluded

- Email sending.
- Client portal.
- Payment collection.
- Production status tracking.

## Acceptance criteria

- A user can find all quote output actions in one place.
- Client-facing and internal/workshop outputs are visibly separated.
- Readiness warnings appear before export actions.
- Output actions are disabled or warn clearly when required data is missing.
- The screen uses plain language such as "Client quote" and "Workshop schedule".

## Real cabinetry test scenario

Use a complete kitchen quote and open the review screen. Confirm the estimator can see the client quote action, workshop schedule action, material summary, and hardware pick list without switching across many tabs.

## Definition of done

- Review screen is reachable from the quote workspace.
- It consumes readiness, pricing, cutlist, material, and hardware status.
- Manual QA confirms it guides a user to the right output.
- Tests cover the disabled/warning state for incomplete quotes.

## Suggested technical notes

- Start as a quote-level tab or panel.
- Keep export generation behind separate endpoints/services.
- Avoid duplicating detailed tables already present elsewhere; summarize and link to details.

## Risks/regressions to watch

- Creating another busy dashboard instead of a practical review step.
- Letting users export incomplete quotes without noticing warnings.
- Exposing internal profit information in the client section.
- Spreading output actions across too many screens.
