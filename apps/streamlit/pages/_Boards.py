import streamlit as st

from corequote_core.database import (
    get_all_board_types,
    create_board_type,
    update_board_type,
    delete_board_type,
)
from ui.library_engine import (
    LibraryCallbacks,
    LibraryConfig,
    LibraryValidationResult,
    render_library_page,
)
from ui.formatters import format_board_label
from ui.library_pricing import (
    cents_to_amount,
    get_active_pricing_lookup,
    render_read_only_pricing_header,
)
from ui.library_tabs import render_inventory_pricing_tabs

COLUMNS = [
    "id",
    "brand",
    "material",
    "thickness",
    "length_mm",
    "width_mm",
    "costing_mode",
]


def _validate_board_row(row: dict) -> LibraryValidationResult:
    brand = str(row.get("brand", "")).strip()
    material = str(row.get("material", "")).strip()
    thickness = int(row.get("thickness", 0) or 0)
    length_mm = int(row.get("length_mm", 0) or 0)
    width_mm = int(row.get("width_mm", 0) or 0)
    costing_mode = str(row.get("costing_mode", "sheet")).strip().lower()

    if not brand or not material:
        return LibraryValidationResult(False, "Brand and Material are required for all rows.")
    if thickness < 1 or length_mm < 1 or width_mm < 1:
        return LibraryValidationResult(False, "Thickness, Length, and Width must all be at least 1.")
    if costing_mode not in {"sheet", "sqm"}:
        return LibraryValidationResult(False, "Costing Mode must be either 'sheet' or 'sqm'.")
    return LibraryValidationResult(True)


def _build_board_payload(row: dict) -> dict:
    return {
        "brand": str(row.get("brand", "")).strip(),
        "material": str(row.get("material", "")).strip(),
        "thickness": int(row.get("thickness", 0) or 0),
        "length_mm": int(row.get("length_mm", 0) or 0),
        "width_mm": int(row.get("width_mm", 0) or 0),
        "costing_mode": str(row.get("costing_mode", "sheet")).strip().lower() or "sheet",
    }


def _render_add_board_fields() -> dict:
    brand = st.text_input("Brand *")
    material = st.text_input("Material *")
    col1, col2, col3 = st.columns(3)
    with col1:
        thickness = st.number_input("Thickness (mm)", min_value=1, value=16)
    with col2:
        length_mm = st.number_input("Length (mm)", min_value=1, value=2750)
    with col3:
        width_mm = st.number_input("Width (mm)", min_value=1, value=1830)

    col4 = st.columns(1)[0]
    with col4:
        costing_mode = st.selectbox("Costing Mode", ["sheet", "sqm"], index=0)

    st.caption(
        f"Preview: {format_board_label({'brand': brand or '—', 'material': material or '—', 'thickness': thickness, 'length_mm': length_mm, 'width_mm': width_mm})}"
    )
    return {
        "brand": brand,
        "material": material,
        "thickness": int(thickness),
        "length_mm": int(length_mm),
        "width_mm": int(width_mm),
        "costing_mode": str(costing_mode),
    }


config = LibraryConfig(
    page_title=":material/grid_view: Board Library",
    section_title="Current Inventory",
    add_button_label=":material/add: Add New Board",
    add_dialog_title=":material/add: Add New Board",
    id_column="id",
    columns=COLUMNS,
    editor_key="boards_main_editor",
    session_df_key="original_boards_df",
    empty_state_message="Your library is empty. Click 'Add New Board' to begin.",
    callbacks=LibraryCallbacks(
        list_rows=get_all_board_types,
        create_row=create_board_type,
        update_row=update_board_type,
        delete_row=delete_board_type,
    ),
    validate_row=_validate_board_row,
    render_add_dialog_fields=_render_add_board_fields,
    build_create_payload=_build_board_payload,
    build_update_payload=_build_board_payload,
    dialog_success_message="Added board successfully!",
    editor_kwargs={
        "column_config": {
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "brand": st.column_config.TextColumn("Brand", required=True),
            "material": st.column_config.TextColumn("Material", required=True),
            "thickness": st.column_config.NumberColumn("Thickness (mm)", min_value=1, required=True),
            "length_mm": st.column_config.NumberColumn("Length (mm)", min_value=1, required=True),
            "width_mm": st.column_config.NumberColumn("Width (mm)", min_value=1, required=True),
            "costing_mode": st.column_config.SelectboxColumn("Costing Mode", options=["sheet", "sqm"], required=True),
        }
    },
)


def _render_inventory_tab() -> None:
    render_library_page(config)


def _render_pricing_tab() -> None:
    render_read_only_pricing_header("Board Pricing (Read-only)")
    active_price_list, lookup = get_active_pricing_lookup()
    if not active_price_list:
        st.info("No active price list found.")
        return

    boards = get_all_board_types()
    rows: list[dict] = []
    for b in boards:
        board_id = int(b["id"])
        base = f"board::{board_id}"
        mode = str(b.get("costing_mode", "sheet") or "sheet").strip().lower()
        if mode == "sqm":
            sqm = lookup.get(("board", f"{base}::sqm"))
            rows.append(
                {
                    "board": format_board_label(b),
                    "costing_mode": mode,
                    "sqm_price": cents_to_amount((sqm or {}).get("unit_price_cents", 0)),
                    "sheet_price": None,
                    "edging_price": None,
                    "labour_price": None,
                }
            )
        else:
            sheet = lookup.get(("board", f"{base}::sheet"))
            edging = lookup.get(("board", f"{base}::edging_m"))
            labour = lookup.get(("board", f"{base}::labour_board"))
            rows.append(
                {
                    "board": format_board_label(b),
                    "costing_mode": mode,
                    "sqm_price": None,
                    "sheet_price": cents_to_amount((sheet or {}).get("unit_price_cents", 0)),
                    "edging_price": cents_to_amount((edging or {}).get("unit_price_cents", 0)),
                    "labour_price": cents_to_amount((labour or {}).get("unit_price_cents", 0)),
                }
            )

    if not rows:
        st.info("No boards found.")
        return

    import pandas as pd

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "board": st.column_config.TextColumn("Board"),
            "costing_mode": st.column_config.TextColumn("Mode"),
            "sheet_price": st.column_config.NumberColumn("Sheet Price (R/sheet)", format="%.2f"),
            "edging_price": st.column_config.NumberColumn("Edging (R/m)", format="%.2f"),
            "labour_price": st.column_config.NumberColumn("Labour (R/board)", format="%.2f"),
            "sqm_price": st.column_config.NumberColumn("SQM (R/m²)", format="%.2f"),
        },
    )


render_inventory_pricing_tabs(render_inventory=_render_inventory_tab, render_pricing=_render_pricing_tab)
