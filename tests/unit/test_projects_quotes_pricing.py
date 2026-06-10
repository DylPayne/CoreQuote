from corequote_api.projects_quotes_pricing import _build_cutting_list_preview, _price_quote


class FakeRuntimeService:
    def __init__(self, preview: dict):
        self.preview = preview

    def build_preview(self, *, company_id: str, units: list[dict], use_db_rulesets: bool) -> dict:
        return self.preview


def test_quote_cutting_list_validation_flags_missing_unit_board_choice():
    result = _build_cutting_list_preview(
        company_id="company-1",
        quote={"id": "quote-1", "default_carcass_board_type_id": None},
        units=[{"unit_number": 1, "unit_type_key": "Tall Door", "height": 2100, "width": 900, "depth": 560}],
        runtime_service=FakeRuntimeService(_preview_with_carcass_row()),
        use_rulesets=False,
        board_lookup={},
        slide_lookup={},
    )

    assert result["validation_warnings"] == [
        {
            "severity": "warning",
            "source": "unit",
            "unit_number": 1,
            "section": "carcass",
            "row_desc": "Side",
            "reason": "Choose a carcass board for this unit or quote default.",
        }
    ]
    assert result["readiness"] == {"cutlist_valid": False, "warning_count": 1}


def test_quote_pricing_readiness_includes_cutlist_validation_warnings():
    result = _price_quote(
        quote={
            "id": "quote-1",
            "name": "Kitchen",
            "default_carcass_board_type_id": None,
        },
        units=[{"unit_number": 1, "unit_type_key": "Tall Door", "height": 2100, "width": 900, "depth": 560}],
        quote_extras=[],
        runtime_service=FakeRuntimeService(_preview_with_carcass_row()),
        company_id="company-1",
        use_rulesets=False,
        price_lookup={},
        board_lookup={},
        slide_lookup={},
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={},
        active_price_list_id="price-list-1",
        pricing_settings={},
    )

    assert result["is_complete"] is False
    assert result["missing_items"] == []
    assert result["cutlist_warnings"][0]["reason"] == "Choose a carcass board for this unit or quote default."


def _preview_with_carcass_row() -> dict:
    return {
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
        "runtime_mode": "legacy",
        "unit_sources": [],
    }
