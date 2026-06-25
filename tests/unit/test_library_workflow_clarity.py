from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARIES_PAGE = REPO_ROOT / "apps/web/src/components/libraries-page.tsx"
LIBRARIES_CONSTANTS = REPO_ROOT / "apps/web/src/components/libraries/constants.ts"
LIBRARIES_API = REPO_ROOT / "apps/api/corequote_api/libraries.py"
APP_SOURCE = REPO_ROOT / "apps/web/src/App.tsx"


def test_library_workflow_copy_explains_import_and_price_consequences() -> None:
    source = LIBRARIES_PAGE.read_text()

    expected_copy = [
        "Preview shows exactly what will be added, changed, ignored, or needs fixing before anything is saved.",
        "Safe to apply: CoreQuote will save",
        "Rows marked Needs fixing must be corrected before Apply Import is available",
        "Import receipt",
        "What CoreQuote read",
        "What to do",
        "Saving a manual override replaces the current price for future quote totals and keeps the old price in history.",
        "Current prices are used for new or recalculated totals.",
        "Applying a price change creates a new current price and keeps the old price in history",
        "Add {row.components.map(priceComponentLabel).join(', ')} using Manual Override",
    ]

    missing = [copy for copy in expected_copy if copy not in source]
    assert missing == []


def test_library_workflow_copy_avoids_old_internal_labels() -> None:
    source = LIBRARIES_PAGE.read_text()
    api_source = LIBRARIES_API.read_text()

    old_copy = [
        "<TableHead>Identity</TableHead>",
        "<TableHead>Target</TableHead>",
        "<TableHead>UOM</TableHead>",
        "<TableHead>Retires</TableHead>",
        "Applying a price bulk edit retires",
        "Batch {importApplyResult.batch_id}",
        "Order UOM",
        "SQM price",
        "UOM is required when changing price row units",
    ]

    combined = f"{source}\n{api_source}"
    unexpected = [copy for copy in old_copy if copy in combined]
    assert unexpected == []


def test_setup_checks_and_imports_are_the_first_library_tab() -> None:
    page_source = LIBRARIES_PAGE.read_text()
    constants_source = LIBRARIES_CONSTANTS.read_text()
    app_source = APP_SOURCE.read_text()

    assert "useState<LibraryTab>('setup-imports')" in app_source
    assert "{ label: 'Setup & Imports', value: 'setup-imports' }" in constants_source
    assert constants_source.index("'setup-imports'") < constants_source.index("'pricing'")
    assert "activeTab === 'setup-imports'" in page_source
