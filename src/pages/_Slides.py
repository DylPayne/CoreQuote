from turtle import width

import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Slides", layout="wide")
st.title("Slides")

CSV_PATH = "data/slides.csv"
COLUMNS = ["brand", "model", "code", "length", "side_length", "side_clearance_total"]

def load_data():
    if os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0:
        return pd.read_csv(CSV_PATH)
    return pd.DataFrame(columns=COLUMNS)

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
                new_row = pd.DataFrame([{
                    "brand": brand, "model": model, "code": code, 
                    "length": length, "side_length": side_len, 
                    "side_clearance_total": clearance
                }])
                
                updated_df = pd.concat([st.session_state.original_df, new_row], ignore_index=True)
                updated_df.to_csv(CSV_PATH, index=False)
                st.session_state.original_df = updated_df
                
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
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="main_editor")
    
    has_changes = not edited_df.equals(st.session_state.original_df)

    if has_changes:
        st.warning("⚠️ **Unsaved changes detected!**")
        if st.button("💾 Save All Changes", type="primary", use_container_width=True):
            edited_df.to_csv(CSV_PATH, index=False)
            st.session_state.original_df = edited_df 
            st.success("Library updated!")
            st.rerun()
else:
    st.info("Your library is empty. Click 'Add New Slide' to begin.")