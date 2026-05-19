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
    get_all_handles,
)
from ui.formatters import format_board_label, format_slide_label, format_hinge_label, format_handle_label
from ui.selectors import (
    board_index_for_id as selector_board_index_for_id,
    slide_payload_from_id as selector_slide_payload_from_id,
    hinge_payload_from_id as selector_hinge_payload_from_id,
    handle_payload_from_id as selector_handle_payload_from_id,
    slide_id_from_quote as selector_slide_id_from_quote,
    hinge_id_from_quote as selector_hinge_id_from_quote,
    handle_id_from_quote as selector_handle_id_from_quote,
)


board_types = get_all_board_types()
board_ids = [None] + [b["id"] for b in board_types]
board_lookup = {b["id"]: b for b in board_types}
slides = get_all_slides()
slide_ids = [s["id"] for s in slides]
slide_lookup = {s["id"]: s for s in slides}
hinges = get_all_hinges()
hinge_ids = [h["id"] for h in hinges]
hinge_lookup = {h["id"]: h for h in hinges}
handles = get_all_handles()
handle_ids = [h["id"] for h in handles]
handle_lookup = {h["id"]: h for h in handles}

UNIT_DEFAULT_LABEL_TO_KEY = {
    "Base Drawer": "Base Drawer",
    "Base Door": "Base Door",
    "Wall Door": "Wall Door",
    "Tall Door": "Tall Standard",
}
UNIT_DEFAULT_ITEMS = list(UNIT_DEFAULT_LABEL_TO_KEY.items())


def _board_option_label(board: dict) -> str:
    return format_board_label(board)


def _slide_label(slide: dict) -> str:
    return format_slide_label(slide)


def _hinge_label(hinge: dict) -> str:
    return format_hinge_label(hinge)


def _handle_label(handle: dict) -> str:
    return format_handle_label(handle)


def _board_index_for_id(board_id: int | None) -> int:
    return selector_board_index_for_id(board_ids, board_id)


def _slide_payload_from_id(slide_id: int | None) -> dict:
    return selector_slide_payload_from_id(slide_lookup, slide_id)


def _hinge_payload_from_id(hinge_id: int | None) -> dict:
    return selector_hinge_payload_from_id(hinge_lookup, hinge_id)


def _handle_payload_from_id(handle_id: int | None) -> dict:
    return selector_handle_payload_from_id(handle_lookup, handle_id)


def _slide_id_from_quote(quote: dict | None) -> int | None:
    return selector_slide_id_from_quote(slides, slide_ids, quote)


def _hinge_id_from_quote(quote: dict | None) -> int | None:
    return selector_hinge_id_from_quote(hinges, hinge_ids, quote)


def _handle_id_from_quote(quote: dict | None, prefix: str) -> int | None:
    return selector_handle_id_from_quote(handles, handle_ids, quote, prefix)


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
        col_carcass, col_door, col_panel = st.columns(3)
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
        with col_panel:
            default_panel_board_type_id = st.selectbox(
                "Default Panel Board",
                board_ids,
                index=0,
                format_func=lambda bid: "— None —" if bid is None else _board_option_label(board_lookup[bid]),
            )

        st.markdown("##### Default Unit Dimensions")
        unit_defaults: dict[str, dict[str, int]] = {}
        for unit_label, unit_key in UNIT_DEFAULT_ITEMS:
            if unit_key == "Wall Door":
                default_h, default_d = 720, 330
            elif unit_key == "Tall Standard":
                default_h, default_d = 2100, 580
            else:
                default_h, default_d = 780, 580

            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.caption(unit_label)
            with c2:
                h = st.number_input(f"{unit_label} Height", min_value=1, value=default_h, key=f"new_{unit_key}_h", label_visibility="collapsed")
            with c3:
                d = st.number_input(f"{unit_label} Depth", min_value=1, value=default_d, key=f"new_{unit_key}_d", label_visibility="collapsed")
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

        st.markdown("##### Default Handles")
        if not handles:
            st.info("No handles available yet. Add handles in Handle Library to set defaults.")
            default_base_handle_id = None
            default_wall_handle_id = None
            default_tall_handle_id = None
            default_drawer_handle_id = None
        else:
            c1, c2 = st.columns(2)
            with c1:
                default_base_handle_id = st.selectbox(
                    "Base Unit Handle",
                    handle_ids,
                    index=0,
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key="new_quote_default_base_handle",
                )
                default_tall_handle_id = st.selectbox(
                    "Tall Unit Handle",
                    handle_ids,
                    index=0,
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key="new_quote_default_tall_handle",
                )
            with c2:
                default_wall_handle_id = st.selectbox(
                    "Wall Unit Handle",
                    handle_ids,
                    index=0,
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key="new_quote_default_wall_handle",
                )
                default_drawer_handle_id = st.selectbox(
                    "Drawer Handle",
                    handle_ids,
                    index=0,
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key="new_quote_default_drawer_handle",
                )

        if st.form_submit_button("Create Quote", use_container_width=True):
            if name.strip():
                create_quote(
                    project["id"],
                    name.strip(),
                    notes.strip(),
                    default_carcass_board_type_id=default_carcass_board_type_id,
                    default_door_board_type_id=default_door_board_type_id,
                    default_panel_board_type_id=default_panel_board_type_id,
                    unit_defaults=unit_defaults,
                    default_slide=_slide_payload_from_id(default_slide_id),
                    default_hinge=_hinge_payload_from_id(default_hinge_id),
                    default_base_handle=_handle_payload_from_id(default_base_handle_id),
                    default_wall_handle=_handle_payload_from_id(default_wall_handle_id),
                    default_tall_handle=_handle_payload_from_id(default_tall_handle_id),
                    default_drawer_handle=_handle_payload_from_id(default_drawer_handle_id),
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
        col_carcass, col_door, col_panel = st.columns(3)
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
        with col_panel:
            default_panel_board_type_id = st.selectbox(
                "Default Panel Board",
                board_ids,
                index=_board_index_for_id(quote.get("default_panel_board_type_id")),
                format_func=lambda bid: "— None —" if bid is None else _board_option_label(board_lookup[bid]),
                key=f"edit_quote_panel_{quote['id']}",
            )

        st.markdown("##### Default Unit Dimensions")
        existing_defaults = quote.get("unit_defaults", {}) or {}
        unit_defaults: dict[str, dict[str, int]] = {}
        for unit_label, unit_key in UNIT_DEFAULT_ITEMS:
            fallback_h = 720 if unit_key == "Wall Door" else (2100 if unit_key == "Tall Standard" else 780)
            fallback_d = 330 if unit_key == "Wall Door" else 580
            current = existing_defaults.get(unit_key, {})

            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.caption(unit_label)
            with c2:
                h = st.number_input(
                    f"{unit_label} Height",
                    min_value=1,
                    value=int(current.get("height", fallback_h)),
                    key=f"edit_{quote['id']}_{unit_key}_h",
                    label_visibility="collapsed",
                )
            with c3:
                d = st.number_input(
                    f"{unit_label} Depth",
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

        st.markdown("##### Default Handles")
        if not handles:
            st.info("No handles available yet. Add handles in Handle Library to set defaults.")
            default_base_handle_id = None
            default_wall_handle_id = None
            default_tall_handle_id = None
            default_drawer_handle_id = None
        else:
            resolved_base_handle_id = _handle_id_from_quote(quote, "base")
            resolved_wall_handle_id = _handle_id_from_quote(quote, "wall")
            resolved_tall_handle_id = _handle_id_from_quote(quote, "tall")
            resolved_drawer_handle_id = _handle_id_from_quote(quote, "drawer")

            c1, c2 = st.columns(2)
            with c1:
                default_base_handle_id = st.selectbox(
                    "Base Unit Handle",
                    handle_ids,
                    index=handle_ids.index(resolved_base_handle_id) if resolved_base_handle_id in handle_ids else 0,
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key=f"edit_quote_default_base_handle_{quote['id']}",
                )
                default_tall_handle_id = st.selectbox(
                    "Tall Unit Handle",
                    handle_ids,
                    index=handle_ids.index(resolved_tall_handle_id) if resolved_tall_handle_id in handle_ids else 0,
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key=f"edit_quote_default_tall_handle_{quote['id']}",
                )
            with c2:
                default_wall_handle_id = st.selectbox(
                    "Wall Unit Handle",
                    handle_ids,
                    index=handle_ids.index(resolved_wall_handle_id) if resolved_wall_handle_id in handle_ids else 0,
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key=f"edit_quote_default_wall_handle_{quote['id']}",
                )
                default_drawer_handle_id = st.selectbox(
                    "Drawer Handle",
                    handle_ids,
                    index=handle_ids.index(resolved_drawer_handle_id) if resolved_drawer_handle_id in handle_ids else 0,
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key=f"edit_quote_default_drawer_handle_{quote['id']}",
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
                        default_panel_board_type_id=default_panel_board_type_id,
                        unit_defaults=unit_defaults,
                        default_slide=_slide_payload_from_id(default_slide_id),
                        default_hinge=_hinge_payload_from_id(default_hinge_id),
                        default_base_handle=_handle_payload_from_id(default_base_handle_id),
                        default_wall_handle=_handle_payload_from_id(default_wall_handle_id),
                        default_tall_handle=_handle_payload_from_id(default_tall_handle_id),
                        default_drawer_handle=_handle_payload_from_id(default_drawer_handle_id),
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

if st.button("← Projects"):
    st.switch_page("pages/_Projects.py")

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
