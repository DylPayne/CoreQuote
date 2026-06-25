from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


PRICE_COMPONENT_VALUES = {"unit", "sqm", "sheet", "edging_m", "labour_board"}
ORDER_UOM_VALUES = {"sheet", "m2", "m", "pairs", "pcs", "each", "unit", "set", "day", "trip", "board"}

PRICE_COMPONENT_ALIASES = {
    "each": "unit",
    "piece": "unit",
    "pieces": "unit",
    "sqm": "sqm",
    "sq_m": "sqm",
    "sq_meter": "sqm",
    "sq_metre": "sqm",
    "square_meter": "sqm",
    "square_metre": "sqm",
    "m2": "sqm",
    "sheets": "sheet",
    "edging": "edging_m",
    "edge_m": "edging_m",
    "edge_meter": "edging_m",
    "edge_metre": "edging_m",
    "edging_meter": "edging_m",
    "edging_metre": "edging_m",
    "labour": "labour_board",
    "labor": "labour_board",
    "board_labour": "labour_board",
    "board_labor": "labour_board",
    "labor_board": "labour_board",
}

ORDER_UOM_ALIASES = {
    "sheets": "sheet",
    "sqm": "m2",
    "sq_m": "m2",
    "sq_meter": "m2",
    "sq_metre": "m2",
    "square_meter": "m2",
    "square_metre": "m2",
    "meter": "m",
    "meters": "m",
    "metre": "m",
    "metres": "m",
    "pair": "pairs",
    "pr": "pairs",
    "pc": "pcs",
    "piece": "pcs",
    "pieces": "pcs",
    "ea": "each",
    "unit_each": "each",
    "units": "unit",
    "sets": "set",
    "days": "day",
    "trips": "trip",
    "boards": "board",
}

BOARD_COMPONENT_UOMS_BY_MODE = {
    "sheet": {
        "sheet": {"sheet"},
        "edging_m": {"m"},
        "labour_board": {"board"},
    },
    "sqm": {
        "sqm": {"m2"},
    },
}
BOARD_COMPONENT_UOMS = {
    component: uoms
    for mode_components in BOARD_COMPONENT_UOMS_BY_MODE.values()
    for component, uoms in mode_components.items()
}


@dataclass(frozen=True)
class PricingFieldIssue:
    field: str
    code: str
    message: str
    guidance: str
    input_value: Any = None

    def as_fastapi_error(self) -> dict[str, Any]:
        return {
            "type": "value_error",
            "loc": ["body", self.field],
            "msg": self.message,
            "input": self.input_value,
        }


class PricingFieldValidationError(ValueError):
    def __init__(self, issues: list[PricingFieldIssue]):
        self.issues = tuple(issues)
        super().__init__("; ".join(issue.message for issue in issues))


def normalize_price_component(value: Any, *, field: str = "price_component", default: str | None = "unit") -> str:
    text, key = _canonical_input(value, default=default)
    if not text:
        raise PricingFieldValidationError(
            [
                PricingFieldIssue(
                    field=field,
                    code="missing_price_component",
                    message="Price component is required.",
                    guidance="Choose one of unit, sqm, sheet, edging_m, or labour_board.",
                    input_value=value,
                )
            ]
        )
    canonical = _canonical_value(key, PRICE_COMPONENT_VALUES, PRICE_COMPONENT_ALIASES)
    if canonical is None:
        raise PricingFieldValidationError(
            [
                PricingFieldIssue(
                    field=field,
                    code="invalid_price_component",
                    message="Price component must be unit, sqm, sheet, edging_m, or labour_board.",
                    guidance="Use a canonical pricing component that matches how quote calculations consume the row.",
                    input_value=value,
                )
            ]
        )
    return canonical


def normalize_order_uom(value: Any, *, field: str = "order_uom", default: str | None = None) -> str:
    text, key = _canonical_input(value, default=default)
    if not text:
        raise PricingFieldValidationError(
            [
                PricingFieldIssue(
                    field=field,
                    code="missing_uom",
                    message="Unit is required.",
                    guidance="Choose one of sheet, m2, m, pairs, pcs, each, unit, set, day, trip, or board.",
                    input_value=value,
                )
            ]
        )
    canonical = _canonical_value(key, ORDER_UOM_VALUES, ORDER_UOM_ALIASES)
    if canonical is None:
        raise PricingFieldValidationError(
            [
                PricingFieldIssue(
                    field=field,
                    code="invalid_uom",
                    message="Unit uses an unsupported canonical value.",
                    guidance="Use a familiar unit such as sheet, m2, m, pcs, pairs, each, day, trip, or board.",
                    input_value=value,
                )
            ]
        )
    return canonical


def validate_pricing_combination(
    *,
    item_type: str,
    price_component: str,
    uom: str | None = None,
    uom_field: str = "uom",
    board_costing_mode: str | None = None,
) -> None:
    item_type = str(item_type or "").strip().lower()
    price_component = str(price_component or "").strip().lower()
    issues: list[PricingFieldIssue] = []

    if item_type and item_type != "board" and price_component != "unit":
        issues.append(
            PricingFieldIssue(
                field="price_component",
                code="forbidden_price_component",
                message="Non-board pricing rows must use price_component = unit.",
                guidance="Use unit pricing for slides, hinges, handles, and extras.",
                input_value=price_component,
            )
        )

    if item_type == "board":
        mode = _board_mode(board_costing_mode)
        allowed = BOARD_COMPONENT_UOMS_BY_MODE[mode] if mode else BOARD_COMPONENT_UOMS
        if price_component not in allowed:
            mode_suffix = f" for {mode} board pricing" if mode else " for board pricing"
            issues.append(
                PricingFieldIssue(
                    field="price_component",
                    code="forbidden_price_component",
                    message=f"Price component {price_component or '(blank)'} is not allowed{mode_suffix}.",
                    guidance="Use sqm for sqm-priced boards, or sheet, edging_m, and labour_board for sheet-priced boards.",
                    input_value=price_component,
                )
            )
        elif uom:
            normalized_uom = str(uom).strip().lower()
            allowed_uoms = allowed[price_component]
            if normalized_uom not in allowed_uoms:
                issues.append(
                    PricingFieldIssue(
                        field=uom_field,
                        code="forbidden_uom",
                        message=(
                            f"Unit {normalized_uom or '(blank)'} does not match "
                            f"price_component {price_component}."
                        ),
                        guidance=f"Use {', '.join(sorted(allowed_uoms))} for {price_component}.",
                        input_value=uom,
                    )
                )

    if issues:
        raise PricingFieldValidationError(issues)


def pricing_issues_as_fastapi_errors(error: PricingFieldValidationError) -> list[dict[str, Any]]:
    return [issue.as_fastapi_error() for issue in error.issues]


def _canonical_input(value: Any, *, default: str | None) -> tuple[str, str]:
    if value is None or str(value).strip() == "":
        text = default or ""
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text.strip().lower())
    key = text.replace("-", "_").replace("/", "_").replace(" ", "_")
    return text, key


def _canonical_value(key: str, allowed: set[str], aliases: dict[str, str]) -> str | None:
    if key in allowed:
        return key
    return aliases.get(key)


def _board_mode(value: str | None) -> str | None:
    mode = str(value or "").strip().lower()
    if mode in {"sheet", "sqm"}:
        return mode
    return None
