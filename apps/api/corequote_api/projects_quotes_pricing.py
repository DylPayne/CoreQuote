from __future__ import annotations

from typing import Any

from corequote_core.detailed_pricing import price_quote_detailed, settings_from_mapping
from corequote_core.panels import PANEL_PRESET_KEYS, PANEL_PRESET_LABELS, compute_panel_rows
from corequote_api.cutting_runtime import CutlistRuntimeService
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

    return price_quote_detailed(
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
