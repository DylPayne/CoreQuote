---
title: "Phase 1: Add quote statuses and revisions"
milestone: "Phase 1 — Trustworthy Quote Flow"
labels: "phase-1-trust,type-feature,codex-ready,ui,backend,data-model"
---

## Real-world job supported

A cabinetmaker needs to know whether a quote is still being prepared, ready to send, already sent, accepted, rejected, or revised after a client change.

## User flow

1. The estimator opens a project and selects a quote.
2. The quote shows a clear status near the quote name.
3. The estimator can change the status when the job moves forward.
4. When a sent quote needs changes, the estimator creates a new revision instead of overwriting the accepted/sent record.
5. The quote list shows the latest revision and the current status.

## Scope included

- Add quote statuses: Draft, Ready, Sent, Accepted, Rejected, Revised, Expired.
- Add quote number and revision display.
- Add status controls in the quote workspace.
- Show status and revision on project quote cards and pricing comparison.
- Preserve a clear path to duplicate an existing quote into a new revision.

## Scope excluded

- Client portal.
- Email delivery.
- Payment/deposit tracking.
- Automated expiry reminders.
- Full audit trail beyond the minimum revision/status fields.

## Acceptance criteria

- A user can see each quote status without opening a modal.
- A user can change status from the quote workspace.
- A user can create a revised quote from an existing quote.
- The revised quote keeps a visible relationship to the previous revision.
- Accepted or sent quote information is not silently overwritten by revision work.
- Empty or new quotes default to Draft.
- UI wording avoids technical terms such as state machine, enum, or database.

## Real cabinetry test scenario

Create "Smith Kitchen". Add "Kitchen Quote v1" with three base units and two wall units. Mark it Ready, then Sent. Duplicate it as a revision after the client changes the door material. Confirm the quote list clearly shows v1 Sent and v2 Draft/Revised.

## Definition of done

- Status and revision are visible in the project quote list, quote workspace header, and pricing comparison.
- Revision creation is tested with at least one existing quote.
- The UI makes it clear which quote is safe to edit.
- Relevant API and frontend tests cover status changes and revision creation.
- Documentation notes how statuses should be used by a cabinetmaker.

## Suggested technical notes

- Store status and revision fields on quotes.
- Consider a stable quote number separate from the database id.
- Avoid hard-deleting revision links when old quotes are removed.
- Keep status transitions permissive for the first version unless stricter workflow rules are necessary.

## Risks/regressions to watch

- Accidentally changing old sent quotes when creating a revision.
- Confusing quote duplication with revision creation.
- Breaking existing quote copy behavior.
- Showing too much internal metadata in the UI.
