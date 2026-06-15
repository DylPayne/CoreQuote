"""Production handoff grouping for workshop-facing quote packets."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


MATERIAL_ROLE_LABELS = {
    "carcass": "Carcass",
    "door_panel": "Door/Drawer Panel",
    "visible_panel": "Visible Panel",
}

SECTION_LABELS = {
    "carcass": "Carcass",
    "panel": "Panel",
    "hardware": "Hardware",
    "extra_panel": "Quote Panel",
}

MATERIAL_SECTIONS = {"carcass", "panel", "extra_panel"}
BOARD_REQUIREMENT_ESTIMATE_LABEL = "Sheet counts are estimates only; CoreQuote has not optimized board nesting."


def build_production_handoff(
    *,
    quote: dict[str, Any],
    project: dict[str, Any],
    units: list[dict[str, Any]],
    cutting_list: dict[str, Any] | None,
    material_summary: dict[str, Any] | None,
    hardware_pick_list: dict[str, Any] | None,
    board_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a client-safe production packet from existing quote output sources."""

    cutting_list = cutting_list or {}
    units_by_number = {
        _non_negative_int(unit.get("unit_number"), 0): unit
        for unit in units
        if _non_negative_int(unit.get("unit_number"), 0) > 0
    }
    warnings_by_row = _warnings_by_cutlist_row(cutting_list.get("validation_warnings"))
    rows = _production_rows(
        quote=quote,
        project=project,
        rows=_cutting_rows(cutting_list),
        units_by_number=units_by_number,
        warnings_by_row=warnings_by_row,
        board_lookup=board_lookup,
    )
    rows = sorted(rows, key=_row_sort_key)
    groups = _production_groups(rows)
    labels = [_label_for_row(row) for row in rows]
    hardware = _production_hardware_items(
        quote=quote,
        pick_list=hardware_pick_list or {},
        rows=rows,
    )
    safe_material_summary = _safe_material_summary(material_summary or {}, rows)
    board_requirements = _board_requirements(
        rows=rows,
        material_summary=safe_material_summary,
        board_lookup=board_lookup,
    )

    warning_count = sum(int(row["warning_count"]) for row in rows)
    return {
        "quote_id": str(quote.get("id") or ""),
        "quote_name": str(quote.get("name") or "Quote"),
        "quote_status": str(quote.get("status") or "draft"),
        "quote_number": str(quote.get("quote_number") or ""),
        "revision": max(1, _non_negative_int(quote.get("revision"), 1)),
        "project_id": str(project.get("id") or quote.get("project_id") or ""),
        "project_name": str(project.get("name") or "Project"),
        "row_count": len(rows),
        "group_count": len(groups),
        "label_count": len(labels),
        "warning_count": warning_count,
        "groups": groups,
        "rows": rows,
        "material_summary": safe_material_summary,
        "board_requirements": board_requirements,
        "hardware_pick_list": {
            "items": hardware,
            "warnings": list(hardware_pick_list.get("warnings") or []) if isinstance(hardware_pick_list, dict) else [],
            "total_item_count": len(hardware),
            "total_quantity": sum(int(item["quantity"]) for item in hardware),
        },
        "labels": labels,
    }


def _board_requirements(
    *,
    rows: list[dict[str, Any]],
    material_summary: dict[str, Any],
    board_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    summary_groups = {
        (str(group.get("board_type_id") or "").strip(), str(group.get("material_role") or "").strip()): group
        for group in material_summary.get("groups") or []
    }
    warnings: list[dict[str, Any]] = []
    warning_keys: set[tuple[Any, ...]] = set()
    groups_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}

    for row in rows:
        board_id = str(row.get("board_type_id") or "").strip()
        material_role = str(row.get("material_role") or "").strip()
        key = (
            board_id,
            material_role,
            _non_negative_int(row.get("thickness"), 0),
            str(row.get("brand") or ""),
            str(row.get("material") or ""),
        )
        group = groups_by_key.get(key)
        board = board_lookup.get(board_id) if board_id else None
        if group is None:
            group = {
                "requirement_key": _requirement_key(row),
                "board_type_id": board_id or None,
                "board_name": row.get("board_name") or "Unassigned material",
                "brand": row.get("brand") or "",
                "material": row.get("material") or "",
                "thickness": row.get("thickness"),
                "sheet_length_mm": row.get("sheet_length_mm"),
                "sheet_width_mm": row.get("sheet_width_mm"),
                "material_role": material_role,
                "role_label": row.get("role_label") or MATERIAL_ROLE_LABELS.get(material_role, _title_words(material_role)),
                "row_count": 0,
                "piece_count": 0,
                "area_m2": 0.0,
                "edge_m": 0.0,
                "sheet_area_m2": None,
                "estimated_sheets": None,
                "estimated_sheet_area_m2": None,
                "waste_area_m2": None,
                "waste_percent": None,
                "sheet_estimate_label": "",
                "waste_allowance_label": "",
                "part_ids": [],
                "source_labels": [],
                "warning_count": 0,
                "warning_messages": [],
                "_area_mm2": 0,
                "_piece_areas_mm2": [],
                "_board_record_available": bool(board),
            }
            groups_by_key[key] = group

        length = _non_negative_int(row.get("length"), 0)
        width = _non_negative_int(row.get("width"), 0)
        quantity = _non_negative_int(row.get("quantity"), 0)
        group["row_count"] += 1
        group["piece_count"] += quantity
        _append_unique(group["part_ids"], str(row.get("part_id") or ""))
        _append_unique(group["source_labels"], str(row.get("unit_label") or ""))

        if length <= 0 or width <= 0 or quantity <= 0:
            _append_requirement_warning(
                warnings,
                warning_keys,
                group,
                code="invalid_part_dimensions",
                row=row,
                message=f"{row.get('part_id') or row.get('desc')}: length, width, and quantity must be greater than zero.",
            )
        else:
            piece_area = length * width
            group["_area_mm2"] += piece_area * quantity
            group["_piece_areas_mm2"].extend([piece_area] * quantity)

        if not board_id:
            _append_requirement_warning(
                warnings,
                warning_keys,
                group,
                code="missing_board_selection",
                row=row,
                message=f"Choose a board for {row.get('unit_label') or 'this source'} / {row.get('desc') or 'part'} before ordering material.",
            )
        elif board is None:
            _append_requirement_warning(
                warnings,
                warning_keys,
                group,
                code="missing_board_record",
                row=row,
                message=f"Board {board_id} is not available in the company board library.",
            )
        else:
            if not _optional_positive_int(board.get("length_mm")) or not _optional_positive_int(board.get("width_mm")):
                _append_requirement_warning(
                    warnings,
                    warning_keys,
                    group,
                    code="missing_board_dimensions",
                    row=row,
                    message=f"Add sheet length and width for {_board_description(board)} to estimate sheets.",
                )
            if not str(board.get("brand") or "").strip() or not str(board.get("material") or "").strip() or not _optional_positive_int(board.get("thickness")):
                _append_requirement_warning(
                    warnings,
                    warning_keys,
                    group,
                    code="incomplete_material_data",
                    row=row,
                    message=f"Complete brand, material, and thickness for {_board_description(board)} before ordering material.",
                )

    for warning in material_summary.get("warnings") or []:
        if not isinstance(warning, dict):
            continue
        code = str(warning.get("code") or "").strip()
        if code not in {"missing_board_selection", "missing_board_record", "missing_board_dimensions"}:
            continue
        _append_requirement_warning(
            warnings,
            warning_keys,
            None,
            code=code,
            row={
                "part_id": "",
                "unit_number": warning.get("unit_number"),
                "desc": warning.get("row_desc"),
                "material_role": warning.get("material_role"),
                "role_label": warning.get("role_label"),
                "board_type_id": warning.get("board_type_id"),
            },
            message=str(warning.get("message") or ""),
        )

    groups = []
    for group in groups_by_key.values():
        board_id = str(group.get("board_type_id") or "")
        material_role = str(group.get("material_role") or "")
        summary_group = summary_groups.get((board_id, material_role))
        group["area_m2"] = round(int(group.pop("_area_mm2")) / 1_000_000.0, 4)
        piece_areas = list(group.pop("_piece_areas_mm2"))
        board_record_available = bool(group.pop("_board_record_available"))

        if summary_group:
            group["piece_count"] = _non_negative_int(summary_group.get("piece_count"), group["piece_count"])
            group["area_m2"] = _non_negative_float(summary_group.get("area_m2"), group["area_m2"])
            group["edge_m"] = _non_negative_float(summary_group.get("edge_m"), 0.0)
            group["estimated_sheets"] = _optional_positive_int(summary_group.get("estimated_sheets"), allow_zero=True)
            group["sheet_length_mm"] = group.get("sheet_length_mm") or _optional_positive_int(summary_group.get("length_mm"))
            group["sheet_width_mm"] = group.get("sheet_width_mm") or _optional_positive_int(summary_group.get("width_mm"))

        sheet_length = _optional_positive_int(group.get("sheet_length_mm"))
        sheet_width = _optional_positive_int(group.get("sheet_width_mm"))
        sheet_area_mm2 = (sheet_length or 0) * (sheet_width or 0)
        sheet_area_m2 = round(sheet_area_mm2 / 1_000_000.0, 4) if sheet_area_mm2 > 0 else None
        group["sheet_area_m2"] = sheet_area_m2
        if group["estimated_sheets"] is None and sheet_area_mm2 > 0:
            group["estimated_sheets"] = _estimate_boards_used(piece_areas, sheet_area_mm2)

        estimated_sheets = group["estimated_sheets"]
        if estimated_sheets is not None and sheet_area_m2 is not None:
            group["estimated_sheet_area_m2"] = round(int(estimated_sheets) * sheet_area_m2, 4)
            group["waste_area_m2"] = round(max(0.0, group["estimated_sheet_area_m2"] - group["area_m2"]), 4)
            group["waste_percent"] = (
                round(group["waste_area_m2"] / group["estimated_sheet_area_m2"] * 100.0, 2)
                if group["estimated_sheet_area_m2"] > 0
                else 0.0
            )
        group["sheet_estimate_label"] = _sheet_estimate_label(group, board_record_available=board_record_available)
        group["waste_allowance_label"] = _waste_allowance_label(group)
        groups.append(group)

    groups = sorted(groups, key=_requirement_sort_key)
    total_estimated_sheets: int | None = None
    total_estimated_sheet_area_m2: float | None = None
    total_waste_area_m2: float | None = None
    if groups and all(group.get("estimated_sheets") is not None for group in groups):
        total_estimated_sheets = sum(int(group["estimated_sheets"]) for group in groups)
    if groups and all(group.get("estimated_sheet_area_m2") is not None for group in groups):
        total_estimated_sheet_area_m2 = round(sum(float(group["estimated_sheet_area_m2"]) for group in groups), 4)
    if groups and all(group.get("waste_area_m2") is not None for group in groups):
        total_waste_area_m2 = round(sum(float(group["waste_area_m2"]) for group in groups), 4)

    return {
        "estimate_label": BOARD_REQUIREMENT_ESTIMATE_LABEL,
        "groups": groups,
        "warnings": sorted(warnings, key=_requirement_warning_sort_key),
        "total_area_m2": round(sum(float(group["area_m2"]) for group in groups), 4),
        "total_piece_count": sum(int(group["piece_count"]) for group in groups),
        "total_edge_m": round(sum(float(group["edge_m"]) for group in groups), 3),
        "total_estimated_sheets": total_estimated_sheets,
        "total_estimated_sheet_area_m2": total_estimated_sheet_area_m2,
        "total_waste_area_m2": total_waste_area_m2,
        "warning_count": len(warnings),
    }


def _requirement_key(row: dict[str, Any]) -> str:
    return "::".join(
        [
            str(row.get("board_type_id") or "unassigned"),
            str(row.get("thickness") or 0),
            str(row.get("material") or ""),
            str(row.get("material_role") or ""),
        ]
    )


def _append_requirement_warning(
    warnings: list[dict[str, Any]],
    seen: set[tuple[Any, ...]],
    group: dict[str, Any] | None,
    *,
    code: str,
    row: dict[str, Any],
    message: str,
) -> None:
    clean_message = message.strip()
    key = (
        code,
        str(row.get("part_id") or ""),
        _non_negative_int(row.get("unit_number"), 0),
        str(row.get("material_role") or ""),
        str(row.get("board_type_id") or ""),
        str(row.get("desc") or row.get("row_desc") or ""),
        clean_message,
    )
    if key in seen:
        return
    seen.add(key)
    material_role = str(row.get("material_role") or "")
    warning = {
        "severity": "warning",
        "code": code,
        "material_role": material_role,
        "role_label": str(row.get("role_label") or MATERIAL_ROLE_LABELS.get(material_role, _title_words(material_role))),
        "unit_number": _non_negative_int(row.get("unit_number"), 0),
        "row_desc": str(row.get("desc") or row.get("row_desc") or ""),
        "board_type_id": str(row.get("board_type_id") or "").strip() or None,
        "part_id": str(row.get("part_id") or ""),
        "message": clean_message,
    }
    warnings.append(warning)
    if group is not None:
        _append_unique(group["warning_messages"], clean_message)
        group["warning_count"] = len(group["warning_messages"])


def _requirement_warning_sort_key(warning: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(warning.get("code") or ""),
        str(warning.get("material_role") or ""),
        _non_negative_int(warning.get("unit_number"), 0),
        str(warning.get("row_desc") or ""),
        str(warning.get("message") or ""),
    )


def _sheet_estimate_label(group: dict[str, Any], *, board_record_available: bool) -> str:
    if not group.get("board_type_id"):
        return "Needs board selection before sheets can be estimated."
    if not board_record_available:
        return "Needs a visible board record before sheets can be estimated."
    if not group.get("sheet_length_mm") or not group.get("sheet_width_mm"):
        return "Needs sheet length and width before sheets can be estimated."
    estimated_sheets = group.get("estimated_sheets")
    if estimated_sheets is None:
        return "Needs material data before sheets can be estimated."
    suffix = "sheet" if int(estimated_sheets) == 1 else "sheets"
    return f"{estimated_sheets} estimated {suffix} (area estimate, not optimized nesting)."


def _waste_allowance_label(group: dict[str, Any]) -> str:
    if group.get("waste_percent") is None:
        return "Waste allowance unavailable until sheet estimates can be calculated."
    return f"Estimated waste allowance {float(group['waste_percent']):.1f}% from sheet area minus part area."


def _estimate_boards_used(piece_areas_mm2: list[int], sheet_area_mm2: int) -> int:
    if sheet_area_mm2 <= 0 or not piece_areas_mm2:
        return 0
    bins: list[int] = []
    for area in sorted((int(value) for value in piece_areas_mm2 if int(value) > 0), reverse=True):
        for index, remaining in enumerate(bins):
            if area <= remaining:
                bins[index] = remaining - area
                break
        else:
            bins.append(max(0, sheet_area_mm2 - area))
    return len(bins)


def _requirement_sort_key(group: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _board_sort_label(group),
        _material_role_sort(str(group.get("material_role") or "")),
        str(group.get("requirement_key") or ""),
    )


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _production_rows(
    *,
    quote: dict[str, Any],
    project: dict[str, Any],
    rows: list[dict[str, Any]],
    units_by_number: dict[int, dict[str, Any]],
    warnings_by_row: dict[tuple[int, str, str], list[dict[str, Any]]],
    board_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    repeat_counts: dict[tuple[str, int, str, str, int, int], int] = defaultdict(int)
    production_rows: list[dict[str, Any]] = []

    for row in rows:
        section = str(row.get("section") or "").strip()
        if section not in MATERIAL_SECTIONS:
            continue

        unit_number = _non_negative_int(row.get("unit_number"), 0)
        source_type = "quote_panel" if unit_number == 0 else "unit"
        desc = str(row.get("desc") or "Cutlist row").strip() or "Cutlist row"
        length = _non_negative_int(row.get("length"), 0)
        width = _non_negative_int(row.get("width"), 0)
        quantity = _non_negative_int(row.get("qty"), 0)
        material_role = _material_role_for_section(section)
        unit = units_by_number.get(unit_number)
        board_id = _material_board_id(row=row, quote=quote, unit=unit, material_role=material_role)
        board = board_lookup.get(board_id) if board_id else None
        row_warnings = warnings_by_row.get((unit_number, section, desc), [])
        repeat_key = (source_type, unit_number, section, desc, length, width)
        repeat_counts[repeat_key] += 1
        part_id = _part_id(
            quote=quote,
            source_type=source_type,
            unit_number=unit_number,
            section=section,
            desc=desc,
            length=length,
            width=width,
            repeat=repeat_counts[repeat_key],
        )

        production_rows.append(
            {
                "part_id": part_id,
                "project_id": str(project.get("id") or quote.get("project_id") or ""),
                "project_name": str(project.get("name") or "Project"),
                "quote_id": str(quote.get("id") or ""),
                "quote_name": str(quote.get("name") or "Quote"),
                "quote_number": str(quote.get("quote_number") or ""),
                "revision": max(1, _non_negative_int(quote.get("revision"), 1)),
                "source_type": source_type,
                "unit_number": unit_number,
                "unit_label": _unit_label(unit_number),
                "unit_type_key": str((unit or {}).get("unit_type_key") or ""),
                "section": section,
                "section_label": SECTION_LABELS.get(section, _title_words(section)),
                "material_role": material_role,
                "role_label": MATERIAL_ROLE_LABELS.get(material_role, _title_words(material_role)),
                "board_type_id": board_id or None,
                "board_name": _board_description(board) if board else "Unassigned material",
                "brand": str((board or {}).get("brand") or ""),
                "material": str((board or {}).get("material") or ""),
                "thickness": _optional_positive_int((board or {}).get("thickness")),
                "sheet_length_mm": _optional_positive_int((board or {}).get("length_mm")),
                "sheet_width_mm": _optional_positive_int((board or {}).get("width_mm")),
                "desc": desc,
                "length": length,
                "width": width,
                "quantity": quantity,
                "warning_count": len(row_warnings),
                "warning_messages": [str(warning.get("reason") or warning.get("message") or "") for warning in row_warnings],
            }
        )

    return production_rows


def _production_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}

    for row in rows:
        key = (
            row.get("board_type_id") or "",
            row.get("thickness") or 0,
            row.get("material") or "",
            row.get("material_role") or "",
            row.get("unit_number") or 0,
            row.get("section") or "",
        )
        group = groups_by_key.get(key)
        if group is None:
            group_key = _group_key(row)
            group = {
                "group_key": group_key,
                "board_type_id": row.get("board_type_id"),
                "board_name": row["board_name"],
                "brand": row["brand"],
                "material": row["material"],
                "thickness": row["thickness"],
                "sheet_length_mm": row["sheet_length_mm"],
                "sheet_width_mm": row["sheet_width_mm"],
                "material_role": row["material_role"],
                "role_label": row["role_label"],
                "unit_number": row["unit_number"],
                "unit_label": row["unit_label"],
                "section": row["section"],
                "section_label": row["section_label"],
                "row_count": 0,
                "piece_count": 0,
                "warning_count": 0,
                "part_ids": [],
                "rows": [],
            }
            groups_by_key[key] = group

        group["row_count"] += 1
        group["piece_count"] += int(row["quantity"])
        group["warning_count"] += int(row["warning_count"])
        group["part_ids"].append(row["part_id"])
        group["rows"].append(row)

    return sorted(groups_by_key.values(), key=_group_sort_key)


def _safe_material_summary(material_summary: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    part_ids_by_material: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in rows:
        board_id = str(row.get("board_type_id") or "").strip()
        role = str(row.get("material_role") or "").strip()
        if board_id and role:
            part_ids_by_material[(board_id, role)].append(str(row["part_id"]))

    groups = []
    for group in material_summary.get("groups") or []:
        board_id = str(group.get("board_type_id") or "").strip()
        role = str(group.get("material_role") or "").strip()
        groups.append(
            {
                "board_type_id": board_id,
                "material_role": role,
                "role_label": str(group.get("role_label") or MATERIAL_ROLE_LABELS.get(role) or _title_words(role)),
                "board_name": str(group.get("board_name") or ""),
                "brand": str(group.get("brand") or ""),
                "material": str(group.get("material") or ""),
                "thickness": _optional_positive_int(group.get("thickness")),
                "length_mm": _optional_positive_int(group.get("length_mm")),
                "width_mm": _optional_positive_int(group.get("width_mm")),
                "piece_count": _non_negative_int(group.get("piece_count"), 0),
                "area_m2": _non_negative_float(group.get("area_m2"), 0.0),
                "edge_m": _non_negative_float(group.get("edge_m"), 0.0),
                "estimated_sheets": _optional_positive_int(group.get("estimated_sheets"), allow_zero=True),
                "part_ids": part_ids_by_material.get((board_id, role), []),
            }
        )

    return {
        "groups": groups,
        "warnings": list(material_summary.get("warnings") or []),
        "total_area_m2": _non_negative_float(material_summary.get("total_area_m2"), 0.0),
        "total_piece_count": _non_negative_int(material_summary.get("total_piece_count"), 0),
        "total_edge_m": _non_negative_float(material_summary.get("total_edge_m"), 0.0),
        "total_estimated_sheets": _optional_positive_int(material_summary.get("total_estimated_sheets"), allow_zero=True),
    }


def _production_hardware_items(
    *,
    quote: dict[str, Any],
    pick_list: dict[str, Any],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    part_ids_by_unit: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        unit_number = _non_negative_int(row.get("unit_number"), 0)
        if unit_number > 0:
            part_ids_by_unit[unit_number].append(str(row["part_id"]))

    items = []
    for index, item in enumerate(pick_list.get("items") or [], start=1):
        unit_numbers = [_non_negative_int(value, 0) for value in item.get("unit_numbers") or []]
        related_part_ids = []
        for unit_number in unit_numbers:
            related_part_ids.extend(part_ids_by_unit.get(unit_number, []))
        item_type = str(item.get("item_type") or "item")
        item_ref_id = str(item.get("item_ref_id") or item.get("item_key") or index)
        items.append(
            {
                "part_id": _hardware_part_id(quote, item_type=item_type, item_ref_id=item_ref_id, index=index),
                "item_type": item_type,
                "type_label": str(item.get("type_label") or _title_words(item_type)),
                "item_key": str(item.get("item_key") or ""),
                "item_ref_id": item_ref_id,
                "item_name": str(item.get("item_name") or ""),
                "supplier": str(item.get("supplier") or ""),
                "code": str(item.get("code") or ""),
                "quantity": _non_negative_int(item.get("quantity"), 0),
                "uom": str(item.get("uom") or "pcs"),
                "unit_numbers": [unit_number for unit_number in unit_numbers if unit_number > 0],
                "used_in": list(item.get("used_in") or []),
                "usage_label": str(item.get("usage_label") or ""),
                "related_part_ids": sorted(set(related_part_ids), key=related_part_ids.index),
            }
        )
    return sorted(items, key=lambda item: (item["type_label"], item["item_name"], item["part_id"]))


def _label_for_row(row: dict[str, Any]) -> dict[str, Any]:
    dimensions = f"{row['length']} x {row['width']} mm"
    material = row["board_name"]
    return {
        "part_id": row["part_id"],
        "label": f"{row['part_id']} · {row['desc']} · {dimensions}",
        "source_type": row["source_type"],
        "unit_number": row["unit_number"],
        "unit_label": row["unit_label"],
        "section": row["section"],
        "desc": row["desc"],
        "dimensions_label": dimensions,
        "material_label": material,
        "quantity": row["quantity"],
        "warning_count": row["warning_count"],
    }


def _cutting_rows(cutting_list: dict[str, Any]) -> list[dict[str, Any]]:
    runtime_rows = [dict(row) for row in cutting_list.get("runtime_rows") or []]
    if runtime_rows:
        return runtime_rows

    rows: list[dict[str, Any]] = []
    for key, section in (
        ("carcass", "carcass"),
        ("panels", "panel"),
        ("hardware", "hardware"),
        ("extras", "extra_panel"),
    ):
        rows.extend({**dict(row), "section": section} for row in cutting_list.get(key, []) or [])
    return rows


def _warnings_by_cutlist_row(warnings: Any) -> dict[tuple[int, str, str], list[dict[str, Any]]]:
    result: dict[tuple[int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for warning in warnings or []:
        if not isinstance(warning, dict):
            continue
        key = (
            _non_negative_int(warning.get("unit_number"), 0),
            str(warning.get("section") or ""),
            str(warning.get("row_desc") or ""),
        )
        result[key].append(warning)
    return result


def _material_role_for_section(section: str) -> str:
    if section == "carcass":
        return "carcass"
    if section == "panel":
        return "door_panel"
    if section == "extra_panel":
        return "visible_panel"
    return ""


def _material_board_id(
    *,
    row: dict[str, Any],
    quote: dict[str, Any],
    unit: dict[str, Any] | None,
    material_role: str,
) -> str:
    if material_role == "carcass":
        return str((unit or {}).get("carcass_board_type_id") or quote.get("default_carcass_board_type_id") or "").strip()
    if material_role == "door_panel":
        return str((unit or {}).get("door_board_type_id") or quote.get("default_door_board_type_id") or "").strip()
    if material_role == "visible_panel":
        return str(
            row.get("board_type_id")
            or quote.get("default_panel_board_type_id")
            or (unit or {}).get("door_board_type_id")
            or quote.get("default_door_board_type_id")
            or ""
        ).strip()
    return ""


def _part_id(
    *,
    quote: dict[str, Any],
    source_type: str,
    unit_number: int,
    section: str,
    desc: str,
    length: int,
    width: int,
    repeat: int,
) -> str:
    quote_token = _slug(str(quote.get("quote_number") or "Q"))
    revision = max(1, _non_negative_int(quote.get("revision"), 1))
    source_token = f"U{unit_number:02d}" if source_type == "unit" else "QP"
    section_token = {
        "carcass": "CAR",
        "panel": "PAN",
        "extra_panel": "EXT",
    }.get(section, _slug(section)[:3] or "ROW")
    desc_token = _slug(desc)[:18] or "PART"
    return f"{quote_token}-R{revision}-{source_token}-{section_token}-{desc_token}-{length}X{width}-{repeat:02d}"


def _hardware_part_id(quote: dict[str, Any], *, item_type: str, item_ref_id: str, index: int) -> str:
    quote_token = _slug(str(quote.get("quote_number") or "Q"))
    revision = max(1, _non_negative_int(quote.get("revision"), 1))
    return f"{quote_token}-R{revision}-HW-{_slug(item_type)[:8] or 'ITEM'}-{_slug(item_ref_id)[:12] or index:0>3}"


def _group_key(row: dict[str, Any]) -> str:
    return "::".join(
        [
            str(row.get("board_type_id") or "unassigned"),
            str(row.get("thickness") or 0),
            str(row.get("material") or ""),
            str(row.get("material_role") or ""),
            str(row.get("unit_number") or 0),
            str(row.get("section") or ""),
        ]
    )


def _row_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _board_sort_label(row),
        _material_role_sort(str(row.get("material_role") or "")),
        _unit_sort(_non_negative_int(row.get("unit_number"), 0)),
        _section_sort(str(row.get("section") or "")),
        str(row.get("desc") or ""),
        _non_negative_int(row.get("length"), 0),
        _non_negative_int(row.get("width"), 0),
        str(row.get("part_id") or ""),
    )


def _group_sort_key(group: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _board_sort_label(group),
        _material_role_sort(str(group.get("material_role") or "")),
        _unit_sort(_non_negative_int(group.get("unit_number"), 0)),
        _section_sort(str(group.get("section") or "")),
    )


def _board_sort_label(row: dict[str, Any]) -> tuple[str, int, str, str]:
    return (
        str(row.get("brand") or "").lower(),
        _non_negative_int(row.get("thickness"), 0),
        str(row.get("material") or "").lower(),
        str(row.get("board_name") or "").lower(),
    )


def _material_role_sort(role: str) -> int:
    return {"carcass": 0, "door_panel": 1, "visible_panel": 2}.get(role, 99)


def _section_sort(section: str) -> int:
    return {"carcass": 0, "panel": 1, "extra_panel": 2, "hardware": 3}.get(section, 99)


def _unit_sort(unit_number: int) -> int:
    return unit_number if unit_number > 0 else 999_999


def _board_description(board: dict[str, Any] | None) -> str:
    if not board:
        return "Unassigned material"
    brand = str(board.get("brand") or "").strip()
    material = str(board.get("material") or "").strip()
    thickness = _optional_positive_int(board.get("thickness"))
    parts = [part for part in (brand, material) if part]
    label = " ".join(parts) if parts else "Board"
    return f"{label} ({thickness}mm)" if thickness else label


def _unit_label(unit_number: int) -> str:
    return f"Unit {unit_number}" if unit_number > 0 else "Quote-level"


def _slug(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().upper()).strip("-")
    return token or "X"


def _title_words(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[_\s-]+", value) if part) or "Item"


def _optional_positive_int(value: Any, *, allow_zero: bool = False) -> int | None:
    parsed = _non_negative_int(value, 0)
    if parsed > 0 or (allow_zero and parsed == 0 and value is not None):
        return parsed
    return None


def _non_negative_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(0, parsed)


def _non_negative_float(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, parsed)
