import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import (
    get_project, get_quote,
    get_units_for_quote, add_unit, update_unit, delete_unit_and_renumber,
    get_all_board_types,
    get_all_slides,
)
from logic.models import Slide
from logic.cutlist import build_cutlist
from logic.pdf_gen import generate_pdf

# ── Guards ─────────────────────────────────────────────────────────────────────

if "active_quote_id" not in st.session_state or st.session_state.active_quote_id is None:
    st.warning("No quote selected.")
    if st.button("← Back to Projects"):
        st.switch_page("pages/_Projects.py")
    st.stop()

quote = get_quote(st.session_state.active_quote_id)
if quote is None:
    st.error("Quote not found.")
    st.session_state.active_quote_id = None
    st.stop()

project = get_project(quote["project_id"])

# ── Load slides from DB ────────────────────────────────────────────────────────

slides = get_all_slides()
slide_ids = [s["id"] for s in slides]
slide_lookup = {s["id"]: s for s in slides}
board_types = get_all_board_types()
board_lookup = {b["id"]: b for b in board_types}
board_ids = [None] + [b["id"] for b in board_types]


def _board_option_label(board_id: int | None) -> str:
    if board_id is None:
        return "— None —"
    b = board_lookup.get(board_id)
    if not b:
        return "— None —"
    return f"{b['brand']} • {b['material']} • {b['thickness']}mm • {b['length_mm']}x{b['width_mm']}"


def _board_index_for_id(board_id: int | None) -> int:
    if board_id in board_ids:
        return board_ids.index(board_id)
    return 0

# ── Unit Form + Add/Edit Dialogs ──────────────────────────────────────────────

UNIT_TYPES = ["Base Drawer", "Base Door", "Wall Door", "Tall Standard", "Tall Pantry"]


def _default_dims_for_unit_type(unit_type: str) -> tuple[int, int]:
    defaults = quote.get("unit_defaults", {}) or {}
    item = defaults.get(unit_type, {})

    if unit_type == "Wall Door":
        fallback_h, fallback_d = 720, 330
    elif unit_type == "Tall Standard":
        fallback_h, fallback_d = 2100, 580
    elif unit_type == "Tall Pantry":
        fallback_h, fallback_d = 2400, 580
    else:
        fallback_h, fallback_d = 780, 580

    return int(item.get("height", fallback_h)), int(item.get("depth", fallback_d))


def _normalize_unit_type_and_extra(unit_type: str, extra: dict | None = None) -> tuple[str, dict]:
    """Map legacy unit types to canonical UI types while preserving explicit counts."""
    extra = dict(extra or {})

    if unit_type in ("Base 1 Draw", "Base 2 Draw", "Base 3 Draw", "Base 4 Draw"):
        count = int(unit_type.split()[1])
        extra.setdefault("num_drawers", count)
        return "Base Drawer", extra

    if unit_type in ("Base 1 Door", "Base 2 Door"):
        count = int(unit_type.split()[1])
        extra.setdefault("num_doors", count)
        return "Base Door", extra

    if unit_type in ("Wall 1 Door", "Wall 2 Door"):
        count = int(unit_type.split()[1])
        extra.setdefault("num_doors", count)
        return "Wall Door", extra

    return unit_type, extra


def _get_slide_id(extra: dict) -> int | None:
    if not slides:
        return None
    brand = str(extra.get("slide_brand", ""))
    model = str(extra.get("slide_model", ""))
    code = str(extra.get("slide_code", ""))
    for s in slides:
        if str(s["brand"]) == brand and str(s["model"]) == model and str(s["code"]) == code:
            return int(s["id"])

    # Fall back to quote default slide if available.
    q_brand = str(quote.get("default_slide_brand", "") or "")
    q_model = str(quote.get("default_slide_model", "") or "")
    q_code = str(quote.get("default_slide_code", "") or "")
    for s in slides:
        if str(s["brand"]) == q_brand and str(s["model"]) == q_model and str(s["code"]) == q_code:
            return int(s["id"])

    return slide_ids[0] if slide_ids else None


def unit_form(initial: dict | None = None, key_prefix: str = "add"):
    initial = initial or {}
    initial_type = str(initial.get("unit_type", UNIT_TYPES[0]))
    initial_extra = initial.get("extra_params", {}) or {}
    normalized_type, normalized_extra = _normalize_unit_type_and_extra(initial_type, initial_extra)

    initial_carcass_board_id = initial.get("carcass_board_type_id")
    initial_door_board_id = initial.get("door_board_type_id")
    if initial_carcass_board_id is None:
        initial_carcass_board_id = quote.get("default_carcass_board_type_id")
    if initial_door_board_id is None:
        initial_door_board_id = quote.get("default_door_board_type_id")

    st.markdown("##### Materials")
    col_cb, col_db = st.columns(2)
    with col_cb:
        carcass_board_type_id = st.selectbox(
            "Carcass Board Type",
            board_ids,
            index=_board_index_for_id(initial_carcass_board_id),
            format_func=_board_option_label,
            key=f"{key_prefix}_carcass_board",
        )
    with col_db:
        door_board_type_id = st.selectbox(
            "Door Board Type",
            board_ids,
            index=_board_index_for_id(initial_door_board_id),
            format_func=_board_option_label,
            key=f"{key_prefix}_door_board",
        )

    selected_carcass = board_lookup.get(carcass_board_type_id) if carcass_board_type_id is not None else None
    bt = int(selected_carcass["thickness"]) if selected_carcass else int(initial.get("thickness", 16))
    st.caption(f"Carcass thickness applied: **{bt} mm**")

    st.markdown("##### Unit Setup")
    default_type = normalized_type if normalized_type in UNIT_TYPES else UNIT_TYPES[0]
    type_index = UNIT_TYPES.index(default_type) if default_type in UNIT_TYPES else 0
    ut = st.selectbox("Unit Type", UNIT_TYPES, index=type_index, key=f"{key_prefix}_type")

    default_h, default_d = _default_dims_for_unit_type(ut)
    col_h, col_w, col_d = st.columns(3)
    with col_h:
        h = st.number_input(
            "Height (mm)",
            min_value=1,
            value=int(initial.get("height", default_h)),
            key=f"{key_prefix}_height",
        )
    with col_w:
        w = st.number_input(
            "Width (mm)",
            min_value=1,
            value=int(initial.get("width", 600)),
            key=f"{key_prefix}_width",
        )
    with col_d:
        d = st.number_input(
            "Depth (mm)",
            min_value=1,
            value=int(initial.get("depth", default_d)),
            key=f"{key_prefix}_depth",
        )

    extra = {}
    is_valid = True

    if ut == "Base Drawer":
        st.markdown("##### Drawer Options")
        col_nd, col_sl = st.columns(2)
        with col_nd:
            num_drawers = st.selectbox(
                "Number of Drawers",
                [1, 2, 3, 4],
                index=max(0, min(3, int(normalized_extra.get("num_drawers", 3)) - 1)),
                key=f"{key_prefix}_num_drawers",
            )
        with col_sl:
            if not slides:
                st.warning("No slides available. Add slides in Slides Library.")
                is_valid = False
                selected_slide_id = None
            else:
                default_slide_id = _get_slide_id(normalized_extra)
                default_index = slide_ids.index(default_slide_id) if default_slide_id in slide_ids else 0
                selected_slide_id = st.selectbox(
                    "Drawer Slide",
                    slide_ids,
                    index=default_index,
                    format_func=lambda sid: (
                        f'{slide_lookup[sid]["brand"]} {slide_lookup[sid]["model"]} '
                        f'({slide_lookup[sid]["length"]}mm)'
                    ),
                    key=f"{key_prefix}_slide_id",
                )

        if selected_slide_id is None:
            return {
                "unit_type": ut,
                "height": int(h),
                "width": int(w),
                "depth": int(d),
                "thickness": int(bt),
                "carcass_board_type_id": carcass_board_type_id,
                "door_board_type_id": door_board_type_id,
                "extra_params": {},
                "is_valid": False,
            }

        row = slide_lookup[selected_slide_id]
        slide = Slide(
            brand=row["brand"], model=row["model"], code=row["code"],
            length=int(row["length"]), side_length=int(row["side_length"]),
            side_clearance_total=int(row["side_clearance_total"])
        )

        from logic.units import DrawerUnit
        test_unit = DrawerUnit(h=h, w=w, d=d, slide=slide,
                               num_drawers=num_drawers, thickness=bt)
        valid, err = test_unit.validate_slide()
        if not valid:
            st.error(err)
            is_valid = False

        extra = {
            "num_drawers": int(num_drawers),
            "slide_brand": slide.brand,
            "slide_model": slide.model,
            "slide_code": str(slide.code),
            "slide_length": int(slide.length),
            "slide_side_length": int(slide.side_length),
            "slide_side_clearance_total": int(slide.side_clearance_total),
        }

    elif ut in ("Base Door", "Wall Door", "Tall Standard", "Tall Pantry"):
        st.markdown("##### Door / Shelf Options")
        col_nd, col_ns = st.columns(2)
        with col_nd:
            num_doors = st.selectbox(
                "Number of Doors",
                [1, 2],
                index=max(0, min(1, int(normalized_extra.get("num_doors", 2)) - 1)),
                key=f"{key_prefix}_num_doors",
            )
        with col_ns:
            default_shelves = 4 if ut in ("Tall Standard", "Tall Pantry") else 1
            num_shelves = st.number_input(
                "Number of Shelves",
                min_value=0,
                value=int(normalized_extra.get("num_shelves", default_shelves)),
                key=f"{key_prefix}_num_shelves",
            )

        if ut == "Wall Door":
            d = st.number_input("Depth (mm)", min_value=1, value=int(initial.get("depth", 330)), key=f"{key_prefix}_wall_depth")
        elif ut in ("Tall Standard", "Tall Pantry"):
            default_tall_h = 2100 if ut == "Tall Standard" else 2400
            h = st.number_input("Height (mm)", min_value=1, value=int(initial.get("height", default_tall_h)), key=f"{key_prefix}_tall_height")
            d = st.number_input("Depth (mm)", min_value=1, value=int(initial.get("depth", 580)), key=f"{key_prefix}_tall_depth")

        extra = {"num_doors": int(num_doors), "num_shelves": int(num_shelves)}

    return {
        "unit_type": ut,
        "height": int(h),
        "width": int(w),
        "depth": int(d),
        "thickness": int(bt),
        "carcass_board_type_id": carcass_board_type_id,
        "door_board_type_id": door_board_type_id,
        "extra_params": extra,
        "is_valid": is_valid,
    }


@st.dialog("➕ Add Unit", width="large")
def add_unit_dialog():
    payload = unit_form(key_prefix="add")
    if st.button("Add Unit to Quote", type="primary", use_container_width=True):
        if not payload["is_valid"]:
            st.warning("Please fix validation errors before adding this unit.")
            return
        add_unit(
            quote_id=quote["id"],
            unit_type=payload["unit_type"],
            height=payload["height"],
            width=payload["width"],
            depth=payload["depth"],
            thickness=payload["thickness"],
            carcass_board_type_id=payload["carcass_board_type_id"],
            door_board_type_id=payload["door_board_type_id"],
            extra_params=payload["extra_params"],
        )
        st.success("Unit added!")
        st.rerun()


@st.dialog("✏️ Edit Unit", width="large")
def edit_unit_dialog(unit: dict):
    payload = unit_form(initial=unit, key_prefix=f"edit_{unit['id']}")
    if st.button("Save Changes", type="primary", use_container_width=True, key=f"save_edit_{unit['id']}"):
        if not payload["is_valid"]:
            st.warning("Please fix validation errors before saving this unit.")
            return
        update_unit(
            unit_id=unit["id"],
            unit_type=payload["unit_type"],
            height=payload["height"],
            width=payload["width"],
            depth=payload["depth"],
            thickness=payload["thickness"],
            carcass_board_type_id=payload["carcass_board_type_id"],
            door_board_type_id=payload["door_board_type_id"],
            extra_params=payload["extra_params"],
        )
        st.success("Unit updated!")
        st.rerun()


# ── Page header ────────────────────────────────────────────────────────────────

col_back, col_title = st.columns([1, 6])
with col_back:
    if st.button("← Quotes"):
        st.switch_page("pages/_Quotes.py")
with col_title:
    proj_label = f"{project['name']} › " if project else ""
    st.title(f"📋 {proj_label}{quote['name']}")

if quote["notes"]:
    st.caption(quote["notes"])

st.divider()

# ── Units list ─────────────────────────────────────────────────────────────────

col_sub, col_add = st.columns([4, 1])
with col_sub:
    st.subheader("Units")
with col_add:
    if st.button("➕ Add Unit", use_container_width=True, type="primary"):
        add_unit_dialog()

units = get_units_for_quote(quote["id"])

if not units:
    st.info("No units yet. Click **➕ Add Unit** to begin building this quote.")
else:
    for u in units:
        extra = u.get("extra_params", {})
        with st.container(border=True):
            col_info, col_actions = st.columns([6, 2])
            with col_info:
                st.markdown(
                    f"**Unit {u['unit_number']}** — {u['unit_type']}  "
                    f"&nbsp;&nbsp; H: {u['height']} × W: {u['width']} × D: {u['depth']} mm  "
                    f"&nbsp;&nbsp; Thickness: {u['thickness']} mm"
                )
                carcass_label = _board_option_label(u.get("carcass_board_type_id"))
                door_label = _board_option_label(u.get("door_board_type_id"))
                st.caption(f"Carcass Board: {carcass_label}  •  Door Board: {door_label}")
                if "Draw" in u["unit_type"]:
                    slide_label = (
                        f"{extra.get('slide_brand', '')} {extra.get('slide_model', '')} "
                        f"({extra.get('slide_length', '')}mm)"
                    )
                    st.caption(
                        f"Drawers: {extra.get('num_drawers', '?')}  •  Slide: {slide_label}"
                    )
                elif ("Door" in u["unit_type"]) or ("Tall" in u["unit_type"]):
                    st.caption(
                        f"Doors: {extra.get('num_doors', '?')}  •  "
                        f"Shelves: {extra.get('num_shelves', '?')}"
                    )
            with col_actions:
                act_edit, act_del = st.columns(2)
                with act_edit:
                    if st.button("✏️", key=f"edit_unit_{u['id']}", help="Edit this unit", use_container_width=True):
                        edit_unit_dialog(u)
                with act_del:
                    if st.button("🗑️", key=f"del_unit_{u['id']}", help="Remove this unit",
                                 use_container_width=True):
                        delete_unit_and_renumber(u["id"])
                        st.rerun()

    # ── Cutting List Preview & Export ──────────────────────────────────────────

    st.divider()
    st.subheader("📐 Cutting List")

    carcass_df, panels_df = build_cutlist(units)

    col_c, col_p = st.columns(2)
    with col_c:
        st.write("**Carcass Boards**")
        st.dataframe(carcass_df, use_container_width=True, hide_index=True)
    with col_p:
        st.write("**Panels (Doors / Drawer Fronts)**")
        st.dataframe(panels_df, use_container_width=True, hide_index=True)

    # PDF export
    proj_name = project["name"] if project else ""
    pdf_bytes = generate_pdf(
        carcass_df, panels_df,
        project_name=proj_name,
        quote_name=quote["name"]
    )
    safe_name = quote["name"].replace(" ", "_").lower()
    st.download_button(
        label="⬇️ Download Cutting List PDF",
        data=bytes(pdf_bytes),
        file_name=f"cutlist_{safe_name}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )
