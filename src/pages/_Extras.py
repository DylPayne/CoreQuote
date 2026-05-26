import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import (
    get_all_extras,
    create_extra,
    update_extra,
    delete_extra,
    get_all_extra_categories,
)
from ui.library_engine import (
    LibraryCallbacks,
    LibraryConfig,
    LibraryValidationResult,
    render_library_page,
)
from ui.formatters import format_extra_label
from ui.library_pricing import (
    cents_to_amount,
    get_active_pricing_lookup,
    render_read_only_pricing_header,
)
from ui.library_tabs import render_inventory_pricing_tabs

COLUMNS = ["id", "name", "category_id", "supplier", "code", "notes"]

_categories = get_all_extra_categories()
_category_ids = [c["id"] for c in _categories]
_category_lookup = {c["id"]: c for c in _categories}


def _category_label(category_id: int) -> str:
    row = _category_lookup.get(int(category_id)) if category_id is not None else None
    return str((row or {}).get("name", "—"))


def _validate_extra_row(row: dict) -> LibraryValidationResult:
    name = str(row.get("name", "")).strip()
    category_id = row.get("category_id")
    if not name:
        return LibraryValidationResult(False, "Each row must have an Extra Name.")
    if category_id in (None, ""):
        return LibraryValidationResult(False, "Each row must have a Category.")
    try:
        category_id = int(category_id)
    except Exception:
        return LibraryValidationResult(False, "Category is invalid.")
    if category_id not in _category_lookup:
        return LibraryValidationResult(False, "Selected category no longer exists.")
    return LibraryValidationResult(True)


def _build_extra_payload(row: dict) -> dict:
    return {
        "name": str(row.get("name", "")).strip(),
        "category_id": int(row.get("category_id")),
        "supplier": str(row.get("supplier", "")).strip(),
        "code": str(row.get("code", "")).strip(),
        "notes": str(row.get("notes", "")).strip(),
    }


def _render_add_extra_fields() -> dict:
    if not _category_ids:
        st.warning("No categories available. Add categories in Extras Categories first.")
        return {"name": "", "category_id": None, "supplier": "", "code": "", "notes": ""}

    name = st.text_input("Extra Name", placeholder="e.g. Stove")
    category_id = st.selectbox(
        "Category",
        _category_ids,
        index=0,
        format_func=_category_label,
    )
    supplier = st.text_input("Supplier", placeholder="e.g. Defy")
    code = st.text_input("Product Code")
    notes = st.text_area("Notes", placeholder="Optional one-off detail")
    st.caption(
        f"Preview: {format_extra_label({'name': name, 'category_name': _category_label(category_id), 'supplier': supplier, 'code': code})}"
    )
    return {
        "name": name,
        "category_id": int(category_id),
        "supplier": supplier,
        "code": code,
        "notes": notes,
    }


config = LibraryConfig(
    page_title=":material/inventory_2: Extras Library",
    section_title="Current Inventory",
    add_button_label=":material/add: Add New Extra",
    add_dialog_title=":material/add: Add New Extra",
    id_column="id",
    columns=COLUMNS,
    editor_key="extras_main_editor",
    session_df_key="original_extras_df",
    empty_state_message="Your extras library is empty. Click 'Add New Extra' to begin.",
    callbacks=LibraryCallbacks(
        list_rows=get_all_extras,
        create_row=create_extra,
        update_row=update_extra,
        delete_row=delete_extra,
    ),
    validate_row=_validate_extra_row,
    render_add_dialog_fields=_render_add_extra_fields,
    build_create_payload=_build_extra_payload,
    build_update_payload=_build_extra_payload,
    dialog_success_message="Added extra successfully!",
    editor_kwargs={
        "column_config": {
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "name": st.column_config.TextColumn("Extra Name", required=True),
            "category_id": st.column_config.SelectboxColumn(
                "Category",
                options=_category_ids,
                required=True,
                format_func=_category_label,
            ),
            "supplier": st.column_config.TextColumn("Supplier"),
            "code": st.column_config.TextColumn("Product Code"),
            "notes": st.column_config.TextColumn("Notes"),
        }
    },
)


def _render_inventory_tab() -> None:
    if not _category_ids:
        st.title(config.page_title)
        st.info("No extra categories found. Please add categories in **Extras Categories** first.")
        return
    render_library_page(config)


def _render_pricing_tab() -> None:
    render_read_only_pricing_header("Extra Pricing (Read-only)")
    active_price_list, lookup = get_active_pricing_lookup()
    if not active_price_list:
        st.info("No active price list found.")
        return

    extras = get_all_extras()
    rows = [
        {
            "extra": format_extra_label(e),
            "cost_price": cents_to_amount((lookup.get(("extra", f"extra::{int(e['id'])}")) or {}).get("unit_price_cents", 0)),
            "uom": "pcs",
        }
        for e in extras
    ]
    if not rows:
        st.info("No extras found.")
        return

    import pandas as pd

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "extra": st.column_config.TextColumn("Extra"),
            "cost_price": st.column_config.NumberColumn("Cost Price (R)", format="%.2f"),
            "uom": st.column_config.TextColumn("UOM"),
        },
    )


render_inventory_pricing_tabs(render_inventory=_render_inventory_tab, render_pricing=_render_pricing_tab)