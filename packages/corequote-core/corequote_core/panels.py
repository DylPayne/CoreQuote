"""Panel computation helpers for quote detail workflows.

This module is intentionally pure (no Streamlit imports) so it can be tested
in isolation.
"""

from __future__ import annotations

PANEL_PRESET_KEYS = [
    "base_side_panel",
    "base_side_filler",
    "wall_side_panel",
    "wall_side_filler",
    "tall_side_panel",
    "tall_side_filler",
]

PANEL_PRESET_LABELS = {
    "base_side_panel": "Base Side Panel",
    "base_side_filler": "Base Side Filler",
    "wall_side_panel": "Wall Side Panel",
    "wall_side_filler": "Wall Side Filler",
    "tall_side_panel": "Tall Side Panel",
    "tall_side_filler": "Tall Side Filler",
}

PANEL_PRESET_UNIT_FAMILY = {
    "base_side_panel": "base",
    "base_side_filler": "base",
    "wall_side_panel": "wall",
    "wall_side_filler": "wall",
    "tall_side_panel": "tall",
    "tall_side_filler": "tall",
}


def split_run_into_rows(
    desc: str,
    run_length: int,
    width: int,
    board_length_mm: int,
    board_type_id: int | None,
    production_metadata: dict | None = None,
) -> list[dict]:
    if run_length <= 0 or width <= 0:
        return []
    if board_length_mm <= 0:
        return [
            {
                "Desc": desc,
                "L": int(run_length),
                "W": int(width),
                "Qty": 1,
                "board_type_id": board_type_id,
                "production_metadata": production_metadata or {},
            }
        ]

    full = run_length // board_length_mm
    rem = run_length % board_length_mm
    rows: list[dict] = []
    if full > 0:
        rows.append(
            {
                "Desc": desc,
                "L": int(board_length_mm),
                "W": int(width),
                "Qty": int(full),
                "board_type_id": board_type_id,
                "production_metadata": production_metadata or {},
            }
        )
    if rem > 0:
        rows.append(
            {
                "Desc": desc,
                "L": int(rem),
                "W": int(width),
                "Qty": 1,
                "board_type_id": board_type_id,
                "production_metadata": production_metadata or {},
            }
        )
    return rows


def compute_panel_rows(
    *,
    units: list[dict],
    state: dict,
    default_panel_board_type_id: int | None,
    panel_preset_keys: list[str],
    panel_preset_labels: dict[str, str],
    default_dims_for_panel_preset,
    default_dims_for_unit_type,
    board_length_for,
) -> list[dict]:
    rows: list[dict] = []
    presets = state.get("presets", {}) or {}

    for key in panel_preset_keys:
        conf = presets.get(key, {}) if isinstance(presets.get(key, {}), dict) else {}
        qty = int(conf.get("qty", 1) or 0)
        board_type_id = conf.get("board_type_id", default_panel_board_type_id)
        production_metadata = conf.get("production_metadata", {}) if isinstance(conf.get("production_metadata", {}), dict) else {}
        l_mm, w_mm = default_dims_for_panel_preset(key)
        rows.append(
            {
                "Desc": panel_preset_labels[key],
                "L": l_mm,
                "W": w_mm,
                "Qty": qty,
                "board_type_id": board_type_id,
                "production_metadata": production_metadata,
            }
        )

    for manual in state.get("manual", []) or []:
        if not isinstance(manual, dict):
            continue
        rows.append(
            {
                "Desc": str(manual.get("name", "Custom Panel") or "Custom Panel"),
                "L": int(manual.get("length", 0) or 0),
                "W": int(manual.get("width", 0) or 0),
                "Qty": int(manual.get("qty", 0) or 0),
                "board_type_id": manual.get("board_type_id", default_panel_board_type_id),
                "production_metadata": manual.get("production_metadata", {}) if isinstance(manual.get("production_metadata", {}), dict) else {},
            }
        )

    auto = state.get("auto", {}) or {}
    base_total = sum(int(u.get("width", 0) or 0) for u in units if "Base" in str(u.get("unit_type", "")))
    wall_side_panel_qty = int((presets.get("wall_side_panel", {}) or {}).get("qty", 0) or 0)
    wall_side_filler_qty = int((presets.get("wall_side_filler", {}) or {}).get("qty", 0) or 0)
    _, wall_side_w = default_dims_for_panel_preset("wall_side_panel")
    _, wall_filler_w = default_dims_for_panel_preset("wall_side_filler")
    kicker_extra = (wall_side_panel_qty * int(wall_side_w)) + (wall_side_filler_qty * int(wall_filler_w))
    _, base_d = default_dims_for_unit_type("Base Door")
    kicker_return_count = max(0, int(auto.get("kicker_return_count", 0) or 0))
    kicker_return_depth_mm = max(0, int(auto.get("kicker_return_depth_mm", base_d) or base_d))
    kicker_return_extra = kicker_return_count * kicker_return_depth_mm
    kicker_run_total = int(base_total) + int(kicker_extra) + int(kicker_return_extra)
    wall_total = sum(int(u.get("width", 0) or 0) for u in units if "Wall" in str(u.get("unit_type", "")))
    _, wall_d = default_dims_for_unit_type("Wall Door")

    kicker_board_type_id = auto.get("kicker_board_type_id", default_panel_board_type_id)
    pelmet_board_type_id = auto.get("pelmet_board_type_id", default_panel_board_type_id)

    kicker_override_on = bool(auto.get("kicker_override_on", False))
    pelmet_override_on = bool(auto.get("pelmet_override_on", False))
    auto_production_metadata = auto.get("production_metadata", {}) if isinstance(auto.get("production_metadata", {}), dict) else {}

    if kicker_override_on:
        rows.append(
            {
                "Desc": "Kicker",
                "L": int(auto.get("kicker_override_length", 0) or 0),
                "W": int(auto.get("kicker_override_width", 100) or 100),
                "Qty": int(auto.get("kicker_override_qty", 0) or 0),
                "board_type_id": kicker_board_type_id,
                "production_metadata": auto_production_metadata,
            }
        )
    else:
        rows.extend(
            split_run_into_rows(
                "Kicker",
                run_length=kicker_run_total,
                width=100,
                board_length_mm=board_length_for(kicker_board_type_id),
                board_type_id=kicker_board_type_id,
                production_metadata=auto_production_metadata,
            )
        )

    if pelmet_override_on:
        rows.append(
            {
                "Desc": "Wall Pelmet",
                "L": int(auto.get("pelmet_override_length", 0) or 0),
                "W": int(auto.get("pelmet_override_width", wall_d) or wall_d),
                "Qty": int(auto.get("pelmet_override_qty", 0) or 0),
                "board_type_id": pelmet_board_type_id,
                "production_metadata": auto_production_metadata,
            }
        )
    else:
        rows.extend(
            split_run_into_rows(
                "Wall Pelmet",
                run_length=wall_total,
                width=int(wall_d),
                board_length_mm=board_length_for(pelmet_board_type_id),
                board_type_id=pelmet_board_type_id,
                production_metadata=auto_production_metadata,
            )
        )

    return [r for r in rows if int(r.get("L", 0)) > 0 and int(r.get("W", 0)) > 0 and int(r.get("Qty", 0)) > 0]
