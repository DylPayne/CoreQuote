"""
pricing.py
────────────────────────────────────────────────────────────────────────────────
Quote pricing service with immutable snapshot runs.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from logic import database
from logic.cutlist import build_cutlist
from logic.panels import PANEL_PRESET_KEYS, PANEL_PRESET_LABELS, compute_panel_rows


@dataclass
class PricingResult:
    run_id: int
    quote_id: int
    price_list_id: int
    pricing_mode: str
    pricing_value_bps: int
    vat_rate_bps: int
    subtotal_cents: int
    sell_before_vat_cents: int
    vat_cents: int
    grand_total_cents: int
    line_count: int


@dataclass
class RequiredPriceItem:
    item_type: str
    item_key: str
    description: str
    uom: str
    qty_required: float
    unit_price_cents: int | None


def _to_bps(percent: float) -> int:
    return int(round(float(percent) * 100.0))


def _apply_pricing_mode(subtotal_cents: int, mode: str, value_bps: int) -> int:
    mode = str(mode).strip().lower()
    if mode == "markup":
        return int(round(subtotal_cents * (1.0 + (value_bps / 10_000.0))))
    if mode == "margin":
        margin = value_bps / 10_000.0
        if margin >= 1.0:
            raise ValueError("Margin must be less than 100%.")
        return int(round(subtotal_cents / max(1e-9, (1.0 - margin))))
    raise ValueError("pricing_mode must be 'markup' or 'margin'")


def _component_lines(units: list[dict], lookup: dict[tuple[str, str], dict]) -> tuple[list[dict], list[str]]:
    counts: dict[str, dict] = {}
    missing: list[str] = []

    def _add(key: str, desc: str, qty: int, uom: str):
        if qty <= 0:
            return
        row = counts.setdefault(key, {"description": desc, "qty": 0.0, "uom": uom})
        row["qty"] += float(qty)

    for u in units:
        extra = u.get("extra_params", {}) or {}
        utype = str(u.get("unit_type", ""))

        if "Draw" in utype:
            qty = int(extra.get("num_drawers", 0) or 0)
            slide_key = f"slide::{extra.get('slide_brand', '')}::{extra.get('slide_model', '')}::{extra.get('slide_code', '')}::{extra.get('slide_length', '')}"
            slide_label = " ".join(
                p for p in [str(extra.get("slide_brand", "")).strip(), str(extra.get("slide_model", "")).strip()] if p
            ).strip() or "Slide"
            _add(slide_key, slide_label, qty, "pairs")

        if ("Door" in utype) or ("Tall" in utype):
            num_doors = int(extra.get("num_doors", 0) or 0)
            height_mm = int(u.get("height", 0) or 0)
            hinges_per_door = max(2, math.ceil(height_mm / 600)) if height_mm > 0 else 2
            qty = num_doors * hinges_per_door
            hinge_key = f"hinge::{extra.get('hinge_brand', '')}::{extra.get('hinge_model', '')}::{extra.get('hinge_code', '')}::{extra.get('hinge_opening_angle_deg', '')}"
            hinge_label = " ".join(
                p for p in [str(extra.get("hinge_brand", "")).strip(), str(extra.get("hinge_model", "")).strip()] if p
            ).strip() or "Hinge"
            _add(hinge_key, hinge_label, qty, "pcs")

        if "Draw" in utype:
            qty = int(extra.get("handle_qty", extra.get("num_drawers", 0)) or 0)
            h_name = str(extra.get("drawer_handle_name", "")).strip()
            h_supplier = str(extra.get("drawer_handle_supplier", "")).strip()
            h_code = str(extra.get("drawer_handle_code", "")).strip()
        else:
            qty = int(extra.get("handle_qty", extra.get("num_doors", 0)) or 0)
            h_name = str(extra.get("handle_name", "")).strip()
            h_supplier = str(extra.get("handle_supplier", "")).strip()
            h_code = str(extra.get("handle_code", "")).strip()
        handle_key = f"handle::{h_name}::{h_supplier}::{h_code}"
        handle_label = h_name or "Handle"
        _add(handle_key, handle_label, qty, "pcs")

    lines: list[dict] = []
    for item_key, row in counts.items():
        item_type = item_key.split("::", 1)[0]
        rate_row = lookup.get((item_type, item_key))
        if not rate_row:
            missing.append(item_key)
            continue
        qty = float(row["qty"])
        unit_price = int(rate_row["unit_price_cents"])
        lines.append(
            {
                "source_type": item_type,
                "source_ref": item_key,
                "description": str(row["description"]),
                "qty": qty,
                "uom": str(row["uom"]),
                "unit_price_cents": unit_price,
                "line_total_cents": int(round(qty * unit_price)),
                "meta": {},
            }
        )
    return lines, missing


def _extra_lines(quote_id: int, lookup: dict[tuple[str, str], dict]) -> tuple[list[dict], list[str]]:
    rows = database.get_quote_extras(int(quote_id))
    lines: list[dict] = []
    missing: list[str] = []
    for r in rows:
        item_key = f"extra::{int(r['extra_id'])}"
        rate_row = lookup.get(("extra", item_key))
        if not rate_row:
            missing.append(item_key)
            continue
        qty = float(int(r.get("qty", 1) or 1))
        unit_price = int(rate_row["unit_price_cents"])
        lines.append(
            {
                "source_type": "extra",
                "source_ref": str(r["id"]),
                "description": str(r.get("extra_name", "Extra")),
                "qty": qty,
                "uom": "pcs",
                "unit_price_cents": unit_price,
                "line_total_cents": int(round(qty * unit_price)),
                "meta": {"extra_id": int(r["extra_id"])},
            }
        )
    return lines, missing


def _estimate_boards_used(piece_areas_mm2: list[int], sheet_area_mm2: int) -> int:
    if sheet_area_mm2 <= 0 or not piece_areas_mm2:
        return 0
    bins: list[int] = []
    for area in sorted((int(a) for a in piece_areas_mm2 if int(a) > 0), reverse=True):
        for i, remaining in enumerate(bins):
            if area <= remaining:
                bins[i] = remaining - area
                break
        else:
            bins.append(max(0, sheet_area_mm2 - area))
    return len(bins)


def _default_dims_for_unit_type_from_quote(quote: dict, unit_type: str) -> tuple[int, int]:
    defaults = quote.get("unit_defaults", {}) or {}
    item = defaults.get(unit_type, {}) if isinstance(defaults, dict) else {}
    if unit_type == "Wall Door":
        fallback_h, fallback_d = 720, 330
    elif unit_type == "Tall Standard":
        fallback_h, fallback_d = 2100, 580
    else:
        fallback_h, fallback_d = 780, 580
    return int(item.get("height", fallback_h)), int(item.get("depth", fallback_d))


def _default_dims_for_panel_preset_from_quote(quote: dict, key: str) -> tuple[int, int]:
    base_h, base_d = _default_dims_for_unit_type_from_quote(quote, "Base Door")
    wall_h, wall_d = _default_dims_for_unit_type_from_quote(quote, "Wall Door")
    tall_h, tall_d = _default_dims_for_unit_type_from_quote(quote, "Tall Standard")
    if key == "base_side_panel":
        return int(base_h), int(base_d)
    if key == "base_side_filler":
        return int(base_h), 100
    if key == "wall_side_panel":
        return int(wall_h), int(wall_d)
    if key == "wall_side_filler":
        return int(wall_h), 100
    if key == "tall_side_panel":
        return int(tall_h), int(tall_d)
    if key == "tall_side_filler":
        return int(tall_h), 100
    return 0, 0


def _board_usage_rows(quote_id: int, units: list[dict]) -> list[dict]:
    quote = database.get_quote(int(quote_id)) or {}
    boards = database.get_all_board_types()
    board_lookup = {int(b["id"]): b for b in boards}

    carcass_default = quote.get("default_carcass_board_type_id")
    door_default = quote.get("default_door_board_type_id")
    panel_default = quote.get("default_panel_board_type_id")

    per_board_piece_areas: dict[int, list[int]] = {}
    per_board_edge_mm: dict[int, int] = {}

    def _add_piece(board_type_id: int | None, l_mm: int, w_mm: int, qty: int):
        if board_type_id is None:
            return
        bid = int(board_type_id)
        if bid not in board_lookup:
            return
        l = int(l_mm or 0)
        w = int(w_mm or 0)
        q = int(qty or 0)
        if l <= 0 or w <= 0 or q <= 0:
            return
        area = l * w
        per_board_piece_areas.setdefault(bid, []).extend([area] * q)
        per_board_edge_mm[bid] = int(per_board_edge_mm.get(bid, 0) + ((2 * (l + w)) * q))

    units_by_num = {int(u.get("unit_number", 0)): u for u in units if int(u.get("unit_number", 0)) > 0}

    carcass_df, panel_df = build_cutlist(units)
    for _, row in carcass_df.iterrows():
        unit = units_by_num.get(int(row["Unit #"]))
        board_id = (unit or {}).get("carcass_board_type_id", carcass_default)
        _add_piece(board_id, int(row["L"]), int(row["W"]), int(row["Qty"]))

    for _, row in panel_df.iterrows():
        unit = units_by_num.get(int(row["Unit #"]))
        board_id = (unit or {}).get("door_board_type_id", door_default)
        _add_piece(board_id, int(row["L"]), int(row["W"]), int(row["Qty"]))

    panel_state = quote.get("custom_panels", {}) or {}
    if isinstance(panel_state, dict):
        panel_rows = compute_panel_rows(
            units=units,
            state=panel_state,
            default_panel_board_type_id=panel_default,
            panel_preset_keys=PANEL_PRESET_KEYS,
            panel_preset_labels=PANEL_PRESET_LABELS,
            default_dims_for_panel_preset=lambda key: _default_dims_for_panel_preset_from_quote(quote, key),
            default_dims_for_unit_type=lambda unit_type: _default_dims_for_unit_type_from_quote(quote, unit_type),
            board_length_for=lambda board_type_id: int((board_lookup.get(board_type_id) or {}).get("length_mm", 0)),
        )
        for p in panel_rows:
            _add_piece(p.get("board_type_id", panel_default), int(p.get("L", 0)), int(p.get("W", 0)), int(p.get("Qty", 0)))

    rows: list[dict] = []
    for board_id, piece_areas in per_board_piece_areas.items():
        board = board_lookup.get(int(board_id))
        if not board:
            continue
        board_area = int(board["length_mm"]) * int(board["width_mm"])
        boards_used = _estimate_boards_used(piece_areas, board_area)
        if boards_used <= 0:
            continue
        used_area = int(sum(piece_areas))
        total_area = int(boards_used * board_area)
        waste_area = max(0, total_area - used_area)
        waste_pct = (waste_area / total_area * 100.0) if total_area > 0 else 0.0
        desc = (
            f"{board['brand']} {board['material']} {board['thickness']}mm "
            f"({board['length_mm']}x{board['width_mm']})"
            f" • Wastage {waste_pct:.1f}%"
        )
        rows.append(
            {
                "item_type": "board",
                "item_key": f"board::{int(board_id)}",
                "description": desc,
                "uom": "sheet",
                "qty": float(boards_used),
                "meta": {
                    "board_type_id": int(board_id),
                    "boards_used": int(boards_used),
                    "used_area_mm2": int(used_area),
                    "used_area_m2": float(round(used_area / 1_000_000.0, 4)),
                    "total_edge_mm": int(per_board_edge_mm.get(int(board_id), 0)),
                    "total_edge_m": float(round(per_board_edge_mm.get(int(board_id), 0) / 1000.0, 3)),
                    "wastage_area_mm2": int(waste_area),
                    "wastage_pct": float(round(waste_pct, 2)),
                    "costing_mode": str(board.get("costing_mode", "sheet") or "sheet").strip().lower(),
                },
            }
        )
    rows.sort(key=lambda r: str(r["description"]).lower())
    return rows


def _board_lines(quote_id: int, units: list[dict], lookup: dict[tuple[str, str], dict]) -> tuple[list[dict], list[str]]:
    rows = _board_usage_rows(int(quote_id), units)
    lines: list[dict] = []
    missing: list[str] = []
    for r in rows:
        item_type = str(r["item_type"])
        item_key = str(r["item_key"])
        qty = float(r["qty"])
        meta = dict(r.get("meta", {}))
        costing_mode = str(meta.get("costing_mode", "sheet") or "sheet").strip().lower()

        if costing_mode == "sqm":
            used_area_m2 = float(meta.get("used_area_m2", 0.0) or 0.0)
            sqm_key = f"{item_key}::sqm"
            sqm_rate = lookup.get((item_type, sqm_key))
            if not sqm_rate:
                missing.append(sqm_key)
                continue
            sqm_price_cents = int(sqm_rate["unit_price_cents"])
            unit_price = sqm_price_cents
            line_total = int(round(used_area_m2 * sqm_price_cents))
            uom = "m2"
            source_ref = sqm_key
        else:
            sheet_key = f"{item_key}::sheet"
            edging_key = f"{item_key}::edging_m"
            labour_key = f"{item_key}::labour_board"
            sheet_rate = lookup.get((item_type, sheet_key))
            edging_rate = lookup.get((item_type, edging_key))
            labour_rate = lookup.get((item_type, labour_key))
            if not sheet_rate:
                missing.append(sheet_key)
            if not edging_rate:
                missing.append(edging_key)
            if not labour_rate:
                missing.append(labour_key)
            if not sheet_rate or not edging_rate or not labour_rate:
                continue
            sheet_price = int(sheet_rate["unit_price_cents"])
            edging_cost_cpm = int(edging_rate["unit_price_cents"])
            labour_per_board = int(labour_rate["unit_price_cents"])
            total_edge_m = float(meta.get("total_edge_m", 0.0) or 0.0)

            material_total = int(round(qty * sheet_price))
            edging_total = int(round(total_edge_m * edging_cost_cpm))
            labour_total = int(round(qty * labour_per_board))
            line_total = int(material_total + edging_total + labour_total)
            unit_price = sheet_price
            uom = str(r["uom"])
            source_ref = sheet_key
            meta.update(
                {
                    "material_total_cents": material_total,
                    "edging_total_cents": edging_total,
                    "labour_total_cents": labour_total,
                }
            )

        lines.append(
            {
                "source_type": item_type,
                "source_ref": source_ref,
                "description": str(r["description"]),
                "qty": qty,
                "uom": uom,
                "unit_price_cents": unit_price,
                "line_total_cents": int(line_total),
                "meta": meta,
            }
        )
    return lines, missing


def get_required_price_items(quote_id: int) -> list[RequiredPriceItem]:
    active_price_list = database.get_active_price_list()
    items_lookup: dict[tuple[str, str], dict] = {}
    if active_price_list:
        items = database.get_price_list_items(int(active_price_list["id"]))
        items_lookup = {(str(i["item_type"]), str(i["item_key"])): i for i in items}

    units = database.get_units_for_quote(int(quote_id))
    counts: dict[str, dict] = {}

    def _add_required(item_key: str, description: str, qty: float, uom: str):
        if qty <= 0:
            return
        row = counts.setdefault(item_key, {"description": description, "qty": 0.0, "uom": uom})
        row["qty"] += float(qty)

    for u in units:
        extra = u.get("extra_params", {}) or {}
        utype = str(u.get("unit_type", ""))

        if "Draw" in utype:
            qty = int(extra.get("num_drawers", 0) or 0)
            slide_key = f"slide::{extra.get('slide_brand', '')}::{extra.get('slide_model', '')}::{extra.get('slide_code', '')}::{extra.get('slide_length', '')}"
            slide_label = " ".join(
                p for p in [str(extra.get("slide_brand", "")).strip(), str(extra.get("slide_model", "")).strip()] if p
            ).strip() or "Slide"
            _add_required(slide_key, slide_label, qty, "pairs")

        if ("Door" in utype) or ("Tall" in utype):
            num_doors = int(extra.get("num_doors", 0) or 0)
            height_mm = int(u.get("height", 0) or 0)
            hinges_per_door = max(2, math.ceil(height_mm / 600)) if height_mm > 0 else 2
            qty = num_doors * hinges_per_door
            hinge_key = f"hinge::{extra.get('hinge_brand', '')}::{extra.get('hinge_model', '')}::{extra.get('hinge_code', '')}::{extra.get('hinge_opening_angle_deg', '')}"
            hinge_label = " ".join(
                p for p in [str(extra.get("hinge_brand", "")).strip(), str(extra.get("hinge_model", "")).strip()] if p
            ).strip() or "Hinge"
            _add_required(hinge_key, hinge_label, qty, "pcs")

        if "Draw" in utype:
            qty = int(extra.get("handle_qty", extra.get("num_drawers", 0)) or 0)
            h_name = str(extra.get("drawer_handle_name", "")).strip()
            h_supplier = str(extra.get("drawer_handle_supplier", "")).strip()
            h_code = str(extra.get("drawer_handle_code", "")).strip()
        else:
            qty = int(extra.get("handle_qty", extra.get("num_doors", 0)) or 0)
            h_name = str(extra.get("handle_name", "")).strip()
            h_supplier = str(extra.get("handle_supplier", "")).strip()
            h_code = str(extra.get("handle_code", "")).strip()
        handle_key = f"handle::{h_name}::{h_supplier}::{h_code}"
        handle_label = h_name or "Handle"
        _add_required(handle_key, handle_label, qty, "pcs")

    for r in database.get_quote_extras(int(quote_id)):
        _add_required(f"extra::{int(r['extra_id'])}", str(r.get("extra_name", "Extra")), float(int(r.get("qty", 1) or 1)), "pcs")

    for b in _board_usage_rows(int(quote_id), units):
        meta = dict(b.get("meta", {}))
        costing_mode = str(meta.get("costing_mode", "sheet") or "sheet").strip().lower()
        if costing_mode == "sqm":
            _add_required(f"{b['item_key']}::sqm", f"{b['description']} (SQM)", float(meta.get("used_area_m2", 0.0) or 0.0), "m2")
            continue
        _add_required(f"{b['item_key']}::sheet", f"{b['description']} (Sheet)", float(b["qty"]), "sheet")
        _add_required(f"{b['item_key']}::edging_m", f"{b['description']} (Edging)", float(meta.get("total_edge_m", 0.0) or 0.0), "m")
        _add_required(f"{b['item_key']}::labour_board", f"{b['description']} (Labour)", float(b["qty"]), "board")

    rows: list[RequiredPriceItem] = []
    for item_key, payload in counts.items():
        item_type = item_key.split("::", 1)[0]
        rate_row = items_lookup.get((item_type, item_key))
        rows.append(
            RequiredPriceItem(
                item_type=item_type,
                item_key=item_key,
                description=str(payload["description"]),
                uom=str(payload["uom"]),
                qty_required=float(payload["qty"]),
                unit_price_cents=(int(rate_row["unit_price_cents"]) if rate_row else None),
            )
        )

    rows.sort(key=lambda x: (x.item_type, x.description.lower()))
    return rows


def price_quote(quote_id: int, pricing_mode: str, pricing_value_percent: float) -> PricingResult:
    active_price_list = database.get_active_price_list()
    if not active_price_list:
        raise ValueError("No active price list found.")

    items = database.get_price_list_items(int(active_price_list["id"]))
    lookup = {(str(i["item_type"]), str(i["item_key"])): i for i in items}

    units = database.get_units_for_quote(int(quote_id))
    lines_a, missing_a = _component_lines(units, lookup)
    lines_b, missing_b = _extra_lines(int(quote_id), lookup)
    lines_c, missing_c = _board_lines(int(quote_id), units, lookup)
    lines = lines_a + lines_b + lines_c
    missing = missing_a + missing_b + missing_c

    if missing:
        user_missing: list[str] = []
        for m in sorted(set(missing)):
            user_missing.append(str(m))
        missing_s = "\n".join(user_missing)
        raise ValueError(f"Missing prices for required items:\n{missing_s}")

    subtotal_cents = int(sum(int(x["line_total_cents"]) for x in lines))
    pricing_value_bps = _to_bps(float(pricing_value_percent))
    sell_before_vat_cents = _apply_pricing_mode(subtotal_cents, pricing_mode, pricing_value_bps)

    settings = database.get_pricing_settings()
    vat_rate_bps = int(settings.get("vat_rate_bps", 0) or 0)
    vat_cents = int(round(sell_before_vat_cents * (vat_rate_bps / 10_000.0)))
    grand_total_cents = int(sell_before_vat_cents + vat_cents)

    run_id = database.create_quote_pricing_run(
        quote_id=int(quote_id),
        price_list_id=int(active_price_list["id"]),
        pricing_mode=str(pricing_mode).strip().lower(),
        pricing_value_bps=int(pricing_value_bps),
        vat_rate_bps_snapshot=int(vat_rate_bps),
        subtotal_cents=int(subtotal_cents),
        sell_before_vat_cents=int(sell_before_vat_cents),
        vat_cents=int(vat_cents),
        grand_total_cents=int(grand_total_cents),
        lines=lines,
    )

    return PricingResult(
        run_id=int(run_id),
        quote_id=int(quote_id),
        price_list_id=int(active_price_list["id"]),
        pricing_mode=str(pricing_mode).strip().lower(),
        pricing_value_bps=int(pricing_value_bps),
        vat_rate_bps=int(vat_rate_bps),
        subtotal_cents=int(subtotal_cents),
        sell_before_vat_cents=int(sell_before_vat_cents),
        vat_cents=int(vat_cents),
        grand_total_cents=int(grand_total_cents),
        line_count=len(lines),
    )
