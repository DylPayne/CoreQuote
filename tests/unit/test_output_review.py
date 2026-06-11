from corequote_core.output_review import build_quote_output_review


def test_output_review_enables_actions_for_complete_quote():
    review = build_quote_output_review(
        quote=quote(unit_count=2),
        project={"id": "project-1", "name": "Main Kitchen"},
        currency_code="USD",
        readiness=readiness(is_ready=True),
        cutting_list=cutting_list(),
        pricing_summary=pricing_summary(),
        active_price_list_id="price-list-1",
    )

    actions = {action["id"]: action for action in review["actions"]}
    assert review["client_quote"]["status"] == "ready"
    assert review["internal_pricing"]["status"] == "ready"
    assert actions["client_quote_pdf"]["enabled"] is True
    assert actions["client_quote_pdf"]["hides_internal_costs"] is True
    assert actions["workshop_schedule"]["enabled"] is True
    assert actions["material_summary"]["enabled"] is True
    assert actions["hardware_pick_list"]["enabled"] is True


def test_output_review_disables_actions_and_warns_for_incomplete_quote():
    review = build_quote_output_review(
        quote=quote(unit_count=1),
        project={"id": "project-1", "name": "Main Kitchen"},
        currency_code="USD",
        readiness=readiness(is_ready=False, warning_count=2),
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
        pricing_summary=pricing_summary(
            is_complete=False,
            missing_prices=[{"item_key": "board::board-1"}],
            material_summary={
                **material_summary(),
                "warnings": [{"message": "Add sheet dimensions."}],
            },
            hardware_pick_list={
                **hardware_pick_list(),
                "warnings": [{"message": "Choose a drawer handle."}],
            },
        ),
        active_price_list_id="price-list-1",
    )

    actions = {action["id"]: action for action in review["actions"]}
    assert review["client_quote"]["status"] == "needs_attention"
    assert review["internal_pricing"]["status"] == "needs_attention"
    assert actions["client_quote_pdf"]["enabled"] is False
    assert actions["client_quote_pdf"]["warning"] == "Resolve readiness warnings before generating the client quote."
    assert actions["workshop_schedule"]["enabled"] is True
    assert actions["workshop_schedule"]["warning"] == "Cutting-list warnings will be included in the workshop schedule."
    assert actions["material_summary"]["enabled"] is False
    assert actions["material_summary"]["warning"] == "Resolve material summary warnings before generating the material summary."
    assert actions["hardware_pick_list"]["enabled"] is False
    assert actions["hardware_pick_list"]["warning"] == "Choose missing hardware before generating the hardware pick list."


def test_output_review_blocks_workshop_export_when_no_rows_exist():
    review = build_quote_output_review(
        quote=quote(unit_count=0),
        project={"id": "project-1", "name": "Main Kitchen"},
        currency_code="USD",
        readiness=readiness(is_ready=False, warning_count=1),
        cutting_list=cutting_list(carcass=[], panels=[]),
        pricing_summary=pricing_summary(),
        active_price_list_id="price-list-1",
    )

    action = next(action for action in review["actions"] if action["id"] == "workshop_schedule")
    assert review["workshop_schedule"]["status"] == "needs_attention"
    assert action["enabled"] is False
    assert action["warning"] == "Add cabinet units before generating the workshop schedule."


def quote(*, unit_count: int) -> dict:
    return {
        "id": "quote-1",
        "project_id": "project-1",
        "name": "Kitchen Quote",
        "status": "draft",
        "quote_number": "Q-001",
        "revision": 1,
        "unit_count": unit_count,
    }


def readiness(*, is_ready: bool, warning_count: int = 0) -> dict:
    return {
        "quote_id": "quote-1",
        "status": "ready" if is_ready else "needs_attention",
        "is_ready": is_ready,
        "summary_title": "Ready for review" if is_ready else "Needs attention before review",
        "summary_message": "Ready." if is_ready else "Warnings need attention.",
        "warning_count": warning_count,
        "error_count": 0,
        "checks": [],
    }


def cutting_list(
    *,
    carcass: list[dict] | None = None,
    panels: list[dict] | None = None,
    validation_warnings: list[dict] | None = None,
) -> dict:
    warnings = validation_warnings or []
    return {
        "carcass": [{"unit_number": 1, "desc": "Side", "length": 748, "width": 564, "qty": 2}] if carcass is None else carcass,
        "panels": [{"unit_number": 1, "desc": "Door", "length": 777, "width": 297, "qty": 2}] if panels is None else panels,
        "hardware": [],
        "extras": [],
        "validation_warnings": warnings,
        "readiness": {"cutlist_valid": not warnings, "warning_count": len(warnings)},
    }


def pricing_summary(
    *,
    is_complete: bool = True,
    missing_prices: list[dict] | None = None,
    material_summary: dict | None = None,
    hardware_pick_list: dict | None = None,
) -> dict:
    return {
        "is_complete": is_complete,
        "missing_prices": missing_prices or [],
        "cutlist_warnings": [],
        "grand_total_cents": 498000,
        "material_summary": material_summary or material_summary_default(),
        "hardware_pick_list": hardware_pick_list or hardware_pick_list_default(),
    }


def material_summary_default() -> dict:
    return material_summary()


def material_summary() -> dict:
    return {
        "groups": [{"board_type_id": "board-1", "material_role": "carcass", "board_name": "PG White"}],
        "warnings": [],
        "total_area_m2": 1.42,
        "total_piece_count": 4,
        "total_edge_m": 3.0,
        "total_estimated_sheets": 1,
    }


def hardware_pick_list_default() -> dict:
    return hardware_pick_list()


def hardware_pick_list() -> dict:
    return {
        "items": [{"item_type": "slide", "item_key": "slide::slide-1", "quantity": 3}],
        "warnings": [],
        "total_item_count": 1,
        "total_quantity": 3,
    }
