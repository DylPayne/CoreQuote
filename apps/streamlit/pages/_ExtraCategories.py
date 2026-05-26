import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "packages", "corequote-core"))

from corequote_core.database import (
    get_all_extra_categories,
    create_extra_category,
    update_extra_category,
    delete_extra_category,
)
from ui.library_engine import (
    LibraryCallbacks,
    LibraryConfig,
    LibraryValidationResult,
    render_library_page,
)
from ui.formatters import format_extra_category_label

COLUMNS = ["id", "name"]


def _validate_category_row(row: dict) -> LibraryValidationResult:
    name = str(row.get("name", "")).strip()
    if not name:
        return LibraryValidationResult(False, "Each row must have a Category Name.")
    return LibraryValidationResult(True)


def _build_category_payload(row: dict) -> dict:
    return {"name": str(row.get("name", "")).strip()}


def _render_add_category_fields() -> dict:
    name = st.text_input("Category Name", placeholder="e.g. Appliances")
    st.caption(f"Preview: {format_extra_category_label({'name': name})}")
    return {"name": name}


config = LibraryConfig(
    page_title=":material/category: Extras Categories",
    section_title="Current Categories",
    add_button_label=":material/add: Add New Category",
    add_dialog_title=":material/add: Add New Category",
    id_column="id",
    columns=COLUMNS,
    editor_key="extra_categories_main_editor",
    session_df_key="original_extra_categories_df",
    empty_state_message="No categories yet. Click 'Add New Category' to begin.",
    callbacks=LibraryCallbacks(
        list_rows=get_all_extra_categories,
        create_row=create_extra_category,
        update_row=update_extra_category,
        delete_row=delete_extra_category,
    ),
    validate_row=_validate_category_row,
    render_add_dialog_fields=_render_add_category_fields,
    build_create_payload=_build_category_payload,
    build_update_payload=_build_category_payload,
    dialog_success_message="Added category successfully!",
    editor_kwargs={
        "column_config": {
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "name": st.column_config.TextColumn("Category Name", required=True),
        }
    },
)

render_library_page(config)