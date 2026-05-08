import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import get_all_slides, create_slide, update_slide, delete_slide

st.title("🗂️ Slides Library")

COLUMNS = ["brand", "model", "code", "length", "side_length", "side_clearance_total"]

def load_data():
    rows = get_all_slides()
    if not rows:
        return pd.DataFrame(columns=["id", *COLUMNS])
    return pd.DataFrame(rows)[["id", *COLUMNS]]

if 'original_df' not in st.session_state:
    st.session_state.original_df = load_data()

# --- 1. Define the Pop-up (Dialog) ---
@st.dialog("➕ Add New Slide", width="medium")
def add_slide_dialog():
    # Inside the dialog, we use a standard form
    with st.form("add_slide_form", clear_on_submit=True):
        brand = st.text_input("Brand", placeholder="e.g. Grass")
        model = st.text_input("Model", placeholder="e.g. Dynapro")
        code = st.text_input("Product Code")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            length = st.number_input("Nominal Length (mm)", min_value=0, step=50, value=500)
        with col2:
            side_len = st.number_input("Actual Side Length (mm)", min_value=0, step=1, value=500)
        with col3:
            clearance = st.number_input("Total Clearance (mm)", min_value=0, step=1, value=13)
            
        if st.form_submit_button("Add to Library", use_container_width=True):
            if brand and model:
                create_slide(
                    brand=brand,
                    model=model,
                    code=code,
                    length=int(length),
                    side_length=int(side_len),
                    side_clearance_total=int(clearance),
                )
                st.session_state.original_df = load_data()
                st.success(f"Added {brand} {model}!")
                st.rerun() # This closes the dialog and refreshes the table
            else:
                st.error("Brand and Model are required.")

# --- 2. Main Page Layout ---
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.subheader("Current Inventory")
with col_btn:
    # This button triggers the pop-up
    if st.button("➕ Add New Slide", use_container_width=True):
        add_slide_dialog()

# Display the Table
df = st.session_state.original_df
if not df.empty:
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="main_editor", hide_index=True)
    
    has_changes = not edited_df.equals(st.session_state.original_df)

    if has_changes:
        st.warning("⚠️ **Unsaved changes detected!**")
        if st.button("💾 Save All Changes", type="primary", use_container_width=True):
            original_df = st.session_state.original_df.copy()

            original_ids = set(original_df["id"].dropna().astype(int).tolist()) if not original_df.empty else set()
            edited_ids = set(edited_df["id"].dropna().astype(int).tolist()) if "id" in edited_df.columns else set()

            # Deletes
            for sid in sorted(original_ids - edited_ids):
                delete_slide(int(sid))

            # Inserts / updates
            for _, row in edited_df.iterrows():
                sid = row.get("id")
                payload = {
                    "brand": str(row.get("brand", "")).strip(),
                    "model": str(row.get("model", "")).strip(),
                    "code": str(row.get("code", "")).strip(),
                    "length": int(row.get("length", 0) or 0),
                    "side_length": int(row.get("side_length", 0) or 0),
                    "side_clearance_total": int(row.get("side_clearance_total", 0) or 0),
                }
                if not payload["brand"] or not payload["model"]:
                    st.error("Each row must have Brand and Model.")
                    st.stop()

                if pd.isna(sid) or sid == "":
                    create_slide(**payload)
                else:
                    update_slide(int(sid), **payload)

            st.session_state.original_df = load_data()
            st.success("Library updated!")
            st.rerun()
else:
    st.info("Your library is empty. Click 'Add New Slide' to begin.")