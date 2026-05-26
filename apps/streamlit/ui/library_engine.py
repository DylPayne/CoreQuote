from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class LibraryCallbacks:
    list_rows: Callable[[], list[dict]]
    create_row: Callable[..., Any]
    update_row: Callable[..., Any]
    delete_row: Callable[[int], Any]


@dataclass(frozen=True)
class LibraryValidationResult:
    is_valid: bool
    message: str | None = None


@dataclass(frozen=True)
class LibraryConfig:
    page_title: str
    section_title: str
    add_button_label: str
    add_dialog_title: str
    id_column: str
    columns: list[str]
    editor_key: str
    session_df_key: str
    empty_state_message: str
    callbacks: LibraryCallbacks
    validate_row: Callable[[dict], LibraryValidationResult]
    render_add_dialog_fields: Callable[[], dict]
    build_create_payload: Callable[[dict], dict]
    build_update_payload: Callable[[dict], dict]
    dialog_submit_label: str = "Add to Library"
    dialog_success_message: str = "Added successfully!"
    save_success_message: str = "Library updated!"
    editor_kwargs: dict[str, Any] | None = None


def rows_to_df(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows)[columns]


def compute_id_diff(original_df: pd.DataFrame, edited_df: pd.DataFrame, id_column: str) -> tuple[set[int], set[int]]:
    original_ids = set(original_df[id_column].dropna().astype(int).tolist()) if not original_df.empty else set()
    edited_ids = set(edited_df[id_column].dropna().astype(int).tolist()) if id_column in edited_df.columns else set()
    return original_ids, edited_ids


def apply_library_mutations(
    *,
    original_df: pd.DataFrame,
    edited_df: pd.DataFrame,
    id_column: str,
    validate_row: Callable[[dict], LibraryValidationResult],
    build_create_payload: Callable[[dict], dict],
    build_update_payload: Callable[[dict], dict],
    create_row: Callable[..., Any],
    update_row: Callable[..., Any],
    delete_row: Callable[[int], Any],
) -> None:
    original_ids, edited_ids = compute_id_diff(original_df, edited_df, id_column)

    for deleted_id in sorted(original_ids - edited_ids):
        delete_row(int(deleted_id))

    for _, row in edited_df.iterrows():
        row_dict = dict(row)
        validation = validate_row(row_dict)
        if not validation.is_valid:
            st.error(validation.message or "Invalid row data.")
            st.stop()

        row_id = row.get(id_column)
        if pd.isna(row_id) or row_id == "":
            create_row(**build_create_payload(row_dict))
        else:
            update_row(int(row_id), **build_update_payload(row_dict))


def render_library_page(config: LibraryConfig) -> None:
    st.title(config.page_title)

    def load_data() -> pd.DataFrame:
        return rows_to_df(config.callbacks.list_rows(), config.columns)

    if config.session_df_key not in st.session_state:
        st.session_state[config.session_df_key] = load_data()

    @st.dialog(config.add_dialog_title, width="medium")
    def add_item_dialog() -> None:
        with st.form(f"{config.editor_key}_add_form", clear_on_submit=True):
            fields = config.render_add_dialog_fields()
            if st.form_submit_button(config.dialog_submit_label, use_container_width=True):
                validation = config.validate_row(fields)
                if not validation.is_valid:
                    st.error(validation.message or "Please fix validation issues.")
                    return
                config.callbacks.create_row(**config.build_create_payload(fields))
                st.session_state[config.session_df_key] = load_data()
                st.success(config.dialog_success_message)
                st.rerun()

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.subheader(config.section_title)
    with col_btn:
        if st.button(config.add_button_label, use_container_width=True):
            add_item_dialog()

    original_df = st.session_state[config.session_df_key]
    if original_df.empty:
        st.info(config.empty_state_message)
        return

    editor_kwargs = config.editor_kwargs or {}
    edited_df = st.data_editor(
        original_df,
        num_rows="dynamic",
        use_container_width=True,
        key=config.editor_key,
        hide_index=True,
        **editor_kwargs,
    )
    has_changes = not edited_df.equals(original_df)

    if has_changes:
        st.warning(":material/warning: **Unsaved changes detected!**")
        if st.button(":material/save: Save All Changes", type="primary", use_container_width=True):
            apply_library_mutations(
                original_df=original_df.copy(),
                edited_df=edited_df,
                id_column=config.id_column,
                validate_row=config.validate_row,
                build_create_payload=config.build_create_payload,
                build_update_payload=config.build_update_payload,
                create_row=config.callbacks.create_row,
                update_row=config.callbacks.update_row,
                delete_row=config.callbacks.delete_row,
            )
            st.session_state[config.session_df_key] = load_data()
            st.success(config.save_success_message)
            st.rerun()
