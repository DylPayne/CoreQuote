from corequote_core.production_handoff import build_production_handoff


def test_production_handoff_groups_sorts_custom_panels_and_stable_part_ids():
    result = build_production_handoff(
        quote=quote(),
        project=project(),
        units=[
            unit(1, "Base Door", carcass_board_type_id="board-white", door_board_type_id="board-oak"),
            unit(2, "Wall Door", carcass_board_type_id="board-white", door_board_type_id="board-oak"),
        ],
        cutting_list={
            "runtime_rows": [
                {"unit_number": 2, "section": "panel", "desc": "Door", "length": 720, "width": 297, "qty": 2},
                {"unit_number": 1, "section": "carcass", "desc": "Side", "length": 748, "width": 564, "qty": 2},
                {
                    "unit_number": 0,
                    "section": "extra_panel",
                    "desc": "Kicker",
                    "length": 2400,
                    "width": 100,
                    "qty": 1,
                    "board_type_id": "board-black",
                },
                {"unit_number": 2, "section": "carcass", "desc": "Shelf", "length": 568, "width": 300, "qty": 1},
            ],
            "validation_warnings": [
                {
                    "severity": "warning",
                    "source": "quote_panel",
                    "unit_number": 0,
                    "section": "extra_panel",
                    "row_desc": "Kicker",
                    "reason": "Confirm kicker split before cutting.",
                }
            ],
        },
        material_summary=material_summary(),
        hardware_pick_list=hardware_pick_list(),
        board_lookup=board_lookup(),
    )
    repeated = build_production_handoff(
        quote=quote(),
        project=project(),
        units=[
            unit(1, "Base Door", carcass_board_type_id="board-white", door_board_type_id="board-oak"),
            unit(2, "Wall Door", carcass_board_type_id="board-white", door_board_type_id="board-oak"),
        ],
        cutting_list={
            "runtime_rows": [
                {"unit_number": 2, "section": "panel", "desc": "Door", "length": 720, "width": 297, "qty": 2},
                {"unit_number": 1, "section": "carcass", "desc": "Side", "length": 748, "width": 564, "qty": 2},
                {
                    "unit_number": 0,
                    "section": "extra_panel",
                    "desc": "Kicker",
                    "length": 2400,
                    "width": 100,
                    "qty": 1,
                    "board_type_id": "board-black",
                },
                {"unit_number": 2, "section": "carcass", "desc": "Shelf", "length": 568, "width": 300, "qty": 1},
            ],
            "validation_warnings": [
                {
                    "severity": "warning",
                    "source": "quote_panel",
                    "unit_number": 0,
                    "section": "extra_panel",
                    "row_desc": "Kicker",
                    "reason": "Confirm kicker split before cutting.",
                }
            ],
        },
        material_summary=material_summary(),
        hardware_pick_list=hardware_pick_list(),
        board_lookup=board_lookup(),
    )

    assert [row["part_id"] for row in result["rows"]] == [row["part_id"] for row in repeated["rows"]]
    assert [row["desc"] for row in result["rows"]] == ["Kicker", "Side", "Shelf", "Door"]
    assert [group["board_name"] for group in result["groups"]] == [
        "PG Black (16mm)",
        "PG White (16mm)",
        "PG White (16mm)",
        "Seno Oak (18mm)",
    ]

    kicker = next(row for row in result["rows"] if row["desc"] == "Kicker")
    assert kicker["source_type"] == "quote_panel"
    assert kicker["unit_label"] == "Quote-level"
    assert kicker["warning_count"] == 1
    assert kicker["part_id"] == "Q-007-R2-QP-EXT-KICKER-2400X100-01"

    row_part_ids = {row["part_id"] for row in result["rows"]}
    label_part_ids = {label["part_id"] for label in result["labels"]}
    material_part_ids = {
        part_id
        for group in result["material_summary"]["groups"]
        for part_id in group["part_ids"]
    }
    hardware_related_part_ids = set(result["hardware_pick_list"]["items"][0]["related_part_ids"])

    assert label_part_ids == row_part_ids
    assert material_part_ids == row_part_ids
    assert hardware_related_part_ids == {
        row["part_id"]
        for row in result["rows"]
        if row["unit_number"] in {1, 2}
    }
    assert result["row_count"] == 4
    assert result["group_count"] == 4
    assert result["warning_count"] == 1
    assert_no_pricing_fields(result)


def test_production_handoff_uses_workspace_cutlist_rows_and_unassigned_warnings():
    result = build_production_handoff(
        quote={**quote(), "default_carcass_board_type_id": None},
        project=project(),
        units=[unit(1, "Base Door", carcass_board_type_id=None, door_board_type_id="board-oak")],
        cutting_list={
            "carcass": [{"unit_number": 1, "desc": "Side", "length": 748, "width": 564, "qty": 2}],
            "panels": [{"unit_number": 1, "desc": "Door", "length": 777, "width": 297, "qty": 2}],
            "extras": [],
            "validation_warnings": [
                {
                    "severity": "warning",
                    "source": "unit",
                    "unit_number": 1,
                    "section": "carcass",
                    "row_desc": "Side",
                    "reason": "Choose a carcass board for this unit or quote default.",
                }
            ],
        },
        material_summary={"groups": [], "warnings": [], "total_area_m2": 0, "total_piece_count": 0, "total_edge_m": 0},
        hardware_pick_list={"items": [], "warnings": [], "total_item_count": 0, "total_quantity": 0},
        board_lookup=board_lookup(),
    )

    assert [(row["section"], row["desc"], row["length"], row["width"], row["quantity"]) for row in result["rows"]] == [
        ("carcass", "Side", 748, 564, 2),
        ("panel", "Door", 777, 297, 2),
    ]
    assert result["rows"][0]["board_name"] == "Unassigned material"
    assert result["rows"][0]["warning_messages"] == ["Choose a carcass board for this unit or quote default."]
    assert result["rows"][1]["board_name"] == "Seno Oak (18mm)"
    assert result["groups"][0]["board_name"] == "Unassigned material"


def assert_no_pricing_fields(value):
    blocked = {
        "client_quote_total_cents",
        "cost_total_cents",
        "sell_total_cents",
        "profit_cents",
        "line_total_cents",
        "unit_cost_cents",
        "unit_price_cents",
        "markup_bps",
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


def project() -> dict:
    return {"id": "project-1", "name": "Smith Kitchen Phase 5 Workshop Handoff"}


def quote() -> dict:
    return {
        "id": "quote-1",
        "project_id": "project-1",
        "name": "Workshop Handoff",
        "status": "ready",
        "quote_number": "Q-007",
        "revision": 2,
        "default_carcass_board_type_id": "board-white",
        "default_door_board_type_id": "board-oak",
        "default_panel_board_type_id": "board-black",
    }


def unit(
    unit_number: int,
    unit_type_key: str,
    *,
    carcass_board_type_id: str | None,
    door_board_type_id: str | None,
) -> dict:
    return {
        "unit_number": unit_number,
        "unit_type_key": unit_type_key,
        "carcass_board_type_id": carcass_board_type_id,
        "door_board_type_id": door_board_type_id,
    }


def board_lookup() -> dict:
    return {
        "board-white": {
            "id": "board-white",
            "brand": "PG",
            "material": "White",
            "thickness": 16,
            "length_mm": 2750,
            "width_mm": 1830,
        },
        "board-oak": {
            "id": "board-oak",
            "brand": "Seno",
            "material": "Oak",
            "thickness": 18,
            "length_mm": 2800,
            "width_mm": 1220,
        },
        "board-black": {
            "id": "board-black",
            "brand": "PG",
            "material": "Black",
            "thickness": 16,
            "length_mm": 2750,
            "width_mm": 1830,
        },
    }


def material_summary() -> dict:
    return {
        "groups": [
            {
                "board_type_id": "board-white",
                "material_role": "carcass",
                "role_label": "Carcass",
                "board_name": "PG White (16mm)",
                "brand": "PG",
                "material": "White",
                "thickness": 16,
                "length_mm": 2750,
                "width_mm": 1830,
                "piece_count": 3,
                "area_m2": 1.01,
                "edge_m": 2.4,
                "estimated_sheets": 1,
                "cost_total_cents": 120000,
                "sell_total_cents": 150000,
            },
            {
                "board_type_id": "board-oak",
                "material_role": "door_panel",
                "role_label": "Door/Drawer Panel",
                "board_name": "Seno Oak (18mm)",
                "brand": "Seno",
                "material": "Oak",
                "thickness": 18,
                "length_mm": 2800,
                "width_mm": 1220,
                "piece_count": 2,
                "area_m2": 0.43,
                "edge_m": 1.2,
                "estimated_sheets": 1,
                "cost_total_cents": 90000,
                "sell_total_cents": 112500,
            },
            {
                "board_type_id": "board-black",
                "material_role": "visible_panel",
                "role_label": "Visible Panel",
                "board_name": "PG Black (16mm)",
                "brand": "PG",
                "material": "Black",
                "thickness": 16,
                "length_mm": 2750,
                "width_mm": 1830,
                "piece_count": 1,
                "area_m2": 0.24,
                "edge_m": 0.0,
                "estimated_sheets": 1,
                "cost_total_cents": 60000,
                "sell_total_cents": 75000,
            },
        ],
        "warnings": [],
        "total_area_m2": 1.68,
        "total_piece_count": 6,
        "total_edge_m": 3.6,
        "total_estimated_sheets": 3,
    }


def hardware_pick_list() -> dict:
    return {
        "items": [
            {
                "item_type": "hinge",
                "type_label": "Hinges",
                "item_key": "hinge::hinge-1",
                "item_ref_id": "hinge-1",
                "item_name": "Blum Clip top",
                "supplier": "Blum",
                "code": "H110",
                "quantity": 8,
                "uom": "pcs",
                "unit_numbers": [1, 2],
                "used_in": ["Unit 1 doors", "Unit 2 doors"],
                "usage_label": "Unit 1 doors, Unit 2 doors",
            }
        ],
        "warnings": [],
        "total_item_count": 1,
        "total_quantity": 8,
    }
