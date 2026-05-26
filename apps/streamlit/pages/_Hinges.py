import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "packages", "corequote-core"))

from corequote_core.database import get_all_hinges, create_hinge, update_hinge, delete_hinge
from ui.library_engine import (
    LibraryCallbacks,
    LibraryConfig,
    LibraryValidationResult,
    render_library_page,
)
from ui.formatters import format_hinge_label
from ui.library_pricing import (
    cents_to_amount,
    get_active_pricing_lookup,
    render_read_only_pricing_header,
)
from ui.library_tabs import render_inventory_pricing_tabs

COLUMNS = ["id", "brand", "model", "code", "opening_angle_deg"]


def _validate_hinge_row(row: dict) -> LibraryValidationResult:
    brand = str(row.get("brand", "")).strip()
    model = str(row.get("model", "")).strip()
    opening = int(row.get("opening_angle_deg", 0) or 0)

    if not brand or not model:
        return LibraryValidationResult(False, "Each row must have Brand and Model.")
    if opening < 0:
        return LibraryValidationResult(False, "Opening Angle must be 0 or greater.")

    return LibraryValidationResult(True)


def _build_hinge_payload(row: dict) -> dict:
    return {
        "brand": str(row.get("brand", "")).strip(),
        "model": str(row.get("model", "")).strip(),
        "code": str(row.get("code", "")).strip(),
        "opening_angle_deg": int(row.get("opening_angle_deg", 0) or 0),
    }


def _render_add_hinge_fields() -> dict:
    brand = st.text_input("Brand", placeholder="e.g. Blum")
    model = st.text_input("Model", placeholder="e.g. Clip Top")
    code = st.text_input("Product Code")
    opening_angle_deg = st.number_input("Opening Angle (°)", min_value=0, step=1, value=110)
    st.caption(f"Preview: {format_hinge_label({'brand': brand or '—', 'model': model or '—', 'opening_angle_deg': opening_angle_deg})}")
    return {
        "brand": brand,
        "model": model,
        "code": code,
        "opening_angle_deg": int(opening_angle_deg),
    }


config = LibraryConfig(
    page_title=":material/hardware: Hinges Library",
    section_title="Current Inventory",
    add_button_label=":material/add: Add New Hinge",
    add_dialog_title=":material/add: Add New Hinge",
    id_column="id",
    columns=COLUMNS,
    editor_key="hinges_main_editor",
    session_df_key="original_hinges_df",
    empty_state_message="Your library is empty. Click 'Add New Hinge' to begin.",
    callbacks=LibraryCallbacks(
        list_rows=get_all_hinges,
        create_row=create_hinge,
        update_row=update_hinge,
        delete_row=delete_hinge,
    ),
    validate_row=_validate_hinge_row,
    render_add_dialog_fields=_render_add_hinge_fields,
    build_create_payload=_build_hinge_payload,
    build_update_payload=_build_hinge_payload,
    dialog_submit_label="Add to Library",
    dialog_success_message="Added hinge successfully!",
    save_success_message="Library updated!",
)


def _hinge_key(h: dict) -> str:
    return f"hinge::{h.get('brand','')}::{h.get('model','')}::{h.get('code','')}::{h.get('opening_angle_deg','')}"


def _render_inventory_tab() -> None:
    render_library_page(config)


def _render_pricing_tab() -> None:
    render_read_only_pricing_header("Hinge Pricing (Read-only)")
    active_price_list, lookup = get_active_pricing_lookup()
    if not active_price_list:
        st.info("No active price list found.")
        return

    hinges = get_all_hinges()
    rows = [
        {
            "hinge": format_hinge_label(h),
            "cost_price": cents_to_amount((lookup.get(("hinge", _hinge_key(h))) or {}).get("unit_price_cents", 0)),
            "uom": "pcs",
        }
        for h in hinges
    ]
    if not rows:
        st.info("No hinges found.")
        return

    import pandas as pd

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "hinge": st.column_config.TextColumn("Hinge"),
            "cost_price": st.column_config.NumberColumn("Cost Price (R)", format="%.2f"),
            "uom": st.column_config.TextColumn("UOM"),
        },
    )


render_inventory_pricing_tabs(render_inventory=_render_inventory_tab, render_pricing=_render_pricing_tab)
