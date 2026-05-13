import streamlit as st
import pandas as pd
import sys
import os

# Add src to path to allow absolute imports in streamlit pages
sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.logic import get_door_panel_list, get_draw_panel_list
from logic.units import DoorUnit, DrawerUnit
from logic.models import Slide
from logic.pdf_gen import generate_pdf
from logic.database import get_all_slides

st.title(":material/build: Cutlist Generator")

slides = get_all_slides()


def _slide_label(slide: dict) -> str:
    return f"{slide['brand']} {slide['model']} ({int(slide['length'])}mm)"

# 1. Inputs
board_thickness, unit_type = st.columns(2)
with board_thickness: bt = st.number_input("Board Thickness", value=16)
with unit_type: ut = st.selectbox(
    "Select Unit Type",
    ["Base 2 Door", "Base 3 Draw"]
)

unit = None

height, width, depth = st.columns(3)
with height: h = st.number_input("Height (mm)", value=780)
with width: w = st.number_input("Width (mm)", value=600)
with depth: d = st.number_input("Depth (mm)", value=580)

# Initialize variables that are used outside their conditional blocks
num_drawers = 0
num_doors = 0

if ut == "Base 3 Draw":
    num_draws_input, slide_input = st.columns(2)
    with num_draws_input: num_drawers = st.selectbox("Number of Drawers", options=[1,2,3,4])
    if not slides:
        st.warning("No slides available. Add slides in Slides Library.")
        st.stop()

    with slide_input: selected_slide_id = st.selectbox(
        "Select Drawer Slide",
        [s["id"] for s in slides],
        format_func=lambda sid: _slide_label(next(s for s in slides if s["id"] == sid)),
    )
    row = next(s for s in slides if s["id"] == selected_slide_id)
    active_slide = Slide(
        brand=row['brand'],
        model=row['model'],
        code=row['code'],
        length=int(row['length']),
        side_length=int(row['side_length']),
        side_clearance_total=int(row['side_clearance_total']),
        side_height_uplift=int(row.get('side_height_uplift', 0) or 0),
    )

    unit = DrawerUnit(
        h=h, w=w, d=d, 
        num_drawers=num_drawers, 
        slide=active_slide, 
        thickness=bt
    )
    
    is_valid, error_msg = unit.validate_slide()
    if not is_valid:
        st.error(error_msg)
elif ut == "Base 2 Door":
    num_doors_input, num_shelves_input = st.columns(2)
    with num_doors_input: num_doors = st.selectbox("Number of Doors", options=[1,2])
    with num_shelves_input: num_shelves = st.number_input("Number of Shelves", value=1)
    unit = DoorUnit(h, w, d, num_doors, num_shelves)

# 2. Trigger Calculation
if st.button("Calculate Cut List"):
    st.subheader("Results")
    
    carcass_list_df = None
    panels_df = None

    if ut == "Base 3 Draw":
        carcass_list_results = unit.get_carcass_list()
        data = [{"Desc": b.name, "L": b.length, "W": b.width, "Qty": b.qty} for b in carcass_list_results]
        carcass_list_df = pd.DataFrame(data)
        
        panel_results = get_draw_panel_list(h, w, num_drawers)
        panels_df = pd.DataFrame(panel_results)
        panels_df['Desc'] = "Drawer Front"
        
    elif ut == "Base 2 Door":
        carcass_list_results = unit.get_carcass_list()
        data = [{"Desc": b.name, "L": b.length, "W": b.width, "Qty": b.qty} for b in carcass_list_results]
        carcass_list_df = pd.DataFrame(data)
        
        panel_results = get_door_panel_list(h, w, num_doors)
        panels_df = pd.DataFrame(panel_results)
        panels_df['Desc'] = "Door"

    col1, col2 = st.columns(2)
    with col1:
        st.write("**Carcass Cut List**")
        st.dataframe(carcass_list_df, use_container_width=True)
    with col2:
        st.write("**Panels Cut List**")
        st.dataframe(panels_df, use_container_width=True)
        
    # PDF Generation
    pdf_bytes = generate_pdf(carcass_list_df, panels_df)
    st.download_button(
        label="Download Cutlist PDF",
        data=bytes(pdf_bytes),
        file_name=f"cutlist_{ut.replace(' ', '_').lower()}.pdf",
        mime="application/pdf"
    )