"""Quote output review status for client and workshop handoff."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


EMPTY_MATERIAL_SUMMARY = {
    "groups": [],
    "warnings": [],
    "total_area_m2": 0,
    "total_piece_count": 0,
    "total_edge_m": 0,
    "total_estimated_sheets": None,
}

EMPTY_HARDWARE_PICK_LIST = {
    "items": [],
    "warnings": [],
    "total_item_count": 0,
    "total_quantity": 0,
}


def build_quote_output_review(
    *,
    quote: dict[str, Any],
    project: dict[str, Any],
    currency_code: str,
    readiness: dict[str, Any],
    cutting_list: dict[str, Any] | None,
    pricing_summary: dict[str, Any] | None,
    active_price_list_id: str | None,
    hardware_pick_list: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the quote-level output review payload from live quote status."""

    material_summary = _material_summary(pricing_summary)
    pick_list = hardware_pick_list or _hardware_pick_list(pricing_summary)
    unit_count = _positive_int(quote.get("unit_count"))
    cutlist_row_count = _cutlist_row_count(cutting_list)
    cutlist_warning_count = _warning_count(cutting_list.get("validation_warnings") if cutting_list else [])
    material_warning_count = _warning_count(material_summary.get("warnings"))
    hardware_warning_count = _warning_count(pick_list.get("warnings"))
    missing_price_count = _warning_count(pricing_summary.get("missing_prices") if pricing_summary else [])

    readiness_ready = bool(readiness.get("is_ready"))
    pricing_ready = (
        bool(active_price_list_id)
        and bool(pricing_summary)
        and bool(pricing_summary.get("is_complete"))
        and missing_price_count == 0
        and _positive_int(pricing_summary.get("grand_total_cents")) > 0
    )
    workshop_export_enabled = cutlist_row_count > 0
    workshop_ready = workshop_export_enabled and cutlist_warning_count == 0
    material_ready = bool(_list(material_summary.get("groups"))) and material_warning_count == 0
    hardware_ready = unit_count > 0 and hardware_warning_count == 0

    client_warning = _client_quote_warning(readiness_ready=readiness_ready, pricing_ready=pricing_ready)
    workshop_warning = _workshop_schedule_warning(
        row_count=cutlist_row_count,
        warning_count=cutlist_warning_count,
    )
    material_warning = _material_summary_warning(
        has_groups=bool(_list(material_summary.get("groups"))),
        warning_count=material_warning_count,
    )
    hardware_warning = _hardware_pick_list_warning(
        unit_count=unit_count,
        warning_count=hardware_warning_count,
    )

    return {
        "quote_id": str(quote.get("id") or ""),
        "quote_name": str(quote.get("name") or "Quote"),
        "project_id": str(project.get("id") or quote.get("project_id") or ""),
        "project_name": str(project.get("name") or "Project"),
        "quote_status": str(quote.get("status") or "draft"),
        "quote_number": str(quote.get("quote_number") or ""),
        "revision": max(1, _positive_int(quote.get("revision"))),
        "currency_code": currency_code,
        "client_quote_total_cents": _positive_int(pricing_summary.get("grand_total_cents") if pricing_summary else 0),
        "pricing_missing_price_count": missing_price_count,
        "cutlist_row_count": cutlist_row_count,
        "cutlist_warning_count": cutlist_warning_count,
        "material_warning_count": material_warning_count,
        "hardware_warning_count": hardware_warning_count,
        "readiness": readiness,
        "client_quote": _status(
            id="client_quote",
            label="Client quote",
            ready=client_warning is None,
            ready_message="Client quote can be generated with sell totals only. Internal costs and profit stay hidden.",
            warning_message=client_warning,
        ),
        "internal_pricing": _status(
            id="internal_pricing",
            label="Internal pricing confidence",
            ready=pricing_ready,
            ready_message="Quote total is priced with no missing price rows.",
            warning_message=_pricing_warning(
                active_price_list_id=active_price_list_id,
                pricing_summary=pricing_summary,
                missing_price_count=missing_price_count,
            ),
        ),
        "workshop_schedule": _status(
            id="workshop_schedule",
            label="Workshop schedule",
            ready=workshop_ready,
            ready_message=f"{cutlist_row_count} cutting-list {_plural(cutlist_row_count, 'row')} ready for workshop handoff.",
            warning_message=workshop_warning,
        ),
        "material_status": _status(
            id="material_summary",
            label="Material summary",
            ready=material_ready,
            ready_message="Material summary is ready for review.",
            warning_message=material_warning,
        ),
        "hardware_status": _status(
            id="hardware_pick_list",
            label="Hardware pick list",
            ready=hardware_ready,
            ready_message="Hardware pick list is ready for review.",
            warning_message=hardware_warning,
        ),
        "material_summary": material_summary,
        "hardware_pick_list": pick_list,
        "actions": [
            {
                "id": "client_quote_pdf",
                "group": "client",
                "label": "Client quote",
                "description": "Customer PDF with sell totals only. Internal costs and profit stay hidden.",
                "enabled": client_warning is None,
                "warning": client_warning,
                "hides_internal_costs": True,
                "action_target": "pricing",
            },
            {
                "id": "workshop_schedule",
                "group": "workshop",
                "label": "Workshop schedule",
                "description": "Cutting and production schedule for the workshop.",
                "enabled": workshop_export_enabled,
                "warning": workshop_warning,
                "hides_internal_costs": False,
                "action_target": "cutting-lists",
            },
            {
                "id": "production_handoff_csv",
                "group": "workshop",
                "label": "Production CSV",
                "description": "Cutting schedule rows for downstream workshop tools.",
                "enabled": workshop_export_enabled,
                "warning": workshop_warning,
                "hides_internal_costs": False,
                "action_target": "production",
            },
            {
                "id": "production_handoff_xlsx",
                "group": "workshop",
                "label": "Production workbook",
                "description": "XLSX handoff with cutting rows, materials, board requirements, hardware, labels, and warnings.",
                "enabled": workshop_export_enabled,
                "warning": workshop_warning,
                "hides_internal_costs": False,
                "action_target": "production",
            },
            {
                "id": "material_summary",
                "group": "workshop",
                "label": "Material summary",
                "description": "Board quantities and estimated sheets for internal ordering.",
                "enabled": material_ready,
                "warning": material_warning,
                "hides_internal_costs": False,
                "action_target": "pricing",
            },
            {
                "id": "hardware_pick_list",
                "group": "workshop",
                "label": "Hardware pick list",
                "description": "Slides, hinges, handles, and extras to pick for production.",
                "enabled": hardware_ready,
                "warning": hardware_warning,
                "hides_internal_costs": False,
                "action_target": "pricing",
            },
        ],
    }


def _status(
    *,
    id: str,
    label: str,
    ready: bool,
    ready_message: str,
    warning_message: str | None,
) -> dict[str, str]:
    return {
        "id": id,
        "label": label,
        "status": "ready" if ready else "needs_attention",
        "severity": "pass" if ready else "warning",
        "message": ready_message if ready else warning_message or "Review this output before generating it.",
    }


def _client_quote_warning(*, readiness_ready: bool, pricing_ready: bool) -> str | None:
    if not readiness_ready:
        return "Resolve readiness warnings before generating the client quote."
    if not pricing_ready:
        return "Finish pricing before generating the client quote."
    return None


def _pricing_warning(
    *,
    active_price_list_id: str | None,
    pricing_summary: dict[str, Any] | None,
    missing_price_count: int,
) -> str:
    if not active_price_list_id:
        return "Activate a price list before trusting internal pricing."
    if not pricing_summary:
        return "Build the quote pricing summary before trusting internal margin and totals."
    if missing_price_count:
        return "Review missing prices before trusting internal margin and totals."
    if _positive_int(pricing_summary.get("grand_total_cents")) <= 0:
        return "Add quote items before trusting internal margin and totals."
    return "Review quote pricing before generating outputs."


def _workshop_schedule_warning(*, row_count: int, warning_count: int) -> str | None:
    if warning_count:
        return "Cutting-list warnings will be included in the workshop schedule."
    if row_count == 0:
        return "Add cabinet units before generating the workshop schedule."
    return None


def _material_summary_warning(*, has_groups: bool, warning_count: int) -> str | None:
    if warning_count:
        return "Resolve material summary warnings before generating the material summary."
    if not has_groups:
        return "Add cabinet units and material choices before generating the material summary."
    return None


def _hardware_pick_list_warning(*, unit_count: int, warning_count: int) -> str | None:
    if warning_count:
        return "Choose missing hardware before generating the hardware pick list."
    if unit_count == 0:
        return "Add cabinet units before generating the hardware pick list."
    return None


def _material_summary(pricing_summary: dict[str, Any] | None) -> dict[str, Any]:
    if pricing_summary and isinstance(pricing_summary.get("material_summary"), dict):
        return pricing_summary["material_summary"]
    return deepcopy(EMPTY_MATERIAL_SUMMARY)


def _hardware_pick_list(pricing_summary: dict[str, Any] | None) -> dict[str, Any]:
    if pricing_summary and isinstance(pricing_summary.get("hardware_pick_list"), dict):
        return pricing_summary["hardware_pick_list"]
    return deepcopy(EMPTY_HARDWARE_PICK_LIST)


def _cutlist_row_count(cutting_list: dict[str, Any] | None) -> int:
    if not cutting_list:
        return 0
    runtime_rows = _list(cutting_list.get("runtime_rows"))
    if runtime_rows:
        return len(runtime_rows)
    return sum(len(_list(cutting_list.get(section))) for section in ("carcass", "panels", "hardware", "extras"))


def _warning_count(rows: Any) -> int:
    return len(_list(rows))


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _plural(count: int, noun: str) -> str:
    return noun if count == 1 else f"{noun}s"
