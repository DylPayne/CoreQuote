import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "packages", "corequote-core"))

from corequote_core.database import get_all_handles, create_handle, update_handle, delete_handle
from ui.library_engine import (
    LibraryCallbacks,
    LibraryConfig,
    LibraryValidationResult,
    render_library_page,
)
from ui.formatters import format_handle_label
from ui.library_pricing import (
    cents_to_amount,
    get_active_pricing_lookup,
    render_read_only_pricing_header,
)
from ui.library_tabs import render_inventory_pricing_tabs

COLUMNS = ["id", "name", "supplier", "code"]


def _validate_handle_row(row: dict) -> LibraryValidationResult:
    name = str(row.get("name", "")).strip()
    if not name:
        return LibraryValidationResult(False, "Each row must have a Handle Name.")
    return LibraryValidationResult(True)


def _build_handle_payload(row: dict) -> dict:
    return {
        "name": str(row.get("name", "")).strip(),
        "supplier": str(row.get("supplier", "")).strip(),
        "code": str(row.get("code", "")).strip(),
    }


def _render_add_handle_fields() -> dict:
    name = st.text_input("Handle Name", placeholder="e.g. Slim Bar 160")
    supplier = st.text_input("Supplier", placeholder="e.g. Häfele")
    code = st.text_input("Product Code")
    st.caption(f"Preview: {format_handle_label({'name': name, 'supplier': supplier, 'code': code})}")
    return {
        "name": name,
        "supplier": supplier,
        "code": code,
    }


config = LibraryConfig(
    page_title=":material/touch_app: Handle Library",
    section_title="Current Inventory",
    add_button_label=":material/add: Add New Handle",
    add_dialog_title=":material/add: Add New Handle",
    id_column="id",
    columns=COLUMNS,
    editor_key="handles_main_editor",
    session_df_key="original_handles_df",
    empty_state_message="Your library is empty. Click 'Add New Handle' to begin.",
    callbacks=LibraryCallbacks(
        list_rows=get_all_handles,
        create_row=create_handle,
        update_row=update_handle,
        delete_row=delete_handle,
    ),
    validate_row=_validate_handle_row,
    render_add_dialog_fields=_render_add_handle_fields,
    build_create_payload=_build_handle_payload,
    build_update_payload=_build_handle_payload,
    dialog_success_message="Added handle successfully!",
)


def _handle_key(h: dict) -> str:
    return f"handle::{h.get('name','')}::{h.get('supplier','')}::{h.get('code','')}"


def _render_inventory_tab() -> None:
    render_library_page(config)


def _render_pricing_tab() -> None:
    render_read_only_pricing_header("Handle Pricing (Read-only)")
    active_price_list, lookup = get_active_pricing_lookup()
    if not active_price_list:
        st.info("No active price list found.")
        return

    handles = get_all_handles()
    rows = [
        {
            "handle": format_handle_label(h),
            "cost_price": cents_to_amount((lookup.get(("handle", _handle_key(h))) or {}).get("unit_price_cents", 0)),
            "uom": "pcs",
        }
        for h in handles
    ]
    if not rows:
        st.info("No handles found.")
        return

    import pandas as pd

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "handle": st.column_config.TextColumn("Handle"),
            "cost_price": st.column_config.NumberColumn("Cost Price (R)", format="%.2f"),
            "uom": st.column_config.TextColumn("UOM"),
        },
    )


render_inventory_pricing_tabs(render_inventory=_render_inventory_tab, render_pricing=_render_pricing_tab)
