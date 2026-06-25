from corequote_api.projects_quotes_pricing import _build_cutting_list_preview, _price_quote, _to_runtime_unit
from corequote_core.front_overhangs import WALL_FRONT_OVERHANG_QUOTE_DEFAULT_KEY


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


def test_quote_cutting_list_validation_flags_drawer_slide_depth_mismatch():
    result = _build_cutting_list_preview(
        company_id="company-1",
        quote={
            "id": "quote-1",
            "default_carcass_board_type_id": "board-1",
            "default_panel_board_type_id": "board-1",
        },
        units=[
            {
                "unit_number": 1,
                "unit_type_key": "Base Draw",
                "height": 780,
                "width": 900,
                "depth": 450,
                "carcass_board_type_id": "board-1",
                "extra_params": {"num_drawers": 3, "slide_id": "slide-500"},
            }
        ],
        runtime_service=FakeRuntimeService(_preview_with_carcass_row()),
        use_rulesets=False,
        board_lookup={"board-1": {"thickness": 16, "length_mm": 2750}},
        slide_lookup={"slide-500": {"length": 500}},
    )

    assert result["validation_warnings"] == [
        {
            "severity": "warning",
            "source": "unit",
            "unit_number": 1,
            "section": "hardware",
            "row_desc": "Drawer slide",
            "reason": "Selected 500 mm slide requires a carcass depth of at least 500 mm internally.",
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


def test_runtime_unit_includes_configured_drawer_system_from_slide_lookup():
    result = _to_runtime_unit(
        {
            "unit_number": 1,
            "unit_type_key": "Base Draw",
            "height": 780,
            "width": 600,
            "depth": 560,
            "carcass_board_type_id": "board-1",
            "extra_params": {"slide_id": "slide-metal"},
        },
        quote={"default_carcass_board_type_id": "board-1"},
        board_lookup={"board-1": {"thickness": 16}},
        slide_lookup={
            "slide-metal": {
                "id": "slide-metal",
                "brand": "Blum",
                "model": "Legrabox",
                "code": "LEG-500",
                "length": 500,
                "side_length": 500,
                "side_clearance_total": 26,
                "side_height_uplift": 0,
                "drawer_system_kind": "metal",
                "drawer_system_config": {
                    "product_family": "Legrabox",
                    "installation_width_mm": 31,
                },
            }
        },
    )

    assert result["extra_params"]["slide_length"] == 500
    assert result["extra_params"]["drawer_system_kind"] == "metal"
    assert result["extra_params"]["drawer_system_config"] == {
        "product_family": "Legrabox",
        "installation_width_mm": 31,
    }


def test_runtime_unit_attaches_default_full_length_handle_lookup():
    result = _to_runtime_unit(
        {
            "unit_number": 2,
            "unit_type_key": "Base Door",
            "height": 780,
            "width": 900,
            "depth": 560,
            "carcass_board_type_id": "board-1",
            "extra_params": {"num_doors": 2, "full_length_handle_orientation": "width"},
        },
        quote={"default_carcass_board_type_id": "board-1", "default_base_handle_id": "handle-profile"},
        board_lookup={"board-1": {"thickness": 16}},
        handle_lookup={
            "handle-profile": {
                "id": "handle-profile",
                "name": "Edge Pull",
                "handle_type": "full_length",
                "front_reduction_mm": 30,
            }
        },
    )

    assert result["extra_params"]["handle_id"] == "handle-profile"
    assert result["extra_params"]["_profile_handle_lookup"]["handle-profile"]["handle_type"] == "full_length"


def test_runtime_unit_includes_quote_wall_front_overhang_default():
    quote_default = {"enabled": True, "amount_mm": 20, "edge": "bottom", "apply_to": "all", "front_indexes": []}

    result = _to_runtime_unit(
        {
            "unit_number": 3,
            "unit_type_key": "Wall Door",
            "height": 720,
            "width": 600,
            "depth": 330,
            "carcass_board_type_id": "board-1",
            "extra_params": {"num_doors": 2, "num_shelves": 1},
        },
        quote={"default_carcass_board_type_id": "board-1", "wall_front_overhang_default": quote_default},
        board_lookup={"board-1": {"thickness": 16}},
    )

    assert result["extra_params"][WALL_FRONT_OVERHANG_QUOTE_DEFAULT_KEY] == quote_default


def test_quote_pricing_includes_required_slide_accessory_prices():
    result = _price_quote(
        quote={
            "id": "quote-1",
            "name": "Kitchen",
            "default_slide_id": "slide-dynapro",
        },
        units=[
            {
                "unit_number": 1,
                "unit_type_key": "Base Draw",
                "height": 720,
                "width": 600,
                "depth": 560,
                "extra_params": {"num_drawers": 2, "handle_qty": 0},
            }
        ],
        quote_extras=[],
        runtime_service=FakeRuntimeService(
            {
                "carcass": [],
                "panels": [],
                "hardware": [],
                "extras": [],
                "runtime_rows": [],
                "runtime_mode": "legacy",
                "unit_sources": [],
            }
        ),
        company_id="company-1",
        use_rulesets=False,
        price_lookup={
            ("slide", "slide::slide-dynapro", "unit"): {"unit_price_cents": 10000},
            ("extra", "extra::extra-locking-plate", "unit"): {"unit_price_cents": 2500},
        },
        board_lookup={},
        slide_lookup={
            "slide-dynapro": {
                "id": "slide-dynapro",
                "brand": "Grass",
                "model": "Dynapro",
                "code": "DYN-500",
                "accessory_config": {
                    "accessories": [
                        {
                            "item_type": "extra",
                            "item_ref_id": "extra-locking-plate",
                            "name": "3D locking plate",
                            "quantity": 2,
                            "quantity_rule": "per_drawer",
                            "required": True,
                        }
                    ]
                },
            }
        },
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={
            "extra-locking-plate": {
                "id": "extra-locking-plate",
                "name": "Dynapro 3D locking plate",
                "category_name": "Drawer accessories",
                "supplier": "Grass",
                "code": "F134",
            }
        },
        active_price_list_id="price-list-1",
        pricing_settings={},
    )

    lines = {line["item_key"]: line for line in result["lines"]}

    assert result["missing_prices"] == []
    assert result["hardware_pick_list"]["items"][1]["item_key"] == "extra::extra-locking-plate"
    assert lines["slide::slide-dynapro"]["qty"] == 2.0
    assert lines["extra::extra-locking-plate"]["qty"] == 4.0
    assert lines["extra::extra-locking-plate"]["cost_total_cents"] == 10000


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
