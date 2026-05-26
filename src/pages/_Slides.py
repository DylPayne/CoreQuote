import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import get_all_slides, create_slide, update_slide, delete_slide
from ui.library_engine import (
    LibraryCallbacks,
    LibraryConfig,
    LibraryValidationResult,
    render_library_page,
)
from ui.formatters import format_slide_label
from ui.library_pricing import (
    cents_to_amount,
    get_active_pricing_lookup,
    render_read_only_pricing_header,
)
from ui.library_tabs import render_inventory_pricing_tabs

COLUMNS = ["id", "brand", "model", "code", "length", "side_length", "side_clearance_total", "side_height_uplift"]


def _validate_slide_row(row: dict) -> LibraryValidationResult:
    brand = str(row.get("brand", "")).strip()
    model = str(row.get("model", "")).strip()
    length = int(row.get("length", 0) or 0)
    side_length = int(row.get("side_length", 0) or 0)
    clearance = int(row.get("side_clearance_total", 0) or 0)
    uplift = int(row.get("side_height_uplift", 0) or 0)

    if not brand or not model:
        return LibraryValidationResult(False, "Each row must have Brand and Model.")
    if min(length, side_length, clearance, uplift) < 0:
        return LibraryValidationResult(False, "Slide dimensions and uplift must be 0 or greater.")

    return LibraryValidationResult(True)


def _build_slide_payload(row: dict) -> dict:
    return {
        "brand": str(row.get("brand", "")).strip(),
        "model": str(row.get("model", "")).strip(),
        "code": str(row.get("code", "")).strip(),
        "length": int(row.get("length", 0) or 0),
        "side_length": int(row.get("side_length", 0) or 0),
        "side_clearance_total": int(row.get("side_clearance_total", 0) or 0),
        "side_height_uplift": int(row.get("side_height_uplift", 0) or 0),
    }


def _render_add_slide_fields() -> dict:
    brand = st.text_input("Brand", placeholder="e.g. Grass")
    model = st.text_input("Model", placeholder="e.g. Dynapro")
    code = st.text_input("Product Code")
    col1, col2, col3 = st.columns(3)
    with col1:
        length = st.number_input("Nominal Length (mm)", min_value=0, step=50, value=500)
    with col2:
        side_len = st.number_input("Actual Side Length (mm)", min_value=0, step=1, value=500)
    with col3:
        clearance = st.number_input("Side Clearance (per side, mm)", min_value=0, step=1, value=13)
    side_uplift = st.number_input("Side Height Uplift (mm)", min_value=0, step=1, value=0)
    st.caption(f"Preview: {format_slide_label({'brand': brand or '—', 'model': model or '—', 'length': length})}")
    return {
        "brand": brand,
        "model": model,
        "code": code,
        "length": int(length),
        "side_length": int(side_len),
        "side_clearance_total": int(clearance),
        "side_height_uplift": int(side_uplift),
    }


config = LibraryConfig(
    page_title=":material/view_list: Slides Library",
    section_title="Current Inventory",
    add_button_label=":material/add: Add New Slide",
    add_dialog_title=":material/add: Add New Slide",
    id_column="id",
    columns=COLUMNS,
    editor_key="slides_main_editor",
    session_df_key="original_slides_df",
    empty_state_message="Your library is empty. Click 'Add New Slide' to begin.",
    callbacks=LibraryCallbacks(
        list_rows=get_all_slides,
        create_row=create_slide,
        update_row=update_slide,
        delete_row=delete_slide,
    ),
    validate_row=_validate_slide_row,
    render_add_dialog_fields=_render_add_slide_fields,
    build_create_payload=_build_slide_payload,
    build_update_payload=_build_slide_payload,
    dialog_success_message="Added slide successfully!",
)


def _slide_key(s: dict) -> str:
    return f"slide::{s.get('brand','')}::{s.get('model','')}::{s.get('code','')}::{s.get('length','')}"


def _render_inventory_tab() -> None:
    render_library_page(config)


def _render_pricing_tab() -> None:
    render_read_only_pricing_header("Slide Pricing (Read-only)")
    active_price_list, lookup = get_active_pricing_lookup()
    if not active_price_list:
        st.info("No active price list found.")
        return

    slides = get_all_slides()
    rows = [
        {
            "slide": format_slide_label(s),
            "cost_price": cents_to_amount((lookup.get(("slide", _slide_key(s))) or {}).get("unit_price_cents", 0)),
            "uom": "pairs",
        }
        for s in slides
    ]
    if not rows:
        st.info("No slides found.")
        return

    import pandas as pd

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "slide": st.column_config.TextColumn("Slide"),
            "cost_price": st.column_config.NumberColumn("Cost Price (R)", format="%.2f"),
            "uom": st.column_config.TextColumn("UOM"),
        },
    )


render_inventory_pricing_tabs(render_inventory=_render_inventory_tab, render_pricing=_render_pricing_tab)