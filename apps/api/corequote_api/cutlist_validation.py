from __future__ import annotations

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
    require_materials: bool = False,
) -> dict[str, Any]:
    warnings = validate_cutlist_preview(
        preview,
        quote=quote,
        units=units,
        board_lookup=board_lookup,
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


def _clean_id(value: Any) -> str:
    return str(value or "").strip()


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
