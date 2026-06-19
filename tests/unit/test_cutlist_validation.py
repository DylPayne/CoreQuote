from corequote_api.cutlist_validation import preview_with_validation


def test_cutlist_validation_keeps_valid_rows_ready():
    result = preview_with_validation(
        {
            "carcass": [{"unit_number": 1, "desc": "Side", "length": 748, "width": 544, "qty": 2}],
            "panels": [],
            "hardware": [],
            "extras": [],
            "runtime_rows": [
                {
                    "unit_number": 1,
                    "section": "carcass",
                    "desc": "Side",
                    "length": 748,
                    "width": 544,
                    "qty": 2,
                }
            ],
            "runtime_mode": "ruleset",
            "unit_sources": [],
        },
        quote={"default_carcass_board_type_id": "board-1"},
        units=[{"unit_number": 1, "carcass_board_type_id": None}],
        board_lookup={"board-1": {"id": "board-1"}},
        require_materials=True,
    )

    assert result["validation_warnings"] == []
    assert result["readiness"] == {"cutlist_valid": True, "warning_count": 0}


def test_cutlist_validation_flags_zero_and_negative_row_values():
    result = preview_with_validation(
        {
            "carcass": [],
            "panels": [],
            "hardware": [],
            "extras": [],
            "runtime_rows": [
                {
                    "unit_number": 2,
                    "section": "carcass",
                    "desc": "Rail",
                    "length": 0,
                    "width": -20,
                    "qty": 0,
                }
            ],
            "runtime_mode": "ruleset",
            "unit_sources": [],
        }
    )

    assert result["validation_warnings"] == [
        {
            "severity": "warning",
            "source": "unit",
            "unit_number": 2,
            "section": "carcass",
            "row_desc": "Rail",
            "reason": "Length must be greater than 0 mm.",
        },
        {
            "severity": "warning",
            "source": "unit",
            "unit_number": 2,
            "section": "carcass",
            "row_desc": "Rail",
            "reason": "Width must be greater than 0 mm.",
        },
        {
            "severity": "warning",
            "source": "unit",
            "unit_number": 2,
            "section": "carcass",
            "row_desc": "Rail",
            "reason": "Quantity must be greater than 0.",
        },
    ]
    assert result["readiness"] == {"cutlist_valid": False, "warning_count": 3}


def test_cutlist_validation_flags_missing_unit_and_quote_panel_boards():
    result = preview_with_validation(
        {
            "carcass": [],
            "panels": [],
            "hardware": [],
            "extras": [],
            "runtime_rows": [
                {
                    "unit_number": 1,
                    "section": "carcass",
                    "desc": "Side",
                    "length": 748,
                    "width": 544,
                    "qty": 2,
                },
                {
                    "unit_number": 0,
                    "section": "extra_panel",
                    "desc": "Kicker",
                    "length": 1760,
                    "width": 100,
                    "qty": 1,
                    "board_type_id": None,
                },
            ],
            "runtime_mode": "legacy",
            "unit_sources": [],
        },
        quote={},
        units=[{"unit_number": 1, "carcass_board_type_id": None}],
        board_lookup={},
        require_materials=True,
    )

    assert result["validation_warnings"] == [
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
            "source": "quote_panel",
            "unit_number": 0,
            "section": "extra_panel",
            "row_desc": "Kicker",
            "reason": "Choose a board for this quote-level panel.",
        },
    ]


def test_cutlist_validation_flags_incompatible_metal_drawer_system():
    result = preview_with_validation(
        {
            "carcass": [],
            "panels": [],
            "hardware": [],
            "extras": [],
            "runtime_rows": [],
            "runtime_mode": "drawer_system",
            "unit_sources": [],
        },
        quote={"default_slide_id": "slide-metal"},
        units=[
            {
                "unit_number": 7,
                "unit_type_key": "Base Draw",
                "height": 780,
                "width": 900,
                "depth": 480,
                "thickness": 18,
                "extra_params": {
                    "num_drawers": 3,
                    "drawer_face_heights": [100, 180, 240],
                },
            }
        ],
        slide_lookup={
            "slide-metal": {
                "id": "slide-metal",
                "brand": "Grass",
                "model": "Nova Pro Scala",
                "length": 500,
                "drawer_system_kind": "metal",
                "drawer_system_config": {
                    "product_family": "Nova Pro Scala",
                    "min_depth_mm": 520,
                    "compatible_side_thicknesses": [16, 19],
                    "compatible_nominal_lengths": [450],
                    "max_internal_width_mm": 700,
                    "min_front_height_mm": 120,
                    "max_front_height_mm": 220,
                },
            }
        },
    )

    reasons = [warning["reason"] for warning in result["validation_warnings"]]
    assert any("requires a carcass depth of at least 520 mm" in reason for reason in reasons)
    assert any("compatible with side-wall thicknesses 16 mm, 19 mm" in reason for reason in reasons)
    assert any("supports nominal lengths 450 mm" in reason for reason in reasons)
    assert any("supports internal widths up to 700 mm" in reason for reason in reasons)
    assert any("requires drawer fronts of at least 120 mm" in reason for reason in reasons)
    assert any("supports drawer fronts up to 220 mm" in reason for reason in reasons)
    assert result["readiness"] == {"cutlist_valid": False, "warning_count": 6}
