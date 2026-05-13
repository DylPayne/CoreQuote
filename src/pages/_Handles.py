import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import get_all_handles, create_handle, update_handle, delete_handle

st.title(":material/touch_app: Handle Library")

COLUMNS = ["name", "supplier", "code"]


def load_data():
    rows = get_all_handles()
    if not rows:
        return pd.DataFrame(columns=["id", *COLUMNS])
    return pd.DataFrame(rows)[["id", *COLUMNS]]


if 'original_handles_df' not in st.session_state:
    st.session_state.original_handles_df = load_data()


@st.dialog(":material/add: Add New Handle", width="medium")
def add_handle_dialog():
    with st.form("add_handle_form", clear_on_submit=True):
        name = st.text_input("Handle Name", placeholder="e.g. Slim Bar 160")
        supplier = st.text_input("Supplier", placeholder="e.g. Häfele")
        code = st.text_input("Product Code")

        if st.form_submit_button("Add to Library", use_container_width=True):
            if name.strip():
                create_handle(name=name, supplier=supplier, code=code)
                st.session_state.original_handles_df = load_data()
                st.success(f"Added {name}!")
                st.rerun()
            else:
                st.error("Handle Name is required.")


col_title, col_btn = st.columns([4, 1])
with col_title:
    st.subheader("Current Inventory")
with col_btn:
    if st.button(":material/add: Add New Handle", use_container_width=True):
        add_handle_dialog()


df = st.session_state.original_handles_df
if not df.empty:
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="handles_editor", hide_index=True)

    has_changes = not edited_df.equals(st.session_state.original_handles_df)

    if has_changes:
        st.warning(":material/warning: **Unsaved changes detected!**")
        if st.button(":material/save: Save All Changes", type="primary", use_container_width=True):
            original_df = st.session_state.original_handles_df.copy()

            original_ids = set(original_df["id"].dropna().astype(int).tolist()) if not original_df.empty else set()
            edited_ids = set(edited_df["id"].dropna().astype(int).tolist()) if "id" in edited_df.columns else set()

            for hid in sorted(original_ids - edited_ids):
                delete_handle(int(hid))

            for _, row in edited_df.iterrows():
                hid = row.get("id")
                payload = {
                    "name": str(row.get("name", "")).strip(),
                    "supplier": str(row.get("supplier", "")).strip(),
                    "code": str(row.get("code", "")).strip(),
                }
                if not payload["name"]:
                    st.error("Each row must have a Handle Name.")
                    st.stop()

                if pd.isna(hid) or hid == "":
                    create_handle(**payload)
                else:
                    update_handle(int(hid), **payload)

            st.session_state.original_handles_df = load_data()
            st.success("Library updated!")
            st.rerun()
else:
    st.info("Your library is empty. Click 'Add New Handle' to begin.")
