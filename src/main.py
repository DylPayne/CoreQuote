import streamlit as st
import pandas as pd
from logic.logic import get_cabinet_parts, get_door_panel_list, get_draw_panel_list
from logic.units import DoorUnit, DrawerUnit

st.set_page_config(page_title="Core Quotes", layout="wide")

st.title("Core Quotes")
st.write("Select a tool from the sidebar to get started")