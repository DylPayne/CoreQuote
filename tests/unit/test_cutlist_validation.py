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
