"""Hardware and extras pick-list helpers for workshop outputs."""

from __future__ import annotations

import math
from typing import Any, Mapping


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
    optional_items: dict[tuple[str, str], dict[str, Any]] = {}
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
        _add_pick_list_item(
            collection=items,
            item_type=item_type,
            item_ref_id=item_ref_id,
            item_name=item_name,
            supplier=supplier,
            code=code,
            quantity=quantity,
            uom=uom,
            unit_number=unit_number,
            used_in=used_in,
        )

    def add_optional_item(
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
        _add_pick_list_item(
            collection=optional_items,
            item_type=item_type,
            item_ref_id=item_ref_id,
            item_name=item_name,
            supplier=supplier,
            code=code,
            quantity=quantity,
            uom=uom,
            unit_number=unit_number,
            used_in=used_in,
        )

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
        width = _non_negative_int(unit.get("width"), 0)
        depth = _non_negative_int(unit.get("depth"), 0)

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
                    _add_configured_accessories(
                        add_item=add_item,
                        add_optional_item=add_optional_item,
                        add_warning=add_warning,
                        primary_item=slide,
                        primary_item_type="slide",
                        primary_item_id=slide_id,
                        extra_lookup=extra_lookup,
                        handle_lookup=handle_lookup,
                        hinge_lookup=hinge_lookup,
                        slide_lookup=slide_lookup,
                        quantity_context=_drawer_quantity_context(
                            unit_height=height,
                            unit_width=width,
                            unit_depth=depth,
                            extra_params=extra_params,
                            slide=slide,
                            num_drawers=num_drawers,
                        ),
                        unit_number=unit_number,
                        location=location,
                    )
                    _add_drawer_system_hardware_items(
                        add_item=add_item,
                        add_warning=add_warning,
                        slide=slide,
                        slide_id=slide_id,
                        extra_params=extra_params,
                        extra_lookup=extra_lookup,
                        handle_lookup=handle_lookup,
                        hinge_lookup=hinge_lookup,
                        num_drawers=num_drawers,
                        unit_number=unit_number,
                        location=location,
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
                _add_configured_accessories(
                    add_item=add_item,
                    add_optional_item=add_optional_item,
                    add_warning=add_warning,
                    primary_item=hinge,
                    primary_item_type="hinge",
                    primary_item_id=hinge_id,
                    extra_lookup=extra_lookup,
                    handle_lookup=handle_lookup,
                    hinge_lookup=hinge_lookup,
                    slide_lookup=slide_lookup,
                    quantity_context=_door_quantity_context(
                        unit_height=height,
                        unit_width=width,
                        unit_depth=depth,
                        extra_params=extra_params,
                        hinge=hinge,
                        num_doors=num_doors,
                        hinges_per_door=hinges_per_door,
                    ),
                    unit_number=unit_number,
                    location=location,
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
    grouped_optional_items = sorted(optional_items.values(), key=_item_sort_key)
    for item in [*grouped_items, *grouped_optional_items]:
        item["unit_numbers"] = sorted(int(value) for value in item["unit_numbers"])
        item["usage_label"] = _join_labels(list(item["used_in"]))

    return {
        "items": grouped_items,
        "optional_items": grouped_optional_items,
        "warnings": warnings,
        "total_item_count": len(grouped_items),
        "total_quantity": sum(int(item["quantity"]) for item in grouped_items),
    }


def canonical_unit_type(unit_type: str) -> str:
    return UNIT_TYPE_ALIAS_TO_CANONICAL.get(unit_type, unit_type)


def _add_pick_list_item(
    *,
    collection: dict[tuple[str, str], dict[str, Any]],
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
    item = collection.get(key)
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
        collection[key] = item

    item["quantity"] = int(item["quantity"]) + quantity
    if unit_number > 0 and unit_number not in item["unit_numbers"]:
        item["unit_numbers"].append(unit_number)
    if used_in and used_in not in item["used_in"]:
        item["used_in"].append(used_in)


def _add_configured_accessories(
    *,
    add_item,
    add_optional_item,
    add_warning,
    primary_item: dict[str, Any] | None,
    primary_item_type: str,
    primary_item_id: str,
    extra_lookup: dict[str, dict[str, Any]],
    handle_lookup: dict[str, dict[str, Any]],
    hinge_lookup: dict[str, dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
    quantity_context: dict[str, Any],
    unit_number: int,
    location: str,
) -> None:
    config = _accessory_config(primary_item)
    for index, raw_item in enumerate(config.get("accessories") or []):
        if not isinstance(raw_item, Mapping):
            continue
        item_name = str(raw_item.get("name") or "").strip()
        if not item_name:
            continue

        item_type = str(raw_item.get("item_type") or "extra").strip().lower()
        if item_type not in ITEM_TYPE_LABELS:
            item_type = "extra"

        item_ref_id = str(raw_item.get("item_ref_id") or "").strip()
        synthetic_ref = False
        if not item_ref_id:
            item_ref_id = f"accessory:{primary_item_type}:{primary_item_id}:{index}:{_slug(item_name)}"
            synthetic_ref = True

        condition = raw_item.get("condition") if isinstance(raw_item.get("condition"), Mapping) else {}
        quantity_rule = str(raw_item.get("quantity_rule") or "per_unit").strip().lower()
        base_quantity = _non_negative_int(raw_item.get("quantity"), 1)
        quantity = _configured_accessory_quantity(
            base_quantity=base_quantity,
            quantity_rule=quantity_rule,
            condition=condition,
            context=quantity_context,
        )
        if quantity <= 0:
            continue

        catalog_item = _configured_hardware_catalog_item(
            item_type=item_type,
            item_ref_id=item_ref_id,
            extra_lookup=extra_lookup,
            handle_lookup=handle_lookup,
            hinge_lookup=hinge_lookup,
            slide_lookup=slide_lookup,
        )
        if item_ref_id and not synthetic_ref and catalog_item is None:
            add_warning(
                code="missing_catalog_item",
                item_type=item_type,
                unit_number=unit_number,
                item_ref_id=item_ref_id,
                message=f"{item_name} {item_ref_id} is not available for {location}.",
            )

        required = bool(raw_item.get("required", True))
        enabled = bool(raw_item.get("enabled", False))
        add_target = add_item if required or enabled else add_optional_item
        add_target(
            item_type=item_type,
            item_ref_id=item_ref_id,
            item_name=_configured_hardware_name(raw_item, catalog_item, fallback=item_name),
            supplier=str(raw_item.get("supplier") or _catalog_supplier(catalog_item) or _brand_supplier(primary_item) or "").strip(),
            code=str(raw_item.get("code") or _catalog_code(catalog_item) or "").strip(),
            quantity=quantity,
            uom=str(raw_item.get("uom") or "pcs").strip() or "pcs",
            unit_number=unit_number,
            used_in=location,
        )


def _accessory_config(primary_item: dict[str, Any] | None) -> dict[str, Any]:
    config = (primary_item or {}).get("accessory_config") or {}
    return dict(config) if isinstance(config, Mapping) else {}


def _drawer_quantity_context(
    *,
    unit_height: int,
    unit_width: int,
    unit_depth: int,
    extra_params: dict[str, Any],
    slide: dict[str, Any] | None,
    num_drawers: int,
) -> dict[str, Any]:
    drawer_front_heights = _drawer_front_heights(unit_height=unit_height, extra_params=extra_params, num_drawers=num_drawers)
    drawer_front_height = max(drawer_front_heights) if drawer_front_heights else 0
    drawer_front_back_height = max(0, drawer_front_height - 100)
    side_height_uplift = _non_negative_int(extra_params.get("slide_side_height_uplift") or (slide or {}).get("side_height_uplift"), 0)
    drawer_side_height = max(0, drawer_front_back_height + side_height_uplift)
    drawer_system_config = _drawer_system_config(extra_params, slide)
    return {
        "unit_height": unit_height,
        "unit_width": unit_width,
        "unit_depth": unit_depth,
        "num_drawers": num_drawers,
        "drawer_count": num_drawers,
        "slide_pair_count": num_drawers,
        "drawer_front_height": drawer_front_height,
        "drawer_front_heights": drawer_front_heights,
        "drawer_side_height": drawer_side_height,
        "hardware_variant": _hardware_variant(slide),
        "load_class": str(drawer_system_config.get("load_class") or (slide or {}).get("load_class") or "").strip(),
    }


def _door_quantity_context(
    *,
    unit_height: int,
    unit_width: int,
    unit_depth: int,
    extra_params: dict[str, Any],
    hinge: dict[str, Any] | None,
    num_doors: int,
    hinges_per_door: int,
) -> dict[str, Any]:
    hinge_count = num_doors * hinges_per_door
    return {
        "unit_height": unit_height,
        "unit_width": unit_width,
        "unit_depth": unit_depth,
        "door_count": num_doors,
        "num_doors": num_doors,
        "hinges_per_door": hinges_per_door,
        "hinge_count": hinge_count,
        "hardware_variant": _hardware_variant(hinge),
        "load_class": str(extra_params.get("load_class") or "").strip(),
    }


def _configured_accessory_quantity(
    *,
    base_quantity: int,
    quantity_rule: str,
    condition: Mapping[str, Any],
    context: dict[str, Any],
) -> int:
    if not _condition_matches(condition, context):
        return 0
    basis = _quantity_basis(quantity_rule=quantity_rule, condition=condition, context=context)
    return base_quantity * basis


def _quantity_basis(*, quantity_rule: str, condition: Mapping[str, Any], context: dict[str, Any]) -> int:
    normalized = quantity_rule.replace("-", "_")
    if normalized in {"fixed", "per_unit"}:
        return 1
    if normalized in {"per_drawer", "per_slide_pair"}:
        if _condition_field(condition) == "drawer_front_height":
            return _matching_drawer_front_count(condition, context)
        return _non_negative_int(context.get("num_drawers") or context.get("drawer_count") or context.get("slide_pair_count"), 0)
    if normalized == "per_hinge":
        return _non_negative_int(context.get("hinge_count"), 0)
    if normalized == "per_door":
        return _non_negative_int(context.get("door_count") or context.get("num_doors"), 0)
    return 1


def _condition_matches(condition: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    field = _condition_field(condition)
    operator = _condition_operator(condition)
    if field == "always" or operator == "always":
        return True
    value = context.get(field)
    if isinstance(value, list):
        return any(_condition_value_matches(item, operator, condition) for item in value)
    return _condition_value_matches(value, operator, condition)


def _matching_drawer_front_count(condition: Mapping[str, Any], context: Mapping[str, Any]) -> int:
    values = context.get("drawer_front_heights")
    if not isinstance(values, list):
        return _non_negative_int(context.get("num_drawers"), 0) if _condition_matches(condition, context) else 0
    return sum(1 for value in values if _condition_value_matches(value, _condition_operator(condition), condition))


def _condition_value_matches(value: Any, operator: str, condition: Mapping[str, Any]) -> bool:
    if operator == "always":
        return True
    comparison_number = condition.get("value_number")
    if comparison_number is None and "value" in condition:
        comparison_number = condition.get("value")
    comparison_text = str(condition.get("value_text") or condition.get("value") or "").strip()

    if operator in {"greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal"}:
        actual = _float_or_none(value)
        expected = _float_or_none(comparison_number)
        if actual is None or expected is None:
            return False
        if operator == "greater_than":
            return actual > expected
        if operator == "greater_than_or_equal":
            return actual >= expected
        if operator == "less_than":
            return actual < expected
        return actual <= expected

    actual_text = str(value or "").strip()
    if operator == "equals":
        if comparison_text:
            return actual_text.lower() == comparison_text.lower()
        expected = _float_or_none(comparison_number)
        actual = _float_or_none(value)
        return expected is not None and actual is not None and actual == expected
    if operator == "not_equals":
        if comparison_text:
            return actual_text.lower() != comparison_text.lower()
        expected = _float_or_none(comparison_number)
        actual = _float_or_none(value)
        return expected is not None and actual is not None and actual != expected
    return False


def _condition_field(condition: Mapping[str, Any]) -> str:
    field = str(condition.get("field") or "always").strip().lower().replace("-", "_")
    aliases = {
        "height": "unit_height",
        "width": "unit_width",
        "depth": "unit_depth",
        "drawer_height": "drawer_front_height",
        "front_height": "drawer_front_height",
        "doors": "door_count",
        "hinges": "hinge_count",
        "variant": "hardware_variant",
    }
    return aliases.get(field, field)


def _condition_operator(condition: Mapping[str, Any]) -> str:
    operator = str(condition.get("operator") or "always").strip().lower().replace("-", "_")
    aliases = {
        ">": "greater_than",
        "gt": "greater_than",
        ">=": "greater_than_or_equal",
        "gte": "greater_than_or_equal",
        "<": "less_than",
        "lt": "less_than",
        "<=": "less_than_or_equal",
        "lte": "less_than_or_equal",
        "==": "equals",
        "=": "equals",
        "eq": "equals",
        "!=": "not_equals",
        "neq": "not_equals",
    }
    return aliases.get(operator, operator)


def _drawer_front_heights(*, unit_height: int, extra_params: dict[str, Any], num_drawers: int) -> list[int]:
    raw_heights = extra_params.get("drawer_face_heights")
    if isinstance(raw_heights, list):
        heights = [_non_negative_int(value, 0) for value in raw_heights]
        return [height for height in heights if height > 0]
    if num_drawers <= 0:
        return []
    panel_gap = _non_negative_int(extra_params.get("panel_gap_mm"), 3)
    return [max(0, int((unit_height / num_drawers) - panel_gap)) for _ in range(num_drawers)]


def _hardware_variant(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return " ".join(
        part
        for part in (
            str(row.get("brand") or "").strip(),
            str(row.get("model") or "").strip(),
            str(row.get("code") or "").strip(),
        )
        if part
    )


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


def _add_drawer_system_hardware_items(
    *,
    add_item,
    add_warning,
    slide: dict[str, Any] | None,
    slide_id: str,
    extra_params: dict[str, Any],
    extra_lookup: dict[str, dict[str, Any]],
    handle_lookup: dict[str, dict[str, Any]],
    hinge_lookup: dict[str, dict[str, Any]],
    num_drawers: int,
    unit_number: int,
    location: str,
) -> None:
    if _drawer_system_kind(extra_params, slide) != "metal":
        return
    config = _drawer_system_config(extra_params, slide)
    for index, raw_item in enumerate(config.get("hardware_items") or []):
        if not isinstance(raw_item, dict):
            continue
        item_name = str(raw_item.get("name") or "").strip()
        if not item_name:
            continue
        item_type = str(raw_item.get("item_type") or "extra").strip().lower()
        if item_type not in ITEM_TYPE_LABELS:
            item_type = "extra"
        item_ref_id = str(raw_item.get("item_ref_id") or "").strip()
        synthetic_ref = False
        if not item_ref_id:
            item_ref_id = f"drawer-system:{slide_id}:{index}:{_slug(item_name)}"
            synthetic_ref = True

        quantity = _non_negative_int(raw_item.get("quantity"), 0)
        if quantity <= 0:
            quantity = _non_negative_int(raw_item.get("quantity_per_drawer"), 1) * num_drawers
        if quantity <= 0:
            continue

        catalog_item = _configured_hardware_catalog_item(
            item_type=item_type,
            item_ref_id=item_ref_id,
            extra_lookup=extra_lookup,
            handle_lookup=handle_lookup,
            hinge_lookup=hinge_lookup,
            slide=slide,
            slide_id=slide_id,
        )
        if item_ref_id and not synthetic_ref and catalog_item is None and item_type in {"extra", "handle", "hinge"}:
            add_warning(
                code="missing_catalog_item",
                item_type=item_type,
                unit_number=unit_number,
                item_ref_id=item_ref_id,
                message=f"{item_name} {item_ref_id} is not available for {location}.",
            )

        add_item(
            item_type=item_type,
            item_ref_id=item_ref_id,
            item_name=_configured_hardware_name(raw_item, catalog_item, fallback=item_name),
            supplier=str(raw_item.get("supplier") or _catalog_supplier(catalog_item) or _brand_supplier(slide) or "").strip(),
            code=str(raw_item.get("code") or _catalog_code(catalog_item) or "").strip(),
            quantity=quantity,
            uom=str(raw_item.get("uom") or "pcs").strip() or "pcs",
            unit_number=unit_number,
            used_in=location,
        )


def _drawer_system_kind(extra_params: dict[str, Any], slide: dict[str, Any] | None) -> str:
    return str(extra_params.get("drawer_system_kind") or (slide or {}).get("drawer_system_kind") or "conventional").strip().lower()


def _drawer_system_config(extra_params: dict[str, Any], slide: dict[str, Any] | None) -> dict[str, Any]:
    config = extra_params.get("drawer_system_config") or (slide or {}).get("drawer_system_config") or {}
    return dict(config) if isinstance(config, dict) else {}


def _configured_hardware_catalog_item(
    *,
    item_type: str,
    item_ref_id: str,
    extra_lookup: dict[str, dict[str, Any]],
    handle_lookup: dict[str, dict[str, Any]],
    hinge_lookup: dict[str, dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]] | None = None,
    slide: dict[str, Any] | None = None,
    slide_id: str = "",
) -> dict[str, Any] | None:
    if item_type == "extra":
        return extra_lookup.get(item_ref_id)
    if item_type == "handle":
        return handle_lookup.get(item_ref_id)
    if item_type == "hinge":
        return hinge_lookup.get(item_ref_id)
    if item_type == "slide":
        if item_ref_id == slide_id:
            return slide
        return (slide_lookup or {}).get(item_ref_id)
    return None


def _configured_hardware_name(raw_item: dict[str, Any], catalog_item: dict[str, Any] | None, *, fallback: str) -> str:
    if catalog_item:
        if "name" in catalog_item:
            return _extra_name(catalog_item) if "category_name" in catalog_item else _handle_name(catalog_item)
        if "brand" in catalog_item and "model" in catalog_item:
            return _slide_name(catalog_item) if "length" in catalog_item else _hinge_name(catalog_item)
    return str(raw_item.get("name") or fallback).strip()


def _slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "item"


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


def _float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed
