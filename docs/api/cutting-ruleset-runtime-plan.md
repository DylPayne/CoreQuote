# Cutting Ruleset Runtime Plan

This document defines how CoreQuote should evolve from hardcoded strategy-based cutlist generation to database-driven cutting ruleset evaluation.

It exists to guide a future implementation task and keep architecture decisions consistent.

## Current State (as of June 17, 2026)

- Rulesets and rows are stored and editable through the API:
  - `GET/POST/PATCH /api/v1/cutting/rulesets`
  - `GET /api/v1/cutting/unit-configs`
- Frontend editor labels built-in templates and active company revisions as read-only, while company draft revisions are editable.
- Runtime cutlist generation can use DB rulesets when `CUTLIST_USE_DB_RULESETS` is enabled.
- The legacy strategy engine remains the fallback path when the feature flag is disabled, no ruleset is found, or ruleset evaluation fails.

## Target Outcome

When generating cutlists, the system should:

1. Resolve the applicable unit config and active ruleset (company-owned override first, then global default).
2. Evaluate each ruleset row formula against a unit context.
3. Emit normalized carcass/panel/hardware/extra rows with dimensions and quantity.
4. Preserve current permission, tenancy, and visibility rules.

## Runtime Resolution Rules

For each unit in a quote:

1. Identify `unit_type_key`.
2. Resolve `unit_config` in priority order:
   - Company config (`company_id = current company`, `status = active`)
   - Global default config (`company_id IS NULL`, `is_default = true`, `status = active`)
3. Resolve ruleset in priority order:
   - Company ruleset for `unit_type_key` (`status = active`). Each company can have only one active ruleset per unit type.
   - Global default ruleset for `unit_type_key` (`company_id IS NULL`, `is_default = true`, `status = active`)
4. If no ruleset is found, fall back to legacy strategy engine (temporary compatibility behavior).

Lifecycle decision:

- Built-in/global rulesets are templates. They are read-only for company users and should be duplicated before customization.
- Company draft ruleset revisions are editable.
- Draft company rulesets are not used by quote cutlists.
- Active company ruleset revisions are read-only; changes require creating a new draft revision.
- Activating a company ruleset for a unit type archives any other active company ruleset for that unit type.

## Evaluation Context

Each formula should evaluate with a deterministic context containing:

- Base geometric vars: `h`, `w`, `d`, `t`
- Unit variant vars from `unit_config.variant_config`:
  - e.g. `num_doors`, `num_drawers`, `num_shelves`, `panel_gap_mm`, `shelf_setback`
- Optionally derived vars (future): e.g. `inner_w`, `inner_h`

Recommended validation:

- Formula expression length and character whitelist
- Parentheses balance
- Unknown identifier detection against allowed variable set

## Formula Semantics

Each row has:

- `condition_formula`:
  - If blank, row is included.
  - If present and false, row is skipped.
- `length_formula` and `width_formula`:
  - Numeric expressions in millimeters.
- `qty_formula`:
  - Numeric expression, coerced to integer >= 0.

Row output should include:

- `section`
- `description`
- evaluated `length`, `width`, `qty`
- edge flags: `edge_long_1`, `edge_long_2`, `edge_short_1`, `edge_short_2`

If `qty = 0`, the row should be ignored.

## Safety Model for Evaluation

Do not use Python `eval`.

Use a safe expression evaluator with:

- restricted grammar
- allowed operators only
- explicit numeric/bool semantics
- no attribute access, imports, calls, globals, or side effects

Recommended implementation options:

1. Small custom parser/evaluator for arithmetic + logical operators
2. A battle-tested safe-expression library with strict sandboxing and tests

## Proposed Integration Points

Add a runtime service in API layer (or core package) roughly like:

- `CuttingRulesetResolver`:
  - resolves unit config + ruleset for `(company_id, unit_type_key)`
- `CuttingFormulaEvaluator`:
  - validates and evaluates expressions against context
- `RulesetCutlistBuilder`:
  - converts rows into output rows used by preview and quote generation

Then update `preview_cutlist(...)` to:

1. Try ruleset runtime path first.
2. Fall back to existing `build_cutlist(...)` if missing/invalid config (initial rollout).

## Rollout Plan

1. Build evaluator + resolver behind feature flag (`CUTLIST_USE_DB_RULESETS`).
2. Add parity tests against existing strategy output for representative unit types.
3. Enable for preview endpoint first.
4. Enable for persisted quote cutlist generation.
5. Remove fallback once parity and production confidence are reached.

## Test Strategy (for future task)

- Unit tests:
  - expression validation/evaluation edge cases
  - context building
  - row inclusion/exclusion via condition formula
- API tests:
  - company-vs-global ruleset resolution
  - active/archived behavior
  - fallback behavior while feature flag is off/on
- Regression tests:
  - known unit fixtures compared against legacy strategy outputs

## Non-Goals for Initial Runtime

- Arbitrary user-defined functions
- Cross-row dependencies
- Runtime writes back into rulesets
- Mixed-unit batched optimization logic

## Notes for Future UI/API Enhancements

- Add “effective ruleset” debug endpoint for one unit input payload.
- Add compile/validate endpoint for formulas without saving.
- Add row-level validation details in API responses (line/field errors).
