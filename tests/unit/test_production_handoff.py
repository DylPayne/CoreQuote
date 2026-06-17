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
    assert result["board_requirements"]["estimate_label"] == (
        "Sheet counts are estimates only; CoreQuote has not optimized board nesting."
    )
    assert result["board_requirements"]["total_piece_count"] == result["material_summary"]["total_piece_count"]
    assert result["board_requirements"]["total_area_m2"] == result["material_summary"]["total_area_m2"]
    assert result["board_requirements"]["total_estimated_sheets"] == result["material_summary"]["total_estimated_sheets"]

    white_requirement = next(
        group
        for group in result["board_requirements"]["groups"]
        if group["board_type_id"] == "board-white" and group["material_role"] == "carcass"
    )
    assert white_requirement["piece_count"] == 3
    assert white_requirement["area_m2"] == 1.01
    assert white_requirement["estimated_sheets"] == 1
    assert white_requirement["sheet_estimate_label"] == "1 estimated sheet (area estimate, not optimized nesting)."
    assert white_requirement["waste_allowance_label"].startswith("Estimated waste allowance ")

    panel_requirement = next(
        group
        for group in result["board_requirements"]["groups"]
        if group["board_type_id"] == "board-black" and group["material_role"] == "visible_panel"
    )
    assert panel_requirement["part_ids"] == [kicker["part_id"]]
    assert panel_requirement["source_labels"] == ["Quote-level"]
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


def test_production_handoff_keeps_split_drawer_rows_distinct():
    result = build_production_handoff(
        quote=quote(),
        project=project(),
        units=[unit(1, "Base Draw", carcass_board_type_id="board-white", door_board_type_id="board-oak")],
        cutting_list={
            "runtime_rows": [
                {"unit_number": 1, "section": "carcass", "desc": "Drawer Front/Back", "length": 548, "width": 94, "qty": 4},
                {"unit_number": 1, "section": "carcass", "desc": "Drawer Front/Back", "length": 548, "width": 283, "qty": 2},
                {"unit_number": 1, "section": "panel", "desc": "Drawer Front", "length": 194, "width": 597, "qty": 2},
                {"unit_number": 1, "section": "panel", "desc": "Drawer Front", "length": 383, "width": 597, "qty": 1},
            ],
            "validation_warnings": [],
        },
        material_summary={"groups": [], "warnings": [], "total_area_m2": 0, "total_piece_count": 0, "total_edge_m": 0},
        hardware_pick_list={"items": [], "warnings": [], "total_item_count": 0, "total_quantity": 0},
        board_lookup=board_lookup(),
    )

    assert [(row["section"], row["desc"], row["length"], row["width"], row["quantity"]) for row in result["rows"]] == [
        ("carcass", "Drawer Front/Back", 548, 94, 4),
        ("carcass", "Drawer Front/Back", 548, 283, 2),
        ("panel", "Drawer Front", 194, 597, 2),
        ("panel", "Drawer Front", 383, 597, 1),
    ]
    assert {row["board_name"] for row in result["rows"] if row["section"] == "panel"} == {"Seno Oak (18mm)"}
    assert result["label_count"] == 4


def test_production_handoff_board_requirements_surface_material_data_warnings():
    result = build_production_handoff(
        quote={
            **quote(),
            "default_carcass_board_type_id": None,
            "default_door_board_type_id": "board-missing",
            "default_panel_board_type_id": "board-no-dimensions",
        },
        project=project(),
        units=[unit(1, "Base Door", carcass_board_type_id=None, door_board_type_id="board-missing")],
        cutting_list={
            "runtime_rows": [
                {"unit_number": 1, "section": "carcass", "desc": "Side", "length": 0, "width": 564, "qty": 2},
                {"unit_number": 1, "section": "panel", "desc": "Door", "length": 720, "width": 297, "qty": 2},
                {
                    "unit_number": 0,
                    "section": "extra_panel",
                    "desc": "Filler",
                    "length": 2200,
                    "width": 80,
                    "qty": 1,
                    "board_type_id": "board-no-dimensions",
                },
            ],
            "validation_warnings": [
                {
                    "severity": "warning",
                    "source": "unit",
                    "unit_number": 1,
                    "section": "carcass",
                    "row_desc": "Side",
                    "reason": "Length must be greater than 0 mm.",
                },
                {
                    "severity": "warning",
                    "source": "unit",
                    "unit_number": 1,
                    "section": "carcass",
                    "row_desc": "Side",
                    "reason": "Choose a carcass board for this unit or quote default.",
                },
                {
                    "severity": "warning",
                    "source": "unit",
                    "unit_number": 1,
                    "section": "panel",
                    "row_desc": "Door",
                    "reason": "Selected board is not available in the company board library.",
                },
            ],
        },
        material_summary={"groups": [], "warnings": [], "total_area_m2": 0, "total_piece_count": 0, "total_edge_m": 0},
        hardware_pick_list={"items": [], "warnings": [], "total_item_count": 0, "total_quantity": 0},
        board_lookup={
            **board_lookup(),
            "board-no-dimensions": {
                "id": "board-no-dimensions",
                "brand": "PG",
                "material": "",
                "thickness": 0,
                "length_mm": 0,
                "width_mm": 0,
            },
        },
    )

    warning_codes = {warning["code"] for warning in result["board_requirements"]["warnings"]}
    assert {
        "invalid_part_dimensions",
        "missing_board_selection",
        "missing_board_record",
        "missing_board_dimensions",
        "incomplete_material_data",
    }.issubset(warning_codes)

    unassigned = next(group for group in result["board_requirements"]["groups"] if group["board_type_id"] is None)
    assert unassigned["sheet_estimate_label"] == "Needs board selection before sheets can be estimated."
    missing_record = next(group for group in result["board_requirements"]["groups"] if group["board_type_id"] == "board-missing")
    assert missing_record["sheet_estimate_label"] == "Needs a visible board record before sheets can be estimated."
    missing_dimensions = next(group for group in result["board_requirements"]["groups"] if group["board_type_id"] == "board-no-dimensions")
    assert missing_dimensions["sheet_estimate_label"] == "Needs sheet length and width before sheets can be estimated."
    assert result["board_requirements"]["warning_count"] >= 5


def test_production_handoff_shows_edge_grain_metadata_and_workshop_warnings():
    result = build_production_handoff(
        quote={
            **quote(),
            "production_metadata": {
                "door_panel": {
                    "edge_banding": "1mm oak ABS on all exposed door edges",
                    "grain_direction": "length",
                    "rotation": "no_rotation",
                    "notes": "Bookmatch adjacent doors.",
                },
                "visible_panel": {
                    "edge_banding": "",
                    "grain_direction": "none",
                    "rotation": "none",
                    "notes": "",
                },
            },
        },
        project=project(),
        units=[
            {
                **unit(1, "Base Door", carcass_board_type_id="board-white", door_board_type_id="board-oak"),
                "production_metadata": {
                    "door_panel": {
                        "edge_banding": "2mm front edge, 1mm remaining edges",
                        "grain_direction": "width",
                        "rotation": "no_rotation",
                        "notes": "Keep front edge labelled.",
                    }
                },
            }
        ],
        cutting_list={
            "runtime_rows": [
                {
                    "unit_number": 1,
                    "section": "panel",
                    "desc": "Door",
                    "length": 720,
                    "width": 297,
                    "qty": 2,
                    "edge_long_1": True,
                    "edge_long_2": True,
                    "edge_short_1": False,
                    "edge_short_2": False,
                    "grain_direction": "length",
                    "can_rotate": False,
                },
                {
                    "unit_number": 0,
                    "section": "extra_panel",
                    "desc": "Feature End",
                    "length": 2300,
                    "width": 300,
                    "qty": 1,
                    "board_type_id": "board-black",
                    "production_metadata": {
                        "edge_banding": "",
                        "grain_direction": "none",
                        "rotation": "none",
                        "notes": "",
                    },
                },
            ],
            "validation_warnings": [],
        },
        material_summary={"groups": [], "warnings": [], "total_area_m2": 0, "total_piece_count": 0, "total_edge_m": 0},
        hardware_pick_list={"items": [], "warnings": [], "total_item_count": 0, "total_quantity": 0},
        board_lookup=board_lookup(),
    )

    door = next(row for row in result["rows"] if row["desc"] == "Door")
    assert door["edge_sides"] == ["L1", "L2"]
    assert door["edge_banding"] == "2mm front edge, 1mm remaining edges"
    assert door["grain_direction"] == "width"
    assert door["rotation"] == "no_rotation"
    assert door["production_notes"] == "Keep front edge labelled."
    assert door["warning_count"] == 0

    feature_end = next(row for row in result["rows"] if row["desc"] == "Feature End")
    assert feature_end["warning_count"] == 2
    assert "Add edge-banding instruction for Quote-level / Feature End." in feature_end["warning_messages"]
    assert "Add grain direction for Quote-level / Feature End." in feature_end["warning_messages"]
    assert result["warning_count"] == 2


def test_production_handoff_suppresses_grain_for_non_grained_board_types():
    lookup = board_lookup()
    lookup["board-black"] = {**lookup["board-black"], "grain_policy": "none"}
    result = build_production_handoff(
        quote={
            **quote(),
            "production_metadata": {
                "visible_panel": {
                    "edge_banding": "",
                    "grain_direction": "length",
                    "rotation": "none",
                    "notes": "",
                },
            },
        },
        project=project(),
        units=[],
        cutting_list={
            "runtime_rows": [
                {
                    "unit_number": 0,
                    "section": "extra_panel",
                    "desc": "MDF Utility Panel",
                    "length": 2300,
                    "width": 300,
                    "qty": 1,
                    "board_type_id": "board-black",
                    "production_metadata": {
                        "edge_banding": "",
                        "grain_direction": "width",
                        "rotation": "none",
                        "notes": "",
                    },
                },
            ],
            "validation_warnings": [],
        },
        material_summary={"groups": [], "warnings": [], "total_area_m2": 0, "total_piece_count": 0, "total_edge_m": 0},
        hardware_pick_list={"items": [], "warnings": [], "total_item_count": 0, "total_quantity": 0},
        board_lookup=lookup,
    )

    panel = result["rows"][0]
    assert panel["grain_policy"] == "none"
    assert panel["grain_direction"] == "none"
    assert panel["grain_label"] == "Not applicable"
    assert panel["warning_count"] == 1
    assert "Add edge-banding instruction for Quote-level / MDF Utility Panel." in panel["warning_messages"]
    assert all("grain direction" not in message.lower() for message in panel["warning_messages"])


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
        "production_metadata": {
            "door_panel": {
                "edge_banding": "1mm ABS on door edges",
                "grain_direction": "length",
                "rotation": "no_rotation",
                "notes": "",
            },
            "visible_panel": {
                "edge_banding": "1mm ABS on exposed quote-panel edges",
                "grain_direction": "length",
                "rotation": "no_rotation",
                "notes": "",
            },
        },
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
            "grain_policy": "required",
        },
        "board-oak": {
            "id": "board-oak",
            "brand": "Seno",
            "material": "Oak",
            "thickness": 18,
            "length_mm": 2800,
            "width_mm": 1220,
            "grain_policy": "required",
        },
        "board-black": {
            "id": "board-black",
            "brand": "PG",
            "material": "Black",
            "thickness": 16,
            "length_mm": 2750,
            "width_mm": 1830,
            "grain_policy": "required",
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
