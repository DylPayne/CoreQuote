"""Hardware and extras pick-list helpers for workshop outputs."""

from __future__ import annotations

import math
from typing import Any


SIMPLIFIED_UNIT_TYPE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "Base Draw": ("Base Draw", "Base Drawer", "Base 1 Draw", "Base 2 Draw", "Base 3 Draw", "Base 4 Draw"),
    "Base Door": ("Base Door", "Base 1 Door", "Base 2 Door"),
    "Wall Door": ("Wall Door", "Wall 1 Door", "Wall 2 Door"),
    "Tall Door": ("Tall Door", "Tall Standard", "Tall Pantry"),
}
UNIT_TYPE_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in SIMPLIFIED_UNIT_TYPE_CANDIDATES.items()
    for alias in aliases
}

ITEM_TYPE_LABELS = {
    "slide": "Slides",
    "hinge": "Hinges",
    "handle": "Handles",
    "extra": "Extras",
}


def build_hardware_pick_list(
    *,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    quote_extras: list[dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
    hinge_lookup: dict[str, dict[str, Any]],
    handle_lookup: dict[str, dict[str, Any]],
    extra_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return grouped hardware and quote-extra quantities without pricing data."""

    items: dict[tuple[str, str], dict[str, Any]] = {}
    warnings: list[dict[str, Any]] = []

    def add_item(
        *,
        item_type: str,
        item_ref_id: str,
        item_name: str,
        supplier: str,
        code: str,
        quantity: int,
        uom: str,
        unit_number: int,
        used_in: str,
    ) -> None:
        item_ref_id = str(item_ref_id or "").strip()
        quantity = _non_negative_int(quantity, 0)
        if not item_ref_id or quantity <= 0:
            return

        key = (item_type, item_ref_id)
        item = items.get(key)
        if item is None:
            item = {
                "item_type": item_type,
                "type_label": ITEM_TYPE_LABELS.get(item_type, _title_words(item_type)),
                "item_key": f"{item_type}::{item_ref_id}",
                "item_ref_id": item_ref_id,
                "item_name": item_name,
                "supplier": supplier,
                "code": code,
                "quantity": 0,
                "uom": uom,
                "unit_numbers": [],
                "used_in": [],
                "usage_label": "",
            }
            items[key] = item

        item["quantity"] = int(item["quantity"]) + quantity
        if unit_number > 0 and unit_number not in item["unit_numbers"]:
            item["unit_numbers"].append(unit_number)
        if used_in and used_in not in item["used_in"]:
            item["used_in"].append(used_in)

    def add_warning(
        *,
        code: str,
        item_type: str,
        unit_number: int,
        item_ref_id: str | None,
        message: str,
    ) -> None:
        warnings.append(
            {
                "severity": "warning",
                "code": code,
                "item_type": item_type,
                "unit_number": int(unit_number),
                "item_ref_id": item_ref_id,
                "message": message,
            }
        )

    for unit in units:
        canonical_type = canonical_unit_type(str(unit.get("unit_type_key") or unit.get("unit_type") or ""))
        extra_params = unit.get("extra_params", {}) or {}
        unit_number = _non_negative_int(unit.get("unit_number"), 0)
        height = _non_negative_int(unit.get("height"), 0)

        if canonical_type == "Base Draw":
            num_drawers = _non_negative_int(extra_params.get("num_drawers"), 3)
            if num_drawers > 0:
                location = _unit_location(unit_number, "drawers")
                slide_id = str(extra_params.get("slide_id") or quote.get("default_slide_id") or "").strip()
                if slide_id:
                    slide = slide_lookup.get(slide_id)
                    if not slide:
                        add_warning(
                            code="missing_catalog_item",
                            item_type="slide",
                            unit_number=unit_number,
                            item_ref_id=slide_id,
                            message=f"Slide {slide_id} is not available for {location}.",
                        )
                    add_item(
                        item_type="slide",
                        item_ref_id=slide_id,
                        item_name=_slide_name(slide),
                        supplier=_brand_supplier(slide),
                        code=_catalog_code(slide),
                        quantity=num_drawers,
                        uom="pairs",
                        unit_number=unit_number,
                        used_in=location,
                    )
                else:
                    add_warning(
                        code="missing_slide_selection",
                        item_type="slide",
                        unit_number=unit_number,
                        item_ref_id=None,
                        message=f"Choose a drawer slide for {location}.",
                    )

                handle_qty = _non_negative_int(extra_params.get("handle_qty"), num_drawers)
                handle_id = str(extra_params.get("handle_id") or quote.get("default_drawer_handle_id") or "").strip()
                _add_handle_requirement(
                    add_item=add_item,
                    add_warning=add_warning,
                    handle_lookup=handle_lookup,
                    handle_id=handle_id,
                    handle_qty=handle_qty,
                    unit_number=unit_number,
                    location=location,
                    handle_label="drawer handle",
                )

        if canonical_type in {"Base Door", "Wall Door", "Tall Door"}:
            num_doors = _non_negative_int(extra_params.get("num_doors"), 2)
            if num_doors <= 0:
                continue

            location = _unit_location(unit_number, "doors")
            hinge_id = str(extra_params.get("hinge_id") or quote.get("default_hinge_id") or "").strip()
            hinges_per_door = max(2, math.ceil(height / 600)) if height > 0 else 2
            if hinge_id:
                hinge = hinge_lookup.get(hinge_id)
                if not hinge:
                    add_warning(
                        code="missing_catalog_item",
                        item_type="hinge",
                        unit_number=unit_number,
                        item_ref_id=hinge_id,
                        message=f"Hinge {hinge_id} is not available for {location}.",
                    )
                add_item(
                    item_type="hinge",
                    item_ref_id=hinge_id,
                    item_name=_hinge_name(hinge),
                    supplier=_brand_supplier(hinge),
                    code=_catalog_code(hinge),
                    quantity=num_doors * hinges_per_door,
                    uom="pcs",
                    unit_number=unit_number,
                    used_in=location,
                )
            else:
                add_warning(
                    code="missing_hinge_selection",
                    item_type="hinge",
                    unit_number=unit_number,
                    item_ref_id=None,
                    message=f"Choose a door hinge for {location}.",
                )

            if canonical_type == "Wall Door":
                default_handle_id = str(quote.get("default_wall_handle_id") or "").strip()
                handle_label = "wall handle"
            elif canonical_type == "Tall Door":
                default_handle_id = str(quote.get("default_tall_handle_id") or "").strip()
                handle_label = "tall handle"
            else:
                default_handle_id = str(quote.get("default_base_handle_id") or "").strip()
                handle_label = "base handle"
            handle_id = str(extra_params.get("handle_id") or default_handle_id).strip()
            handle_qty = _non_negative_int(extra_params.get("handle_qty"), num_doors)
            _add_handle_requirement(
                add_item=add_item,
                add_warning=add_warning,
                handle_lookup=handle_lookup,
                handle_id=handle_id,
                handle_qty=handle_qty,
                unit_number=unit_number,
                location=location,
                handle_label=handle_label,
            )

    for selected_extra in quote_extras:
        extra_id = str(selected_extra.get("extra_id") or "").strip()
        quantity = _non_negative_int(selected_extra.get("quantity"), 1)
        if not extra_id or quantity <= 0:
            continue
        extra = extra_lookup.get(extra_id)
        if not extra:
            add_warning(
                code="missing_catalog_item",
                item_type="extra",
                unit_number=0,
                item_ref_id=extra_id,
                message=f"Extra {extra_id} is not available for this quote.",
            )
        add_item(
            item_type="extra",
            item_ref_id=extra_id,
            item_name=_extra_name(extra),
            supplier=_catalog_supplier(extra),
            code=_catalog_code(extra),
            quantity=quantity,
            uom="pcs",
            unit_number=0,
            used_in="Quote extra",
        )

    grouped_items = sorted(items.values(), key=_item_sort_key)
    for item in grouped_items:
        item["unit_numbers"] = sorted(int(value) for value in item["unit_numbers"])
        item["usage_label"] = _join_labels(list(item["used_in"]))

    return {
        "items": grouped_items,
        "warnings": warnings,
        "total_item_count": len(grouped_items),
        "total_quantity": sum(int(item["quantity"]) for item in grouped_items),
    }


def canonical_unit_type(unit_type: str) -> str:
    return UNIT_TYPE_ALIAS_TO_CANONICAL.get(unit_type, unit_type)


def _add_handle_requirement(
    *,
    add_item,
    add_warning,
    handle_lookup: dict[str, dict[str, Any]],
    handle_id: str,
    handle_qty: int,
    unit_number: int,
    location: str,
    handle_label: str,
) -> None:
    if handle_qty <= 0:
        return
    if not handle_id:
        add_warning(
            code="missing_handle_selection",
            item_type="handle",
            unit_number=unit_number,
            item_ref_id=None,
            message=f"Choose a {handle_label} for {location}.",
        )
        return

    handle = handle_lookup.get(handle_id)
    if not handle:
        add_warning(
            code="missing_catalog_item",
            item_type="handle",
            unit_number=unit_number,
            item_ref_id=handle_id,
            message=f"Handle {handle_id} is not available for {location}.",
        )
    add_item(
        item_type="handle",
        item_ref_id=handle_id,
        item_name=_handle_name(handle),
        supplier=_catalog_supplier(handle),
        code=_catalog_code(handle),
        quantity=handle_qty,
        uom="pcs",
        unit_number=unit_number,
        used_in=location,
    )


def _unit_location(unit_number: int, part_label: str) -> str:
    if unit_number > 0:
        return f"Unit {unit_number} {part_label}"
    return part_label


def _slide_name(slide: dict[str, Any] | None) -> str:
    if not slide:
        return "Slide"
    return " ".join(part for part in (str(slide.get("brand") or "").strip(), str(slide.get("model") or "").strip()) if part) or "Slide"


def _hinge_name(hinge: dict[str, Any] | None) -> str:
    if not hinge:
        return "Hinge"
    return " ".join(part for part in (str(hinge.get("brand") or "").strip(), str(hinge.get("model") or "").strip()) if part) or "Hinge"


def _handle_name(handle: dict[str, Any] | None) -> str:
    if not handle:
        return "Handle"
    return str(handle.get("name") or "").strip() or "Handle"


def _extra_name(extra: dict[str, Any] | None) -> str:
    if not extra:
        return "Extra"
    return str(extra.get("name") or "").strip() or "Extra"


def _brand_supplier(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("brand") or "").strip()


def _catalog_supplier(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("supplier") or "").strip()


def _catalog_code(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return str(row.get("code") or "").strip()


def _item_sort_key(item: dict[str, Any]) -> tuple[int, str, str]:
    order = {"slide": 10, "hinge": 20, "handle": 30, "extra": 40}
    return (
        order.get(str(item.get("item_type") or ""), 999),
        str(item.get("item_name") or ""),
        str(item.get("item_ref_id") or ""),
    )


def _join_labels(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _title_words(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("_", " ").replace("-", " ").split() if part)


def _non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = int(default)
    return max(0, parsed)
