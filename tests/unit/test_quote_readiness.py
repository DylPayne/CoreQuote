from __future__ import annotations

from corequote_core.quote_readiness import evaluate_quote_readiness


def test_readiness_warns_when_quote_has_no_units():
    readiness = evaluate_quote_readiness(
        quote=quote(),
        project=project(),
        units=[],
        cutting_list=cutting_list(rows=[]),
        pricing_summary=pricing_summary(grand_total_cents=0, lines=[]),
        active_price_list_id="price-list-1",
    )

    check = check_by_id(readiness, "unit_count")

    assert readiness["is_ready"] is False
    assert "checks need attention" in readiness["summary_message"]
    assert check["severity"] == "warning"
    assert "no cabinets" in check["message"]
    assert check["action_target"] == "units"


def test_readiness_warns_for_missing_boards():
    readiness = evaluate_quote_readiness(
        quote=quote(default_carcass_board_type_id=None, default_door_board_type_id="board-front"),
        project=project(),
        units=[unit(carcass_board_type_id=None, door_board_type_id="board-front")],
        cutting_list=cutting_list(rows=[]),
        pricing_summary=pricing_summary(grand_total_cents=0),
        active_price_list_id="price-list-1",
        cutting_error="Unit carcass board is required to determine thickness",
    )

    default_check = check_by_id(readiness, "default_boards")
    unit_check = check_by_id(readiness, "unit_boards")

    assert default_check["severity"] == "warning"
    assert "default carcass board" in default_check["message"]
    assert unit_check["severity"] == "warning"
    assert "carcass board" in unit_check["message"]


def test_readiness_warns_for_missing_prices():
    readiness = evaluate_quote_readiness(
        quote=quote(),
        project=project(),
        units=[unit()],
        cutting_list=cutting_list(),
        pricing_summary=pricing_summary(
            missing_prices=[
                {
                    "item_type": "board",
                    "item_name": "PG White (16mm)",
                    "price_component": "sheet",
                }
            ]
        ),
        active_price_list_id="price-list-1",
    )

    check = check_by_id(readiness, "missing_prices")

    assert check["severity"] == "warning"
    assert check["title"] == "Add missing prices"
    assert "1 required price missing" in check["message"]
    assert check["action_target"] == "pricing"


def test_readiness_counts_legacy_missing_items_when_structured_rows_are_empty():
    readiness = evaluate_quote_readiness(
        quote=quote(),
        project=project(),
        units=[unit()],
        cutting_list=cutting_list(),
        pricing_summary=pricing_summary(missing_items=["board::board-carcass::sheet"], missing_prices=[]),
        active_price_list_id="price-list-1",
    )

    check = check_by_id(readiness, "missing_prices")

    assert check["severity"] == "warning"
    assert "1 required price missing" in check["message"]


def test_readiness_warns_for_invalid_cutlist_rows():
    readiness = evaluate_quote_readiness(
        quote=quote(),
        project=project(),
        units=[unit()],
        cutting_list=cutting_list(rows=[runtime_row(length=0)]),
        pricing_summary=pricing_summary(),
        active_price_list_id="price-list-1",
    )

    check = check_by_id(readiness, "cutlist_rows")

    assert check["severity"] == "warning"
    assert check["title"] == "Fix cutlist rows"
    assert "unusable sizes" in check["message"]
    assert check["action_target"] == "cutting-lists"


def test_readiness_warns_for_missing_hardware_pick_list_choices():
    readiness = evaluate_quote_readiness(
        quote=quote(),
        project=project(),
        units=[unit()],
        cutting_list=cutting_list(),
        pricing_summary=pricing_summary(),
        active_price_list_id="price-list-1",
        hardware_pick_list={
            "items": [],
            "warnings": [
                {
                    "severity": "warning",
                    "code": "missing_slide_selection",
                    "item_type": "slide",
                    "unit_number": 1,
                    "item_ref_id": None,
                    "message": "Choose a drawer slide for Unit 1 drawers.",
                }
            ],
            "total_item_count": 0,
            "total_quantity": 0,
        },
    )

    hardware_check = check_by_id(readiness, "hardware_pick_list")
    outputs_check = check_by_id(readiness, "required_outputs")

    assert readiness["is_ready"] is False
    assert hardware_check["severity"] == "warning"
    assert hardware_check["title"] == "Choose hardware for the quote"
    assert "1 component choice needs attention" in hardware_check["message"]
    assert hardware_check["action_target"] == "quote"
    assert outputs_check["severity"] == "warning"


def test_readiness_uses_structured_cutlist_validation_warnings():
    readiness = evaluate_quote_readiness(
        quote=quote(),
        project=project(),
        units=[unit()],
        cutting_list=cutting_list(
            validation_warnings=[
                {
                    "severity": "warning",
                    "source": "unit",
                    "unit_number": 1,
                    "section": "carcass",
                    "row_desc": "Side",
                    "reason": "Choose a carcass board for this unit or quote default.",
                }
            ]
        ),
        pricing_summary=pricing_summary(),
        active_price_list_id="price-list-1",
    )

    cutlist_check = check_by_id(readiness, "cutlist_rows")
    outputs_check = check_by_id(readiness, "required_outputs")

    assert readiness["is_ready"] is False
    assert cutlist_check["severity"] == "warning"
    assert "missing material choices" in cutlist_check["message"]
    assert outputs_check["severity"] == "warning"


def test_readiness_is_ready_when_required_checks_pass():
    readiness = evaluate_quote_readiness(
        quote=quote(),
        project=project(),
        units=[unit()],
        cutting_list=cutting_list(),
        pricing_summary=pricing_summary(),
        active_price_list_id="price-list-1",
    )

    assert readiness["status"] == "ready"
    assert readiness["is_ready"] is True
    assert readiness["summary_title"] == "Ready for review"
    assert readiness["warning_count"] == 0
    assert readiness["error_count"] == 0
    assert {check["severity"] for check in readiness["checks"]} == {"pass"}


def check_by_id(readiness: dict, check_id: str) -> dict:
    return next(check for check in readiness["checks"] if check["id"] == check_id)


def project(**overrides) -> dict:
    payload = {
        "id": "project-1",
        "name": "Main Kitchen",
        "client": "John Smith",
        "address": "12 Oak Street",
    }
    payload.update(overrides)
    return payload


def quote(**overrides) -> dict:
    payload = {
        "id": "quote-1",
        "name": "Kitchen Quote",
        "default_carcass_board_type_id": "board-carcass",
        "default_door_board_type_id": "board-front",
        "default_panel_board_type_id": "board-panel",
    }
    payload.update(overrides)
    return payload


def unit(**overrides) -> dict:
    payload = {
        "unit_number": 1,
        "unit_type_key": "Base Draw",
        "carcass_board_type_id": "board-carcass",
        "door_board_type_id": "board-front",
    }
    payload.update(overrides)
    return payload


def cutting_list(rows: list[dict] | None = None, validation_warnings: list[dict] | None = None) -> dict:
    return {
        "carcass": [],
        "panels": [],
        "hardware": [],
        "extras": [],
        "runtime_rows": rows
        if rows is not None
        else [
            runtime_row(section="carcass"),
            runtime_row(section="panel", desc="Drawer Front", length=777, width=297),
        ],
        "runtime_mode": "legacy",
        "unit_sources": [],
        "validation_warnings": validation_warnings or [],
    }


def runtime_row(**overrides) -> dict:
    payload = {
        "unit_number": 1,
        "desc": "Side",
        "length": 748,
        "width": 564,
        "qty": 2,
        "section": "carcass",
        "board_type_id": "board-carcass",
    }
    payload.update(overrides)
    return payload


def pricing_summary(**overrides) -> dict:
    payload = {
        "quote_id": "quote-1",
        "quote_name": "Kitchen Quote",
        "is_complete": True,
        "missing_items": [],
        "missing_prices": [],
        "grand_total_cents": 498000,
        "lines": [{"description": "Carcass board", "missing": False}],
    }
    payload.update(overrides)
    return payload
