from __future__ import annotations

from typing import Any

from corequote_core.detailed_pricing import price_quote_detailed
from corequote_core.production_export import render_production_handoff_csv, render_production_handoff_xlsx
from corequote_core.production_handoff import build_production_handoff

from test_production_exports import _csv_rows, _xlsx_sheets
from test_real_job_output_package import smith_kitchen_phase_2


def test_smith_kitchen_phase5_workshop_handoff_exports_safe_workshop_packet():
    scenario = _smith_kitchen_phase5()
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
    handoff = build_production_handoff(
        quote=scenario["quote"],
        project=scenario["project"],
        units=scenario["units"],
        cutting_list=cutting_list,
        material_summary=pricing_summary["material_summary"],
        hardware_pick_list=pricing_summary["hardware_pick_list"],
        board_lookup=scenario["board_lookup"],
    )

    assert handoff["project_name"] == "Smith Kitchen Phase 5 Workshop Handoff"
    assert handoff["row_count"] == 22
    assert handoff["group_count"] == 13
    assert handoff["label_count"] == handoff["row_count"]
    assert handoff["warning_count"] == 0
    assert handoff["board_requirements"]["warning_count"] == 0

    rows_by_desc = {row["desc"]: row for row in handoff["rows"]}
    assert rows_by_desc["Base 1 door"]["part_id"] == "Q-043-R1-U01-PAN-BASE-1-DOOR-777X597-01"
    assert rows_by_desc["Base 1 door"]["edge_sides_label"] == "L1, L2"
    assert rows_by_desc["Base 1 door"]["edge_banding"] == "1mm ABS on all exposed door and drawer-front edges"
    assert rows_by_desc["Base 1 door"]["grain_label"] == "Length grain"
    assert rows_by_desc["Base 1 door"]["rotation_label"] == "No rotation"

    drawer_front = rows_by_desc["Drawer front"]
    assert drawer_front["part_id"] == "Q-043-R1-U03-PAN-DRAWER-FRONT-252X897-01"
    assert drawer_front["edge_banding"] == "1mm ABS on all drawer-front edges"
    assert drawer_front["grain_label"] == "Width grain"
    assert drawer_front["production_notes"] == "Stack drawer-front labels from top to bottom."

    visible_panel_descs = {"Base side panel pair", "Wall side filler", "Kicker", "Wall pelmet"}
    quote_panel_rows = [row for row in handoff["rows"] if row["source_type"] == "quote_panel"]
    assert {row["desc"] for row in quote_panel_rows} == visible_panel_descs
    assert rows_by_desc["Kicker"]["part_id"] == "Q-043-R1-QP-EXT-KICKER-2100X100-01"
    assert rows_by_desc["Kicker"]["edge_banding"] == "1mm ABS on all exposed visible-panel edges"
    assert rows_by_desc["Wall pelmet"]["grain_label"] == "Width grain"
    assert rows_by_desc["Wall pelmet"]["production_notes"] == "Run pelmet grain continuously across the wall units."

    row_part_ids = {row["part_id"] for row in handoff["rows"]}
    assert {label["part_id"] for label in handoff["labels"]} == row_part_ids
    assert all(label["warning_count"] == 0 for label in handoff["labels"])

    material_groups = {
        (group["board_type_id"], group["material_role"]): group
        for group in handoff["material_summary"]["groups"]
    }
    assert handoff["material_summary"]["total_piece_count"] == sum(row["qty"] for row in scenario["cutting_rows"])
    assert material_groups[("board-visible", "visible_panel")]["part_ids"] == [row["part_id"] for row in quote_panel_rows]

    board_requirements = handoff["board_requirements"]
    assert board_requirements["estimate_label"] == "Sheet counts are estimates only; CoreQuote has not optimized board nesting."
    assert board_requirements["total_piece_count"] == handoff["material_summary"]["total_piece_count"]
    assert board_requirements["total_estimated_sheets"] == handoff["material_summary"]["total_estimated_sheets"]
    visible_requirement = next(
        group
        for group in board_requirements["groups"]
        if group["board_type_id"] == "board-visible" and group["material_role"] == "visible_panel"
    )
    assert visible_requirement["source_labels"] == ["Quote-level"]
    assert visible_requirement["part_ids"] == [row["part_id"] for row in quote_panel_rows]
    assert visible_requirement["sheet_estimate_label"].endswith("(area estimate, not optimized nesting).")

    pick_items = {item["item_key"]: item for item in handoff["hardware_pick_list"]["items"]}
    assert pick_items["slide::slide-soft-close-500"]["quantity"] == 3
    assert pick_items["hinge::hinge-110-soft-close"]["quantity"] == 12
    assert pick_items["handle::handle-base-pull"]["quantity"] == 2
    assert pick_items["handle::handle-wall-pull"]["quantity"] == 2
    assert pick_items["handle::handle-tall-pull"]["quantity"] == 1
    assert pick_items["handle::handle-drawer-pull"]["quantity"] == 3
    assert pick_items["extra::extra-site-protection"]["quantity"] == 1
    assert all(part_id in row_part_ids for part_id in pick_items["slide::slide-soft-close-500"]["related_part_ids"])

    csv_rows = _csv_rows(render_production_handoff_csv(handoff))
    assert len(csv_rows) == handoff["row_count"]
    assert csv_rows[0]["Project"] == "Smith Kitchen Phase 5 Workshop Handoff"
    assert rows_by_csv_part(csv_rows)["Q-043-R1-QP-EXT-KICKER-2100X100-01"]["Warning State"] == "Ready"

    workbook = _xlsx_sheets(render_production_handoff_xlsx(handoff))
    assert set(workbook) == {
        "Cutting Schedule",
        "Material Summary",
        "Board Requirements",
        "Hardware Pick List",
        "Labels",
        "Warnings",
    }
    assert workbook["Warnings"] == [["Warning Source", "Severity", "Code", "Part ID", "Unit", "Section", "Item", "Message"]]
    assert any("Q-043-R1-QP-EXT-KICKER-2100X100-01" in row for row in workbook["Labels"])
    assert any(
        "Q-043-R1-QP-EXT-KICKER-2100X100-01" in str(cell)
        for row in workbook["Board Requirements"]
        for cell in row
    )
    assert_no_pricing_fields(handoff)
    assert_no_private_export_text(csv_rows, workbook)


def rows_by_csv_part(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["Part ID"]: row for row in rows}


def _smith_kitchen_phase5() -> dict[str, Any]:
    scenario = smith_kitchen_phase_2()
    scenario["project"] = {
        **scenario["project"],
        "name": "Smith Kitchen Phase 5 Workshop Handoff",
        "description": "Phase 5 workshop handoff acceptance kitchen.",
    }
    scenario["quote"] = {
        **scenario["quote"],
        "name": "Smith Kitchen Phase 5 Workshop Handoff",
        "notes": "Workshop handoff scenario with edge, grain, labels, materials, hardware, and safe exports.",
        "production_metadata": {
            "door_panel": {
                "edge_banding": "1mm ABS on all exposed door and drawer-front edges",
                "grain_direction": "length",
                "rotation": "no_rotation",
                "notes": "Keep door labels matched to the unit number.",
            },
            "visible_panel": {
                "edge_banding": "1mm ABS on all exposed visible-panel edges",
                "grain_direction": "length",
                "rotation": "no_rotation",
                "notes": "Label finished face before cutting.",
            },
        },
    }
    scenario["units"] = [
        {
            **unit,
            "production_metadata": {
                "door_panel": {
                    "edge_banding": "1mm ABS on all drawer-front edges",
                    "grain_direction": "width",
                    "rotation": "no_rotation",
                    "notes": "Stack drawer-front labels from top to bottom.",
                }
            },
        }
        if unit["unit_number"] == 3
        else unit
        for unit in scenario["units"]
    ]
    scenario["board_lookup"] = {
        board_id: {
            **board,
            "grain_policy": "none" if board_id == "board-carcass" else "required",
        }
        for board_id, board in scenario["board_lookup"].items()
    }
    scenario["cutting_rows"] = [_phase5_cutting_row(row) for row in scenario["cutting_rows"]]
    return scenario


def _phase5_cutting_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    if payload["section"] == "panel":
        payload.update(
            {
                "edge_long_1": True,
                "edge_long_2": True,
                "edge_short_1": False,
                "edge_short_2": False,
                "can_rotate": False,
            }
        )
    if payload["section"] == "extra_panel":
        payload.update(
            {
                "edge_long_1": True,
                "edge_long_2": False,
                "edge_short_1": True,
                "edge_short_2": False,
                "can_rotate": False,
            }
        )
    if payload["desc"] == "Wall pelmet":
        payload["production_metadata"] = {
            "edge_banding": "1mm ABS on front long edge only",
            "grain_direction": "width",
            "rotation": "no_rotation",
            "notes": "Run pelmet grain continuously across the wall units.",
        }
    return payload


def assert_no_pricing_fields(value: Any) -> None:
    blocked = {
        "client_quote_total_cents",
        "cost_total_cents",
        "sell_total_cents",
        "profit_cents",
        "line_total_cents",
        "unit_cost_cents",
        "unit_price_cents",
        "markup_bps",
        "margin_bps",
        "grand_total_cents",
        "subtotal_cents",
    }
    if isinstance(value, dict):
        assert blocked.isdisjoint(value)
        for child in value.values():
            assert_no_pricing_fields(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_pricing_fields(child)


def assert_no_private_export_text(csv_rows: list[dict[str, str]], workbook: dict[str, list[list[object]]]) -> None:
    blocked = (
        "client_quote_total_cents",
        "cost_total_cents",
        "sell_total_cents",
        "profit_cents",
        "line_total_cents",
        "unit_cost_cents",
        "unit_price_cents",
        "markup_bps",
        "margin_bps",
        "grand_total_cents",
        "subtotal_cents",
    )
    flattened = "\n".join(
        [
            *(",".join(row.values()) for row in csv_rows),
            *(",".join(str(value) for value in row) for rows in workbook.values() for row in rows),
        ]
    )
    for text in blocked:
        assert text not in flattened
