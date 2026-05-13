import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import get_all_hinges, create_hinge, update_hinge, delete_hinge

st.title(":material/hardware: Hinges Library")

COLUMNS = ["brand", "model", "code", "opening_angle_deg"]


def load_data():
    rows = get_all_hinges()
    if not rows:
        return pd.DataFrame(columns=["id", *COLUMNS])
    return pd.DataFrame(rows)[["id", *COLUMNS]]


if 'original_df' not in st.session_state:
    st.session_state.original_df = load_data()


@st.dialog(":material/add: Add New Hinge", width="medium")
def add_hinge_dialog():
    with st.form("add_hinge_form", clear_on_submit=True):
        brand = st.text_input("Brand", placeholder="e.g. Blum")
        model = st.text_input("Model", placeholder="e.g. Clip Top")
        code = st.text_input("Product Code")
        opening_angle_deg = st.number_input("Opening Angle (°)", min_value=0, step=1, value=110)

        if st.form_submit_button("Add to Library", use_container_width=True):
            if brand and model:
                create_hinge(
                    brand=brand,
                    model=model,
                    code=code,
                    opening_angle_deg=int(opening_angle_deg),
                )
                st.session_state.original_df = load_data()
                st.success(f"Added {brand} {model}!")
                st.rerun()
            else:
                st.error("Brand and Model are required.")


col_title, col_btn = st.columns([4, 1])
with col_title:
    st.subheader("Current Inventory")
with col_btn:
    if st.button(":material/add: Add New Hinge", use_container_width=True):
        add_hinge_dialog()


df = st.session_state.original_df
if not df.empty:
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="main_editor", hide_index=True)

    has_changes = not edited_df.equals(st.session_state.original_df)

    if has_changes:
        st.warning(":material/warning: **Unsaved changes detected!**")
        if st.button(":material/save: Save All Changes", type="primary", use_container_width=True):
            original_df = st.session_state.original_df.copy()

            original_ids = set(original_df["id"].dropna().astype(int).tolist()) if not original_df.empty else set()
            edited_ids = set(edited_df["id"].dropna().astype(int).tolist()) if "id" in edited_df.columns else set()

            for hid in sorted(original_ids - edited_ids):
                delete_hinge(int(hid))

            for _, row in edited_df.iterrows():
                hid = row.get("id")
                payload = {
                    "brand": str(row.get("brand", "")).strip(),
                    "model": str(row.get("model", "")).strip(),
                    "code": str(row.get("code", "")).strip(),
                    "opening_angle_deg": int(row.get("opening_angle_deg", 0) or 0),
                }
                if not payload["brand"] or not payload["model"]:
                    st.error("Each row must have Brand and Model.")
                    st.stop()

                if pd.isna(hid) or hid == "":
                    create_hinge(**payload)
                else:
                    update_hinge(int(hid), **payload)

            st.session_state.original_df = load_data()
            st.success("Library updated!")
            st.rerun()
else:
    st.info("Your library is empty. Click 'Add New Hinge' to begin.")
