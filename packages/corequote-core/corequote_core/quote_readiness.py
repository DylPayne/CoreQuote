"""Quote readiness checks for review/export workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


ReadinessSeverity = Literal["pass", "warning", "error"]
ReadinessStatus = Literal["ready", "needs_attention"]
ReadinessActionTarget = Literal[
    "project",
    "quote",
    "units",
    "panels",
    "cutting-lists",
    "pricing",
    "outputs",
    "libraries-pricing",
]


@dataclass(frozen=True)
class QuoteReadinessCheck:
    id: str
    severity: ReadinessSeverity
    title: str
    message: str
    action_label: str
    action_target: ReadinessActionTarget

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def evaluate_quote_readiness(
    *,
    quote: dict[str, Any],
    project: dict[str, Any],
    units: list[dict[str, Any]],
    cutting_list: dict[str, Any] | None,
    pricing_summary: dict[str, Any] | None,
    active_price_list_id: str | None,
    hardware_pick_list: dict[str, Any] | None = None,
    cutting_error: str | None = None,
    pricing_error: str | None = None,
) -> dict[str, Any]:
    """Return structured quote readiness checks from current quote data."""

    hardware_pick_list = hardware_pick_list or _hardware_pick_list_from_pricing_summary(pricing_summary)
    cutting_rows = _cutting_rows(cutting_list)
    validation_warnings = _cutlist_validation_warnings(cutting_list)
    invalid_cutting_rows = [] if validation_warnings else [row for row in cutting_rows if _invalid_cutting_row(row)]
    cutlist_warning_count = len(validation_warnings) if validation_warnings else len(invalid_cutting_rows)
    custom_panel_rows = [row for row in cutting_rows if str(row.get("section") or "") == "extra_panel"]
    panel_rows = [row for row in cutting_rows if str(row.get("section") or "") == "panel"]
    missing_default_boards = _missing_default_boards(quote, custom_panel_rows)
    missing_unit_carcass_count = _missing_unit_carcass_count(quote, units)
    missing_unit_front_count = _missing_unit_front_count(quote, units, panel_rows)
    missing_custom_panel_count = _missing_custom_panel_board_count(quote, custom_panel_rows)
    missing_price_count = _missing_price_count(pricing_summary)
    hardware_check = _hardware_pick_list_check(
        hardware_pick_list=hardware_pick_list,
        has_units=bool(units),
    )

    checks = [
        _project_details_check(project),
        _unit_count_check(units),
        _default_boards_check(missing_default_boards),
        _unit_boards_check(
            missing_unit_carcass_count=missing_unit_carcass_count,
            missing_unit_front_count=missing_unit_front_count,
            missing_custom_panel_count=missing_custom_panel_count,
        ),
        _cutlist_rows_check(
            row_count=len(cutting_rows),
            invalid_count=cutlist_warning_count,
            cutting_error=cutting_error,
            has_units=bool(units),
        ),
        _missing_prices_check(
            active_price_list_id=active_price_list_id,
            missing_price_count=missing_price_count,
            pricing_error=pricing_error,
        ),
        _quote_totals_check(
            pricing_summary=pricing_summary,
            pricing_error=pricing_error,
            has_units=bool(units),
            missing_price_count=missing_price_count,
        ),
        hardware_check,
        _required_outputs_check(
            has_valid_cutting_rows=bool(cutting_rows) and cutlist_warning_count == 0 and not cutting_error,
            has_priced_total=_has_priced_total(pricing_summary, missing_price_count=missing_price_count),
            has_component_pick_list=hardware_check.severity == "pass",
            has_units=bool(units),
        ),
    ]

    warning_count = sum(1 for check in checks if check.severity == "warning")
    error_count = sum(1 for check in checks if check.severity == "error")
    is_ready = warning_count == 0 and error_count == 0
    status: ReadinessStatus = "ready" if is_ready else "needs_attention"

    return {
        "quote_id": str(quote.get("id") or ""),
        "status": status,
        "is_ready": is_ready,
        "summary_title": "Ready for review" if is_ready else "Needs attention before review",
        "summary_message": _summary_message(is_ready=is_ready, warning_count=warning_count, error_count=error_count),
        "warning_count": warning_count,
        "error_count": error_count,
        "checks": [check.to_dict() for check in checks],
    }


def _project_details_check(project: dict[str, Any]) -> QuoteReadinessCheck:
    missing = []
    if not _has_text(project.get("client")):
        missing.append("client")
    if not _has_text(project.get("address")):
        missing.append("site address")

    if not missing:
        return QuoteReadinessCheck(
            id="project_details",
            severity="pass",
            title="Client details confirmed",
            message="The quote has enough client and site detail for review.",
            action_label="Review project",
            action_target="project",
        )

    return QuoteReadinessCheck(
        id="project_details",
        severity="warning",
        title="Confirm client details",
        message=f"Add the {_join_words(missing)} so this quote is clearly tied to the right job.",
        action_label="Update project details",
        action_target="project",
    )


def _unit_count_check(units: list[dict[str, Any]]) -> QuoteReadinessCheck:
    if units:
        return QuoteReadinessCheck(
            id="unit_count",
            severity="pass",
            title="Cabinets added",
            message=f"{len(units)} cabinet {_plural(len(units), 'unit')} included in this quote.",
            action_label="Review units",
            action_target="units",
        )

    return QuoteReadinessCheck(
        id="unit_count",
        severity="warning",
        title="Add cabinet units",
        message="This quote has no cabinets yet, so there is nothing to price, cut, or review.",
        action_label="Add units",
        action_target="units",
    )


def _default_boards_check(missing_default_boards: list[str]) -> QuoteReadinessCheck:
    if not missing_default_boards:
        return QuoteReadinessCheck(
            id="default_boards",
            severity="pass",
            title="Default boards selected",
            message="New units and quote-level panels have board choices to fall back to.",
            action_label="Review quote setup",
            action_target="quote",
        )

    return QuoteReadinessCheck(
        id="default_boards",
        severity="warning",
        title="Choose default boards",
        message=f"Set the {_join_words(missing_default_boards)} so new quote items have trusted material choices.",
        action_label="Edit quote setup",
        action_target="quote",
    )


def _unit_boards_check(
    *,
    missing_unit_carcass_count: int,
    missing_unit_front_count: int,
    missing_custom_panel_count: int,
) -> QuoteReadinessCheck:
    issue_count = missing_unit_carcass_count + missing_unit_front_count + missing_custom_panel_count
    if issue_count == 0:
        return QuoteReadinessCheck(
            id="unit_boards",
            severity="pass",
            title="Unit boards selected",
            message="Every cabinet and panel has the material choices needed for review.",
            action_label="Review units",
            action_target="units",
        )

    parts = []
    if missing_unit_carcass_count:
        parts.append(f"{missing_unit_carcass_count} {_plural(missing_unit_carcass_count, 'cabinet')} without a carcass board")
    if missing_unit_front_count:
        parts.append(f"{missing_unit_front_count} {_plural(missing_unit_front_count, 'cabinet')} without a door or drawer-front board")
    if missing_custom_panel_count:
        parts.append(f"{missing_custom_panel_count} quote panel {_plural(missing_custom_panel_count, 'row')} without a board")
    only_panel_rows = missing_custom_panel_count > 0 and not missing_unit_carcass_count and not missing_unit_front_count

    return QuoteReadinessCheck(
        id="unit_boards",
        severity="warning",
        title="Choose boards for the quote",
        message=f"{_capitalize(_join_words(parts))} cannot be trusted for pricing or cutting yet.",
        action_label="Review panel boards" if only_panel_rows else "Review board choices",
        action_target="panels" if only_panel_rows else "units",
    )


def _cutlist_rows_check(
    *,
    row_count: int,
    invalid_count: int,
    cutting_error: str | None,
    has_units: bool,
) -> QuoteReadinessCheck:
    if cutting_error:
        return QuoteReadinessCheck(
            id="cutlist_rows",
            severity="warning",
            title="Build the cutting list",
            message="Finish the quote setup so workshop cutting rows can be checked.",
            action_label="Review units",
            action_target="units",
        )
    if invalid_count:
        return QuoteReadinessCheck(
            id="cutlist_rows",
            severity="warning",
            title="Fix cutlist rows",
            message=f"{invalid_count} cutting-list {_plural(invalid_count, 'row')} has missing material choices or unusable sizes, so workshop output is not ready.",
            action_label="Review cutting list",
            action_target="cutting-lists",
        )
    if row_count > 0:
        return QuoteReadinessCheck(
            id="cutlist_rows",
            severity="pass",
            title="Cutting list looks usable",
            message=f"{row_count} cutting-list {_plural(row_count, 'row')} ready for review.",
            action_label="Review cutting list",
            action_target="cutting-lists",
        )
    return QuoteReadinessCheck(
        id="cutlist_rows",
        severity="warning",
        title="Generate cutting rows",
        message=(
            "Add cabinet units before checking the workshop list."
            if not has_units
            else "Review the unit setup so the workshop list has rows to check."
        ),
        action_label="Review cutting list",
        action_target="cutting-lists",
    )


def _missing_prices_check(
    *,
    active_price_list_id: str | None,
    missing_price_count: int,
    pricing_error: str | None,
) -> QuoteReadinessCheck:
    if pricing_error:
        return QuoteReadinessCheck(
            id="missing_prices",
            severity="warning",
            title="Review quote pricing",
            message="Finish setup choices so required prices can be checked.",
            action_label="Review pricing",
            action_target="pricing",
        )
    if not active_price_list_id:
        return QuoteReadinessCheck(
            id="missing_prices",
            severity="warning",
            title="Activate a price list",
            message="Open Libraries > Pricing and make one price list active before trusting quote totals.",
            action_label="Open price lists",
            action_target="libraries-pricing",
        )
    if missing_price_count:
        return QuoteReadinessCheck(
            id="missing_prices",
            severity="warning",
            title="Add missing prices",
            message=(
                f"{missing_price_count} required {_plural(missing_price_count, 'price')} missing from the active price list, "
                "so totals are not ready for review."
            ),
            action_label="Open price list",
            action_target="libraries-pricing",
        )
    return QuoteReadinessCheck(
        id="missing_prices",
        severity="pass",
        title="Prices available",
        message="Required price list items are available for the current quote.",
        action_label="Review pricing",
        action_target="pricing",
    )


def _quote_totals_check(
    *,
    pricing_summary: dict[str, Any] | None,
    pricing_error: str | None,
    has_units: bool,
    missing_price_count: int,
) -> QuoteReadinessCheck:
    if _has_priced_total(pricing_summary, missing_price_count=missing_price_count):
        return QuoteReadinessCheck(
            id="quote_totals",
            severity="pass",
            title="Quote total ready",
            message="The quote has a priced total ready for review.",
            action_label="Review pricing",
            action_target="pricing",
        )

    if pricing_error:
        message = "Finish board and unit choices before quote totals can be checked."
    elif not has_units:
        message = "Add cabinet units before checking the quote total."
    else:
        message = "Review prices and cabinet selections before trusting the quote total."

    return QuoteReadinessCheck(
        id="quote_totals",
        severity="warning",
        title="Build a quote total",
        message=message,
        action_label="Review pricing",
        action_target="pricing",
    )


def _hardware_pick_list_check(
    *,
    hardware_pick_list: dict[str, Any] | None,
    has_units: bool,
) -> QuoteReadinessCheck:
    if not has_units:
        return QuoteReadinessCheck(
            id="hardware_pick_list",
            severity="pass",
            title="Hardware pick list pending",
            message="Add cabinet units before checking slides, hinges, handles, and extras.",
            action_label="Review units",
            action_target="units",
        )

    warning_count = _hardware_pick_list_warning_count(hardware_pick_list)
    if warning_count:
        return QuoteReadinessCheck(
            id="hardware_pick_list",
            severity="warning",
            title="Choose hardware for the quote",
            message=f"{warning_count} component {_plural(warning_count, 'choice')} {_count_verb(warning_count)} attention before workshop handoff.",
            action_label="Review quote hardware",
            action_target="quote",
        )

    item_count = _hardware_pick_list_item_count(hardware_pick_list)
    if item_count:
        return QuoteReadinessCheck(
            id="hardware_pick_list",
            severity="pass",
            title="Hardware pick list ready",
            message=f"{item_count} hardware or extra {_plural(item_count, 'line')} ready for workshop review.",
            action_label="Review outputs",
            action_target="outputs",
        )

    return QuoteReadinessCheck(
        id="hardware_pick_list",
        severity="pass",
        title="Hardware pick list ready",
        message="No slides, hinges, handles, or extras are currently selected for this quote.",
        action_label="Review outputs",
        action_target="outputs",
    )


def _required_outputs_check(
    *,
    has_valid_cutting_rows: bool,
    has_priced_total: bool,
    has_component_pick_list: bool,
    has_units: bool,
) -> QuoteReadinessCheck:
    if has_valid_cutting_rows and has_priced_total and has_component_pick_list:
        return QuoteReadinessCheck(
            id="required_outputs",
            severity="pass",
            title="Review outputs ready",
            message="The quote has the working outputs needed before client or workshop handoff.",
            action_label="Review outputs",
            action_target="outputs",
        )

    if not has_units:
        message = "Add cabinet units so CoreQuote can prepare review outputs."
    else:
        missing = []
        if not has_valid_cutting_rows:
            missing.append("a usable cutting list")
        if not has_priced_total:
            missing.append("a priced quote total")
        if not has_component_pick_list:
            missing.append("a complete hardware pick list")
        message = f"Prepare {_join_words(missing)} before review."

    return QuoteReadinessCheck(
        id="required_outputs",
        severity="warning",
        title="Prepare review outputs",
        message=message,
        action_label="Review outputs",
        action_target="outputs",
    )


def _summary_message(*, is_ready: bool, warning_count: int, error_count: int) -> str:
    if is_ready:
        return "This quote has client details, cabinet units, board choices, cutting rows, component pick list, and priced totals ready for review."
    if error_count:
        return (
            f"{error_count} readiness {_plural(error_count, 'check')} "
            f"{_count_verb(error_count)} review before this quote can be trusted."
        )
    return (
        f"{warning_count} readiness {_plural(warning_count, 'check')} "
        f"{_count_verb(warning_count)} attention before this quote is ready for review."
    )


def _missing_default_boards(quote: dict[str, Any], custom_panel_rows: list[dict[str, Any]]) -> list[str]:
    missing = []
    if not _has_id(quote.get("default_carcass_board_type_id")):
        missing.append("default carcass board")
    if not _has_id(quote.get("default_door_board_type_id")):
        missing.append("default door or drawer-front board")
    if custom_panel_rows and not _has_id(quote.get("default_panel_board_type_id")):
        missing.append("default panel board")
    return missing


def _missing_unit_carcass_count(quote: dict[str, Any], units: list[dict[str, Any]]) -> int:
    return sum(
        1
        for unit in units
        if not _has_id(unit.get("carcass_board_type_id") or quote.get("default_carcass_board_type_id"))
    )


def _missing_unit_front_count(
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    panel_rows: list[dict[str, Any]],
) -> int:
    if not panel_rows:
        return 0
    panel_unit_numbers = {
        int(row.get("unit_number", 0) or 0)
        for row in panel_rows
        if int(row.get("unit_number", 0) or 0) > 0
    }
    count = 0
    for unit in units:
        unit_number = int(unit.get("unit_number", 0) or 0)
        if unit_number not in panel_unit_numbers:
            continue
        if not _has_id(unit.get("door_board_type_id") or quote.get("default_door_board_type_id")):
            count += 1
    return count


def _missing_custom_panel_board_count(quote: dict[str, Any], custom_panel_rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in custom_panel_rows:
        if not _has_id(
            row.get("board_type_id")
            or quote.get("default_panel_board_type_id")
            or quote.get("default_door_board_type_id")
        ):
            count += 1
    return count


def _cutting_rows(cutting_list: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not cutting_list:
        return []

    runtime_rows = cutting_list.get("runtime_rows")
    if isinstance(runtime_rows, list) and runtime_rows:
        return [row for row in runtime_rows if isinstance(row, dict)]

    rows: list[dict[str, Any]] = []
    for section_name in ("carcass", "panels", "hardware", "extras"):
        section_rows = cutting_list.get(section_name)
        if not isinstance(section_rows, list):
            continue
        section = "panel" if section_name == "panels" else "extra_panel" if section_name == "extras" else section_name
        rows.extend({**row, "section": section} for row in section_rows if isinstance(row, dict))
    return rows


def _cutlist_validation_warnings(cutting_list: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not cutting_list:
        return []
    warnings = cutting_list.get("validation_warnings")
    if isinstance(warnings, list):
        return [warning for warning in warnings if isinstance(warning, dict)]
    return []


def _invalid_cutting_row(row: dict[str, Any]) -> bool:
    return (
        not _has_text(row.get("desc"))
        or _positive_int(row.get("length")) <= 0
        or _positive_int(row.get("width")) <= 0
        or _positive_int(row.get("qty")) <= 0
    )


def _missing_price_count(pricing_summary: dict[str, Any] | None) -> int:
    if not pricing_summary:
        return 0
    missing_prices = pricing_summary.get("missing_prices")
    if isinstance(missing_prices, list) and missing_prices:
        return len(missing_prices)
    missing_items = pricing_summary.get("missing_items")
    if isinstance(missing_items, list):
        return len(missing_items)
    lines = pricing_summary.get("lines")
    if isinstance(lines, list):
        return sum(1 for line in lines if isinstance(line, dict) and bool(line.get("missing")))
    return 0


def _hardware_pick_list_from_pricing_summary(pricing_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not pricing_summary:
        return {"items": [], "warnings": []}
    pick_list = pricing_summary.get("hardware_pick_list")
    if isinstance(pick_list, dict):
        return pick_list
    return {"items": [], "warnings": []}


def _hardware_pick_list_warning_count(hardware_pick_list: dict[str, Any] | None) -> int:
    if not hardware_pick_list:
        return 0
    warnings = hardware_pick_list.get("warnings")
    if not isinstance(warnings, list):
        return 0
    return sum(1 for warning in warnings if isinstance(warning, dict))


def _hardware_pick_list_item_count(hardware_pick_list: dict[str, Any] | None) -> int:
    if not hardware_pick_list:
        return 0
    items = hardware_pick_list.get("items")
    if not isinstance(items, list):
        return 0
    return sum(1 for item in items if isinstance(item, dict))


def _has_priced_total(pricing_summary: dict[str, Any] | None, *, missing_price_count: int) -> bool:
    if not pricing_summary or missing_price_count:
        return False
    return _positive_int(pricing_summary.get("grand_total_cents")) > 0


def _has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _has_id(value: Any) -> bool:
    return bool(str(value or "").strip())


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _plural(count: int, noun: str) -> str:
    return noun if count == 1 else f"{noun}s"


def _count_verb(count: int) -> str:
    return "needs" if count == 1 else "need"


def _join_words(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _capitalize(value: str) -> str:
    if not value:
        return value
    return f"{value[0].upper()}{value[1:]}"
