---
title: "Phase 2: Generate branded customer quote PDF"
milestone: "Phase 2 — Real Quote Outputs"
labels: "phase-2-outputs,type-feature,codex-ready,ui,backend,pdf-export,pricing,data-model"
---

## Real-world job supported

An estimator needs to send a professional quote to a client that includes the right totals and business details without exposing internal costs or profit.

## User flow

1. The estimator opens a Ready quote.
2. The estimator reviews customer-facing details.
3. The estimator generates a PDF.
4. The PDF includes company branding, client details, quote number, revision, expiry, VAT, totals, and terms.
5. Internal costs and profit remain hidden from the customer PDF.

## Scope included

- Customer quote PDF generation.
- Company name, logo placeholder or configured logo, contact details, and currency.
- Client name, site address, quote number, revision, issue date, and expiry date.
- Quote summary sections for cabinetry, panels, hardware/extras, delivery, installation, VAT, and grand total where available.
- Terms/notes area.
- Download action from the quote workspace.

## Scope excluded

- Email sending.
- Public quote link.
- Client acceptance/signature.
- Payment/deposit collection.
- Full visual branding studio.

## Acceptance criteria

- A Ready quote can generate a PDF from the quote workspace.
- The PDF never shows internal cost, margin, or profit.
- The PDF clearly shows VAT and grand total.
- The PDF shows quote number and revision.
- Missing readiness requirements are surfaced before export.
- The output filename is understandable to a business user.

## Real cabinetry test scenario

Generate a customer PDF for "Smith Kitchen Quote v1" with base units, wall units, visible panels, delivery, and installation. Confirm the client sees the total price and terms but not the internal cost or profit.

## Definition of done

- PDF generation works for the real-job scenario.
- PDF layout is manually reviewed on desktop.
- Tests verify customer PDF data excludes internal cost/profit fields.
- Readiness checks are consulted before export.
- Documentation states what appears in the customer PDF.

## Suggested technical notes

- Prefer a dedicated quote output service that receives structured quote/pricing data.
- Keep customer output models separate from internal pricing models.
- Add company profile fields if required for branding and contact details.

## Risks/regressions to watch

- Leaking margin or cost data to clients.
- PDF totals diverging from on-screen quote totals.
- Poor page breaks for long quotes.
- Exporting a quote with missing prices as if complete.
