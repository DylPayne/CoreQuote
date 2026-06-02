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
    assert any(line["missing"] for line in result["lines"])
