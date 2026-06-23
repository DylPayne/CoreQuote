from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import math


PROFILE_HANDLE_LOOKUP_KEY = "_profile_handle_lookup"

TOP_J_CHANNEL_HANDLE_ID = "top_j_channel_handle_id"
MIDDLE_C_CHANNEL_HANDLE_ID = "middle_c_channel_handle_id"
BETWEEN_LOWER_C_CHANNEL_HANDLE_ID = "between_lower_c_channel_handle_id"
BASE_DOOR_TOP_J_CHANNEL_HANDLE_ID = "base_door_top_j_channel_handle_id"
TALL_VERTICAL_CHANNEL_HANDLE_ID = "tall_vertical_channel_handle_id"
FULL_LENGTH_HANDLE_ORIENTATION = "full_length_handle_orientation"

PROFILE_HANDLE_ID_KEYS = (
    TOP_J_CHANNEL_HANDLE_ID,
    MIDDLE_C_CHANNEL_HANDLE_ID,
    BETWEEN_LOWER_C_CHANNEL_HANDLE_ID,
    BASE_DOOR_TOP_J_CHANNEL_HANDLE_ID,
    TALL_VERTICAL_CHANNEL_HANDLE_ID,
    "handle_id",
)


@dataclass(frozen=True)
class ProfileHandle:
    item_ref_id: str
    name: str
    handle_type: str
    front_reduction_mm: int
    supplier: str = ""
    code: str = ""


@dataclass(frozen=True)
class ChannelPlacement:
    handle: ProfileHandle
    desc: str
    orientation: str
    cut_length_mm: int
    affected_drawer_index: int | None = None
    qty: int = 1


def attach_profile_handle_lookup(extra_params: Mapping[str, Any] | None, handle_lookup: Mapping[str, Mapping[str, Any]] | None) -> dict[str, Any]:
    params = dict(extra_params or {})
    handles: dict[str, dict[str, Any]] = {}
    for key in PROFILE_HANDLE_ID_KEYS:
        handle_id = _clean_id(params.get(key))
        if not handle_id:
            continue
        handle = (handle_lookup or {}).get(handle_id)
        if handle:
            handles[handle_id] = dict(handle)
    if handles:
        params[PROFILE_HANDLE_LOOKUP_KEY] = handles
    return params


def profile_params_from_unit(unit: Any) -> Mapping[str, Any] | None:
    params = getattr(unit, "profile_handles", None)
    if isinstance(params, Mapping):
        return params
    return None


def adjust_drawer_front_heights(base_heights: Sequence[int], profile_params: Mapping[str, Any] | None) -> list[int]:
    values = [max(0, int(value)) for value in base_heights]
    placements = drawer_channel_placements(profile_params, len(values), unit_width=0)
    for placement in placements:
        if placement.affected_drawer_index is None:
            continue
        if placement.affected_drawer_index >= len(values):
            continue
        values[placement.affected_drawer_index] = max(0, values[placement.affected_drawer_index] - placement.handle.front_reduction_mm)
    return values


def adjust_door_front_dimensions(
    *,
    unit_height: int,
    unit_width: int,
    num_doors: int,
    gap_mm: int,
    profile_params: Mapping[str, Any] | None,
    unit_type_key: str = "",
    is_pantry: bool = False,
) -> tuple[int, int]:
    row_height = (unit_height / 2) - gap_mm if is_pantry else unit_height - gap_mm
    total_width = unit_width - (gap_mm * num_doors)
    canonical = _canonical_unit_type(unit_type_key)
    params = profile_params if isinstance(profile_params, Mapping) else {}

    if canonical == "Base Door":
        top_j = _profile_handle(params, BASE_DOOR_TOP_J_CHANNEL_HANDLE_ID, {"j_channel"})
        if top_j:
            row_height -= top_j.front_reduction_mm

    if canonical == "Tall Door":
        vertical_channel = _profile_handle(params, TALL_VERTICAL_CHANNEL_HANDLE_ID, {"c_channel", "j_channel"})
        if vertical_channel:
            total_width -= vertical_channel.front_reduction_mm * max(1, num_doors - 1)

    full_length = _selected_full_length_handle(params)
    if full_length:
        orientation = full_length_orientation(params)
        if orientation == "width":
            row_height -= full_length.front_reduction_mm
        else:
            total_width -= full_length.front_reduction_mm * max(1, num_doors)

    panel_width = total_width / num_doors if num_doors > 0 else 0
    return int(max(0, math.floor(row_height))), int(max(0, math.floor(panel_width)))


def channel_profile_rows_for_unit(
    *,
    unit_number: int,
    unit_type_key: str,
    height: int,
    width: int,
    num_fronts: int,
    profile_params: Mapping[str, Any] | None,
    is_pantry: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for placement in channel_placements_for_unit(
        unit_type_key=unit_type_key,
        height=height,
        width=width,
        num_fronts=num_fronts,
        profile_params=profile_params,
        is_pantry=is_pantry,
    ):
        rows.append(_hardware_row(unit_number=unit_number, placement=placement))
    return rows


def full_length_profile_rows_for_unit(
    *,
    unit_number: int,
    unit_type_key: str,
    unit_height: int,
    unit_width: int,
    num_doors: int,
    gap_mm: int,
    profile_params: Mapping[str, Any] | None,
    is_pantry: bool = False,
) -> list[dict[str, Any]]:
    canonical = _canonical_unit_type(unit_type_key)
    if canonical not in {"Base Door", "Wall Door", "Tall Door"}:
        return []
    handle = _selected_full_length_handle(profile_params if isinstance(profile_params, Mapping) else {})
    if handle is None:
        return []

    base_height = (unit_height / 2) - gap_mm if is_pantry else unit_height - gap_mm
    base_width = (unit_width - (gap_mm * num_doors)) / num_doors if num_doors > 0 else 0
    orientation = full_length_orientation(profile_params)
    cut_length = int(max(0, math.floor(base_width if orientation == "width" else base_height)))
    qty = num_doors * (2 if is_pantry else 1)
    return [
        {
            "unit_number": int(unit_number),
            "desc": handle.name,
            "length": max(1, int(handle.front_reduction_mm)),
            "width": cut_length,
            "qty": max(0, int(qty)),
            "item_ref_id": handle.item_ref_id,
        }
    ]


def channel_placements_for_unit(
    *,
    unit_type_key: str,
    height: int,
    width: int,
    num_fronts: int,
    profile_params: Mapping[str, Any] | None,
    is_pantry: bool = False,
) -> list[ChannelPlacement]:
    canonical = _canonical_unit_type(unit_type_key)
    params = profile_params if isinstance(profile_params, Mapping) else {}
    if canonical == "Base Draw":
        return drawer_channel_placements(params, num_fronts, unit_width=width)
    if canonical == "Base Door":
        handle = _profile_handle(params, BASE_DOOR_TOP_J_CHANNEL_HANDLE_ID, {"j_channel"})
        if not handle:
            return []
        return [
            ChannelPlacement(
                handle=handle,
                desc=f"{handle.name} top channel",
                orientation="horizontal",
                cut_length_mm=width,
            )
        ]
    if canonical == "Tall Door":
        handle = _profile_handle(params, TALL_VERTICAL_CHANNEL_HANDLE_ID, {"c_channel", "j_channel"})
        if not handle:
            return []
        return [
            ChannelPlacement(
                handle=handle,
                desc=f"{handle.name} vertical channel",
                orientation="vertical",
                cut_length_mm=height,
            )
        ]
    return []


def drawer_channel_placements(profile_params: Mapping[str, Any] | None, num_drawers: int, *, unit_width: int) -> list[ChannelPlacement]:
    params = profile_params if isinstance(profile_params, Mapping) else {}
    placements: list[ChannelPlacement] = []
    if num_drawers in {1, 2, 3}:
        top_j = _profile_handle(params, TOP_J_CHANNEL_HANDLE_ID, {"j_channel"})
        if top_j:
            placements.append(
                ChannelPlacement(
                    handle=top_j,
                    desc=f"{top_j.name} top channel",
                    orientation="horizontal",
                    cut_length_mm=unit_width,
                    affected_drawer_index=0,
                )
            )
    if num_drawers == 2:
        middle_c = _profile_handle(params, MIDDLE_C_CHANNEL_HANDLE_ID, {"c_channel"})
        if middle_c:
            placements.append(
                ChannelPlacement(
                    handle=middle_c,
                    desc=f"{middle_c.name} middle channel",
                    orientation="horizontal",
                    cut_length_mm=unit_width,
                    affected_drawer_index=1,
                )
            )
    if num_drawers == 3:
        lower_c = _profile_handle(params, BETWEEN_LOWER_C_CHANNEL_HANDLE_ID, {"c_channel"})
        if lower_c:
            placements.append(
                ChannelPlacement(
                    handle=lower_c,
                    desc=f"{lower_c.name} lower channel",
                    orientation="horizontal",
                    cut_length_mm=unit_width,
                    affected_drawer_index=2,
                )
            )
    return placements


def channel_front_validation_messages(unit: Mapping[str, Any], *, unit_type_key: str | None = None) -> list[str]:
    extra_params = unit.get("extra_params") or {}
    if not isinstance(extra_params, Mapping):
        return []
    canonical = _canonical_unit_type(unit_type_key or str(unit.get("unit_type_key") or unit.get("unit_type") or ""))
    height = _positive_int(unit.get("height"), 0)
    width = _positive_int(unit.get("width"), 0)
    messages: list[str] = []

    if canonical == "Base Draw":
        num_drawers = _positive_int(extra_params.get("num_drawers"), _default_num_drawers(unit_type_key or canonical))
        adjusted = adjust_drawer_front_heights(_drawer_base_heights(unit, num_drawers), extra_params)
        if adjusted and min(adjusted) <= 0:
            messages.append("Selected drawer channel profiles consume all available drawer-front height.")
        return messages

    if canonical in {"Base Door", "Wall Door", "Tall Door"}:
        num_doors = _positive_int(extra_params.get("num_doors"), 2)
        is_pantry = str(unit.get("unit_type_key") or unit.get("unit_type") or "") == "Tall Pantry"
        panel_height, panel_width = adjust_door_front_dimensions(
            unit_height=height,
            unit_width=width,
            num_doors=num_doors,
            gap_mm=3,
            profile_params=extra_params,
            unit_type_key=unit_type_key or canonical,
            is_pantry=is_pantry,
        )
        if panel_height <= 0:
            messages.append("Selected profile handles consume all available door-front height.")
        if panel_width <= 0:
            messages.append("Selected profile handles consume all available door-front width.")
    return messages


def full_length_orientation(profile_params: Mapping[str, Any] | None) -> str:
    value = str((profile_params or {}).get(FULL_LENGTH_HANDLE_ORIENTATION) or "length").strip().lower()
    return "width" if value == "width" else "length"


def has_channel_selection(profile_params: Mapping[str, Any] | None, *, unit_type_key: str = "", num_fronts: int = 1) -> bool:
    return bool(
        channel_placements_for_unit(
            unit_type_key=unit_type_key,
            height=0,
            width=0,
            num_fronts=num_fronts,
            profile_params=profile_params,
        )
    )


def selected_profile_handle_ids(extra_params: Mapping[str, Any] | None) -> list[str]:
    params = extra_params if isinstance(extra_params, Mapping) else {}
    ids: list[str] = []
    for key in PROFILE_HANDLE_ID_KEYS:
        handle_id = _clean_id(params.get(key))
        if handle_id and handle_id not in ids:
            ids.append(handle_id)
    return ids


def _hardware_row(*, unit_number: int, placement: ChannelPlacement) -> dict[str, Any]:
    return {
        "unit_number": int(unit_number),
        "desc": placement.desc,
        "length": max(1, int(placement.handle.front_reduction_mm)),
        "width": max(0, int(placement.cut_length_mm)),
        "qty": max(0, int(placement.qty)),
        "item_ref_id": placement.handle.item_ref_id,
    }


def _selected_full_length_handle(profile_params: Mapping[str, Any] | None) -> ProfileHandle | None:
    params = profile_params if isinstance(profile_params, Mapping) else {}
    return _profile_handle(params, "handle_id", {"full_length"})


def _profile_handle(profile_params: Mapping[str, Any], key: str, allowed_types: set[str]) -> ProfileHandle | None:
    handle_id = _clean_id(profile_params.get(key))
    if not handle_id:
        return None
    lookup = profile_params.get(PROFILE_HANDLE_LOOKUP_KEY)
    if not isinstance(lookup, Mapping):
        return None
    raw = lookup.get(handle_id)
    if not isinstance(raw, Mapping):
        return None
    handle_type = _normalize_handle_type(raw.get("handle_type"))
    if handle_type not in allowed_types:
        return None
    reduction = _positive_int(raw.get("front_reduction_mm"), 0)
    return ProfileHandle(
        item_ref_id=handle_id,
        name=str(raw.get("name") or _fallback_handle_name(handle_type)).strip() or _fallback_handle_name(handle_type),
        handle_type=handle_type,
        front_reduction_mm=reduction,
        supplier=str(raw.get("supplier_name") or raw.get("supplier") or "").strip(),
        code=str(raw.get("code") or "").strip(),
    )


def _fallback_handle_name(handle_type: str) -> str:
    return {
        "full_length": "Full-length profile handle",
        "c_channel": "C channel",
        "j_channel": "J channel",
    }.get(handle_type, "Handle")


def _normalize_handle_type(value: Any) -> str:
    text = str(value or "standard").strip().lower().replace("-", "_").replace(" ", "_")
    if text in {"full", "profile", "profile_handle", "full_length_profile"}:
        return "full_length"
    if text in {"c", "c_profile"}:
        return "c_channel"
    if text in {"j", "j_profile"}:
        return "j_channel"
    if text in {"standard", "full_length", "c_channel", "j_channel"}:
        return text
    return "standard"


def _drawer_base_heights(unit: Mapping[str, Any], num_drawers: int, gap_mm: int = 3) -> list[int]:
    extra_params = unit.get("extra_params") or {}
    manual = extra_params.get("drawer_face_heights") if isinstance(extra_params, Mapping) else None
    if isinstance(manual, list) and len(manual) == num_drawers:
        heights = [_positive_int(value, 0) for value in manual]
        if all(value > 0 for value in heights):
            return heights

    ratios_raw = extra_params.get("drawer_face_ratios") if isinstance(extra_params, Mapping) else None
    ratios: list[float] = []
    if isinstance(ratios_raw, list) and len(ratios_raw) == num_drawers:
        ratios = [_positive_float(value) for value in ratios_raw]
        if sum(ratios) <= 0:
            ratios = []
    if not ratios:
        ratios = [0.25, 0.25, 0.5] if num_drawers == 3 else [1 / num_drawers] * num_drawers
    total = max(0, _positive_int(unit.get("height"), 0) - (gap_mm * num_drawers))
    raw = [(ratio / sum(ratios)) * total for ratio in ratios]
    floors = [int(math.floor(value)) for value in raw]
    remainder = total - sum(floors)
    order = sorted(range(num_drawers), key=lambda index: raw[index] - floors[index], reverse=True)
    for index in range(remainder):
        floors[order[index % num_drawers]] += 1
    return floors


def _canonical_unit_type(unit_type: str | None) -> str:
    value = str(unit_type or "")
    if value in {"Base Draw", "Base Drawer", "Base 1 Draw", "Base 2 Draw", "Base 3 Draw", "Base 4 Draw"}:
        return "Base Draw"
    if value in {"Base Door", "Base 1 Door", "Base 2 Door"}:
        return "Base Door"
    if value in {"Wall Door", "Wall 1 Door", "Wall 2 Door"}:
        return "Wall Door"
    if value in {"Tall Door", "Tall Standard", "Tall Pantry"}:
        return "Tall Door"
    return value


def _default_num_drawers(unit_type: str) -> int:
    value = str(unit_type or "")
    if value in {"Base 1 Draw", "Base 2 Draw", "Base 3 Draw", "Base 4 Draw"}:
        return int(value.split()[1])
    return 3


def _clean_id(value: Any) -> str:
    return str(value or "").strip()


def _positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _positive_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed > 0 else 0.0
