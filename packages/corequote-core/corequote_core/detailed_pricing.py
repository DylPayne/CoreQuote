"""Detailed quote pricing helpers.

This module is intentionally data-shape oriented: API/database code adapts rows
into dictionaries, and this module performs the deterministic pricing math.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


PRICEABLE_ITEM_TYPES = {
    "board",
    "slide",
    "hinge",
    "handle",
    "extra",
    "labour",
    "consumable",
    "installation",
    "delivery",
    "adjustment",
}

ITEM_TYPE_LABELS = {
    "board": "Board",
    "slide": "Slide",
    "hinge": "Hinge",
    "handle": "Handle",
    "extra": "Extra",
    "labour": "Labour",
    "consumable": "Consumable",
    "installation": "Installation",
    "delivery": "Delivery",
    "adjustment": "Adjustment",
}

PRICE_COMPONENT_LABELS = {
    "sqm": "Square metre price",
    "m2": "Square metre rate",
    "sheet": "Sheet price",
    "unit": "Unit price",
    "day": "Day rate",
    "trip": "Trip rate",
    "commission": "Commission allowance",
}


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


@dataclass(frozen=True)
class DetailedPricingSettings:
    vat_rate_bps: int = 1500
    default_markup_bps: int = 2500
    carcass_markup_bps: int = 2500
    door_panel_markup_bps: int = 2500
    component_markup_bps: int = 2500
    handle_markup_bps: int = 2500
    extras_markup_bps: int = 2500
    fabrication_markup_bps: int = 2500
    install_markup_bps: int = 2500
    delivery_markup_bps: int = 2500
    joinery_commission_bps: int = 0
    labour_cents_per_m2: int = 2000
    consumables_cents_per_m2: int = 1000
    install_day_cost_cents: int = 190000
    delivery_base_cents: int = 95000
    install_units_per_day: int = 3
    delivery_units_per_trip: int = 20
    minimum_install_days_bps: int = 5000
    minimum_delivery_trips_bps: int = 5000


def settings_from_mapping(payload: dict[str, Any] | None) -> DetailedPricingSettings:
    payload = payload or {}
    data: dict[str, int] = {}
    for field_name, field_def in DetailedPricingSettings.__dataclass_fields__.items():
        data[field_name] = _non_negative_int(payload.get(field_name), int(field_def.default))
    return DetailedPricingSettings(**data)


def price_quote_detailed(
    *,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    quote_extras: list[dict[str, Any]],
    cutting_rows: list[dict[str, Any]],
    settings: DetailedPricingSettings,
    price_lookup: dict[tuple[str, str, str], dict[str, Any]],
    board_lookup: dict[str, dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
    hinge_lookup: dict[str, dict[str, Any]],
    handle_lookup: dict[str, dict[str, Any]],
    extra_lookup: dict[str, dict[str, Any]],
    active_price_list_id: str | None,
) -> dict[str, Any]:
    lines: list[dict[str, Any]] = []
    missing_items: list[str] = []
    commissionable_sell_cents = 0

    def add_line(line: dict[str, Any]) -> None:
        nonlocal commissionable_sell_cents
        lines.append(line)
        if line.get("missing"):
            missing_key = str(line.get("missing_item") or f"{line['item_key']}::{line['price_component']}")
            missing_items.append(missing_key)
        if line.get("commissionable") and line.get("sell_total_cents") is not None:
            commissionable_sell_cents += int(line["sell_total_cents"])

    units_by_number = {
        int(unit.get("unit_number", 0) or 0): unit
        for unit in units
        if int(unit.get("unit_number", 0) or 0) > 0
    }

    board_groups = _collect_board_usage(
        quote=quote,
        units_by_number=units_by_number,
        cutting_rows=cutting_rows,
        board_lookup=board_lookup,
    )
    carcass_area_m2 = 0.0

    for key, usage in sorted(board_groups.items(), key=lambda item: (_bucket_sort(item[0][1]), item[0][0])):
        board_id, material_role = key
        board = board_lookup.get(board_id)
        if not board:
            continue
        if material_role == "carcass":
            carcass_area_m2 += float(usage["used_area_m2"])
        markup_bps = settings.carcass_markup_bps if material_role == "carcass" else settings.door_panel_markup_bps
        add_line(
            _board_pricing_line(
                board=board,
                board_id=board_id,
                material_role=material_role,
                usage=usage,
                markup_bps=markup_bps,
                price_lookup=price_lookup,
            )
        )

    if carcass_area_m2 > 0:
        add_line(
            _service_line(
                item_type="labour",
                item_key="labour::unit_assembly",
                price_component="m2",
                bucket="labour",
                description="Unit assembly labour",
                qty=carcass_area_m2,
                uom="m2",
                unit_cost_cents=settings.labour_cents_per_m2,
                markup_bps=settings.fabrication_markup_bps,
                commissionable=True,
            )
        )
        add_line(
            _service_line(
                item_type="consumable",
                item_key="consumable::unit_materials",
                price_component="m2",
                bucket="consumable",
                description="Unit consumables",
                qty=carcass_area_m2,
                uom="m2",
                unit_cost_cents=settings.consumables_cents_per_m2,
                markup_bps=settings.carcass_markup_bps,
                commissionable=True,
            )
        )

    for line in _hardware_lines(
        quote=quote,
        units=units,
        settings=settings,
        price_lookup=price_lookup,
        slide_lookup=slide_lookup,
        hinge_lookup=hinge_lookup,
        handle_lookup=handle_lookup,
    ):
        add_line(line)

    for selected_extra in quote_extras:
        extra_id = str(selected_extra.get("extra_id") or "").strip()
        quantity = _non_negative_int(selected_extra.get("quantity"), 1)
        if not extra_id or quantity <= 0:
            continue
        add_line(
            _priced_catalog_line(
                item_type="extra",
                item_key=f"extra::{extra_id}",
                price_component="unit",
                bucket="extra",
                description=_extra_description(extra_lookup.get(extra_id)),
                qty=float(quantity),
                uom="pcs",
                markup_bps=settings.extras_markup_bps,
                price_lookup=price_lookup,
                commissionable=False,
            )
        )

    unit_count = len(units)
    if unit_count > 0:
        install_days = _scaled_minimum_quantity(
            count=unit_count,
            divisor=settings.install_units_per_day,
            minimum_bps=settings.minimum_install_days_bps,
        )
        delivery_units = _scaled_minimum_quantity(
            count=unit_count,
            divisor=settings.delivery_units_per_trip,
            minimum_bps=settings.minimum_delivery_trips_bps,
        )
        add_line(
            _service_line(
                item_type="installation",
                item_key="installation::cabinet_install",
                price_component="day",
                bucket="installation",
                description="Cabinet installation",
                qty=install_days,
                uom="days",
                unit_cost_cents=settings.install_day_cost_cents,
                markup_bps=settings.install_markup_bps,
                commissionable=False,
            )
        )
        add_line(
            _service_line(
                item_type="delivery",
                item_key="delivery::cabinet_delivery",
                price_component="trip",
                bucket="delivery",
                description="Delivery",
                qty=delivery_units,
                uom="trips",
                unit_cost_cents=settings.delivery_base_cents,
                markup_bps=settings.delivery_markup_bps,
                commissionable=False,
            )
        )

    if settings.joinery_commission_bps > 0 and commissionable_sell_cents > 0:
        commission_cents = int(round(commissionable_sell_cents * (settings.joinery_commission_bps / 10_000.0)))
        add_line(
            {
                "item_type": "adjustment",
                "item_key": "adjustment::joinery_commission",
                "price_component": "commission",
                "bucket": "commission",
                "description": "Joinery commission",
                "qty": 1.0,
                "uom": "allowance",
                "unit_price_cents": commission_cents,
                "unit_cost_cents": 0,
                "cost_total_cents": 0,
                "markup_bps": settings.joinery_commission_bps,
                "sell_total_cents": commission_cents,
                "line_total_cents": commission_cents,
                "profit_cents": commission_cents,
                "missing": False,
                "commissionable": False,
            }
        )

    cost_total_cents = int(sum(int(line.get("cost_total_cents") or 0) for line in lines))
    sell_before_vat_cents = int(sum(int(line.get("sell_total_cents") or 0) for line in lines))
    profit_cents = int(sell_before_vat_cents - cost_total_cents)
    vat_cents = int(round(sell_before_vat_cents * (settings.vat_rate_bps / 10_000.0)))
    grand_total_cents = int(sell_before_vat_cents + vat_cents)
    missing_items = sorted(set(missing_items))
    missing_prices = _missing_price_summaries(lines=lines, quote=quote)

    bucket_totals = _bucket_totals(lines)
    response_lines = [_public_line(line) for line in sorted(lines, key=_line_sort_key)]

    return {
        "quote_id": quote["id"],
        "quote_name": quote["name"],
        "is_complete": bool(active_price_list_id) and not missing_prices,
        "missing_items": missing_items,
        "missing_prices": missing_prices,
        "subtotal_cents": cost_total_cents,
        "cost_total_cents": cost_total_cents,
        "sell_before_vat_cents": sell_before_vat_cents,
        "vat_cents": vat_cents,
        "grand_total_cents": grand_total_cents,
        "profit_cents": profit_cents,
        "bucket_totals": bucket_totals,
        "lines": response_lines,
    }


def _collect_board_usage(
    *,
    quote: dict[str, Any],
    units_by_number: dict[int, dict[str, Any]],
    cutting_rows: list[dict[str, Any]],
    board_lookup: dict[str, dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}

    for row in cutting_rows:
        section = str(row.get("section", ""))
        unit = units_by_number.get(int(row.get("unit_number", 0) or 0))
        material_role = ""
        board_id = ""
        if section == "carcass":
            material_role = "carcass"
            board_id = str((unit or {}).get("carcass_board_type_id") or quote.get("default_carcass_board_type_id") or "")
        elif section == "panel":
            material_role = "door_panel"
            board_id = str((unit or {}).get("door_board_type_id") or quote.get("default_door_board_type_id") or "")
        elif section == "extra_panel":
            material_role = "visible_panel"
            board_id = str(
                row.get("board_type_id")
                or quote.get("default_panel_board_type_id")
                or (unit or {}).get("door_board_type_id")
                or quote.get("default_door_board_type_id")
                or ""
            )
        else:
            continue

        board_id = board_id.strip()
        if not board_id or board_id not in board_lookup:
            continue

        length = _non_negative_int(row.get("length"), 0)
        width = _non_negative_int(row.get("width"), 0)
        qty = _non_negative_int(row.get("qty"), 0)
        if length <= 0 or width <= 0 or qty <= 0:
            continue

        piece_area = int(length * width)
        group = groups.setdefault(
            (board_id, material_role),
            {
                "piece_areas": [],
                "used_area_mm2": 0,
                "used_area_m2": 0.0,
                "edge_mm": 0,
            },
        )
        group["piece_areas"].extend([piece_area] * qty)
        group["used_area_mm2"] += piece_area * qty
        group["used_area_m2"] = round(float(group["used_area_mm2"]) / 1_000_000.0, 4)
        group["edge_mm"] += int(_edge_length_mm(row, length, width) * qty)

    return groups


def _board_pricing_line(
    *,
    board: dict[str, Any],
    board_id: str,
    material_role: str,
    usage: dict[str, Any],
    markup_bps: int,
    price_lookup: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    item_key = f"board::{board_id}"
    costing_mode = str(board.get("costing_mode", "sheet") or "sheet").strip().lower()
    sheet_area_mm2 = _non_negative_int(board.get("length_mm"), 0) * _non_negative_int(board.get("width_mm"), 0)
    boards_used = _estimate_boards_used(list(usage.get("piece_areas") or []), sheet_area_mm2)
    used_area_m2 = float(usage.get("used_area_m2", 0.0) or 0.0)

    if costing_mode == "sqm":
        price_component = "sqm"
        qty = used_area_m2
        uom = "m2"
    else:
        price_component = "sheet"
        qty = float(boards_used)
        uom = "sheet"

    active_price = price_lookup.get(("board", item_key, price_component))
    description = f"{_material_role_label(material_role)}: {_board_description(board)}"
    if not active_price:
        return _missing_line(
            item_type="board",
            item_key=item_key,
            price_component=price_component,
            bucket="material",
            description=description,
            qty=qty,
            uom=uom,
            markup_bps=markup_bps,
            commissionable=True,
        )

    unit_cost = int(active_price["unit_price_cents"])
    line = _line_from_cost(
        item_type="board",
        item_key=item_key,
        price_component=price_component,
        bucket="material",
        description=description,
        qty=qty,
        uom=uom,
        unit_cost_cents=unit_cost,
        markup_bps=markup_bps,
        commissionable=True,
    )
    line["meta"] = {
        "board_type_id": board_id,
        "material_role": material_role,
        "costing_mode": costing_mode,
        "boards_used": boards_used,
        "used_area_m2": used_area_m2,
        "edge_m": round(float(usage.get("edge_mm", 0) or 0) / 1000.0, 3),
    }
    return line


def _hardware_lines(
    *,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    settings: DetailedPricingSettings,
    price_lookup: dict[tuple[str, str, str], dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
    hinge_lookup: dict[str, dict[str, Any]],
    handle_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    required: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add_required(
        item_type: str,
        item_key: str,
        price_component: str,
        bucket: str,
        description: str,
        qty: float,
        uom: str,
        markup_bps: int,
    ) -> None:
        if not item_key or qty <= 0:
            return
        key = (item_type, item_key, price_component)
        row = required.get(key)
        if row:
            row["qty"] += float(qty)
            return
        required[key] = {
            "item_type": item_type,
            "item_key": item_key,
            "price_component": price_component,
            "bucket": bucket,
            "description": description,
            "qty": float(qty),
            "uom": uom,
            "markup_bps": markup_bps,
        }

    for unit in units:
        canonical_type = _canonical_unit_type(str(unit.get("unit_type_key") or unit.get("unit_type") or ""))
        extra_params = unit.get("extra_params", {}) or {}
        height = _non_negative_int(unit.get("height"), 0)

        if canonical_type == "Base Draw":
            num_drawers = _non_negative_int(extra_params.get("num_drawers"), 3)
            slide_id = str(quote.get("default_slide_id") or "").strip()
            if slide_id:
                add_required(
                    "slide",
                    f"slide::{slide_id}",
                    "unit",
                    "component",
                    _slide_description(slide_lookup.get(slide_id)),
                    float(num_drawers),
                    "pairs",
                    settings.component_markup_bps,
                )
            handle_id = str(quote.get("default_drawer_handle_id") or "").strip()
            drawer_handle_qty = _non_negative_int(extra_params.get("handle_qty"), num_drawers)
            if handle_id:
                add_required(
                    "handle",
                    f"handle::{handle_id}",
                    "unit",
                    "handle",
                    _handle_description(handle_lookup.get(handle_id)),
                    float(drawer_handle_qty),
                    "pcs",
                    settings.handle_markup_bps,
                )

        if canonical_type in {"Base Door", "Wall Door", "Tall Door"}:
            num_doors = _non_negative_int(extra_params.get("num_doors"), 2)
            hinge_id = str(quote.get("default_hinge_id") or "").strip()
            hinges_per_door = max(2, math.ceil(height / 600)) if height > 0 else 2
            if hinge_id:
                add_required(
                    "hinge",
                    f"hinge::{hinge_id}",
                    "unit",
                    "component",
                    _hinge_description(hinge_lookup.get(hinge_id)),
                    float(num_doors * hinges_per_door),
                    "pcs",
                    settings.component_markup_bps,
                )

            if canonical_type == "Wall Door":
                handle_id = str(quote.get("default_wall_handle_id") or "").strip()
            elif canonical_type == "Tall Door":
                handle_id = str(quote.get("default_tall_handle_id") or "").strip()
            else:
                handle_id = str(quote.get("default_base_handle_id") or "").strip()
            handle_qty = _non_negative_int(extra_params.get("handle_qty"), num_doors)
            if handle_id:
                add_required(
                    "handle",
                    f"handle::{handle_id}",
                    "unit",
                    "handle",
                    _handle_description(handle_lookup.get(handle_id)),
                    float(handle_qty),
                    "pcs",
                    settings.handle_markup_bps,
                )

    lines: list[dict[str, Any]] = []
    for row in required.values():
        lines.append(
            _priced_catalog_line(
                item_type=row["item_type"],
                item_key=row["item_key"],
                price_component=row["price_component"],
                bucket=row["bucket"],
                description=row["description"],
                qty=float(row["qty"]),
                uom=str(row["uom"]),
                markup_bps=int(row["markup_bps"]),
                price_lookup=price_lookup,
                commissionable=True,
            )
        )
    return lines


def _priced_catalog_line(
    *,
    item_type: str,
    item_key: str,
    price_component: str,
    bucket: str,
    description: str,
    qty: float,
    uom: str,
    markup_bps: int,
    price_lookup: dict[tuple[str, str, str], dict[str, Any]],
    commissionable: bool,
) -> dict[str, Any]:
    active_price = price_lookup.get((item_type, item_key, price_component))
    if not active_price:
        return _missing_line(
            item_type=item_type,
            item_key=item_key,
            price_component=price_component,
            bucket=bucket,
            description=description,
            qty=qty,
            uom=uom,
            markup_bps=markup_bps,
            commissionable=commissionable,
        )
    return _line_from_cost(
        item_type=item_type,
        item_key=item_key,
        price_component=price_component,
        bucket=bucket,
        description=description,
        qty=qty,
        uom=uom,
        unit_cost_cents=int(active_price["unit_price_cents"]),
        markup_bps=markup_bps,
        commissionable=commissionable,
    )


def _service_line(
    *,
    item_type: str,
    item_key: str,
    price_component: str,
    bucket: str,
    description: str,
    qty: float,
    uom: str,
    unit_cost_cents: int,
    markup_bps: int,
    commissionable: bool,
) -> dict[str, Any]:
    return _line_from_cost(
        item_type=item_type,
        item_key=item_key,
        price_component=price_component,
        bucket=bucket,
        description=description,
        qty=qty,
        uom=uom,
        unit_cost_cents=unit_cost_cents,
        markup_bps=markup_bps,
        commissionable=commissionable,
    )


def _line_from_cost(
    *,
    item_type: str,
    item_key: str,
    price_component: str,
    bucket: str,
    description: str,
    qty: float,
    uom: str,
    unit_cost_cents: int,
    markup_bps: int,
    commissionable: bool,
) -> dict[str, Any]:
    rounded_qty = float(round(float(qty), 4))
    cost_total = int(round(float(qty) * int(unit_cost_cents)))
    sell_total = _apply_markup(cost_total, markup_bps)
    return {
        "item_type": item_type,
        "item_key": item_key,
        "price_component": price_component,
        "bucket": bucket,
        "description": description,
        "qty": rounded_qty,
        "uom": uom,
        "unit_price_cents": int(unit_cost_cents),
        "unit_cost_cents": int(unit_cost_cents),
        "cost_total_cents": cost_total,
        "markup_bps": int(markup_bps),
        "sell_total_cents": sell_total,
        "line_total_cents": sell_total,
        "profit_cents": int(sell_total - cost_total),
        "missing": False,
        "commissionable": commissionable,
    }


def _missing_line(
    *,
    item_type: str,
    item_key: str,
    price_component: str,
    bucket: str,
    description: str,
    qty: float,
    uom: str,
    markup_bps: int,
    commissionable: bool,
) -> dict[str, Any]:
    return {
        "item_type": item_type,
        "item_key": item_key,
        "price_component": price_component,
        "bucket": bucket,
        "description": description,
        "qty": float(round(float(qty), 4)),
        "uom": uom,
        "unit_price_cents": None,
        "unit_cost_cents": None,
        "cost_total_cents": None,
        "markup_bps": int(markup_bps),
        "sell_total_cents": None,
        "line_total_cents": None,
        "profit_cents": None,
        "missing": True,
        "missing_item": f"{item_key}::{price_component}",
        "commissionable": commissionable,
    }


def _public_line(line: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_type": line["item_type"],
        "item_key": line["item_key"],
        "price_component": line["price_component"],
        "bucket": line["bucket"],
        "description": line["description"],
        "qty": line["qty"],
        "uom": line["uom"],
        "unit_price_cents": line.get("unit_price_cents"),
        "unit_cost_cents": line.get("unit_cost_cents"),
        "cost_total_cents": line.get("cost_total_cents"),
        "markup_bps": line.get("markup_bps", 0),
        "sell_total_cents": line.get("sell_total_cents"),
        "line_total_cents": line.get("line_total_cents"),
        "profit_cents": line.get("profit_cents"),
        "missing": bool(line.get("missing")),
    }


def _bucket_totals(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, int]] = {}
    for line in lines:
        bucket = str(line.get("bucket") or "other")
        row = totals.setdefault(bucket, {"cost_total_cents": 0, "sell_total_cents": 0, "profit_cents": 0})
        row["cost_total_cents"] += int(line.get("cost_total_cents") or 0)
        row["sell_total_cents"] += int(line.get("sell_total_cents") or 0)
        row["profit_cents"] += int(line.get("profit_cents") or 0)
    return [
        {
            "bucket": bucket,
            "cost_total_cents": values["cost_total_cents"],
            "sell_total_cents": values["sell_total_cents"],
            "profit_cents": values["profit_cents"],
        }
        for bucket, values in sorted(totals.items(), key=lambda item: _bucket_sort(item[0]))
    ]


def _missing_price_summaries(*, lines: list[dict[str, Any]], quote: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: dict[tuple[str, str, str], dict[str, Any]] = {}
    quote_id = str(quote.get("id") or "")
    quote_name = str(quote.get("name") or "Quote")

    for line in lines:
        if not line.get("missing"):
            continue

        item_type = str(line.get("item_type") or "adjustment")
        item_key = str(line.get("item_key") or "")
        price_component = str(line.get("price_component") or "unit")
        key = (item_type, item_key, price_component)
        item_name = _missing_item_name(line)
        component = _price_component_label(price_component)
        usage = _missing_usage_label(line)

        summary = summaries.get(key)
        if summary is None:
            summary = {
                "item_type": item_type,
                "item_type_label": _item_type_label(item_type),
                "item_key": item_key,
                "item_ref_id": _item_ref_id(item_key),
                "price_component": price_component,
                "component": component,
                "bucket": str(line.get("bucket") or "other"),
                "item_name": item_name,
                "uom": str(line.get("uom") or ""),
                "quantity": 0.0,
                "used_in": [],
                "usage_label": "",
                "affected_quote_id": quote_id,
                "affected_quote_name": quote_name,
                "library_area": "pricing",
                "action_label": f"Add a price for {item_name}",
                "message": f"Add a price for {item_name} using {component} in the pricing library.",
            }
            summaries[key] = summary

        summary["quantity"] = float(round(float(summary["quantity"]) + float(line.get("qty") or 0.0), 4))
        if usage and usage not in summary["used_in"]:
            summary["used_in"].append(usage)

    for summary in summaries.values():
        if not summary["used_in"]:
            summary["used_in"].append(summary["item_type_label"])
        summary["usage_label"] = _join_labels(summary["used_in"])

    return sorted(
        summaries.values(),
        key=lambda row: (_bucket_sort(str(row.get("bucket") or "")), str(row.get("item_name") or "")),
    )


def _missing_item_name(line: dict[str, Any]) -> str:
    description = str(line.get("description") or "").strip()
    if ": " in description:
        return description.split(": ", 1)[1].strip() or description
    return description or _item_type_label(str(line.get("item_type") or ""))


def _missing_usage_label(line: dict[str, Any]) -> str:
    description = str(line.get("description") or "").strip()
    if ": " in description:
        return description.split(": ", 1)[0].strip()
    return _item_type_label(str(line.get("item_type") or ""))


def _item_type_label(item_type: str) -> str:
    return ITEM_TYPE_LABELS.get(str(item_type), _title_words(str(item_type)))


def _price_component_label(price_component: str) -> str:
    return PRICE_COMPONENT_LABELS.get(str(price_component), f"{_title_words(str(price_component))} price")


def _item_ref_id(item_key: str) -> str:
    if "::" not in item_key:
        return item_key
    return item_key.split("::", 1)[1]


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


def _edge_length_mm(row: dict[str, Any], length: int, width: int) -> int:
    total = 0
    if bool(row.get("edge_long_1")):
        total += length
    if bool(row.get("edge_long_2")):
        total += length
    if bool(row.get("edge_short_1")):
        total += width
    if bool(row.get("edge_short_2")):
        total += width
    return total


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


def _apply_markup(cost_total_cents: int, markup_bps: int) -> int:
    return int(round(cost_total_cents * (1.0 + (_non_negative_int(markup_bps, 0) / 10_000.0))))


def _scaled_minimum_quantity(*, count: int, divisor: int, minimum_bps: int) -> float:
    divisor = max(1, _non_negative_int(divisor, 1))
    minimum = _non_negative_int(minimum_bps, 0) / 10_000.0
    return float(round(max(minimum, count / divisor), 4))


def _canonical_unit_type(unit_type: str) -> str:
    return UNIT_TYPE_ALIAS_TO_CANONICAL.get(unit_type, unit_type)


def _non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = int(default)
    return max(0, parsed)


def _bucket_sort(bucket: str) -> tuple[int, str]:
    order = {
        "material": 10,
        "component": 20,
        "handle": 30,
        "labour": 40,
        "consumable": 50,
        "extra": 60,
        "installation": 70,
        "delivery": 80,
        "commission": 90,
    }
    return order.get(str(bucket), 999), str(bucket)


def _line_sort_key(line: dict[str, Any]) -> tuple[int, str, str]:
    return (*_bucket_sort(str(line.get("bucket") or "")), str(line.get("description") or ""))


def _material_role_label(material_role: str) -> str:
    labels = {
        "carcass": "Carcass material",
        "door_panel": "Door and drawer material",
        "visible_panel": "Visible panel material",
    }
    return labels.get(material_role, "Board material")


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
