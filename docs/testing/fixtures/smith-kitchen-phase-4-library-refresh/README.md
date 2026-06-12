# Smith Kitchen Phase 4 Library Refresh Fixture

These CSV files are sanitized sample data for
[Smith Kitchen Phase 4 Library Refresh](../../smith-kitchen-phase-4-library-refresh.md).
They are safe to commit: contacts use `example.invalid`, suppliers are generic,
and prices are non-proprietary scenario values.

Import order for a blank local company:

1. `suppliers.csv`
2. `boards.csv`
3. `slides.csv`
4. `hinges.csv`
5. `handles.csv`
6. `extra_categories.csv`
7. `extras.csv`
8. `supplier_item_costs.csv`
9. `price_list_items.csv` into the active Smith Kitchen price list

The `price_list_items.csv` file is the active price source used by the automated
fixture regression. The supplier-cost file mirrors the same catalog rows for
supplier refresh testing and audit-history workflows.
