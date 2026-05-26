import streamlit as st
import sys
import os
import math

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import (
    get_project, get_quote,
    get_units_for_quote, add_unit, update_unit, delete_unit_and_renumber,
    update_quote_panels,
    get_all_board_types,
    get_all_slides,
    get_all_hinges,
    get_all_handles,
    get_all_extras,
    add_quote_extra,
    get_quote_extras,
    update_quote_extra,
    delete_quote_extra,
    get_active_price_list,
    get_price_list_items,
    upsert_price_list_item,
    get_pricing_settings,
    update_vat_rate_bps,
    update_default_markup_bps,
    update_quote_default_markup_bps,
    get_current_quote_pricing_run,
    get_quote_pricing_runs,
)
from logic.models import Slide
from logic.cutlist import build_cutlist
from logic.pdf_gen import generate_pdf
from logic.pricing import price_quote, get_required_price_items
from logic.panels import (
    PANEL_PRESET_KEYS,
    PANEL_PRESET_LABELS,
    PANEL_PRESET_UNIT_FAMILY,
    compute_panel_rows,
)

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
hinges = get_all_hinges()
hinge_ids = [h["id"] for h in hinges]
hinge_lookup = {h["id"]: h for h in hinges}
handles = get_all_handles()
handle_ids = [h["id"] for h in handles]
handle_lookup = {h["id"]: h for h in handles}
extras = get_all_extras()
extra_ids = [e["id"] for e in extras]
extra_lookup = {e["id"]: e for e in extras}
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


def _panel_state() -> dict:
    payload = quote.get("custom_panels", {}) or {}
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("presets", {})
    payload.setdefault("manual", [])
    payload.setdefault("auto", {})
    return payload


def _default_dims_for_panel_preset(key: str) -> tuple[int, int]:
    base_h, base_d = _default_dims_for_unit_type("Base Door")
    wall_h, wall_d = _default_dims_for_unit_type("Wall Door")
    tall_h, tall_d = _default_dims_for_unit_type("Tall Standard")

    if key == "base_side_panel":
        return int(base_h), int(base_d)
    if key == "base_side_filler":
        return int(base_h), 100
    if key == "wall_side_panel":
        return int(wall_h), int(wall_d)
    if key == "wall_side_filler":
        return int(wall_h), 100
    if key == "tall_side_panel":
        return int(tall_h), int(tall_d)
    if key == "tall_side_filler":
        return int(tall_h), 100
    return 0, 0


def _computed_panel_rows(units: list[dict], state: dict) -> list[dict]:
    return compute_panel_rows(
        units=units,
        state=state,
        default_panel_board_type_id=quote.get("default_panel_board_type_id"),
        panel_preset_keys=PANEL_PRESET_KEYS,
        panel_preset_labels=PANEL_PRESET_LABELS,
        default_dims_for_panel_preset=_default_dims_for_panel_preset,
        default_dims_for_unit_type=_default_dims_for_unit_type,
        board_length_for=lambda board_type_id: int((board_lookup.get(board_type_id) or {}).get("length_mm", 0)),
    )

# ── Unit Form + Add/Edit Dialogs ──────────────────────────────────────────────

UNIT_TYPE_LABEL_TO_KEY = {
    "Base Drawer": "Base Drawer",
    "Base Door": "Base Door",
    "Wall Door": "Wall Door",
    "Tall Door": "Tall Standard",
}
UNIT_TYPE_KEYS = list(UNIT_TYPE_LABEL_TO_KEY.values())
UNIT_TYPE_LABELS = list(UNIT_TYPE_LABEL_TO_KEY.keys())
UNIT_TYPE_KEY_TO_LABEL = {v: k for k, v in UNIT_TYPE_LABEL_TO_KEY.items()}


def _default_dims_for_unit_type(unit_type: str) -> tuple[int, int]:
    defaults = quote.get("unit_defaults", {}) or {}
    item = defaults.get(unit_type, {})

    if unit_type == "Wall Door":
        fallback_h, fallback_d = 720, 330
    elif unit_type == "Tall Standard":
        fallback_h, fallback_d = 2100, 580
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

    if unit_type == "Tall Door":
        return "Tall Standard", extra

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


def _get_hinge_id(extra: dict) -> int | None:
    if not hinges:
        return None
    brand = str(extra.get("hinge_brand", ""))
    model = str(extra.get("hinge_model", ""))
    code = str(extra.get("hinge_code", ""))
    for h in hinges:
        if str(h["brand"]) == brand and str(h["model"]) == model and str(h["code"]) == code:
            return int(h["id"])

    # Fall back to quote default hinge if available.
    q_brand = str(quote.get("default_hinge_brand", "") or "")
    q_model = str(quote.get("default_hinge_model", "") or "")
    q_code = str(quote.get("default_hinge_code", "") or "")
    for h in hinges:
        if str(h["brand"]) == q_brand and str(h["model"]) == q_model and str(h["code"]) == q_code:
            return int(h["id"])

    return hinge_ids[0] if hinge_ids else None


def _handle_label(row: dict) -> str:
    name = str(row.get("name", "")).strip()
    supplier = str(row.get("supplier", "")).strip()
    code = str(row.get("code", "")).strip()
    label = name or "Handle"
    if supplier:
        label += f" • {supplier}"
    if code:
        label += f" • {code}"
    return label


def _extra_label(row: dict) -> str:
    name = str(row.get("name", "")).strip()
    category = str(row.get("category_name", "")).strip()
    supplier = str(row.get("supplier", "")).strip()
    code = str(row.get("code", "")).strip()
    label = name or "Extra"
    if category:
        label += f" • {category}"
    if supplier:
        label += f" • {supplier}"
    if code:
        label += f" • {code}"
    return label


def _quote_extra_editor_df(quote_extra_rows: list[dict]):
    import pandas as pd

    rows = []
    for r in quote_extra_rows:
        rows.append(
            {
                "id": int(r["id"]),
                "extra_id": int(r["extra_id"]),
                "category": str(r.get("category_name", "")),
                "extra": str(r.get("extra_name", "")),
                "qty": int(r.get("qty", 1) or 1),
                "notes": str(r.get("notes", "") or ""),
            }
        )
    return pd.DataFrame(rows, columns=["id", "extra_id", "category", "extra", "qty", "notes"])


def _handle_from_quote(prefix: str) -> dict:
    return {
        "name": str(quote.get(f"default_{prefix}_handle_name") or ""),
        "supplier": str(quote.get(f"default_{prefix}_handle_supplier") or ""),
        "code": str(quote.get(f"default_{prefix}_handle_code") or ""),
    }


def _handle_id_by_payload(payload: dict | None) -> int | None:
    payload = payload or {}
    if not handles:
        return None
    name = str(payload.get("name") or "")
    supplier = str(payload.get("supplier") or "")
    code = str(payload.get("code") or "")
    for h in handles:
        if str(h["name"]) == name and str(h["supplier"]) == supplier and str(h["code"]) == code:
            return int(h["id"])
    return handle_ids[0] if handle_ids else None


def _handle_payload_from_id(handle_id: int | None) -> dict:
    if handle_id is None:
        return {}
    row = handle_lookup.get(handle_id)
    if not row:
        return {}
    return {
        "name": str(row.get("name", "")),
        "supplier": str(row.get("supplier", "")),
        "code": str(row.get("code", "")),
    }


def _default_drawer_face_ratios(num_drawers: int) -> list[float]:
    if num_drawers == 3:
        return [0.25, 0.25, 0.50]
    return [1.0 / num_drawers] * num_drawers


def _face_heights_from_ratios(height_mm: int, ratios: list[float], gap_mm: int = 3) -> list[int]:
    total_face_height = max(0, int(height_mm) - (gap_mm * len(ratios)))
    raw = [r * total_face_height for r in ratios]
    floors = [int(math.floor(v)) for v in raw]
    remainder = total_face_height - sum(floors)
    frac_order = sorted(range(len(ratios)), key=lambda i: (raw[i] - floors[i]), reverse=True)
    for i in range(remainder):
        floors[frac_order[i % len(ratios)]] += 1
    return floors


def unit_form(initial: dict | None = None, key_prefix: str = "add"):
    initial = initial or {}
    initial_type = str(initial.get("unit_type", UNIT_TYPE_KEYS[0]))
    initial_extra = initial.get("extra_params", {}) or {}
    normalized_type, normalized_extra = _normalize_unit_type_and_extra(initial_type, initial_extra)

    initial_carcass_board_id = initial.get("carcass_board_type_id")
    initial_door_board_id = initial.get("door_board_type_id")
    if initial_carcass_board_id is None:
        initial_carcass_board_id = quote.get("default_carcass_board_type_id")
    if initial_door_board_id is None:
        initial_door_board_id = quote.get("default_door_board_type_id")

    carcass_board_type_id = initial_carcass_board_id
    door_board_type_id = initial_door_board_id
    selected_carcass = board_lookup.get(carcass_board_type_id) if carcass_board_type_id is not None else None
    bt = int(selected_carcass["thickness"]) if selected_carcass else int(initial.get("thickness", 16))

    st.markdown("##### Unit Setup")
    default_type_key = normalized_type if normalized_type in UNIT_TYPE_KEYS else UNIT_TYPE_KEYS[0]
    default_type_label = UNIT_TYPE_KEY_TO_LABEL.get(default_type_key, "Base Drawer")
    type_index = UNIT_TYPE_LABELS.index(default_type_label) if default_type_label in UNIT_TYPE_LABELS else 0
    selected_type_label = st.selectbox("Unit Type", UNIT_TYPE_LABELS, index=type_index, key=f"{key_prefix}_type")
    ut = UNIT_TYPE_LABEL_TO_KEY[selected_type_label]

    default_h, default_d = _default_dims_for_unit_type(ut)
    col_w = st.columns(1)[0]
    ut_key_suffix = ut.lower().replace(" ", "_")
    with col_w:
        w = st.number_input(
            "Width (mm)",
            min_value=1,
            value=int(initial.get("width", 600)),
            key=f"{key_prefix}_width_{ut_key_suffix}",
        )

    extra = {}
    is_valid = True

    if ut == "Base Drawer":
        st.markdown("##### Drawer Options")
        num_drawers = st.selectbox(
            "Number of Drawers",
            [1, 2, 3, 4],
            index=max(0, min(3, int(normalized_extra.get("num_drawers", 3)) - 1)),
            key=f"{key_prefix}_num_drawers",
        )

        with st.expander("Overrides", expanded=False):
            st.caption("Preset-backed defaults from the quote. Change only when this unit must differ.")

            col_h, col_d = st.columns(2)
            with col_h:
                h = st.number_input(
                    "Height (mm)",
                    min_value=1,
                    value=int(initial.get("height", default_h)),
                    key=f"{key_prefix}_height_{ut_key_suffix}",
                )
            with col_d:
                d = st.number_input(
                    "Depth (mm)",
                    min_value=1,
                    value=int(initial.get("depth", default_d)),
                    key=f"{key_prefix}_depth_{ut_key_suffix}",
                )

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

            default_drawer_handle_payload = {
                "name": normalized_extra.get("drawer_handle_name", ""),
                "supplier": normalized_extra.get("drawer_handle_supplier", ""),
                "code": normalized_extra.get("drawer_handle_code", ""),
            }
            if not any(str(v).strip() for v in default_drawer_handle_payload.values()):
                default_drawer_handle_payload = _handle_from_quote("drawer")

            if not handles:
                st.warning("No handles available. Add handles in Handle Library.")
                is_valid = False
                selected_drawer_handle_id = None
            else:
                selected_drawer_handle_id = st.selectbox(
                    "Drawer Handle Type",
                    handle_ids,
                    index=(handle_ids.index(_handle_id_by_payload(default_drawer_handle_payload)) if _handle_id_by_payload(default_drawer_handle_payload) in handle_ids else 0),
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key=f"{key_prefix}_drawer_handle_id",
                    help="Uses quote default unless unit override is changed.",
                )

            drawer_handle_qty = st.number_input(
                "Handle Quantity Override",
                min_value=0,
                value=int(normalized_extra.get("handle_qty", int(num_drawers))),
                step=1,
                key=f"{key_prefix}_drawer_handle_qty",
                help="Default is one handle per drawer front.",
            )

        with st.expander("Advanced", expanded=False):
            st.markdown("###### Drawer Face Heights")
            stored_ratios = normalized_extra.get("drawer_face_ratios")
            if isinstance(stored_ratios, list) and len(stored_ratios) == int(num_drawers):
                base_ratios = [float(r) for r in stored_ratios]
            else:
                base_ratios = _default_drawer_face_ratios(int(num_drawers))

            ratio_mode_options = ["Equal", "Custom"]
            default_mode = "Custom" if isinstance(stored_ratios, list) else "Equal"
            if int(num_drawers) == 3 and not isinstance(stored_ratios, list):
                default_mode = "Custom"  # default 25/25/50 for 3-drawer units

            ratio_mode = st.radio(
                "Distribution Mode",
                ratio_mode_options,
                index=ratio_mode_options.index(default_mode),
                horizontal=True,
                key=f"{key_prefix}_drawer_ratio_mode",
                help="Equal = all fronts same height. Custom = choose each drawer's share.",
            )

            if ratio_mode == "Equal":
                drawer_face_ratios = [1.0 / int(num_drawers)] * int(num_drawers)
            else:
                st.caption("Set percentage per drawer from top to bottom. Total must equal 100%.")
                percent_values: list[float] = []
                for i in range(int(num_drawers)):
                    default_pct = round(base_ratios[i] * 100.0, 2)
                    percent_values.append(
                        float(
                            st.number_input(
                                f"Drawer {i+1} face %",
                                min_value=0.0,
                                max_value=100.0,
                                value=float(default_pct),
                                step=1.0,
                                key=f"{key_prefix}_drawer_face_pct_{i}",
                            )
                        )
                    )

                pct_sum = sum(percent_values)
                if pct_sum <= 0:
                    st.error("Drawer face percentages must add up to 100%.")
                    is_valid = False
                    drawer_face_ratios = _default_drawer_face_ratios(int(num_drawers))
                else:
                    drawer_face_ratios = [p / pct_sum for p in percent_values]
                    if abs(pct_sum - 100.0) > 0.01:
                        st.warning(f"Percentages currently total {pct_sum:.2f}%. They should total 100%.")
                        is_valid = False

            drawer_face_heights_manual = None
            st.caption("Optional: manually override drawer face heights in mm (top → bottom).")
            use_manual_heights = st.toggle(
                "Manually set drawer face heights",
                value=isinstance(normalized_extra.get("drawer_face_heights"), list),
                key=f"{key_prefix}_manual_face_heights_toggle",
            )

            if use_manual_heights:
                defaults = normalized_extra.get("drawer_face_heights")
                if not (isinstance(defaults, list) and len(defaults) == int(num_drawers)):
                    defaults = _face_heights_from_ratios(int(h), drawer_face_ratios)

                manual_vals: list[int] = []
                for i in range(int(num_drawers)):
                    manual_vals.append(
                        int(
                            st.number_input(
                                f"Drawer {i+1} face height (mm)",
                                min_value=1,
                                value=int(defaults[i]),
                                step=1,
                                key=f"{key_prefix}_drawer_face_mm_{i}",
                            )
                        )
                    )

                target_total = int(h) - (3 * int(num_drawers))
                manual_total = sum(manual_vals)
                if manual_total != target_total:
                    st.error(
                        f"Manual drawer face heights must total {target_total} mm (height minus 3mm gap per drawer). "
                        f"Current total: {manual_total} mm."
                    )
                    is_valid = False

                if any(v < 101 for v in manual_vals):
                    st.error("Each manual drawer face height must be at least 101mm.")
                    is_valid = False

                drawer_face_heights_manual = manual_vals

        preview_heights = drawer_face_heights_manual or _face_heights_from_ratios(int(h), drawer_face_ratios)
        st.caption(
            "Drawer face heights preview (top → bottom): "
            + " / ".join(f"{v}mm" for v in preview_heights)
        )

        if any(v < 101 for v in preview_heights):
            st.error("Each drawer face must be at least 101mm so carcass front/back can be face height - 100mm.")
            is_valid = False

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
            side_clearance_total=int(row["side_clearance_total"]),
            side_height_uplift=int(row.get("side_height_uplift", 0) or 0),
        )

        from logic.units import DrawerUnit
        test_unit = DrawerUnit(h=h, w=w, d=d, slide=slide,
                               num_drawers=num_drawers,
                               drawer_face_ratios=drawer_face_ratios,
                               drawer_face_heights=drawer_face_heights_manual,
                               thickness=bt)
        valid, err = test_unit.validate_slide()
        if not valid:
            st.error(err)
            is_valid = False

        extra = {
            "num_drawers": int(num_drawers),
            "drawer_face_ratios": [float(r) for r in drawer_face_ratios],
            "drawer_face_heights": drawer_face_heights_manual,
            "slide_brand": slide.brand,
            "slide_model": slide.model,
            "slide_code": str(slide.code),
            "slide_length": int(slide.length),
            "slide_side_length": int(slide.side_length),
            "slide_side_clearance_total": int(slide.side_clearance_total),
            "slide_side_height_uplift": int(slide.side_height_uplift),
            "handle_qty": int(drawer_handle_qty),
        }
        if selected_drawer_handle_id is not None:
            drawer_handle_row = handle_lookup[selected_drawer_handle_id]
            extra.update(
                {
                    "drawer_handle_name": str(drawer_handle_row.get("name", "")),
                    "drawer_handle_supplier": str(drawer_handle_row.get("supplier", "")),
                    "drawer_handle_code": str(drawer_handle_row.get("code", "")),
                }
            )

    elif ut in ("Base Door", "Wall Door", "Tall Standard"):
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
            default_shelves = 4 if ut == "Tall Standard" else 1
            num_shelves = st.number_input(
                "Number of Shelves",
                min_value=0,
                value=int(normalized_extra.get("num_shelves", default_shelves)),
                key=f"{key_prefix}_num_shelves",
            )

        with st.expander("Overrides", expanded=False):
            st.caption("Preset-backed defaults from the quote. Change only when this unit must differ.")

            col_h, col_d = st.columns(2)
            with col_h:
                h = st.number_input(
                    "Height (mm)",
                    min_value=1,
                    value=int(initial.get("height", default_h)),
                    key=f"{key_prefix}_height_{ut_key_suffix}",
                )
            with col_d:
                d = st.number_input(
                    "Depth (mm)",
                    min_value=1,
                    value=int(initial.get("depth", default_d)),
                    key=f"{key_prefix}_depth_{ut_key_suffix}",
                )

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

            if not hinges:
                st.warning("No hinges available. Add hinges in Hinges Library.")
                is_valid = False
                selected_hinge_id = None
            else:
                default_hinge_id = _get_hinge_id(normalized_extra)
                default_hinge_index = hinge_ids.index(default_hinge_id) if default_hinge_id in hinge_ids else 0
                selected_hinge_id = st.selectbox(
                    "Door Hinge",
                    hinge_ids,
                    index=default_hinge_index,
                    format_func=lambda hid: (
                        f'{hinge_lookup[hid]["brand"]} {hinge_lookup[hid]["model"]} '
                        f'({hinge_lookup[hid]["opening_angle_deg"]}°)'
                    ),
                    key=f"{key_prefix}_hinge_id",
                )

            handle_prefix = "base" if ut == "Base Door" else ("wall" if ut == "Wall Door" else "tall")
            default_door_handle_payload = {
                "name": normalized_extra.get("handle_name", ""),
                "supplier": normalized_extra.get("handle_supplier", ""),
                "code": normalized_extra.get("handle_code", ""),
            }
            if not any(str(v).strip() for v in default_door_handle_payload.values()):
                default_door_handle_payload = _handle_from_quote(handle_prefix)

            handle_qty = st.number_input(
                "Handle Quantity Override",
                min_value=0,
                value=int(normalized_extra.get("handle_qty", int(num_doors))),
                step=1,
                key=f"{key_prefix}_door_handle_qty",
                help="Default is one handle per door.",
            )
            if not handles:
                st.warning("No handles available. Add handles in Handle Library.")
                is_valid = False
                selected_door_handle_id = None
            else:
                selected_door_handle_id = st.selectbox(
                    "Handle Type",
                    handle_ids,
                    index=(handle_ids.index(_handle_id_by_payload(default_door_handle_payload)) if _handle_id_by_payload(default_door_handle_payload) in handle_ids else 0),
                    format_func=lambda hid: _handle_label(handle_lookup[hid]),
                    key=f"{key_prefix}_door_handle_id",
                )

        extra = {"num_doors": int(num_doors), "num_shelves": int(num_shelves)}

        with st.expander("Advanced", expanded=False):
            st.caption("Additional controls for less common adjustments.")

        extra["handle_qty"] = int(handle_qty)

        if selected_door_handle_id is not None:
            door_handle_row = handle_lookup[selected_door_handle_id]
            extra.update(
                {
                    "handle_name": str(door_handle_row.get("name", "")),
                    "handle_supplier": str(door_handle_row.get("supplier", "")),
                    "handle_code": str(door_handle_row.get("code", "")),
                }
            )
        if selected_hinge_id is not None:
            hinge_row = hinge_lookup[selected_hinge_id]
            extra.update(
                {
                    "hinge_brand": str(hinge_row["brand"]),
                    "hinge_model": str(hinge_row["model"]),
                    "hinge_code": str(hinge_row["code"]),
                    "hinge_opening_angle_deg": int(hinge_row["opening_angle_deg"]),
                }
            )

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


@st.dialog(":material/add: Add Unit", width="medium")
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


@st.dialog(":material/edit: Edit Unit", width="medium")
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


def _compute_component_counts(units: list[dict]) -> list[dict]:
    """Aggregate hardware counts for the quote.

    Rules:
    - Slides: record as pairs (one pair per drawer)
    - Hinges: per door, one hinge for every 600mm of unit height, minimum 2 hinges per door
    """
    counts: dict[str, dict] = {}

    def _add_component(key: str, label: str, qty: int, unit_label: str):
        if qty <= 0:
            return
        if key not in counts:
            counts[key] = {"component": label, "qty": 0, "unit": unit_label}
        counts[key]["qty"] += int(qty)

    for u in units:
        extra = u.get("extra_params", {}) or {}
        utype = str(u.get("unit_type", ""))

        if "Draw" in utype:
            num_drawers = int(extra.get("num_drawers", 0) or 0)
            slide_brand = str(extra.get("slide_brand", "")).strip()
            slide_model = str(extra.get("slide_model", "")).strip()
            slide_code = str(extra.get("slide_code", "")).strip()
            slide_length = extra.get("slide_length")
            slide_label = " ".join(p for p in [slide_brand, slide_model] if p).strip() or "Slide"
            if slide_length:
                slide_label += f" ({slide_length}mm)"
            if slide_code:
                slide_label += f" • {slide_code}"
            slide_key = f"slide::{slide_brand}::{slide_model}::{slide_code}::{slide_length}"
            _add_component(slide_key, slide_label, num_drawers, "pairs")

        if ("Door" in utype) or ("Tall" in utype):
            num_doors = int(extra.get("num_doors", 0) or 0)
            height_mm = int(u.get("height", 0) or 0)
            hinges_per_door = max(2, math.ceil(height_mm / 600)) if height_mm > 0 else 2
            total_hinges = num_doors * hinges_per_door

            hinge_brand = str(extra.get("hinge_brand", "")).strip()
            hinge_model = str(extra.get("hinge_model", "")).strip()
            hinge_code = str(extra.get("hinge_code", "")).strip()
            hinge_angle = extra.get("hinge_opening_angle_deg")
            hinge_label = " ".join(p for p in [hinge_brand, hinge_model] if p).strip() or "Hinge"
            if hinge_angle:
                hinge_label += f" ({hinge_angle}°)"
            if hinge_code:
                hinge_label += f" • {hinge_code}"
            hinge_key = f"hinge::{hinge_brand}::{hinge_model}::{hinge_code}::{hinge_angle}"
            _add_component(hinge_key, hinge_label, total_hinges, "pcs")

        if "Draw" in utype:
            handle_qty = int(extra.get("handle_qty", extra.get("num_drawers", 0)) or 0)
            handle_name = str(extra.get("drawer_handle_name", "")).strip()
            handle_supplier = str(extra.get("drawer_handle_supplier", "")).strip()
            handle_code = str(extra.get("drawer_handle_code", "")).strip()
        else:
            handle_qty = int(extra.get("handle_qty", extra.get("num_doors", 0)) or 0)
            handle_name = str(extra.get("handle_name", "")).strip()
            handle_supplier = str(extra.get("handle_supplier", "")).strip()
            handle_code = str(extra.get("handle_code", "")).strip()

        if handle_qty > 0:
            handle_label = handle_name or "Handle"
            if handle_supplier:
                handle_label += f" • {handle_supplier}"
            if handle_code:
                handle_label += f" • {handle_code}"
            handle_key = f"handle::{handle_name}::{handle_supplier}::{handle_code}"
            _add_component(handle_key, handle_label, handle_qty, "pcs")

    rows = list(counts.values())
    rows.sort(key=lambda r: r["component"])
    return rows


# ── Page header ────────────────────────────────────────────────────────────────

if st.button("← Quotes"):
    st.switch_page("pages/_Quotes.py")

proj_label = f"{project['name']} › " if project else ""
st.title(f":material/description: {proj_label}{quote['name']}")

if quote["notes"]:
    st.caption(quote["notes"])

st.divider()

units = get_units_for_quote(quote["id"])

tab_units, tab_panels, tab_cutting, tab_components, tab_pricing, tab_extras = st.tabs([
    "Units",
    "Panels",
    "Cutting List",
    "Component Count",
    "Pricing",
    "Extras",
])

with tab_units:
    col_sub, col_add = st.columns([4, 1])
    with col_sub:
        st.subheader("Units")
    with col_add:
        if st.button(":material/add: Add Unit", use_container_width=True, type="primary"):
            add_unit_dialog()

    if not units:
        st.info("No units yet. Click **:material/add: Add Unit** to begin building this quote.")
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
                        drawer_handle_label = "Handle"
                        if extra.get("drawer_handle_name"):
                            drawer_handle_label = str(extra.get("drawer_handle_name"))
                        if extra.get("drawer_handle_supplier"):
                            drawer_handle_label += f" • {extra.get('drawer_handle_supplier')}"
                        if extra.get("drawer_handle_code"):
                            drawer_handle_label += f" • {extra.get('drawer_handle_code')}"
                        st.caption(f"Handles: {extra.get('handle_qty', extra.get('num_drawers', '?'))}  •  Type: {drawer_handle_label}")
                    elif ("Door" in u["unit_type"]) or ("Tall" in u["unit_type"]):
                        hinge_label = (
                            f"{extra.get('hinge_brand', '')} {extra.get('hinge_model', '')} "
                            f"({extra.get('hinge_opening_angle_deg', '')}°)"
                        )
                        st.caption(
                            f"Doors: {extra.get('num_doors', '?')}  •  "
                            f"Shelves: {extra.get('num_shelves', '?')}  •  "
                            f"Hinge: {hinge_label}"
                        )
                        door_handle_label = "Handle"
                        if extra.get("handle_name"):
                            door_handle_label = str(extra.get("handle_name"))
                        if extra.get("handle_supplier"):
                            door_handle_label += f" • {extra.get('handle_supplier')}"
                        if extra.get("handle_code"):
                            door_handle_label += f" • {extra.get('handle_code')}"
                        st.caption(f"Handles: {extra.get('handle_qty', extra.get('num_doors', '?'))}  •  Type: {door_handle_label}")
                with col_actions:
                    act_edit, act_del = st.columns(2)
                    with act_edit:
                        if st.button(":material/edit:", key=f"edit_unit_{u['id']}", help="Edit this unit", use_container_width=True):
                            edit_unit_dialog(u)
                    with act_del:
                        if st.button(":material/delete:", key=f"del_unit_{u['id']}", help="Remove this unit",
                                     use_container_width=True):
                            delete_unit_and_renumber(u["id"])
                            st.rerun()

with tab_cutting:
    st.subheader(":material/straighten: Cutting List")
    if not units:
        st.info("Add units to generate a cutting list.")
    else:
        carcass_df, panels_df = build_cutlist(units)
        panel_rows = _computed_panel_rows(units, _panel_state())
        custom_panels_df = None
        if panel_rows:
            import pandas as pd
            custom_panels_df = pd.DataFrame(panel_rows, columns=["Desc", "L", "W", "Qty", "board_type_id"])
            custom_panels_df = custom_panels_df[["Desc", "L", "W", "Qty"]]

        col_c, col_p = st.columns(2)
        with col_c:
            st.write("**Carcass Boards**")
            st.dataframe(carcass_df, use_container_width=True, hide_index=True)
        with col_p:
            st.write("**Doors / Drawer Fronts**")
            st.dataframe(panels_df, use_container_width=True, hide_index=True)

        st.write("**Panels (Side Panels, Fillers, Kickers, Pelmets, Custom Panels)**")
        if custom_panels_df is not None and not custom_panels_df.empty:
            st.dataframe(custom_panels_df, use_container_width=True, hide_index=True)
        else:
            st.info("No panel rows configured yet.")

        # PDF export
        proj_name = project["name"] if project else ""
        pdf_panels_df = panels_df
        if custom_panels_df is not None and not custom_panels_df.empty:
            import pandas as pd
            pdf_panels_df = pd.concat([panels_df, custom_panels_df], ignore_index=True)

        pdf_bytes = generate_pdf(
            carcass_df, pdf_panels_df,
            project_name=proj_name,
            quote_name=quote["name"]
        )
        safe_name = quote["name"].replace(" ", "_").lower()
        st.download_button(
            label=":material/download: Download Cutting List PDF",
            data=bytes(pdf_bytes),
            file_name=f"cutlist_{safe_name}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

with tab_components:
    st.subheader(":material/hardware: Component Count")
    if not units:
        st.info("Add units to calculate component counts.")
    else:
        component_rows = _compute_component_counts(units)
        if not component_rows:
            st.info("No slide, hinge, or handle data found for the units in this quote.")
        else:
            st.dataframe(component_rows, use_container_width=True, hide_index=True)
        st.caption("Slides are recorded as pairs. Hinges are calculated per door at 1 per 600mm of height (minimum 2 per door). Handles use each unit's stored handle quantity.")

with tab_panels:
    st.subheader(":material/view_in_ar: Panels")
    panel_state = _panel_state()
    panel_presets = panel_state.get("presets", {}) or {}
    panel_auto = panel_state.get("auto", {}) or {}
    panel_manual = panel_state.get("manual", []) or []
    default_panel_board_type_id = quote.get("default_panel_board_type_id")
    base_unit_count = sum(1 for u in units if "Base" in str(u.get("unit_type", "")))
    wall_unit_count = sum(1 for u in units if "Wall" in str(u.get("unit_type", "")))
    tall_unit_count = sum(1 for u in units if "Tall" in str(u.get("unit_type", "")))
    family_counts = {"base": base_unit_count, "wall": wall_unit_count, "tall": tall_unit_count}

    st.caption("Preset panel rows are included in all quotes. Side fillers default to 100mm wide.")
    for key in PANEL_PRESET_KEYS:
        current = panel_presets.get(key, {}) if isinstance(panel_presets.get(key, {}), dict) else {}
        l_mm, w_mm = _default_dims_for_panel_preset(key)
        family = PANEL_PRESET_UNIT_FAMILY.get(key, "base")
        auto_qty = 1 if family_counts.get(family, 0) > 0 else 0
        c1, c2, c3, c4 = st.columns([3, 1, 1, 3])
        with c1:
            st.write(PANEL_PRESET_LABELS[key])
        with c2:
            qty = st.number_input(
                f"{PANEL_PRESET_LABELS[key]} Quantity",
                min_value=0,
                value=int(current.get("qty", auto_qty) if current.get("qty") is not None else auto_qty),
                step=1,
                key=f"panel_preset_qty_{key}",
            )
        with c3:
            st.caption(f"{l_mm} × {w_mm}")
        with c4:
            bid = st.selectbox(
                f"{key}_board",
                board_ids,
                index=_board_index_for_id(current.get("board_type_id", default_panel_board_type_id)),
                format_func=_board_option_label,
                key=f"panel_preset_board_{key}",
                label_visibility="collapsed",
            )
        panel_presets[key] = {"qty": int(qty), "board_type_id": bid}

    st.divider()
    st.markdown("##### Auto Panels")
    c1, c2 = st.columns(2)
    with c1:
        kicker_board_type_id = st.selectbox(
            "Kicker Board Type",
            board_ids,
            index=_board_index_for_id(panel_auto.get("kicker_board_type_id", default_panel_board_type_id)),
            format_func=_board_option_label,
            key="panel_auto_kicker_board",
        )
    with c2:
        pelmet_board_type_id = st.selectbox(
            "Wall Pelmet Board Type",
            board_ids,
            index=_board_index_for_id(panel_auto.get("pelmet_board_type_id", default_panel_board_type_id)),
            format_func=_board_option_label,
            key="panel_auto_pelmet_board",
        )
    panel_auto["kicker_board_type_id"] = kicker_board_type_id
    panel_auto["pelmet_board_type_id"] = pelmet_board_type_id

    k1, p1 = st.columns(2)
    with k1:
        kicker_override_on = st.toggle("Override Kicker", value=bool(panel_auto.get("kicker_override_on", False)), key="panel_kicker_override_on")
    with p1:
        pelmet_override_on = st.toggle("Override Wall Pelmet", value=bool(panel_auto.get("pelmet_override_on", False)), key="panel_pelmet_override_on")

    kicker_override_qty = int(panel_auto.get("kicker_override_qty", 1) or 1)
    kicker_override_length = int(panel_auto.get("kicker_override_length", 0) or 0)
    kicker_override_width = int(panel_auto.get("kicker_override_width", 100) or 100)
    if kicker_override_on:
        k2, k3, k4 = st.columns(3)
        with k2:
            kicker_override_qty = st.number_input("Kicker Qty", min_value=0, value=kicker_override_qty, key="panel_kicker_override_qty")
        with k3:
            kicker_override_length = st.number_input("Kicker Length (mm)", min_value=0, value=kicker_override_length, key="panel_kicker_override_length")
        with k4:
            kicker_override_width = st.number_input("Kicker Width (mm)", min_value=0, value=kicker_override_width, key="panel_kicker_override_width")

    pelmet_default_w = _default_dims_for_unit_type("Wall Door")[1]
    pelmet_override_qty = int(panel_auto.get("pelmet_override_qty", 1) or 1)
    pelmet_override_length = int(panel_auto.get("pelmet_override_length", 0) or 0)
    pelmet_override_width = int(panel_auto.get("pelmet_override_width", pelmet_default_w) or pelmet_default_w)
    if pelmet_override_on:
        p2, p3, p4 = st.columns(3)
        with p2:
            pelmet_override_qty = st.number_input("Wall Pelmet Qty", min_value=0, value=pelmet_override_qty, key="panel_pelmet_override_qty")
        with p3:
            pelmet_override_length = st.number_input("Wall Pelmet Length (mm)", min_value=0, value=pelmet_override_length, key="panel_pelmet_override_length")
        with p4:
            pelmet_override_width = st.number_input("Wall Pelmet Width (mm)", min_value=0, value=pelmet_override_width, key="panel_pelmet_override_width")

    panel_auto.update(
        {
            "kicker_override_on": bool(kicker_override_on),
            "kicker_override_qty": int(kicker_override_qty),
            "kicker_override_length": int(kicker_override_length),
            "kicker_override_width": int(kicker_override_width),
            "pelmet_override_on": bool(pelmet_override_on),
            "pelmet_override_qty": int(pelmet_override_qty),
            "pelmet_override_length": int(pelmet_override_length),
            "pelmet_override_width": int(pelmet_override_width),
        }
    )

    st.divider()
    st.markdown("##### Custom Panels")

    manual_state_key = f"panel_manual_edit_{quote['id']}"
    if manual_state_key not in st.session_state:
        st.session_state[manual_state_key] = [dict(r) for r in panel_manual if isinstance(r, dict)]
    if st.button(":material/add: Add Custom Panel Row", key="add_custom_panel_row"):
        st.session_state[manual_state_key].append(
            {"name": "Custom Panel", "length": 0, "width": 0, "qty": 1, "board_type_id": default_panel_board_type_id}
        )
        st.rerun()

    manual_rows: list[dict] = st.session_state[manual_state_key]
    delete_idx: int | None = None
    updated_manual: list[dict] = []

    if not manual_rows:
        st.info("No custom rows yet. Click Add Custom Panel Row.")

    for i, row in enumerate(manual_rows):
        c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 1, 3, 1])
        with c1:
            name = st.text_input(f"Name (Row {i+1})", value=str(row.get("name", "Custom Panel")), key=f"manual_panel_name_{i}")
        with c2:
            l_mm = st.number_input(f"Length (mm) #{i+1}", min_value=0, value=int(row.get("length", 0) or 0), key=f"manual_panel_l_{i}")
        with c3:
            w_mm = st.number_input(f"Width (mm) #{i+1}", min_value=0, value=int(row.get("width", 0) or 0), key=f"manual_panel_w_{i}")
        with c4:
            qty = st.number_input(f"Qty #{i+1}", min_value=0, value=int(row.get("qty", 1) or 1), key=f"manual_panel_qty_{i}")
        with c5:
            bid = st.selectbox(
                f"Board Type #{i+1}",
                board_ids,
                index=_board_index_for_id(row.get("board_type_id", default_panel_board_type_id)),
                format_func=_board_option_label,
                key=f"manual_panel_board_{i}",
            )
        with c6:
            st.write("")
            if st.button(":material/delete:", key=f"del_manual_panel_{i}", help="Delete this row"):
                delete_idx = i

        updated_manual.append({"name": name, "length": int(l_mm), "width": int(w_mm), "qty": int(qty), "board_type_id": bid})

    if delete_idx is not None:
        if 0 <= delete_idx < len(updated_manual):
            updated_manual.pop(delete_idx)
        st.session_state[manual_state_key] = updated_manual
        st.rerun()

    st.session_state[manual_state_key] = updated_manual

    preview_rows = _computed_panel_rows(units, {"presets": panel_presets, "auto": panel_auto, "manual": updated_manual})
    if preview_rows:
        import pandas as pd
        preview_df = pd.DataFrame(preview_rows, columns=["Desc", "L", "W", "Qty", "board_type_id"])
        preview_df["Board"] = preview_df["board_type_id"].apply(_board_option_label)
        st.dataframe(preview_df[["Desc", "L", "W", "Qty", "Board"]], use_container_width=True, hide_index=True)
    else:
        st.info("No panel rows currently active.")

    if st.button(":material/save: Save Panels", type="primary", use_container_width=True):
        payload = {
            "presets": panel_presets,
            "auto": panel_auto,
            "manual": [r for r in updated_manual if int(r.get("length", 0)) > 0 and int(r.get("width", 0)) > 0 and int(r.get("qty", 0)) > 0],
        }
        update_quote_panels(quote["id"], payload)
        st.session_state[manual_state_key] = payload["manual"]
        st.success("Panels saved.")
        st.rerun()


with tab_pricing:
    st.subheader(":material/payments: Pricing")

    active_price_list = get_active_price_list()
    if not active_price_list:
        st.error("No active price list available. Please create one first.")
    else:
        st.caption(f"Using active price list: **{active_price_list['name']}**")

        settings = get_pricing_settings()
        vat_pct_default = float(int(settings.get("vat_rate_bps", 1500) or 1500) / 100.0)

        global_markup_pct_default = float(int(settings.get("default_markup_bps", 2500) or 2500) / 100.0)
        quote_markup_pct_default = float(
            int(quote.get("default_markup_bps", settings.get("default_markup_bps", 2500)) or settings.get("default_markup_bps", 2500)) / 100.0
        )

        c_vat, c_global_markup, c_quote_markup = st.columns(3)
        with c_vat:
            vat_pct = st.number_input("VAT %", min_value=0.0, max_value=100.0, value=vat_pct_default, step=0.1)
            if st.button("Save VAT", use_container_width=True):
                update_vat_rate_bps(int(round(vat_pct * 100.0)))
                st.success("VAT updated.")
                st.rerun()
        with c_global_markup:
            global_markup_pct = st.number_input(
                "Global Default Markup %",
                min_value=0.0,
                max_value=500.0,
                value=global_markup_pct_default,
                step=0.5,
                help="Applied by default to new/updated quotes unless quote override is set.",
            )
            if st.button("Save Global Markup", use_container_width=True):
                update_default_markup_bps(int(round(global_markup_pct * 100.0)))
                st.success("Global default markup updated.")
                st.rerun()
        with c_quote_markup:
            quote_markup_pct = st.number_input(
                "This Quote Markup %",
                min_value=0.0,
                max_value=500.0,
                value=quote_markup_pct_default,
                step=0.5,
                help="This quote's default markup. Used when you click Price Quote.",
            )
            if st.button("Save Quote Markup", use_container_width=True):
                update_quote_default_markup_bps(int(quote["id"]), int(round(quote_markup_pct * 100.0)))
                st.success("Quote default markup updated.")
                st.rerun()

        required_items = get_required_price_items(int(quote["id"]))
        missing_items = [r for r in required_items if r.unit_price_cents is None]

        st.markdown("##### Missing Prices")
        if not missing_items:
            st.success("All required quote items have cost prices.")
        else:
            st.warning(f"{len(missing_items)} required item(s) still need pricing.")
            st.dataframe(
                [
                    {
                        "Type": r.item_type,
                        "Description": r.description,
                        "Item Key": r.item_key,
                        "UOM": r.uom,
                        "Qty Required": r.qty_required,
                    }
                    for r in missing_items
                ],
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("##### Cost Price Editor")
        if not required_items:
            st.info("No pricing-relevant items found yet. Add units/extras first.")
        else:
            import pandas as pd

            price_df = pd.DataFrame(
                [
                    {
                        "item_type": r.item_type,
                        "description": r.description,
                        "item_key": r.item_key,
                        "uom": r.uom,
                        "qty_required": float(r.qty_required),
                        "unit_price": (float(r.unit_price_cents) / 100.0) if r.unit_price_cents is not None else 0.0,
                    }
                    for r in required_items
                ]
            )

            edited_prices = st.data_editor(
                price_df,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key=f"pricing_editor_{quote['id']}",
                column_config={
                    "item_type": st.column_config.TextColumn("Type", disabled=True),
                    "description": st.column_config.TextColumn("Description", disabled=True),
                    "item_key": st.column_config.TextColumn("Item Key", disabled=True),
                    "uom": st.column_config.TextColumn("UOM", disabled=True),
                    "qty_required": st.column_config.NumberColumn("Qty Required", disabled=True),
                    "unit_price": st.column_config.NumberColumn("Cost Price", min_value=0.0, step=1.0, format="%.2f"),
                },
            )

            if st.button("Save Cost Prices", type="primary", use_container_width=True):
                for _, row in edited_prices.iterrows():
                    upsert_price_list_item(
                        price_list_id=int(active_price_list["id"]),
                        item_type=str(row["item_type"]),
                        item_key=str(row["item_key"]),
                        uom=str(row["uom"]),
                        unit_price_cents=int(round(float(row["unit_price"]) * 100.0)),
                    )
                st.success("Cost prices saved.")
                st.rerun()

        st.divider()
        st.markdown("##### Quote Pricing")
        st.caption("Pricing uses global cost prices and applies this quote's default markup.")
        if st.button(":material/calculate: Price Quote", type="primary", use_container_width=True):
            try:
                result = price_quote(
                    quote_id=int(quote["id"]),
                    pricing_mode="markup",
                    pricing_value_percent=float(quote_markup_pct),
                )
                st.success(f"Pricing run saved (Run #{result.run_id}).")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        current_run = get_current_quote_pricing_run(int(quote["id"]))
        if current_run:
            st.markdown("##### Current Totals")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Subtotal", f"R {int(current_run['subtotal_cents']) / 100:,.2f}")
            c2.metric("Sell Ex VAT", f"R {int(current_run['sell_before_vat_cents']) / 100:,.2f}")
            c3.metric("VAT", f"R {int(current_run['vat_cents']) / 100:,.2f}")
            c4.metric("Grand Total", f"R {int(current_run['grand_total_cents']) / 100:,.2f}")

        history = get_quote_pricing_runs(int(quote["id"]))
        if history:
            st.markdown("##### Pricing History")
            st.dataframe(
                [
                    {
                        "Run ID": int(r["id"]),
                        "Created": r.get("created_at", ""),
                        "Mode": r.get("pricing_mode", ""),
                        "Value %": float(int(r.get("pricing_value_bps", 0) or 0) / 100.0),
                        "VAT %": float(int(r.get("vat_rate_bps_snapshot", 0) or 0) / 100.0),
                        "Subtotal": float(int(r.get("subtotal_cents", 0) or 0) / 100.0),
                        "Grand Total": float(int(r.get("grand_total_cents", 0) or 0) / 100.0),
                        "Current": bool(int(r.get("is_current", 0) or 0)),
                    }
                    for r in history
                ],
                use_container_width=True,
                hide_index=True,
            )


with tab_extras:
    st.subheader(":material/inventory_2: Extras")

    if not extra_ids:
        st.info("No extras available yet. Add categories and extras in the library first.")
    else:
        with st.expander(":material/add: Add Extra to Quote", expanded=False):
            with st.form("add_quote_extra_form", clear_on_submit=True):
                new_extra_id = st.selectbox(
                    "Extra",
                    extra_ids,
                    index=0,
                    format_func=lambda eid: _extra_label(extra_lookup[eid]),
                )
                new_qty = st.number_input("Quantity", min_value=1, value=1, step=1)
                new_notes = st.text_area("Line Notes", placeholder="Optional note for this quote line")
                if st.form_submit_button("Add Extra", use_container_width=True, type="primary"):
                    add_quote_extra(quote_id=int(quote["id"]), extra_id=int(new_extra_id), qty=int(new_qty), notes=str(new_notes))
                    st.success("Extra added to quote.")
                    st.rerun()

    quote_extra_rows = get_quote_extras(int(quote["id"]))
    if not quote_extra_rows:
        st.info("No extras on this quote yet.")
    else:
        quote_extra_df = _quote_extra_editor_df(quote_extra_rows)

        edited_df = st.data_editor(
            quote_extra_df,
            num_rows="fixed",
            use_container_width=True,
            hide_index=True,
            key=f"quote_extras_editor_{quote['id']}",
            column_config={
                "id": st.column_config.NumberColumn("Line ID", disabled=True),
                "extra_id": st.column_config.SelectboxColumn("Extra", options=extra_ids, required=True, format_func=lambda eid: _extra_label(extra_lookup[eid])),
                "category": st.column_config.TextColumn("Category", disabled=True),
                "extra": st.column_config.TextColumn("Extra Name", disabled=True),
                "qty": st.column_config.NumberColumn("Qty", min_value=1, required=True),
                "notes": st.column_config.TextColumn("Notes"),
            },
        )

        # keep category/name columns in sync with selected extra
        for i, row in edited_df.iterrows():
            eid = int(row["extra_id"])
            edited_df.at[i, "category"] = str(extra_lookup[eid].get("category_name", ""))
            edited_df.at[i, "extra"] = str(extra_lookup[eid].get("name", ""))

        if not edited_df.equals(quote_extra_df):
            st.warning(":material/warning: **Unsaved changes detected!**")
            if st.button(":material/save: Save Extras Changes", type="primary", use_container_width=True):
                original_ids = set(quote_extra_df["id"].astype(int).tolist())
                edited_ids = set(edited_df["id"].astype(int).tolist())

                for deleted_id in sorted(original_ids - edited_ids):
                    delete_quote_extra(int(deleted_id))

                for _, row in edited_df.iterrows():
                    update_quote_extra(
                        quote_extra_id=int(row["id"]),
                        extra_id=int(row["extra_id"]),
                        qty=max(1, int(row["qty"])),
                        notes=str(row.get("notes", "") or ""),
                    )

                st.success("Quote extras updated!")
                st.rerun()
