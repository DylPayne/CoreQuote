from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from corequote_core.customer_quote_pdf import build_customer_quote_document, render_customer_quote_pdf
from corequote_core.detailed_pricing import DetailedPricingSettings, price_quote_detailed
from corequote_core.output_review import build_quote_output_review
from corequote_core.quote_readiness import evaluate_quote_readiness
from corequote_core.workshop_schedule_pdf import build_workshop_schedule_document, render_workshop_schedule_pdf


def test_smith_kitchen_phase_2_generates_complete_output_package():
    scenario = smith_kitchen_phase_2()
    pricing_summary = price_quote_detailed(
        quote=scenario["quote"],
        units=scenario["units"],
        quote_extras=scenario["quote_extras"],
        cutting_rows=scenario["cutting_rows"],
        settings=scenario["pricing_settings"],
        price_lookup=scenario["price_lookup"],
        board_lookup=scenario["board_lookup"],
        slide_lookup=scenario["slide_lookup"],
        hinge_lookup=scenario["hinge_lookup"],
        handle_lookup=scenario["handle_lookup"],
        extra_lookup=scenario["extra_lookup"],
        active_price_list_id=scenario["active_price_list_id"],
    )
    cutting_list = {
        "carcass": [],
        "panels": [],
        "hardware": [],
        "extras": [],
        "runtime_rows": scenario["cutting_rows"],
        "runtime_mode": "legacy",
        "unit_sources": [],
        "validation_warnings": [],
    }
    readiness = evaluate_quote_readiness(
        quote=scenario["quote"],
        project=scenario["project"],
        units=scenario["units"],
        cutting_list=cutting_list,
        pricing_summary=pricing_summary,
        active_price_list_id=scenario["active_price_list_id"],
        hardware_pick_list=pricing_summary["hardware_pick_list"],
    )

    assert pricing_summary["is_complete"] is True
    assert pricing_summary["missing_prices"] == []
    assert pricing_summary["sell_before_vat_cents"] > 0
    assert pricing_summary["vat_cents"] > 0
    assert pricing_summary["grand_total_cents"] == pricing_summary["sell_before_vat_cents"] + pricing_summary["vat_cents"]

    assert readiness["status"] == "ready"
    assert readiness["warning_count"] == 0
    assert {check["id"] for check in readiness["checks"] if check["severity"] == "pass"} == {
        "project_details",
        "unit_count",
        "default_boards",
        "unit_boards",
        "cutlist_rows",
        "missing_prices",
        "quote_totals",
        "hardware_pick_list",
        "required_outputs",
    }

    material_summary = pricing_summary["material_summary"]
    material_groups = {(group["board_type_id"], group["material_role"]): group for group in material_summary["groups"]}
    assert material_summary["warnings"] == []
    assert set(material_groups) == {
        ("board-carcass", "carcass"),
        ("board-door", "door_panel"),
        ("board-visible", "visible_panel"),
    }
    assert material_summary["total_piece_count"] == sum(row["qty"] for row in scenario["cutting_rows"])
    assert material_summary["total_area_m2"] > 0
    assert material_summary["total_estimated_sheets"] is not None
    assert all(group["sell_total_cents"] for group in material_groups.values())

    pick_list = pricing_summary["hardware_pick_list"]
    pick_items = {item["item_key"]: item for item in pick_list["items"]}
    assert pick_list["warnings"] == []
    assert pick_list["total_item_count"] == 7
    assert pick_list["total_quantity"] == 24
    assert pick_items["slide::slide-soft-close-500"]["quantity"] == 3
    assert pick_items["hinge::hinge-110-soft-close"]["quantity"] == 12
    assert pick_items["handle::handle-base-pull"]["quantity"] == 2
    assert pick_items["handle::handle-wall-pull"]["quantity"] == 2
    assert pick_items["handle::handle-tall-pull"]["quantity"] == 1
    assert pick_items["handle::handle-drawer-pull"]["quantity"] == 3
    assert pick_items["extra::extra-site-protection"]["quantity"] == 1

    review = build_quote_output_review(
        quote=scenario["quote"],
        project=scenario["project"],
        currency_code=scenario["currency_code"],
        readiness=readiness,
        cutting_list=cutting_list,
        pricing_summary=pricing_summary,
        active_price_list_id=scenario["active_price_list_id"],
        hardware_pick_list=pick_list,
    )
    actions = {action["id"]: action for action in review["actions"]}
    assert review["client_quote_total_cents"] == pricing_summary["grand_total_cents"]
    assert actions["client_quote_pdf"]["enabled"] is True
    assert actions["client_quote_pdf"]["hides_internal_costs"] is True
    assert actions["workshop_schedule"]["enabled"] is True
    assert actions["material_summary"]["enabled"] is True
    assert actions["hardware_pick_list"]["enabled"] is True

    customer_document = build_customer_quote_document(
        company=scenario["company"],
        quote=scenario["quote"],
        project=scenario["project"],
        currency_code=scenario["currency_code"],
        pricing_summary=pricing_summary,
        issue_date=date(2026, 6, 11),
    )
    section_amounts = {section.label: section.amount_cents for section in customer_document.sections}
    assert customer_document.client_name == "Sam Smith"
    assert customer_document.expiry_date == date(2026, 7, 11)
    assert customer_document.grand_total_cents == pricing_summary["grand_total_cents"]
    assert sum(section_amounts.values()) == customer_document.subtotal_cents
    assert section_amounts["Visible panels"] == material_groups[("board-visible", "visible_panel")]["sell_total_cents"]
    assert section_amounts["Installation"] > 0
    assert section_amounts["Delivery"] > 0
    for key in _keys(asdict(customer_document)):
        assert "cost" not in key
        assert "profit" not in key
        assert "margin" not in key
    assert render_customer_quote_pdf(customer_document).startswith(b"%PDF")

    workshop_document = build_workshop_schedule_document(
        company=scenario["company"],
        quote=scenario["quote"],
        project=scenario["project"],
        units=scenario["units"],
        cutting_list=cutting_list,
        board_lookup=scenario["board_lookup"],
        export_date=date(2026, 6, 11),
    )
    assert [group.title for group in workshop_document.groups] == [
        "Carcass rows",
        "Panel rows",
        "Custom panel rows",
    ]
    assert workshop_document.warnings == []
    workshop_rows = [row for group in workshop_document.groups for row in group.rows]
    assert len(workshop_rows) == len(scenario["cutting_rows"])
    assert all(row.length > 0 and row.width > 0 and row.qty > 0 for row in workshop_rows)
    assert all(row.board_material != "-" for row in workshop_rows)
    assert render_workshop_schedule_pdf(workshop_document).startswith(b"%PDF")


def smith_kitchen_phase_2() -> dict[str, Any]:
    quote = {
        "id": "quote-smith-phase-2",
        "project_id": "project-smith",
        "name": "Smith Kitchen Phase 2",
        "notes": "Quote valid for 30 days. 50% deposit, balance before installation.",
        "status": "ready",
        "quote_number": "Q-043",
        "revision": 1,
        "unit_count": 6,
        "default_carcass_board_type_id": "board-carcass",
        "default_door_board_type_id": "board-door",
        "default_panel_board_type_id": "board-visible",
        "default_slide_id": "slide-soft-close-500",
        "default_hinge_id": "hinge-110-soft-close",
        "default_base_handle_id": "handle-base-pull",
        "default_wall_handle_id": "handle-wall-pull",
        "default_tall_handle_id": "handle-tall-pull",
        "default_drawer_handle_id": "handle-drawer-pull",
    }
    project = {
        "id": "project-smith",
        "name": "Smith Kitchen Phase 2",
        "client": "Sam Smith",
        "address": "12 Oak Street",
        "description": "Phase 2 output package acceptance kitchen.",
    }
    units = [
        unit(1, "Base Door", 600, 780, 580, {"num_doors": 1, "num_shelves": 1}),
        unit(2, "Base Door", 600, 780, 580, {"num_doors": 1, "num_shelves": 1}),
        unit(3, "Base Draw", 900, 780, 580, {"num_drawers": 3, "handle_qty": 3}),
        unit(4, "Wall Door", 600, 720, 330, {"num_doors": 1, "num_shelves": 1}),
        unit(5, "Wall Door", 600, 720, 330, {"num_doors": 1, "num_shelves": 1}),
        unit(6, "Tall Door", 600, 2100, 580, {"num_doors": 1, "num_shelves": 4}),
    ]
    board_lookup = {
        "board-carcass": {
            "id": "board-carcass",
            "brand": "CoreBoard",
            "material": "White melamine",
            "thickness": 16,
            "length_mm": 2750,
            "width_mm": 1830,
            "costing_mode": "sheet",
        },
        "board-door": {
            "id": "board-door",
            "brand": "CoreBoard",
            "material": "Matt white door board",
            "thickness": 18,
            "length_mm": 2750,
            "width_mm": 1830,
            "costing_mode": "sheet",
        },
        "board-visible": {
            "id": "board-visible",
            "brand": "CoreBoard",
            "material": "Matt white visible panel",
            "thickness": 18,
            "length_mm": 2750,
            "width_mm": 1830,
            "costing_mode": "sheet",
        },
    }
    price_lookup = {
        ("board", "board::board-carcass", "sheet"): {"unit_price_cents": 145000},
        ("board", "board::board-door", "sheet"): {"unit_price_cents": 168000},
        ("board", "board::board-visible", "sheet"): {"unit_price_cents": 172000},
        ("slide", "slide::slide-soft-close-500", "unit"): {"unit_price_cents": 18500},
        ("hinge", "hinge::hinge-110-soft-close", "unit"): {"unit_price_cents": 3600},
        ("handle", "handle::handle-base-pull", "unit"): {"unit_price_cents": 9200},
        ("handle", "handle::handle-wall-pull", "unit"): {"unit_price_cents": 8800},
        ("handle", "handle::handle-tall-pull", "unit"): {"unit_price_cents": 11200},
        ("handle", "handle::handle-drawer-pull", "unit"): {"unit_price_cents": 9800},
        ("extra", "extra::extra-site-protection", "unit"): {"unit_price_cents": 30000},
    }
    return {
        "company": {
            "name": "CoreQuote Test Co",
            "contact_name": "Test Owner",
            "contact_email": "test.owner@corequote.local",
        },
        "project": project,
        "quote": quote,
        "units": units,
        "quote_extras": [{"extra_id": "extra-site-protection", "quantity": 1}],
        "cutting_rows": cutting_rows(),
        "currency_code": "ZAR",
        "active_price_list_id": "price-list-smith-phase-2",
        "pricing_settings": DetailedPricingSettings(
            vat_rate_bps=1500,
            default_markup_bps=2500,
            carcass_markup_bps=2500,
            door_panel_markup_bps=2500,
            component_markup_bps=2500,
            handle_markup_bps=2500,
            extras_markup_bps=2500,
            fabrication_markup_bps=2500,
            install_markup_bps=2500,
            delivery_markup_bps=2500,
            labour_cents_per_m2=2000,
            consumables_cents_per_m2=1000,
            install_day_cost_cents=190000,
            delivery_base_cents=95000,
            install_units_per_day=12,
            delivery_units_per_trip=20,
            minimum_install_days_bps=5000,
            minimum_delivery_trips_bps=5000,
        ),
        "board_lookup": board_lookup,
        "slide_lookup": {
            "slide-soft-close-500": {
                "id": "slide-soft-close-500",
                "brand": "Grass",
                "model": "Dynapro soft close",
                "code": "S500",
            }
        },
        "hinge_lookup": {
            "hinge-110-soft-close": {
                "id": "hinge-110-soft-close",
                "brand": "Blum",
                "model": "110 degree soft close",
                "code": "H110",
            }
        },
        "handle_lookup": {
            "handle-base-pull": {"id": "handle-base-pull", "name": "Base pull", "supplier": "Core Hardware", "code": "B128"},
            "handle-wall-pull": {"id": "handle-wall-pull", "name": "Wall pull", "supplier": "Core Hardware", "code": "W128"},
            "handle-tall-pull": {"id": "handle-tall-pull", "name": "Tall pull", "supplier": "Core Hardware", "code": "T256"},
            "handle-drawer-pull": {"id": "handle-drawer-pull", "name": "Drawer pull", "supplier": "Core Hardware", "code": "D192"},
        },
        "extra_lookup": {
            "extra-site-protection": {
                "id": "extra-site-protection",
                "name": "Site protection",
                "category_name": "Site extras",
                "supplier": "CoreQuote",
                "code": "SITE-PROTECT",
            }
        },
        "price_lookup": price_lookup,
    }


def unit(unit_number: int, unit_type_key: str, width: int, height: int, depth: int, extra_params: dict[str, int]) -> dict[str, Any]:
    return {
        "id": f"unit-{unit_number}",
        "quote_id": "quote-smith-phase-2",
        "unit_number": unit_number,
        "unit_type_key": unit_type_key,
        "width": width,
        "height": height,
        "depth": depth,
        "carcass_board_type_id": None,
        "door_board_type_id": None,
        "extra_params": extra_params,
    }


def cutting_rows() -> list[dict[str, Any]]:
    return [
        row(1, "carcass", "Base 1 side", 748, 564, 2),
        row(1, "carcass", "Base 1 shelf", 568, 564, 1),
        row(1, "panel", "Base 1 door", 777, 597, 1),
        row(2, "carcass", "Base 2 side", 748, 564, 2),
        row(2, "carcass", "Base 2 shelf", 568, 564, 1),
        row(2, "panel", "Base 2 door", 777, 597, 1),
        row(3, "carcass", "Drawer unit side", 748, 564, 2),
        row(3, "carcass", "Drawer bottom", 868, 564, 1),
        row(3, "panel", "Drawer front", 252, 897, 3),
        row(4, "carcass", "Wall 1 side", 688, 314, 2),
        row(4, "carcass", "Wall 1 shelf", 568, 314, 1),
        row(4, "panel", "Wall 1 door", 717, 597, 1),
        row(5, "carcass", "Wall 2 side", 688, 314, 2),
        row(5, "carcass", "Wall 2 shelf", 568, 314, 1),
        row(5, "panel", "Wall 2 door", 717, 597, 1),
        row(6, "carcass", "Tall side", 2068, 564, 2),
        row(6, "carcass", "Tall shelf", 568, 564, 4),
        row(6, "panel", "Tall door", 2097, 597, 1),
        row(0, "extra_panel", "Base side panel pair", 780, 580, 2, board_type_id="board-visible"),
        row(0, "extra_panel", "Wall side filler", 720, 100, 1, board_type_id="board-visible"),
        row(0, "extra_panel", "Kicker", 2100, 100, 1, board_type_id="board-visible"),
        row(0, "extra_panel", "Wall pelmet", 1200, 100, 1, board_type_id="board-visible"),
    ]


def row(
    unit_number: int,
    section: str,
    desc: str,
    length: int,
    width: int,
    qty: int,
    *,
    board_type_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "unit_number": unit_number,
        "section": section,
        "desc": desc,
        "length": length,
        "width": width,
        "qty": qty,
    }
    if board_type_id:
        payload["board_type_id"] = board_type_id
    return payload


def _keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for key, child in value.items():
            found.append(str(key))
            found.extend(_keys(child))
        return found
    if isinstance(value, list):
        found = []
        for child in value:
            found.extend(_keys(child))
        return found
    return []
