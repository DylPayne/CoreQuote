from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Literal


CutlistWarningSection = Literal["carcass", "panel", "hardware", "extra_panel"]

DIMENSION_FIELDS = (
    ("length", "Length must be greater than 0 mm."),
    ("width", "Width must be greater than 0 mm."),
    ("qty", "Quantity must be greater than 0."),
)
MATERIAL_SECTIONS = {"carcass", "panel", "extra_panel"}


def validate_cutlist_preview(
    preview: dict[str, Any],
    *,
    quote: dict[str, Any] | None = None,
    units: list[dict[str, Any]] | None = None,
    board_lookup: dict[str, dict[str, Any]] | None = None,
    slide_lookup: dict[str, dict[str, Any]] | None = None,
    require_materials: bool = False,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    units_by_number = {
        int(unit.get("unit_number", 0) or 0): unit
        for unit in (units or [])
        if int(unit.get("unit_number", 0) or 0) > 0
    }

    for row in _iter_validation_rows(preview):
        section = str(row.get("section") or "")
        for field_name, reason in DIMENSION_FIELDS:
            value = _int_value(row.get(field_name))
            if value <= 0:
                warnings.append(_warning(row, section=section, reason=reason))

        if require_materials and section in MATERIAL_SECTIONS:
            board_id = _resolve_board_id(row, quote=quote or {}, units_by_number=units_by_number)
            if not board_id:
                warnings.append(_warning(row, section=section, reason=_missing_material_reason(section, row)))
            elif board_lookup is not None and board_id not in board_lookup:
                warnings.append(
                    _warning(
                        row,
                        section=section,
                        reason="Selected board is not available in the company board library.",
                    )
                )

    warnings.extend(_slide_depth_warnings(quote=quote or {}, units=units or [], slide_lookup=slide_lookup or {}))
    warnings.extend(_drawer_system_warnings(quote=quote or {}, units=units or [], slide_lookup=slide_lookup or {}))
    return warnings


def cutlist_readiness(warnings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cutlist_valid": len(warnings) == 0,
        "warning_count": len(warnings),
    }


def preview_with_validation(
    preview: dict[str, Any],
    *,
    quote: dict[str, Any] | None = None,
    units: list[dict[str, Any]] | None = None,
    board_lookup: dict[str, dict[str, Any]] | None = None,
    slide_lookup: dict[str, dict[str, Any]] | None = None,
    require_materials: bool = False,
) -> dict[str, Any]:
    warnings = validate_cutlist_preview(
        preview,
        quote=quote,
        units=units,
        board_lookup=board_lookup,
        slide_lookup=slide_lookup,
        require_materials=require_materials,
    )
    return {
        **preview,
        "validation_warnings": warnings,
        "readiness": cutlist_readiness(warnings),
    }


def _iter_validation_rows(preview: dict[str, Any]) -> list[dict[str, Any]]:
    runtime_rows = preview.get("runtime_rows") or []
    if runtime_rows:
        return [dict(row) for row in runtime_rows]

    rows: list[dict[str, Any]] = []
    for key, section in (
        ("carcass", "carcass"),
        ("panels", "panel"),
        ("hardware", "hardware"),
        ("extras", "extra_panel"),
    ):
        rows.extend({**dict(row), "section": section} for row in preview.get(key, []) or [])
    return rows


def _warning(row: dict[str, Any], *, section: str, reason: str) -> dict[str, Any]:
    unit_number = _int_value(row.get("unit_number"))
    source = "quote_panel" if unit_number == 0 else "unit"
    return {
        "severity": "warning",
        "source": source,
        "unit_number": unit_number,
        "section": section,
        "row_desc": str(row.get("desc") or "Cutlist row"),
        "reason": reason,
    }


def _resolve_board_id(
    row: dict[str, Any],
    *,
    quote: dict[str, Any],
    units_by_number: dict[int, dict[str, Any]],
) -> str:
    unit_number = _int_value(row.get("unit_number"))
    unit = units_by_number.get(unit_number) or {}
    section = str(row.get("section") or "")

    if section == "carcass":
        return _clean_id(unit.get("carcass_board_type_id") or quote.get("default_carcass_board_type_id"))
    if section == "panel":
        return _clean_id(unit.get("door_board_type_id") or quote.get("default_door_board_type_id"))
    if section == "extra_panel":
        return _clean_id(
            row.get("board_type_id")
            or quote.get("default_panel_board_type_id")
            or unit.get("door_board_type_id")
            or quote.get("default_door_board_type_id")
        )
    return ""


def _missing_material_reason(section: str, row: dict[str, Any]) -> str:
    if section == "carcass":
        return "Choose a carcass board for this unit or quote default."
    if section == "panel":
        return "Choose a door or panel board for this unit or quote default."
    if _int_value(row.get("unit_number")) == 0:
        return "Choose a board for this quote-level panel."
    return "Choose a board for this extra panel row."


def _slide_depth_warnings(
    *,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    default_slide_id = _clean_id(quote.get("default_slide_id"))
    for unit in units:
        unit_type = str(unit.get("unit_type_key") or unit.get("unit_type") or "")
        if "draw" not in unit_type.lower():
            continue
        extra_params = unit.get("extra_params") or {}
        if not isinstance(extra_params, dict):
            extra_params = {}
        slide_id = _clean_id(extra_params.get("slide_id") or default_slide_id)
        if not slide_id:
            continue
        slide = slide_lookup.get(slide_id)
        if not slide:
            continue
        if _effective_drawer_system_kind(extra_params, slide) == "metal":
            continue
        slide_length = _int_value(slide.get("length"))
        unit_depth = _int_value(unit.get("depth"))
        if slide_length <= 0 or unit_depth >= slide_length:
            continue
        warnings.append(
            {
                "severity": "warning",
                "source": "unit",
                "unit_number": _int_value(unit.get("unit_number")),
                "section": "hardware",
                "row_desc": "Drawer slide",
                "reason": f"Selected {slide_length} mm slide requires a carcass depth of at least {slide_length} mm internally.",
            }
        )
    return warnings


def metal_drawer_system_unit_validation_messages(unit: dict[str, Any], slide: dict[str, Any] | None) -> list[str]:
    extra_params = unit.get("extra_params") or {}
    if not isinstance(extra_params, Mapping):
        extra_params = {}
    if _effective_drawer_system_kind(extra_params, slide) != "metal":
        return []

    config = _effective_drawer_system_config(extra_params, slide)
    label = _drawer_system_label(slide, config)
    messages: list[str] = []
    slide_length = _int_value((slide or {}).get("length") or extra_params.get("slide_length"))
    unit_depth = _int_value(unit.get("depth"))
    min_depth = _optional_int(config.get("min_depth_mm"))
    required_depth = max(slide_length, min_depth or 0)
    if required_depth > 0 and unit_depth < required_depth:
        messages.append(f"{label} requires a carcass depth of at least {required_depth} mm.")

    thickness = _int_value(unit.get("thickness"))
    compatible_thicknesses = _positive_int_list(config.get("compatible_side_thicknesses"))
    if compatible_thicknesses and thickness not in compatible_thicknesses:
        allowed = ", ".join(f"{value} mm" for value in compatible_thicknesses)
        messages.append(f"{label} is compatible with side-wall thicknesses {allowed}; this unit uses {thickness} mm.")

    compatible_lengths = _positive_int_list(config.get("compatible_nominal_lengths"))
    if compatible_lengths and slide_length not in compatible_lengths:
        allowed = ", ".join(f"{value} mm" for value in compatible_lengths)
        messages.append(f"{label} supports nominal lengths {allowed}; this slide is {slide_length} mm.")

    internal_width = max(0, _int_value(unit.get("width")) - (2 * thickness))
    min_internal_width = _optional_int(config.get("min_internal_width_mm"))
    max_internal_width = _optional_int(config.get("max_internal_width_mm"))
    if min_internal_width is not None and internal_width < min_internal_width:
        messages.append(f"{label} requires an internal width of at least {min_internal_width} mm; this unit is {internal_width} mm.")
    if max_internal_width is not None and internal_width > max_internal_width:
        messages.append(f"{label} supports internal widths up to {max_internal_width} mm; this unit is {internal_width} mm.")

    min_front_height = _optional_int(config.get("min_front_height_mm"))
    max_front_height = _optional_int(config.get("max_front_height_mm"))
    if min_front_height is not None or max_front_height is not None:
        face_heights = _drawer_face_heights(unit)
        if min_front_height is not None:
            low = [height for height in face_heights if height < min_front_height]
            if low:
                messages.append(f"{label} requires drawer fronts of at least {min_front_height} mm; this unit includes {min(low)} mm.")
        if max_front_height is not None:
            high = [height for height in face_heights if height > max_front_height]
            if high:
                messages.append(f"{label} supports drawer fronts up to {max_front_height} mm; this unit includes {max(high)} mm.")

    return messages


def _drawer_system_warnings(
    *,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    default_slide_id = _clean_id(quote.get("default_slide_id"))
    for unit in units:
        unit_type = str(unit.get("unit_type_key") or unit.get("unit_type") or "")
        if "draw" not in unit_type.lower():
            continue
        extra_params = unit.get("extra_params") or {}
        if not isinstance(extra_params, Mapping):
            extra_params = {}
        slide_id = _clean_id(extra_params.get("slide_id") or default_slide_id)
        slide = slide_lookup.get(slide_id) if slide_id else None
        messages = metal_drawer_system_unit_validation_messages(unit, slide)
        label = _drawer_system_label(slide, _effective_drawer_system_config(extra_params, slide))
        for message in messages:
            warnings.append(
                {
                    "severity": "warning",
                    "source": "unit",
                    "unit_number": _int_value(unit.get("unit_number")),
                    "section": "hardware",
                    "row_desc": label,
                    "reason": message,
                }
            )
    return warnings


def _clean_id(value: Any) -> str:
    return str(value or "").strip()


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    parsed = _int_value(value)
    return parsed if parsed > 0 else None


def _positive_int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        parsed = _int_value(item)
        if parsed > 0:
            result.append(parsed)
    return result


def _effective_drawer_system_kind(extra_params: Mapping[str, Any], slide: dict[str, Any] | None) -> str:
    return str(extra_params.get("drawer_system_kind") or (slide or {}).get("drawer_system_kind") or "conventional").strip().lower()


def _effective_drawer_system_config(extra_params: Mapping[str, Any], slide: dict[str, Any] | None) -> dict[str, Any]:
    config = extra_params.get("drawer_system_config") or (slide or {}).get("drawer_system_config") or {}
    return dict(config) if isinstance(config, Mapping) else {}


def _drawer_system_label(slide: dict[str, Any] | None, config: dict[str, Any]) -> str:
    family = str(config.get("product_family") or "").strip()
    brand = str((slide or {}).get("brand") or config.get("manufacturer") or "").strip()
    model = str((slide or {}).get("model") or "").strip()
    parts = [part for part in (brand, family or model) if part]
    return " ".join(parts) if parts else "Metal drawer system"


def _drawer_face_heights(unit: dict[str, Any], gap_mm: int = 3) -> list[int]:
    extra_params = unit.get("extra_params") or {}
    if not isinstance(extra_params, Mapping):
        extra_params = {}
    num_drawers = max(1, _int_value(extra_params.get("num_drawers")) or 3)
    manual = extra_params.get("drawer_face_heights")
    if isinstance(manual, list) and len(manual) == num_drawers:
        heights = [_int_value(value) for value in manual]
        if all(value > 0 for value in heights):
            return heights

    ratios_raw = extra_params.get("drawer_face_ratios")
    if isinstance(ratios_raw, list) and len(ratios_raw) == num_drawers:
        ratios = [_positive_float(value) for value in ratios_raw]
        if sum(ratios) <= 0:
            ratios = []
    else:
        ratios = []
    if not ratios:
        ratios = [0.25, 0.25, 0.5] if num_drawers == 3 else [1 / num_drawers] * num_drawers
    ratio_sum = sum(ratios)
    ratios = [value / ratio_sum for value in ratios]
    total_face_height = max(0, _int_value(unit.get("height")) - (gap_mm * num_drawers))
    raw = [ratio * total_face_height for ratio in ratios]
    floors = [int(math.floor(value)) for value in raw]
    remainder = total_face_height - sum(floors)
    frac_order = sorted(range(num_drawers), key=lambda index: raw[index] - floors[index], reverse=True)
    for index in range(remainder):
        floors[frac_order[index % num_drawers]] += 1
    return floors


def _positive_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed > 0 else 0.0
