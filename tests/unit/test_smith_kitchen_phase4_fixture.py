from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from corequote_api.library_imports import build_import_preview, build_reference_maps
from corequote_core.customer_quote_pdf import build_customer_quote_document, render_customer_quote_pdf
from corequote_core.detailed_pricing import price_quote_detailed
from corequote_core.output_review import build_quote_output_review
from corequote_core.quote_readiness import evaluate_quote_readiness
from corequote_core.workshop_schedule_pdf import build_workshop_schedule_document, render_workshop_schedule_pdf

from test_real_job_output_package import smith_kitchen_phase_2


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "docs" / "testing" / "fixtures" / "smith-kitchen-phase-4-library-refresh"
PRICE_LIST_ID = "price-list-smith-phase-4-refresh"


def test_smith_kitchen_phase4_import_fixture_prices_complete_output_package():
    snapshot = _empty_snapshot()

    for resource in ("suppliers", "boards", "slides", "hinges", "handles", "extra_categories", "extras"):
        preview = _preview(resource, snapshot)
        assert preview["summary"]["blocked_count"] == 0
        assert preview["summary"]["duplicate_count"] == 0
        assert preview["summary"]["create_count"] == len(preview["rows"])
        snapshot[_snapshot_key(resource)].extend(_applied_rows(resource, preview))

    supplier_cost_preview = _preview("supplier_item_costs", snapshot)
    assert supplier_cost_preview["summary"]["total_rows"] == 10
    assert supplier_cost_preview["summary"]["blocked_count"] == 0
    assert supplier_cost_preview["summary"]["create_count"] == 10
    assert {row["payload"]["currency_code"] for row in supplier_cost_preview["rows"]} == {"ZAR"}

    price_preview = _preview("price_list_items", snapshot)
    assert price_preview["summary"]["total_rows"] == 10
    assert price_preview["summary"]["blocked_count"] == 0
    assert price_preview["summary"]["duplicate_count"] == 0
    assert price_preview["summary"]["create_count"] == 10
    price_rows = _applied_rows("price_list_items", price_preview)
    snapshot["price_items"].extend(price_rows)

    scenario = smith_kitchen_phase_2()
    scenario.update(
        {
            "active_price_list_id": PRICE_LIST_ID,
            "board_lookup": _lookup(snapshot["boards"]),
            "slide_lookup": _lookup(snapshot["slides"]),
            "hinge_lookup": _lookup(snapshot["hinges"]),
            "handle_lookup": _lookup(snapshot["handles"]),
            "extra_lookup": _lookup(snapshot["extras"]),
            "price_lookup": _price_lookup(price_rows),
        }
    )

    pricing_summary, readiness, cutting_list = _price_and_check(scenario)

    assert pricing_summary["is_complete"] is True
    assert pricing_summary["missing_prices"] == []
    assert pricing_summary["grand_total_cents"] > pricing_summary["sell_before_vat_cents"] > 0
    assert readiness["status"] == "ready"
    assert readiness["warning_count"] == 0

    material_groups = {(group["board_type_id"], group["material_role"]): group for group in pricing_summary["material_summary"]["groups"]}
    assert material_groups[("board-carcass", "carcass")]["material"] == "White melamine"
    assert material_groups[("board-door", "door_panel")]["material"] == "Matt white door board"
    assert material_groups[("board-visible", "visible_panel")]["material"] == "Matt white visible panel"
    assert all(group["sell_total_cents"] for group in material_groups.values())

    pick_items = {item["item_key"]: item for item in pricing_summary["hardware_pick_list"]["items"]}
    assert pick_items["slide::slide-soft-close-500"]["item_name"] == "Grass Dynapro soft close"
    assert pick_items["hinge::hinge-110-soft-close"]["item_name"] == "Blum 110 degree soft close"
    assert pick_items["handle::handle-drawer-pull"]["item_name"] == "Drawer pull"
    assert pick_items["extra::extra-site-protection"]["item_name"] == "Site protection"
    assert pricing_summary["hardware_pick_list"]["total_quantity"] == 24

    review = build_quote_output_review(
        quote=scenario["quote"],
        project=scenario["project"],
        currency_code=scenario["currency_code"],
        readiness=readiness,
        cutting_list=cutting_list,
        pricing_summary=pricing_summary,
        active_price_list_id=scenario["active_price_list_id"],
        hardware_pick_list=pricing_summary["hardware_pick_list"],
    )
    assert {action["id"]: action["enabled"] for action in review["actions"]} == {
        "client_quote_pdf": True,
        "workshop_schedule": True,
        "material_summary": True,
        "hardware_pick_list": True,
    }

    customer_document = build_customer_quote_document(
        company=scenario["company"],
        quote=scenario["quote"],
        project=scenario["project"],
        currency_code=scenario["currency_code"],
        pricing_summary=pricing_summary,
        issue_date=date(2026, 6, 12),
    )
    assert customer_document.grand_total_cents == pricing_summary["grand_total_cents"]
    assert render_customer_quote_pdf(customer_document).startswith(b"%PDF")

    workshop_document = build_workshop_schedule_document(
        company=scenario["company"],
        quote=scenario["quote"],
        project=scenario["project"],
        units=scenario["units"],
        cutting_list=cutting_list,
        board_lookup=scenario["board_lookup"],
        export_date=date(2026, 6, 12),
    )
    workshop_materials = {row.board_material for group in workshop_document.groups for row in group.rows}
    assert "CoreBoard White melamine 16mm" in workshop_materials
    assert "CoreBoard Matt white door board 18mm" in workshop_materials
    assert "CoreBoard Matt white visible panel 18mm" in workshop_materials
    assert render_workshop_schedule_pdf(workshop_document).startswith(b"%PDF")

    original_total = pricing_summary["grand_total_cents"]
    refreshed_lookup = dict(scenario["price_lookup"])
    refreshed_lookup[("handle", "handle::handle-drawer-pull", "unit")] = {"unit_price_cents": 14800}
    refreshed_summary, _, _ = _price_and_check({**scenario, "price_lookup": refreshed_lookup})

    assert pricing_summary["grand_total_cents"] == original_total
    assert refreshed_summary["grand_total_cents"] > original_total


def _fixture_content(filename: str) -> str:
    return (FIXTURE_DIR / filename).read_text(encoding="utf-8")


def _preview(resource: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    return build_import_preview(
        {
            "resource": resource,
            "source_format": "csv",
            "content": _fixture_content(f"{resource}.csv"),
            "price_list_id": PRICE_LIST_ID if resource == "price_list_items" else None,
        },
        build_reference_maps({**snapshot, "price_list_id": PRICE_LIST_ID}),
    )


def _empty_snapshot() -> dict[str, Any]:
    return {
        "boards": [],
        "slides": [],
        "hinges": [],
        "handles": [],
        "suppliers": [],
        "extra_categories": [],
        "extras": [],
        "item_suppliers": [],
        "price_items": [],
        "price_list_id": PRICE_LIST_ID,
    }


def _snapshot_key(resource: str) -> str:
    return {
        "extra_categories": "extra_categories",
        "price_list_items": "price_items",
        "supplier_item_costs": "item_suppliers",
    }.get(resource, resource)


def _applied_rows(resource: str, preview: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in preview["rows"]:
        assert row["status"] == "create"
        payload = dict(row["payload"])
        payload["id"] = _stable_id(resource, payload)
        rows.append(payload)
    return rows


def _stable_id(resource: str, payload: dict[str, Any]) -> str:
    if resource == "boards":
        return {
            "White melamine": "board-carcass",
            "Matt white door board": "board-door",
            "Matt white visible panel": "board-visible",
        }[payload["material"]]
    if resource == "slides":
        return {"S500": "slide-soft-close-500"}[payload["code"]]
    if resource == "hinges":
        return {"H110": "hinge-110-soft-close"}[payload["code"]]
    if resource == "handles":
        return {
            "B128": "handle-base-pull",
            "W128": "handle-wall-pull",
            "T256": "handle-tall-pull",
            "D192": "handle-drawer-pull",
        }[payload["code"]]
    if resource == "suppliers":
        return {
            "CoreBoard Supply": "supplier-coreboard",
            "Core Hardware": "supplier-core-hardware",
            "CoreQuote": "supplier-corequote",
        }[payload["name"]]
    if resource == "extra_categories":
        return {"Site extras": "category-site-extras"}[payload["name"]]
    if resource == "extras":
        return {"SITE-PROTECT": "extra-site-protection"}[payload["code"]]
    if resource == "price_list_items":
        return f"price-{payload['item_type']}-{payload['item_ref_id']}-{payload['price_component']}"
    if resource == "supplier_item_costs":
        return f"supplier-cost-{payload['item_type']}-{payload['item_ref_id']}-{payload['supplier_id']}-{payload['supplier_sku']}"
    raise AssertionError(f"Unsupported fixture resource: {resource}")


def _lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in rows}


def _price_lookup(price_rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {
        (row["item_type"], row["item_key"], row["price_component"]): {"unit_price_cents": row["unit_price_cents"]}
        for row in price_rows
    }


def _price_and_check(scenario: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
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
    return pricing_summary, readiness, cutting_list
