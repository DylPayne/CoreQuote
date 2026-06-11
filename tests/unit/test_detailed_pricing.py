import pytest

from corequote_core.detailed_pricing import DetailedPricingSettings, price_quote_detailed


def test_detailed_pricing_applies_bucket_markups_commission_and_vat():
    quote = {
        "id": "quote-1",
        "name": "Kitchen",
        "default_carcass_board_type_id": "board-1",
        "default_slide_id": "slide-1",
        "default_drawer_handle_id": "handle-1",
    }
    units = [
        {
            "unit_number": 1,
            "unit_type_key": "Base Draw",
            "height": 780,
            "extra_params": {"num_drawers": 2, "handle_qty": 2},
        }
    ]
    cutting_rows = [
        {
            "section": "carcass",
            "unit_number": 1,
            "length": 1000,
            "width": 1000,
            "qty": 1,
        }
    ]
    settings = DetailedPricingSettings(
        vat_rate_bps=1500,
        carcass_markup_bps=10000,
        component_markup_bps=10000,
        handle_markup_bps=0,
        joinery_commission_bps=1000,
        labour_cents_per_m2=1000,
        consumables_cents_per_m2=500,
        fabrication_markup_bps=0,
        install_day_cost_cents=10000,
        delivery_base_cents=20000,
        install_markup_bps=0,
        delivery_markup_bps=0,
        minimum_install_days_bps=5000,
        minimum_delivery_trips_bps=5000,
    )

    result = price_quote_detailed(
        quote=quote,
        units=units,
        quote_extras=[],
        cutting_rows=cutting_rows,
        settings=settings,
        price_lookup={
            ("board", "board::board-1", "sqm"): {"unit_price_cents": 10000},
            ("slide", "slide::slide-1", "unit"): {"unit_price_cents": 1000},
            ("handle", "handle::handle-1", "unit"): {"unit_price_cents": 500},
        },
        board_lookup={
            "board-1": {
                "id": "board-1",
                "brand": "PG",
                "material": "White",
                "thickness": 16,
                "length_mm": 2750,
                "width_mm": 1830,
                "costing_mode": "sqm",
            }
        },
        slide_lookup={"slide-1": {"brand": "Grass", "model": "Dynapro", "code": "500"}},
        hinge_lookup={},
        handle_lookup={"handle-1": {"name": "Bar", "supplier": "Core"}},
        extra_lookup={},
        active_price_list_id="price-list-1",
    )

    assert result["is_complete"] is True
    assert result["missing_items"] == []
    assert result["cost_total_cents"] == 29500
    assert result["sell_before_vat_cents"] == 44700
    assert result["vat_cents"] == 6705
    assert result["grand_total_cents"] == 51405
    assert result["profit_cents"] == 15200

    commission = [line for line in result["lines"] if line["bucket"] == "commission"]
    assert len(commission) == 1
    assert commission[0]["sell_total_cents"] == 2700


def test_detailed_pricing_reports_missing_price_items():
    result = price_quote_detailed(
        quote={
            "id": "quote-1",
            "name": "Kitchen",
            "default_carcass_board_type_id": "board-1",
        },
        units=[{"unit_number": 1, "unit_type_key": "Base Door", "height": 780, "extra_params": {"num_doors": 0}}],
        quote_extras=[],
        cutting_rows=[
            {
                "section": "carcass",
                "unit_number": 1,
                "length": 1000,
                "width": 1000,
                "qty": 1,
            }
        ],
        settings=DetailedPricingSettings(),
        price_lookup={},
        board_lookup={
            "board-1": {
                "id": "board-1",
                "brand": "PG",
                "material": "White",
                "thickness": 16,
                "length_mm": 2750,
                "width_mm": 1830,
                "costing_mode": "sqm",
            }
        },
        slide_lookup={},
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={},
        active_price_list_id="price-list-1",
    )

    assert result["is_complete"] is False
    assert result["missing_items"] == ["board::board-1::sqm"]
    assert result["missing_prices"] == [
        {
            "item_type": "board",
            "item_type_label": "Board",
            "item_key": "board::board-1",
            "item_ref_id": "board-1",
            "price_component": "sqm",
            "component": "Square metre price",
            "bucket": "material",
            "item_name": "PG White (16mm)",
            "uom": "m2",
            "quantity": 1.0,
            "used_in": ["Carcass material"],
            "usage_label": "Carcass material",
            "affected_quote_id": "quote-1",
            "affected_quote_name": "Kitchen",
            "library_area": "pricing",
            "action_label": "Add a price for PG White (16mm)",
            "message": "Add a price for PG White (16mm) using Square metre price in the pricing library.",
        }
    ]
    assert any(line["missing"] for line in result["lines"])


def test_detailed_pricing_reports_grouped_missing_hardware_price():
    result = price_quote_detailed(
        quote={
            "id": "quote-1",
            "name": "Kitchen",
            "default_carcass_board_type_id": "board-1",
            "default_slide_id": "slide-1",
            "default_drawer_handle_id": "handle-1",
        },
        units=[
            {"unit_number": 1, "unit_type_key": "Base Draw", "height": 780, "extra_params": {"num_drawers": 3, "handle_qty": 3}},
            {"unit_number": 2, "unit_type_key": "Base Draw", "height": 780, "extra_params": {"num_drawers": 2, "handle_qty": 2}},
        ],
        quote_extras=[],
        cutting_rows=[
            {"section": "carcass", "unit_number": 1, "length": 1000, "width": 1000, "qty": 1},
            {"section": "carcass", "unit_number": 2, "length": 1000, "width": 1000, "qty": 1},
        ],
        settings=DetailedPricingSettings(),
        price_lookup={
            ("board", "board::board-1", "sqm"): {"unit_price_cents": 10000},
            ("slide", "slide::slide-1", "unit"): {"unit_price_cents": 1000},
        },
        board_lookup={
            "board-1": {
                "id": "board-1",
                "brand": "PG",
                "material": "White",
                "thickness": 16,
                "length_mm": 2750,
                "width_mm": 1830,
                "costing_mode": "sqm",
            }
        },
        slide_lookup={"slide-1": {"brand": "Grass", "model": "Dynapro", "code": "500"}},
        hinge_lookup={},
        handle_lookup={"handle-1": {"name": "Bar", "supplier": "Core"}},
        extra_lookup={},
        active_price_list_id="price-list-1",
    )

    assert result["is_complete"] is False
    assert result["missing_items"] == ["handle::handle-1::unit"]
    assert result["missing_prices"][0]["item_type"] == "handle"
    assert result["missing_prices"][0]["item_name"] == "Bar · Core"
    assert result["missing_prices"][0]["component"] == "Unit price"
    assert result["missing_prices"][0]["uom"] == "pcs"
    assert result["missing_prices"][0]["quantity"] == 5.0
    assert result["missing_prices"][0]["used_in"] == ["Handle"]
    assert result["missing_prices"][0]["action_label"] == "Add a price for Bar · Core"


def test_detailed_pricing_includes_hardware_pick_list_without_prices():
    result = price_quote_detailed(
        quote={
            "id": "quote-1",
            "name": "Kitchen",
            "default_slide_id": "slide-1",
            "default_hinge_id": "hinge-1",
            "default_base_handle_id": "handle-base",
            "default_drawer_handle_id": "handle-drawer",
        },
        units=[
            {"unit_number": 1, "unit_type_key": "Base Draw", "height": 780, "extra_params": {"num_drawers": 3}},
            {"unit_number": 2, "unit_type_key": "Base Door", "height": 780, "extra_params": {"num_doors": 2}},
        ],
        quote_extras=[{"extra_id": "extra-1", "quantity": 2}],
        cutting_rows=[],
        settings=DetailedPricingSettings(),
        price_lookup={},
        board_lookup={},
        slide_lookup={"slide-1": {"brand": "Grass", "model": "Dynapro", "code": "500"}},
        hinge_lookup={"hinge-1": {"brand": "Blum", "model": "Clip top", "code": "110"}},
        handle_lookup={
            "handle-base": {"name": "Base pull", "supplier": "Core", "code": "B128"},
            "handle-drawer": {"name": "Drawer pull", "supplier": "Core", "code": "D192"},
        },
        extra_lookup={"extra-1": {"name": "Waste removal", "supplier": "Core", "code": "WR1"}},
        active_price_list_id=None,
    )

    pick_list = result["hardware_pick_list"]
    items = {item["item_key"]: item for item in pick_list["items"]}

    assert result["is_complete"] is False
    assert pick_list["warnings"] == []
    assert items["slide::slide-1"]["quantity"] == 3
    assert items["hinge::hinge-1"]["quantity"] == 4
    assert items["handle::handle-drawer"]["quantity"] == 3
    assert items["handle::handle-base"]["quantity"] == 2
    assert items["extra::extra-1"]["quantity"] == 2
    assert "cost_total_cents" not in items["slide::slide-1"]
    assert "sell_total_cents" not in items["extra::extra-1"]


def test_detailed_pricing_material_summary_groups_board_roles_and_sheet_estimates():
    result = price_quote_detailed(
        quote={
            "id": "quote-1",
            "name": "Kitchen",
            "default_carcass_board_type_id": "white-board",
            "default_door_board_type_id": "oak-board",
            "default_panel_board_type_id": "oak-board",
        },
        units=[
            {
                "unit_number": 1,
                "unit_type_key": "Base Door",
                "height": 780,
                "carcass_board_type_id": None,
                "door_board_type_id": None,
                "extra_params": {"num_doors": 0},
            }
        ],
        quote_extras=[],
        cutting_rows=[
            {"section": "carcass", "unit_number": 1, "desc": "Side", "length": 1000, "width": 500, "qty": 2},
            {"section": "panel", "unit_number": 1, "desc": "Door", "length": 700, "width": 300, "qty": 2},
            {"section": "extra_panel", "unit_number": 0, "desc": "Feature end", "length": 2000, "width": 600, "qty": 1},
        ],
        settings=DetailedPricingSettings(carcass_markup_bps=1000, door_panel_markup_bps=2000),
        price_lookup={
            ("board", "board::white-board", "sheet"): {"unit_price_cents": 50000},
            ("board", "board::oak-board", "sheet"): {"unit_price_cents": 120000},
        },
        board_lookup={
            "white-board": {
                "id": "white-board",
                "brand": "PG",
                "material": "White melamine",
                "thickness": 16,
                "length_mm": 2440,
                "width_mm": 1220,
                "costing_mode": "sheet",
            },
            "oak-board": {
                "id": "oak-board",
                "brand": "Egger",
                "material": "Oak look",
                "thickness": 18,
                "length_mm": 2800,
                "width_mm": 2070,
                "costing_mode": "sheet",
            },
        },
        slide_lookup={},
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={},
        active_price_list_id="price-list-1",
    )

    summary = result["material_summary"]
    assert summary["total_area_m2"] == pytest.approx(2.62)
    assert summary["total_estimated_sheets"] == 3
    assert summary["warnings"] == []

    groups = {(row["board_type_id"], row["material_role"]): row for row in summary["groups"]}
    assert set(groups) == {
        ("white-board", "carcass"),
        ("oak-board", "door_panel"),
        ("oak-board", "visible_panel"),
    }

    carcass = groups[("white-board", "carcass")]
    assert carcass["role_label"] == "Carcass material"
    assert carcass["board_name"] == "PG White melamine (16mm)"
    assert carcass["thickness"] == 16
    assert carcass["piece_count"] == 2
    assert carcass["area_m2"] == pytest.approx(1.0)
    assert carcass["estimated_sheets"] == 1
    assert carcass["pricing_qty"] == 1.0
    assert carcass["cost_total_cents"] == 50000
    assert carcass["sell_total_cents"] == 55000

    door_panel = groups[("oak-board", "door_panel")]
    assert door_panel["role_label"] == "Door and drawer material"
    assert door_panel["area_m2"] == pytest.approx(0.42)
    assert door_panel["estimated_sheets"] == 1

    visible_panel = groups[("oak-board", "visible_panel")]
    assert visible_panel["role_label"] == "Visible panel material"
    assert visible_panel["area_m2"] == pytest.approx(1.2)
    assert visible_panel["estimated_sheets"] == 1


def test_detailed_pricing_material_summary_warns_for_missing_board_data():
    result = price_quote_detailed(
        quote={
            "id": "quote-1",
            "name": "Kitchen",
            "default_carcass_board_type_id": None,
            "default_door_board_type_id": "door-board",
        },
        units=[
            {
                "unit_number": 1,
                "unit_type_key": "Base Door",
                "height": 780,
                "carcass_board_type_id": None,
                "door_board_type_id": None,
                "extra_params": {"num_doors": 0},
            }
        ],
        quote_extras=[],
        cutting_rows=[
            {"section": "carcass", "unit_number": 1, "desc": "Side", "length": 1000, "width": 500, "qty": 1},
            {"section": "panel", "unit_number": 1, "desc": "Door", "length": 700, "width": 300, "qty": 1},
        ],
        settings=DetailedPricingSettings(),
        price_lookup={
            ("board", "board::door-board", "sheet"): {"unit_price_cents": 120000},
        },
        board_lookup={
            "door-board": {
                "id": "door-board",
                "brand": "Egger",
                "material": "Oak look",
                "thickness": 18,
                "length_mm": 0,
                "width_mm": 0,
                "costing_mode": "sheet",
            },
        },
        slide_lookup={},
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={},
        active_price_list_id="price-list-1",
    )

    summary = result["material_summary"]
    assert result["is_complete"] is False
    assert len(summary["groups"]) == 1
    assert summary["groups"][0]["board_type_id"] == "door-board"
    assert summary["groups"][0]["estimated_sheets"] is None
    assert summary["total_estimated_sheets"] is None
    assert [warning["code"] for warning in summary["warnings"]] == [
        "missing_board_selection",
        "missing_board_dimensions",
    ]
    assert summary["warnings"][0]["message"] == "Choose a carcass board for Unit 1 Side."
    assert summary["warnings"][1]["message"] == "Add sheet length and width for Egger Oak look (18mm) to estimate sheets."
