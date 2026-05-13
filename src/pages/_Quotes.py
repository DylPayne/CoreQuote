import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import (
    get_project, get_quotes_for_project,
    create_quote, update_quote, delete_quote,
    get_units_for_quote,
    get_all_board_types,
    get_all_slides,
    get_all_hinges,
)


def _board_option_label(board: dict) -> str:
    return f"{board['brand']} • {board['material']} • {board['thickness']}mm • {board['length_mm']}x{board['width_mm']}"


board_types = get_all_board_types()
board_ids = [None] + [b["id"] for b in board_types]
board_lookup = {b["id"]: b for b in board_types}
slides = get_all_slides()
slide_ids = [s["id"] for s in slides]
slide_lookup = {s["id"]: s for s in slides}
hinges = get_all_hinges()
hinge_ids = [h["id"] for h in hinges]
hinge_lookup = {h["id"]: h for h in hinges}

UNIT_DEFAULT_KEYS = ["Base Drawer", "Base Door", "Wall Door", "Tall Standard", "Tall Pantry"]


def _slide_label(slide: dict) -> str:
    return f"{slide['brand']} {slide['model']} ({int(slide['length'])}mm)"


def _slide_payload_from_id(slide_id: int | None) -> dict:
    if slide_id is None:
        return {}
    r = slide_lookup.get(slide_id)
    if not r:
        return {}
    return {
        "brand": str(r["brand"]),
        "model": str(r["model"]),
        "code": str(r["code"]),
        "length": int(r["length"]),
        "side_length": int(r["side_length"]),
        "side_clearance_total": int(r["side_clearance_total"]),
        "side_height_uplift": int(r.get("side_height_uplift", 0) or 0),
    }


def _slide_id_from_quote(quote: dict | None) -> int | None:
    if not slides or not quote:
        return slide_ids[0] if slide_ids else None
    brand = str(quote.get("default_slide_brand") or "")
    model = str(quote.get("default_slide_model") or "")
    code = str(quote.get("default_slide_code") or "")
    for s in slides:
        if str(s["brand"]) == brand and str(s["model"]) == model and str(s["code"]) == code:
            return int(s["id"])
    return slide_ids[0] if slide_ids else None


def _hinge_label(hinge: dict) -> str:
    return f"{hinge['brand']} {hinge['model']} ({int(hinge['opening_angle_deg'])}°)"


def _hinge_payload_from_id(hinge_id: int | None) -> dict:
    if hinge_id is None:
        return {}
    r = hinge_lookup.get(hinge_id)
    if not r:
        return {}
    return {
        "brand": str(r["brand"]),
        "model": str(r["model"]),
        "code": str(r["code"]),
        "opening_angle_deg": int(r["opening_angle_deg"]),
    }


def _hinge_id_from_quote(quote: dict | None) -> int | None:
    if not hinges or not quote:
        return hinge_ids[0] if hinge_ids else None
    brand = str(quote.get("default_hinge_brand") or "")
    model = str(quote.get("default_hinge_model") or "")
    code = str(quote.get("default_hinge_code") or "")
    for h in hinges:
        if str(h["brand"]) == brand and str(h["model"]) == model and str(h["code"]) == code:
            return int(h["id"])
    return hinge_ids[0] if hinge_ids else None


def _board_index_for_id(board_id: int | None) -> int:
    if board_id in board_ids:
        return board_ids.index(board_id)
    return 0

# ── Guard: must have an active project ────────────────────────────────────────
if "active_project_id" not in st.session_state or st.session_state.active_project_id is None:
    st.warning("No project selected. Please open a project first.")
    if st.button("← Back to Projects"):
        st.switch_page("pages/_Projects.py")
    st.stop()

project = get_project(st.session_state.active_project_id)
if project is None:
    st.error("Project not found.")
    st.session_state.active_project_id = None
    st.stop()

# ── Dialogs ────────────────────────────────────────────────────────────────────

@st.dialog(":material/add: New Quote", width="medium")
def new_quote_dialog():
    with st.form("new_quote_form", clear_on_submit=True):
        name = st.text_input("Quote Name *", placeholder="e.g. Kitchen Quote v1")
        notes = st.text_area("Notes", placeholder="Optional notes…")

        st.markdown("##### Default Boards")
        col_carcass, col_door = st.columns(2)
        with col_carcass:
            default_carcass_board_type_id = st.selectbox(
                "Default Carcass Board",
                board_ids,
                index=0,
                format_func=lambda bid: "— None —" if bid is None else _board_option_label(board_lookup[bid]),
            )
        with col_door:
            default_door_board_type_id = st.selectbox(
                "Default Door Board",
                board_ids,
                index=0,
                format_func=lambda bid: "— None —" if bid is None else _board_option_label(board_lookup[bid]),
            )

        st.markdown("##### Default Unit Dimensions")
        unit_defaults: dict[str, dict[str, int]] = {}
        for unit_key in UNIT_DEFAULT_KEYS:
            if unit_key == "Wall Door":
                default_h, default_d = 720, 330
            elif unit_key == "Tall Standard":
                default_h, default_d = 2100, 580
            elif unit_key == "Tall Pantry":
                default_h, default_d = 2400, 580
            else:
                default_h, default_d = 780, 580

            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.caption(unit_key)
            with c2:
                h = st.number_input(f"{unit_key} Height", min_value=1, value=default_h, key=f"new_{unit_key}_h", label_visibility="collapsed")
            with c3:
                d = st.number_input(f"{unit_key} Depth", min_value=1, value=default_d, key=f"new_{unit_key}_d", label_visibility="collapsed")
            unit_defaults[unit_key] = {"height": int(h), "depth": int(d)}

        st.markdown("##### Default Drawer Slide")
        default_slide_id = slide_ids[0] if slide_ids else None
        if not slides:
            st.info("No slides available yet. Add slides in Slides Library to set a default.")
        else:
            default_slide_id = st.selectbox(
                "Default Slide",
                slide_ids,
                index=0,
                format_func=lambda sid: _slide_label(slide_lookup[sid]),
                key="new_quote_default_slide",
            )

        st.markdown("##### Default Door Hinge")
        default_hinge_id = hinge_ids[0] if hinge_ids else None
        if not hinges:
            st.info("No hinges available yet. Add hinges in Hinges Library to set a default.")
        else:
            default_hinge_id = st.selectbox(
                "Default Hinge",
                hinge_ids,
                index=0,
                format_func=lambda hid: _hinge_label(hinge_lookup[hid]),
                key="new_quote_default_hinge",
            )

        if st.form_submit_button("Create Quote", use_container_width=True):
            if name.strip():
                create_quote(
                    project["id"],
                    name.strip(),
                    notes.strip(),
                    default_carcass_board_type_id=default_carcass_board_type_id,
                    default_door_board_type_id=default_door_board_type_id,
                    unit_defaults=unit_defaults,
                    default_slide=_slide_payload_from_id(default_slide_id),
                    default_hinge=_hinge_payload_from_id(default_hinge_id),
                )
                st.success(f"Quote '{name}' created!")
                st.rerun()
            else:
                st.error("Quote name is required.")


@st.dialog(":material/edit: Edit Quote", width="medium")
def edit_quote_dialog(quote: dict):
    with st.form("edit_quote_form"):
        name = st.text_input("Quote Name *", value=quote["name"])
        notes = st.text_area("Notes", value=quote["notes"])

        st.markdown("##### Default Boards")
        col_carcass, col_door = st.columns(2)
        with col_carcass:
            default_carcass_board_type_id = st.selectbox(
                "Default Carcass Board",
                board_ids,
                index=_board_index_for_id(quote.get("default_carcass_board_type_id")),
                format_func=lambda bid: "— None —" if bid is None else _board_option_label(board_lookup[bid]),
                key=f"edit_quote_carcass_{quote['id']}",
            )
        with col_door:
            default_door_board_type_id = st.selectbox(
                "Default Door Board",
                board_ids,
                index=_board_index_for_id(quote.get("default_door_board_type_id")),
                format_func=lambda bid: "— None —" if bid is None else _board_option_label(board_lookup[bid]),
                key=f"edit_quote_door_{quote['id']}",
            )

        st.markdown("##### Default Unit Dimensions")
        existing_defaults = quote.get("unit_defaults", {}) or {}
        unit_defaults: dict[str, dict[str, int]] = {}
        for unit_key in UNIT_DEFAULT_KEYS:
            fallback_h = 720 if unit_key == "Wall Door" else (2100 if unit_key == "Tall Standard" else (2400 if unit_key == "Tall Pantry" else 780))
            fallback_d = 330 if unit_key == "Wall Door" else 580
            current = existing_defaults.get(unit_key, {})

            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.caption(unit_key)
            with c2:
                h = st.number_input(
                    f"{unit_key} Height",
                    min_value=1,
                    value=int(current.get("height", fallback_h)),
                    key=f"edit_{quote['id']}_{unit_key}_h",
                    label_visibility="collapsed",
                )
            with c3:
                d = st.number_input(
                    f"{unit_key} Depth",
                    min_value=1,
                    value=int(current.get("depth", fallback_d)),
                    key=f"edit_{quote['id']}_{unit_key}_d",
                    label_visibility="collapsed",
                )
            unit_defaults[unit_key] = {"height": int(h), "depth": int(d)}

        st.markdown("##### Default Drawer Slide")
        default_slide_id = slide_ids[0] if slide_ids else None
        if not slides:
            st.info("No slides available yet. Add slides in Slides Library to set a default.")
        else:
            resolved_slide_id = _slide_id_from_quote(quote)
            default_index = slide_ids.index(resolved_slide_id) if resolved_slide_id in slide_ids else 0
            default_slide_id = st.selectbox(
                "Default Slide",
                slide_ids,
                index=default_index,
                format_func=lambda sid: _slide_label(slide_lookup[sid]),
                key=f"edit_quote_default_slide_{quote['id']}",
            )

        st.markdown("##### Default Door Hinge")
        default_hinge_id = hinge_ids[0] if hinge_ids else None
        if not hinges:
            st.info("No hinges available yet. Add hinges in Hinges Library to set a default.")
        else:
            resolved_hinge_id = _hinge_id_from_quote(quote)
            default_hinge_index = hinge_ids.index(resolved_hinge_id) if resolved_hinge_id in hinge_ids else 0
            default_hinge_id = st.selectbox(
                "Default Hinge",
                hinge_ids,
                index=default_hinge_index,
                format_func=lambda hid: _hinge_label(hinge_lookup[hid]),
                key=f"edit_quote_default_hinge_{quote['id']}",
            )

        col_save, col_del = st.columns(2)
        with col_save:
            if st.form_submit_button(":material/save: Save Changes", use_container_width=True):
                if name.strip():
                    update_quote(
                        quote["id"],
                        name.strip(),
                        notes.strip(),
                        default_carcass_board_type_id=default_carcass_board_type_id,
                        default_door_board_type_id=default_door_board_type_id,
                        unit_defaults=unit_defaults,
                        default_slide=_slide_payload_from_id(default_slide_id),
                        default_hinge=_hinge_payload_from_id(default_hinge_id),
                    )
                    st.success("Quote updated!")
                    st.rerun()
                else:
                    st.error("Quote name is required.")
        with col_del:
            if st.form_submit_button(":material/delete: Delete Quote", use_container_width=True,
                                     type="secondary"):
                delete_quote(quote["id"])
                if st.session_state.get("active_quote_id") == quote["id"]:
                    st.session_state.active_quote_id = None
                st.rerun()


# ── Page header ────────────────────────────────────────────────────────────────

col_back, col_title = st.columns([1, 6])
with col_back:
    if st.button("← Projects"):
        st.switch_page("pages/_Projects.py")
with col_title:
    st.title(f":material/folder: {project['name']}")

if project["client"]:
    st.caption(f":material/person: {project['client']}")
if project.get("address"):
    st.caption(f":material/location_on: {project['address']}")
if project["description"]:
    st.caption(project["description"])

st.divider()

col_sub, col_btn = st.columns([4, 1])
with col_sub:
    st.subheader("Quotes")
with col_btn:
    if st.button(":material/add: New Quote", use_container_width=True, type="primary"):
        new_quote_dialog()

# ── Quote list ─────────────────────────────────────────────────────────────────

quotes = get_quotes_for_project(project["id"])

if not quotes:
    st.info("No quotes yet. Click **:material/add: New Quote** to get started.")
else:
    for q in quotes:
        units = get_units_for_quote(q["id"])
        unit_count = len(units)

        with st.container(border=True):
            col_info, col_open, col_edit = st.columns([5, 1, 1])
            with col_info:
                st.markdown(f"### {q['name']}")
                if q["notes"]:
                    st.caption(q["notes"])
                st.caption(
                    f":material/build: {unit_count} unit{'s' if unit_count != 1 else ''}  •  Created {q['created_at'][:10]}"
                )
            with col_open:
                if st.button("Open", key=f"open_q_{q['id']}", use_container_width=True,
                             type="primary"):
                    st.session_state.active_quote_id = q["id"]
                    st.switch_page("pages/_QuoteDetail.py")
            with col_edit:
                if st.button("Edit", key=f"edit_q_{q['id']}", use_container_width=True):
                    edit_quote_dialog(q)
