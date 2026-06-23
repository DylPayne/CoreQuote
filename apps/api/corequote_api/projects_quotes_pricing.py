from __future__ import annotations

from typing import Any

from corequote_core.detailed_pricing import price_quote_detailed, settings_from_mapping
from corequote_core.panels import PANEL_PRESET_KEYS, PANEL_PRESET_LABELS, compute_panel_rows
from corequote_api.cutlist_validation import preview_with_validation
from corequote_api.cutting_runtime import CutlistRuntimeService
from corequote_api.projects_quotes_errors import WorkspaceValidationError
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
            "production_metadata": dict(row.get("production_metadata") or {}),
        }


def _build_cutting_list_preview(
    *,
    company_id: str,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    runtime_service: CutlistRuntimeService,
    use_rulesets: bool,
    board_lookup: dict[str, dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    slide_lookup = slide_lookup or {}
    default_slide = slide_lookup.get(str(quote.get("default_slide_id") or ""))
    payload_units = [
        _to_runtime_unit(
            unit,
            quote=quote,
            board_lookup=board_lookup,
            slide_lookup=slide_lookup,
            default_slide=default_slide,
            allow_missing_board_fallback=True,
        )
        for unit in units
    ]
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
                "grain_direction": "none",
                "can_rotate": True,
                "production_metadata": dict(row.get("production_metadata") or {}),
            }
        )

    return preview_with_validation(
        preview,
        quote=quote,
        units=units,
        board_lookup=board_lookup,
        slide_lookup=slide_lookup,
        require_materials=True,
    )


def _to_runtime_unit(
    unit: dict[str, Any],
    *,
    quote: dict[str, Any],
    board_lookup: dict[str, dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]] | None = None,
    default_slide: dict[str, Any] | None = None,
    allow_missing_board_fallback: bool = False,
) -> dict[str, Any]:
    extra_params = dict(unit.get("extra_params") or {})
    unit_slide = (slide_lookup or {}).get(str(extra_params.get("slide_id") or "")) or default_slide
    if unit_slide:
        extra_params.setdefault("slide_brand", unit_slide.get("brand", ""))
        extra_params.setdefault("slide_model", unit_slide.get("model", ""))
        extra_params.setdefault("slide_code", unit_slide.get("code", ""))
        extra_params.setdefault("slide_length", int(unit_slide.get("length", 0) or 0))
        extra_params.setdefault("slide_side_length", int(unit_slide.get("side_length", 0) or 0))
        extra_params.setdefault("slide_side_clearance_total", int(unit_slide.get("side_clearance_total", 0) or 0))
        extra_params.setdefault("slide_side_height_uplift", int(unit_slide.get("side_height_uplift", 0) or 0))
        extra_params.setdefault("slide_mount_type", str(unit_slide.get("mount_type") or "side_mount"))
        extra_params.setdefault("slide_product_family", str(unit_slide.get("product_family") or ""))
        extra_params.setdefault("slide_required_depth_mm", int(unit_slide.get("required_depth_mm", 0) or 0))
        extra_params.setdefault("slide_drawer_depth_deduction_mm", int(unit_slide.get("drawer_depth_deduction_mm", 0) or 0))
        extra_params.setdefault("slide_box_width_deduction_mm", int(unit_slide.get("box_width_deduction_mm", 0) or 0))
        extra_params.setdefault("drawer_system_kind", str(unit_slide.get("drawer_system_kind") or "conventional"))
        extra_params.setdefault("drawer_system_config", dict(unit_slide.get("drawer_system_config") or {}))
    try:
        thickness = _resolved_unit_thickness(unit, quote=quote, board_lookup=board_lookup)
    except WorkspaceValidationError as exc:
        if not allow_missing_board_fallback or "must be a positive integer" in str(exc):
            raise
        thickness = _fallback_unit_thickness(unit)
    return {
        "unit_number": int(unit["unit_number"]),
        "unit_type": str(unit["unit_type_key"]),
        "height": int(unit["height"]),
        "width": int(unit["width"]),
        "depth": int(unit["depth"]),
        "thickness": thickness,
        "extra_params": extra_params,
    }


def _resolved_unit_thickness(
    unit: dict[str, Any],
    *,
    quote: dict[str, Any],
    board_lookup: dict[str, dict[str, Any]],
) -> int:
    board_id = str(unit.get("carcass_board_type_id") or quote.get("default_carcass_board_type_id") or "").strip()
    if not board_id:
        raise WorkspaceValidationError("Unit carcass board is required to determine thickness")
    board = board_lookup.get(board_id)
    if not board:
        raise WorkspaceValidationError("Unit carcass board is not visible for this company")
    thickness = int(board.get("thickness", 0) or 0)
    if thickness <= 0:
        raise WorkspaceValidationError("Unit carcass board thickness must be a positive integer")
    return thickness


def _fallback_unit_thickness(unit: dict[str, Any]) -> int:
    try:
        thickness = int(unit.get("thickness", 16) or 16)
    except (TypeError, ValueError):
        return 16
    return thickness if thickness > 0 else 16


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
    pricing_settings: dict[str, Any],
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

    cutlist_warnings = list(cutting_list.get("validation_warnings", []))
    summary = price_quote_detailed(
        quote=quote,
        units=units,
        quote_extras=quote_extras,
        cutting_rows=cutting_list.get("runtime_rows", []),
        settings=settings_from_mapping(pricing_settings),
        price_lookup=price_lookup,
        board_lookup=board_lookup,
        slide_lookup=slide_lookup,
        hinge_lookup=hinge_lookup,
        handle_lookup=handle_lookup,
        extra_lookup=extra_lookup,
        active_price_list_id=active_price_list_id,
    )
    summary["cutlist_warnings"] = cutlist_warnings
    if cutlist_warnings:
        summary["is_complete"] = False
    return summary
