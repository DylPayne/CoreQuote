import streamlit as st
import pandas as pd

from logic.database import (
    get_all_board_types,
    create_board_type,
    update_board_type,
    delete_board_type,
)


st.title(":material/grid_view: Board Library")

COLUMNS = ["id", "brand", "material", "thickness", "length_mm", "width_mm"]


def load_data() -> pd.DataFrame:
    rows = get_all_board_types()
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows)[COLUMNS]


@st.dialog(":material/add: Add New Board", width="medium")
def add_board_dialog():
    with st.form("add_board_form", clear_on_submit=True):
        brand = st.text_input("Brand *")
        material = st.text_input("Material *")
        col1, col2, col3 = st.columns(3)
        with col1:
            thickness = st.number_input("Thickness (mm)", min_value=1, value=16)
        with col2:
            length_mm = st.number_input("Length (mm)", min_value=1, value=2750)
        with col3:
            width_mm = st.number_input("Width (mm)", min_value=1, value=1830)

        if st.form_submit_button("Add to Library", use_container_width=True):
            if not brand.strip() or not material.strip():
                st.error("Brand and Material are required.")
                return
            create_board_type(
                brand=brand.strip(),
                material=material.strip(),
                thickness=int(thickness),
                length_mm=int(length_mm),
                width_mm=int(width_mm),
            )
            st.success(f"Added {brand.strip()} {material.strip()}!")
            st.rerun()


if "original_boards_df" not in st.session_state:
    st.session_state.original_boards_df = load_data()


col_title, col_btn = st.columns([4, 1])
with col_title:
    st.subheader("Current Inventory")
with col_btn:
    if st.button(":material/add: Add New Board", use_container_width=True):
        add_board_dialog()

df = st.session_state.original_boards_df

if not df.empty:
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="boards_main_editor",
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "brand": st.column_config.TextColumn("Brand", required=True),
            "material": st.column_config.TextColumn("Material", required=True),
            "thickness": st.column_config.NumberColumn("Thickness (mm)", min_value=1, required=True),
            "length_mm": st.column_config.NumberColumn("Length (mm)", min_value=1, required=True),
            "width_mm": st.column_config.NumberColumn("Width (mm)", min_value=1, required=True),
        },
    )

    has_changes = not edited_df.equals(st.session_state.original_boards_df)

    if has_changes:
        st.warning(":material/warning: **Unsaved changes detected!**")
        if st.button(":material/save: Save All Changes", type="primary", use_container_width=True):
            original_ids = set(
                st.session_state.original_boards_df["id"].dropna().astype(int).tolist()
            )
            edited_ids = set(edited_df["id"].dropna().astype(int).tolist())

            # Delete removed rows
            for board_id in original_ids - edited_ids:
                delete_board_type(board_id)

            # Create or update rows
            for _, row in edited_df.iterrows():
                brand = str(row.get("brand", "")).strip()
                material = str(row.get("material", "")).strip()
                thickness = int(row.get("thickness", 0) or 0)
                length_mm = int(row.get("length_mm", 0) or 0)
                width_mm = int(row.get("width_mm", 0) or 0)

                if not brand or not material:
                    st.error("Brand and Material are required for all rows.")
                    st.stop()
                if thickness < 1 or length_mm < 1 or width_mm < 1:
                    st.error("Thickness, Length, and Width must all be at least 1.")
                    st.stop()

                board_id = row.get("id")
                if pd.isna(board_id):
                    create_board_type(
                        brand=brand,
                        material=material,
                        thickness=thickness,
                        length_mm=length_mm,
                        width_mm=width_mm,
                    )
                else:
                    update_board_type(
                        board_type_id=int(board_id),
                        brand=brand,
                        material=material,
                        thickness=thickness,
                        length_mm=length_mm,
                        width_mm=width_mm,
                    )

            st.session_state.original_boards_df = load_data()
            st.success("Library updated!")
            st.rerun()
else:
    st.info("Your library is empty. Click 'Add New Board' to begin.")
