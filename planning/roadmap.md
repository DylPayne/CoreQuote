# CoreQuote Product Roadmap

This roadmap turns CoreQuote from an internal quoting tool into a commercially usable cabinetry and joinery product. The sequencing is intentionally practical: first make the current quote flow trustworthy, then produce real outputs, then improve speed and operational workflows.

## Phase 1: Trustworthy Quote Flow

Goal: A cabinetmaker can build a quote and see whether it is ready to price, send, or hand to the workshop.

Primary outcomes:

- Quote statuses and revisions make the job state clear.
- Quote readiness checks catch missing boards, missing prices, invalid dimensions, missing client details, and incomplete setup.
- Missing price guidance tells the estimator exactly what needs to be fixed.
- Cutlist warnings catch zero-size or unusable rows before anyone trusts the schedule.
- Empty states and visible wording speak to cabinetmakers, not developers.

## Phase 2: Real Quote Outputs

Goal: A cabinetmaker can generate professional outputs for the client and the workshop from the same trusted quote.

Primary outcomes:

- Branded customer quote PDF with client details, totals, VAT, terms, expiry, and revision information.
- Workshop cutting schedule export grouped for practical production use.
- Material and board summary for purchasing and cost confidence.
- Hardware and extras pick list for ordering and packing.
- Quote package review screen that separates client-facing information from internal costs and margins.

## Phase 3: Job Entry Speed

Goal: A cabinetmaker can quote a full kitchen or joinery project quickly without entering every unit one slow modal at a time.

Primary outcomes:

- Duplicate units and quotes.
- Bulk add unit rows.
- Reorder units.
- Group units by room, run, or area.
- Apply defaults across multiple units.
- Faster presets for common kitchens, wardrobes, vanities, and built-ins.

## Phase 4: Library Setup And Pricing Maintenance

Goal: A business can set up and maintain real boards, hardware, supplier costs, price lists, discounts, and markups without manual re-entry pain.

Primary outcomes:

- First-run setup checklist.
- CSV/XLSX imports for boards, supplier prices, handles, extras, and hardware.
- Bulk edit and filtering for catalog tables.
- Price list versioning and effective dates.
- Supplier price refresh workflows.
- Clear audit history for pricing changes.

## Phase 5: Production Handoff

Goal: The workshop receives schedules that are not just calculated, but practical for manufacturing.

Primary outcomes:

- Cutlists grouped by board, thickness, material, and area.
- Edging summary.
- Grain direction and rotation guidance.
- Part labels.
- Board requirement totals and waste allowance.
- Export formats that work with downstream tools.
- Future cut optimization or optimizer integration.

## Phase 6: Client And Business Workflow

Goal: CoreQuote supports the full commercial quoting workflow around the calculation.

Primary outcomes:

- Client/contact management.
- Quote send flow and public quote link.
- Client accept/reject/request-change workflow.
- Signature or approval capture.
- Deposit/payment tracking.
- User invitations, roles, and business settings.
- Data export, backup, billing, and support workflows.

## Planning Rules

- Phase 1 and Phase 2 issues should be implementation-ready.
- Phases 3 through 6 stay as epics until the commercial core is stable.
- Do not implement application features from this planning package.
- Use real cabinetry test scenarios before marking product work done.
- Keep customer-facing wording simple and non-technical.
