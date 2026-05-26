import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import (
    get_active_price_list,
    get_price_list_items,
    upsert_price_list_item,
    get_pricing_settings,
    update_vat_rate_bps,
    update_default_markup_bps,
    get_all_slides,
    get_all_hinges,
    get_all_handles,
    get_all_extras,
    get_all_board_types,
)


def _slide_key(s: dict) -> str:
    return f"slide::{s.get('brand','')}::{s.get('model','')}::{s.get('code','')}::{s.get('length','')}"


def _hinge_key(h: dict) -> str:
    return f"hinge::{h.get('brand','')}::{h.get('model','')}::{h.get('code','')}::{h.get('opening_angle_deg','')}"


def _handle_key(h: dict) -> str:
    return f"handle::{h.get('name','')}::{h.get('supplier','')}::{h.get('code','')}"


st.title(":material/payments: Pricing Admin")
st.caption("Manage global VAT/default markup and global cost prices used by all quotes.")

active_price_list = get_active_price_list()
if not active_price_list:
    st.error("No active price list found.")
    st.stop()

st.info(f"Active Price List: **{active_price_list['name']}**")

settings = get_pricing_settings()
vat_pct_default = float(int(settings.get("vat_rate_bps", 1500) or 1500) / 100.0)
markup_pct_default = float(int(settings.get("default_markup_bps", 2500) or 2500) / 100.0)

c1, c2 = st.columns(2)
with c1:
    vat_pct = st.number_input("Global VAT %", min_value=0.0, max_value=100.0, value=vat_pct_default, step=0.1)
    if st.button("Save VAT", use_container_width=True):
        update_vat_rate_bps(int(round(vat_pct * 100.0)))
        st.success("VAT updated.")
        st.rerun()

with c2:
    markup_pct = st.number_input("Global Default Markup %", min_value=0.0, max_value=500.0, value=markup_pct_default, step=0.5)
    if st.button("Save Default Markup", use_container_width=True):
        update_default_markup_bps(int(round(markup_pct * 100.0)))
        st.success("Global default markup updated.")
        st.rerun()

st.divider()
st.subheader("Quick Add / Update Cost Price")

item_type = st.selectbox("Item Type", ["slide", "hinge", "handle", "extra", "board"])

selected_row = None
item_key = ""
uom = "pcs"
label = ""

if item_type == "slide":
    slides = get_all_slides()
    if slides:
        idx = st.selectbox(
            "Slide",
            list(range(len(slides))),
            format_func=lambda i: f"{slides[i]['brand']} {slides[i]['model']} ({slides[i]['length']}mm) • {slides[i]['code']}",
        )
        selected_row = slides[idx]
        item_key = _slide_key(selected_row)
        uom = "pairs"
        label = f"{selected_row['brand']} {selected_row['model']}"
elif item_type == "hinge":
    hinges = get_all_hinges()
    if hinges:
        idx = st.selectbox(
            "Hinge",
            list(range(len(hinges))),
            format_func=lambda i: f"{hinges[i]['brand']} {hinges[i]['model']} ({hinges[i]['opening_angle_deg']}°) • {hinges[i]['code']}",
        )
        selected_row = hinges[idx]
        item_key = _hinge_key(selected_row)
        uom = "pcs"
        label = f"{selected_row['brand']} {selected_row['model']}"
elif item_type == "handle":
    handles = get_all_handles()
    if handles:
        idx = st.selectbox(
            "Handle",
            list(range(len(handles))),
            format_func=lambda i: f"{handles[i]['name']} • {handles[i]['supplier']} • {handles[i]['code']}",
        )
        selected_row = handles[idx]
        item_key = _handle_key(selected_row)
        uom = "pcs"
        label = f"{selected_row['name']}"
elif item_type == "extra":
    extras = get_all_extras()
    if extras:
        idx = st.selectbox(
            "Extra",
            list(range(len(extras))),
            format_func=lambda i: f"{extras[i]['name']} • {extras[i].get('category_name','')}",
        )
        selected_row = extras[idx]
        item_key = f"extra::{int(selected_row['id'])}"
        uom = "pcs"
        label = f"{selected_row['name']}"
else:
    boards = get_all_board_types()
    if boards:
        idx = st.selectbox(
            "Board",
            list(range(len(boards))),
            format_func=lambda i: (
                f"{boards[i]['brand']} {boards[i]['material']} {boards[i]['thickness']}mm "
                f"({boards[i]['length_mm']}x{boards[i]['width_mm']})"
            ),
        )
        selected_row = boards[idx]
        item_key = f"board::{int(selected_row['id'])}"
        mode = str(selected_row.get("costing_mode", "sheet") or "sheet").strip().lower()
        uom = "m2" if mode == "sqm" else "sheet"
        label = f"{selected_row['brand']} {selected_row['material']}"

if selected_row:
    st.caption(f"Item Key: `{item_key}`")
    if item_type == "board":
        mode = str(selected_row.get("costing_mode", "sheet") or "sheet").strip().lower()
        if mode == "sqm":
            sqm_key = f"{item_key}::sqm"
            st.caption(f"Pricing Key: `{sqm_key}`")
            sqm_price = st.number_input("SQM Price (R/m²)", min_value=0.0, value=0.0, step=1.0)
            if st.button("Save SQM Price", type="primary", use_container_width=True):
                upsert_price_list_item(
                    price_list_id=int(active_price_list["id"]),
                    item_type="board",
                    item_key=sqm_key,
                    uom="m2",
                    unit_price_cents=int(round(sqm_price * 100.0)),
                )
                st.success(f"Saved SQM price for {label}.")
                st.rerun()
        else:
            sheet_key = f"{item_key}::sheet"
            edging_key = f"{item_key}::edging_m"
            labour_key = f"{item_key}::labour_board"
            st.caption(f"Pricing Keys: `{sheet_key}`, `{edging_key}`, `{labour_key}`")
            c_sheet, c_edge, c_lab = st.columns(3)
            with c_sheet:
                sheet_price = st.number_input("Sheet Price (R/sheet)", min_value=0.0, value=0.0, step=1.0)
            with c_edge:
                edging_price = st.number_input("Edging Price (R/m)", min_value=0.0, value=0.0, step=0.1)
            with c_lab:
                labour_price = st.number_input("Labour (R/board)", min_value=0.0, value=0.0, step=1.0)

            if st.button("Save Board Prices", type="primary", use_container_width=True):
                upsert_price_list_item(
                    price_list_id=int(active_price_list["id"]),
                    item_type="board",
                    item_key=sheet_key,
                    uom="sheet",
                    unit_price_cents=int(round(sheet_price * 100.0)),
                )
                upsert_price_list_item(
                    price_list_id=int(active_price_list["id"]),
                    item_type="board",
                    item_key=edging_key,
                    uom="m",
                    unit_price_cents=int(round(edging_price * 100.0)),
                )
                upsert_price_list_item(
                    price_list_id=int(active_price_list["id"]),
                    item_type="board",
                    item_key=labour_key,
                    uom="board",
                    unit_price_cents=int(round(labour_price * 100.0)),
                )
                st.success(f"Saved board prices for {label}.")
                st.rerun()
    else:
        cost_price = st.number_input("Cost Price", min_value=0.0, value=0.0, step=1.0)
        if st.button("Save Cost Price", type="primary", use_container_width=True):
            upsert_price_list_item(
                price_list_id=int(active_price_list["id"]),
                item_type=item_type,
                item_key=item_key,
                uom=uom,
                unit_price_cents=int(round(cost_price * 100.0)),
            )
            st.success(f"Saved cost price for {label}.")
            st.rerun()

st.divider()
st.subheader("Current Global Cost Prices")
rows = get_price_list_items(int(active_price_list["id"]))

if not rows:
    st.info("No global prices yet.")
else:
    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "item_type": r["item_type"],
                "item_key": r["item_key"],
                "uom": r["uom"],
                "unit_price": float(int(r["unit_price_cents"]) / 100.0),
            }
            for r in rows
        ]
    )
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "item_type": st.column_config.TextColumn("Type", disabled=True),
            "item_key": st.column_config.TextColumn("Item Key", disabled=True),
            "uom": st.column_config.TextColumn("UOM", disabled=True),
            "unit_price": st.column_config.NumberColumn("Cost Price", min_value=0.0, step=1.0, format="%.2f"),
        },
    )
    if st.button("Save Edited Prices", use_container_width=True):
        for _, r in edited.iterrows():
            upsert_price_list_item(
                price_list_id=int(active_price_list["id"]),
                item_type=str(r["item_type"]),
                item_key=str(r["item_key"]),
                uom=str(r["uom"]),
                unit_price_cents=int(round(float(r["unit_price"]) * 100.0)),
            )
        st.success("Global prices updated.")
        st.rerun()
