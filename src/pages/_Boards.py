import streamlit as st

from logic.database import (
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

COLUMNS = ["id", "brand", "material", "thickness", "length_mm", "width_mm"]


def _validate_board_row(row: dict) -> LibraryValidationResult:
    brand = str(row.get("brand", "")).strip()
    material = str(row.get("material", "")).strip()
    thickness = int(row.get("thickness", 0) or 0)
    length_mm = int(row.get("length_mm", 0) or 0)
    width_mm = int(row.get("width_mm", 0) or 0)

    if not brand or not material:
        return LibraryValidationResult(False, "Brand and Material are required for all rows.")
    if thickness < 1 or length_mm < 1 or width_mm < 1:
        return LibraryValidationResult(False, "Thickness, Length, and Width must all be at least 1.")

    return LibraryValidationResult(True)


def _build_board_payload(row: dict) -> dict:
    return {
        "brand": str(row.get("brand", "")).strip(),
        "material": str(row.get("material", "")).strip(),
        "thickness": int(row.get("thickness", 0) or 0),
        "length_mm": int(row.get("length_mm", 0) or 0),
        "width_mm": int(row.get("width_mm", 0) or 0),
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

    st.caption(
        f"Preview: {format_board_label({'brand': brand or '—', 'material': material or '—', 'thickness': thickness, 'length_mm': length_mm, 'width_mm': width_mm})}"
    )
    return {
        "brand": brand,
        "material": material,
        "thickness": int(thickness),
        "length_mm": int(length_mm),
        "width_mm": int(width_mm),
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
        }
    },
)

render_library_page(config)
