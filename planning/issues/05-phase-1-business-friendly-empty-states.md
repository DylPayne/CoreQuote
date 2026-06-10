---
title: "Phase 1: Replace technical wording and improve empty states"
milestone: "Phase 1 — Trustworthy Quote Flow"
labels: "phase-1-trust,type-feature,codex-ready,ui"
---

## Real-world job supported

A new cabinetmaking business signs in and needs to understand what to do next without seeing developer language, raw ids, or confusing setup screens.

## User flow

1. A new user logs in.
2. Empty project, quote, library, and settings screens explain the next practical step.
3. Error messages use plain business language.
4. Technical setup screens are clearly marked as advanced where they remain visible.

## Scope included

- Replace visible auth/API wording with user-facing language.
- Replace raw technical error messages with friendly messages and optional detail.
- Improve empty states for projects, quotes, units, boards, extras, and prices.
- Remove or hide raw ids from normal settings views.
- Make advanced/admin surfaces feel intentionally advanced.

## Scope excluded

- New onboarding wizard.
- Full help center.
- Billing or subscription settings.
- Redesigning the visual style system.

## Acceptance criteria

- Login/session messages do not mention bearer tokens, API paths, localhost URLs, or raw request wording.
- Settings focuses on company profile, user, currency, and practical controls.
- Empty library screens tell the user why the library matters and what to add first.
- Empty quote screens guide the user toward adding units and required defaults.
- Advanced rule/test screens are labelled in a way a non-technical owner can understand.

## Real cabinetry test scenario

Register or sign in as a new business with no projects and no boards. Confirm the first visible messages help the user create a project and set up board materials without exposing technical details.

## Definition of done

- A pass through all main screens finds no user-facing API/session/localhost wording.
- Empty states exist for the core setup gaps.
- UX copy is reviewed from the perspective of a small cabinetry shop owner.
- No application behavior changes beyond wording and empty-state guidance.

## Suggested technical notes

- Add a small error-message mapping layer so raw API failures are not shown directly.
- Keep detailed technical messages available in logs or development tools, not primary UI.
- Reuse shared alert and empty-state primitives.

## Risks/regressions to watch

- Hiding useful troubleshooting details from local development entirely.
- Adding marketing copy that gets in the way of operational workflows.
- Making advanced setup impossible to find for power users.
- Inconsistent wording across feature areas.
