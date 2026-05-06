import streamlit as st
import pandas as pd
from logic.logic import get_cabinet_parts, get_door_panel_list, get_draw_panel_list
from logic.units import DoorUnit, DrawerUnit, Slide

st.title("Cutlist Generator")

slides_df = pd.read_csv("data/slides.csv")

# 1. Inputs
board_thickness, unit_type = st.columns(2)
with board_thickness: bt = st.number_input("Board Thickness", value=16)
with unit_type: ut = st.selectbox(
    "Select Unit Type",
    ["Door Unit", "Draw Unit"]
)

unit = None

height, width, depth = st.columns(3)
with height: h = st.number_input("Height (mm)", value=720)
with width: w = st.number_input("Width (mm)", value=600)
with depth: d = st.number_input("Depth (mm)", value=560)

if ut == "Draw Unit":
    num_draws_input, slide_input = st.columns(2)
    with num_draws_input: num_draws = st.selectbox("Number of Drawers", options=[1,2,3,4])
    with slide_input: selected_index = st.selectbox(
        "Select Drawer Slide", 
        range(len(slides_df)), 
        format_func=lambda x: f"{slides_df.iloc[x]['brand']} {slides_df.iloc[x]['model']} ({slides_df.iloc[x]['length']}mm)"
    )
    row = slides_df.iloc[selected_index]
    active_slide = Slide(
    brand=row['brand'],
    model=row['model'],
    code=row['code'],
    length=int(row['length']),
    side_length=int(row['side_length']),
    side_clearance_total=int(row['side_clearance_total'])
    )

    unit = DrawerUnit(
        h=h, w=w, d=d, 
        num_drawers=num_draws, 
        slide=active_slide, 
        thickness=bt
    )
elif ut == "Door Unit":
    num_doors_input, num_shelves_input = st.columns(2)
    with num_doors_input: num_doors = st.selectbox("Number of Doors", options=[1,2])
    with num_shelves_input: num_shelves = st.number_input("Number of Shelves", value=1)
    unit = DoorUnit(h, w, d, num_doors, num_shelves)

# 2. Trigger Calculation
if st.button("Calculate Cut List"):


    # carcass_cut_list_results = get_cabinet_parts(h, w, d, bt)
    # carcass_cut_list_df = pd.DataFrame(carcass_cut_list_results)
    st.subheader("Carcass Cut List")
    carcass_list_df = None

    if ut == "Draw Unit":
        carcass_list_results = DrawerUnit.get_carcass_list(unit)
        data = [
            {
                "Desc": b.name,
                "L": b.length,
                "W": b.width,
                "Qty": b.qty
            }
            for b in carcass_list_results
        ]
        carcass_list_df = pd.DataFrame(data)
    elif ut == "Door Unit":
        carcass_list_results = DoorUnit.get_carcass_list(unit)
        data = [
            {
                "Desc": b.name,
                "L": b.length,
                "W": b.width,
                "Qty": b.qty
            }
            for b in carcass_list_results
        ]
        carcass_list_df = pd.DataFrame(data)

    st.dataframe(carcass_list_df, use_container_width=True)