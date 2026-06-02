from __future__ import annotations

import math
from typing import Any

from corequote_core.panels import PANEL_PRESET_KEYS, PANEL_PRESET_LABELS, compute_panel_rows
from corequote_api.cutting_runtime import CutlistRuntimeService, canonical_unit_type_key
from corequote_api.projects_quotes_payloads import (
    _clean_custom_panels_payload,
    _default_dims_for_panel_preset_from_quote,
    _default_dims_for_unit_type_from_quote,
    _optional_uuid,
)


def _compute_quote_custom_panel_rows(
    *,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    state: dict[str, Any],
    board_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_units = [
        {
            "unit_type": str(unit.get("unit_type_key") or unit.get("unit_type") or ""),
            "width": int(unit.get("width", 0) or 0),
        }
        for unit in units
    ]

    return compute_panel_rows(
        units=normalized_units,
        state=state,
        default_panel_board_type_id=quote.get("default_panel_board_type_id"),
        panel_preset_keys=PANEL_PRESET_KEYS,
        panel_preset_labels=PANEL_PRESET_LABELS,
        default_dims_for_panel_preset=lambda key: _default_dims_for_panel_preset_from_quote(quote, key),
        default_dims_for_unit_type=lambda unit_type: _default_dims_for_unit_type_from_quote(quote, unit_type),
        board_length_for=lambda board_type_id: int(
            (
                board_lookup.get(str(board_type_id or "").strip())
                or {}
            ).get("length_mm", 0)
            or 0
        ),
    )


def _custom_panel_row_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "desc": str(row.get("Desc", "")),
        "length": int(row.get("L", 0) or 0),
        "width": int(row.get("W", 0) or 0),
        "qty": int(row.get("Qty", 0) or 0),
        "board_type_id": _optional_uuid(row.get("board_type_id")),
    }


def _build_cutting_list_preview(
    *,
    company_id: str,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    runtime_service: CutlistRuntimeService,
    use_rulesets: bool,
    board_lookup: dict[str, dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    default_slide = slide_lookup.get(str(quote.get("default_slide_id") or ""))
    payload_units = [_to_runtime_unit(unit, default_slide=default_slide) for unit in units]
    preview = runtime_service.build_preview(
        company_id=company_id,
        units=payload_units,
        use_db_rulesets=use_rulesets,
    )

    if not preview:
        preview = {
            "carcass": [],
            "panels": [],
            "hardware": [],
            "extras": [],
            "runtime_rows": [],
            "runtime_mode": "legacy",
            "unit_sources": [],
        }

    state = _clean_custom_panels_payload(quote.get("custom_panels"))
    custom_rows = _compute_quote_custom_panel_rows(
        quote=quote,
        units=units,
        state=state,
        board_lookup=board_lookup,
    )
    for row in custom_rows:
        compact = {
            "unit_number": 0,
            "desc": str(row["Desc"]),
            "length": int(row["L"]),
            "width": int(row["W"]),
            "qty": int(row["Qty"]),
        }
        preview.setdefault("extras", []).append(compact)
        preview.setdefault("runtime_rows", []).append(
            {
                **compact,
                "section": "extra_panel",
                "edge_long_1": False,
                "edge_long_2": False,
                "edge_short_1": False,
                "edge_short_2": False,
                "board_type_id": row.get("board_type_id"),
            }
        )

    return preview


def _to_runtime_unit(unit: dict[str, Any], *, default_slide: dict[str, Any] | None) -> dict[str, Any]:
    extra_params = dict(unit.get("extra_params") or {})
    if default_slide:
        extra_params.setdefault("slide_brand", default_slide.get("brand", ""))
        extra_params.setdefault("slide_model", default_slide.get("model", ""))
        extra_params.setdefault("slide_code", default_slide.get("code", ""))
        extra_params.setdefault("slide_length", int(default_slide.get("length", 0) or 0))
        extra_params.setdefault("slide_side_length", int(default_slide.get("side_length", 0) or 0))
        extra_params.setdefault("slide_side_clearance_total", int(default_slide.get("side_clearance_total", 0) or 0))
        extra_params.setdefault("slide_side_height_uplift", int(default_slide.get("side_height_uplift", 0) or 0))
    return {
        "unit_number": int(unit["unit_number"]),
        "unit_type": str(unit["unit_type_key"]),
        "height": int(unit["height"]),
        "width": int(unit["width"]),
        "depth": int(unit["depth"]),
        "thickness": int(unit.get("thickness", 16) or 16),
        "extra_params": extra_params,
    }


def _price_quote(
    *,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    quote_extras: list[dict[str, Any]],
    runtime_service: CutlistRuntimeService,
    company_id: str,
    use_rulesets: bool,
    price_lookup: dict[tuple[str, str, str], dict[str, Any]],
    board_lookup: dict[str, dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
    hinge_lookup: dict[str, dict[str, Any]],
    handle_lookup: dict[str, dict[str, Any]],
    extra_lookup: dict[str, dict[str, Any]],
    active_price_list_id: str | None,
    markup_bps: int,
    vat_rate_bps: int,
) -> dict[str, Any]:
    cutting_list = _build_cutting_list_preview(
        company_id=company_id,
        quote=quote,
        units=units,
        runtime_service=runtime_service,
        use_rulesets=use_rulesets,
        board_lookup=board_lookup,
        slide_lookup=slide_lookup,
    )

    required: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add_required(
        *,
        item_type: str,
        item_key: str | None,
        price_component: str,
        description: str,
        qty: float,
        uom: str,
    ) -> None:
        if not item_key:
            return
        rounded_qty = float(qty)
        if rounded_qty <= 0:
            return
        key = (item_type, item_key, price_component)
        row = required.get(key)
        if row:
            row["qty"] += rounded_qty
            return
        required[key] = {
            "item_type": item_type,
            "item_key": item_key,
            "price_component": price_component,
            "description": description,
            "qty": rounded_qty,
            "uom": uom,
        }

    units_by_number = {int(unit["unit_number"]): unit for unit in units}
    board_usage: dict[str, dict[str, Any]] = {}
    for row in cutting_list.get("runtime_rows", []):
        section = str(row.get("section", ""))
        unit = units_by_number.get(int(row.get("unit_number", 0)))
        if section in {"carcass", "panel"} and not unit:
            continue

        board_id: str | None
        if section == "carcass":
            board_id = str(unit.get("carcass_board_type_id") or quote.get("default_carcass_board_type_id") or "")
        elif section == "panel":
            board_id = str(unit.get("door_board_type_id") or quote.get("default_door_board_type_id") or "")
        elif section == "extra_panel":
            explicit_board_id = str(row.get("board_type_id") or "").strip()
            board_id = explicit_board_id or str(
                quote.get("default_panel_board_type_id")
                or (unit or {}).get("door_board_type_id")
                or quote.get("default_door_board_type_id")
                or ""
            )
        else:
            continue
        if not board_id:
            continue

        length = int(row.get("length", 0) or 0)
        width = int(row.get("width", 0) or 0)
        qty = int(row.get("qty", 0) or 0)
        if length <= 0 or width <= 0 or qty <= 0:
            continue

        usage = board_usage.setdefault(board_id, {"piece_areas": [], "total_area_mm2": 0})
        usage["piece_areas"].extend([length * width] * qty)
        usage["total_area_mm2"] += length * width * qty

    for board_id, usage in board_usage.items():
        board = board_lookup.get(board_id)
        if not board:
            continue
        item_key = f"board::{board_id}"
        costing_mode = str(board.get("costing_mode", "sheet") or "sheet").strip().lower()
        description = _board_description(board)
        if costing_mode == "sqm":
            area_m2 = float(usage["total_area_mm2"]) / 1_000_000.0
            add_required(
                item_type="board",
                item_key=item_key,
                price_component="sqm",
                description=description,
                qty=area_m2,
                uom="m2",
            )
            continue
        sheet_area = int(board.get("length_mm", 0) or 0) * int(board.get("width_mm", 0) or 0)
        sheets_used = _estimate_boards_used(usage["piece_areas"], sheet_area)
        add_required(
            item_type="board",
            item_key=item_key,
            price_component="sheet",
            description=description,
            qty=float(sheets_used),
            uom="sheet",
        )

    for unit in units:
        canonical_type = canonical_unit_type_key(str(unit["unit_type_key"]))
        extra_params = unit.get("extra_params", {}) or {}
        height = int(unit.get("height", 0) or 0)
        num_drawers = _int_or_default(extra_params.get("num_drawers"), default=3 if canonical_type == "Base Draw" else 0, minimum=0)
        num_doors = _int_or_default(
            extra_params.get("num_doors"),
            default=2 if canonical_type in {"Base Door", "Wall Door", "Tall Door"} else 0,
            minimum=0,
        )

        if canonical_type == "Base Draw":
            slide_id = str(quote.get("default_slide_id") or "")
            add_required(
                item_type="slide",
                item_key=f"slide::{slide_id}" if slide_id else None,
                price_component="unit",
                description=_slide_description(slide_lookup.get(slide_id)),
                qty=float(num_drawers),
                uom="pairs",
            )
            drawer_handle_id = str(quote.get("default_drawer_handle_id") or "")
            drawer_handle_qty = _int_or_default(extra_params.get("handle_qty"), default=num_drawers, minimum=0)
            add_required(
                item_type="handle",
                item_key=f"handle::{drawer_handle_id}" if drawer_handle_id else None,
                price_component="unit",
                description=_handle_description(handle_lookup.get(drawer_handle_id)),
                qty=float(drawer_handle_qty),
                uom="pcs",
            )

        if canonical_type in {"Base Door", "Wall Door", "Tall Door"}:
            hinge_id = str(quote.get("default_hinge_id") or "")
            hinges_per_door = max(2, math.ceil(height / 600)) if height > 0 else 2
            add_required(
                item_type="hinge",
                item_key=f"hinge::{hinge_id}" if hinge_id else None,
                price_component="unit",
                description=_hinge_description(hinge_lookup.get(hinge_id)),
                qty=float(num_doors * hinges_per_door),
                uom="pcs",
            )

            if canonical_type == "Wall Door":
                handle_id = str(quote.get("default_wall_handle_id") or "")
            elif canonical_type == "Tall Door":
                handle_id = str(quote.get("default_tall_handle_id") or "")
            else:
                handle_id = str(quote.get("default_base_handle_id") or "")

            handle_qty = _int_or_default(extra_params.get("handle_qty"), default=num_doors, minimum=0)
            add_required(
                item_type="handle",
                item_key=f"handle::{handle_id}" if handle_id else None,
                price_component="unit",
                description=_handle_description(handle_lookup.get(handle_id)),
                qty=float(handle_qty),
                uom="pcs",
            )

    for selected_extra in quote_extras:
        extra_id = str(selected_extra.get("extra_id") or "")
        quantity = _int_or_default(selected_extra.get("quantity"), default=1, minimum=0)
        add_required(
            item_type="extra",
            item_key=f"extra::{extra_id}" if extra_id else None,
            price_component="unit",
            description=_extra_description(extra_lookup.get(extra_id)),
            qty=float(quantity),
            uom="pcs",
        )

    lines: list[dict[str, Any]] = []
    missing_items: list[str] = []
    subtotal_cents = 0
    for _, row in sorted(required.items(), key=lambda entry: (entry[1]["item_type"], entry[1]["description"])):
        lookup_key = (row["item_type"], row["item_key"], row["price_component"])
        active_price = price_lookup.get(lookup_key)
        unit_price_cents: int | None = None
        line_total_cents: int | None = None
        missing = active_price is None
        if active_price is None:
            missing_items.append(f"{row['item_key']}::{row['price_component']}")
        else:
            unit_price_cents = int(active_price["unit_price_cents"])
            line_total_cents = int(round(float(row["qty"]) * unit_price_cents))
            subtotal_cents += line_total_cents

        lines.append(
            {
                "item_type": row["item_type"],
                "item_key": row["item_key"],
                "price_component": row["price_component"],
                "description": row["description"],
                "qty": float(round(float(row["qty"]), 4)),
                "uom": row["uom"],
                "unit_price_cents": unit_price_cents,
                "line_total_cents": line_total_cents,
                "missing": missing,
            }
        )

    sell_before_vat_cents = int(round(subtotal_cents * (1.0 + (markup_bps / 10_000.0))))
    vat_cents = int(round(sell_before_vat_cents * (vat_rate_bps / 10_000.0)))
    grand_total_cents = sell_before_vat_cents + vat_cents

    return {
        "quote_id": quote["id"],
        "quote_name": quote["name"],
        "is_complete": bool(active_price_list_id) and len(missing_items) == 0,
        "missing_items": missing_items,
        "subtotal_cents": subtotal_cents,
        "sell_before_vat_cents": sell_before_vat_cents,
        "vat_cents": vat_cents,
        "grand_total_cents": grand_total_cents,
        "lines": lines,
    }


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


def _int_or_default(value: Any, *, default: int, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _board_description(board: dict[str, Any] | None) -> str:
    if not board:
        return "Board"
    return f"{board['brand']} {board['material']} ({board['thickness']}mm)"


def _slide_description(slide: dict[str, Any] | None) -> str:
    if not slide:
        return "Slide"
    code = str(slide.get("code", "")).strip()
    return f"{slide['brand']} {slide['model']}{f' ({code})' if code else ''}"


def _hinge_description(hinge: dict[str, Any] | None) -> str:
    if not hinge:
        return "Hinge"
    code = str(hinge.get("code", "")).strip()
    return f"{hinge['brand']} {hinge['model']}{f' ({code})' if code else ''}"


def _handle_description(handle: dict[str, Any] | None) -> str:
    if not handle:
        return "Handle"
    supplier = str(handle.get("supplier", "")).strip()
    return f"{handle['name']}{f' · {supplier}' if supplier else ''}"


def _extra_description(extra: dict[str, Any] | None) -> str:
    if not extra:
        return "Extra"
    supplier = str(extra.get("supplier", "")).strip()
    return f"{extra['name']}{f' · {supplier}' if supplier else ''}"
