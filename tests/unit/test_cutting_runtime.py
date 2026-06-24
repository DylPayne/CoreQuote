from __future__ import annotations

import copy

import pytest

from corequote_api.cutting_runtime import CutlistRuntimeService, CuttingFormulaEvaluator, CuttingRuntimeError


class FakeRuntimeStore:
    def __init__(
        self,
        *,
        unit_configs: dict[tuple[str | None, str], dict] | None = None,
        rulesets: dict[tuple[str | None, str], dict] | None = None,
    ):
        self.unit_configs = unit_configs or {}
        self.rulesets = rulesets or {}

    def resolve_unit_config(self, company_id: str, unit_type_key: str) -> dict | None:
        return copy.deepcopy(
            self.unit_configs.get((company_id, unit_type_key))
            or self.unit_configs.get((None, unit_type_key))
        )

    def resolve_ruleset(self, company_id: str, unit_type_key: str) -> dict | None:
        return copy.deepcopy(
            self.rulesets.get((company_id, unit_type_key))
            or self.rulesets.get((None, unit_type_key))
        )


def test_formula_evaluator_rejects_unknown_identifiers():
    evaluator = CuttingFormulaEvaluator()
    with pytest.raises(CuttingRuntimeError, match="Unknown identifier"):
        evaluator.evaluate_numeric("h + unknown_token", {"h": 780}, field_name="length_formula")


def test_formula_evaluator_handles_condition_logic():
    evaluator = CuttingFormulaEvaluator()
    assert evaluator.evaluate_condition("num_doors > 1 and h >= 720", {"num_doors": 2, "h": 780}) is True
    assert evaluator.evaluate_condition("num_doors > 1 and h >= 720", {"num_doors": 1, "h": 780}) is False


def test_formula_context_uses_slide_width_deduction_when_configured():
    service = CutlistRuntimeService(store=FakeRuntimeStore())

    fallback_context = service._build_formula_context(
        unit={
            "height": 720,
            "width": 600,
            "depth": 560,
            "thickness": 16,
            "extra_params": {"slide_side_clearance_total": 26, "slide_box_width_deduction_mm": 0},
        },
        unit_type_key="Base Draw",
        unit_config=None,
    )
    configured_context = service._build_formula_context(
        unit={
            "height": 720,
            "width": 600,
            "depth": 560,
            "thickness": 16,
            "extra_params": {"slide_side_clearance_total": 26, "slide_box_width_deduction_mm": 42},
        },
        unit_type_key="Base Draw",
        unit_config=None,
    )

    assert fallback_context["drawer_width"] == 516
    assert configured_context["drawer_width"] == 526
    assert configured_context["slide_box_width_deduction_mm"] == 42


def test_runtime_service_prefers_company_ruleset_over_global_default():
    store = FakeRuntimeStore(
        unit_configs={
            ("company-1", "Base Door"): {
                "id": "company-config",
                "unit_type_key": "Base Door",
                "variant_config": {"num_doors": 2, "default_shelves": 1, "panel_gap_mm": 3, "shelf_setback": 20},
            }
        },
        rulesets={
            ("company-1", "Base Door"): {
                "id": "company-ruleset",
                "unit_type_key": "Base Door",
                "unit_config_id": "company-config",
                "rows": [
                    {
                        "sort_order": 10,
                        "section": "carcass",
                        "description": "Company Side",
                        "length_formula": "h - (2 * t)",
                        "width_formula": "d - t",
                        "qty_formula": "2",
                        "condition_formula": "",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    }
                ],
            },
            (None, "Base Door"): {
                "id": "global-ruleset",
                "unit_type_key": "Base Door",
                "unit_config_id": "global-config",
                "rows": [
                    {
                        "sort_order": 10,
                        "section": "carcass",
                        "description": "Global Side",
                        "length_formula": "h - (2 * t)",
                        "width_formula": "d - t",
                        "qty_formula": "2",
                        "condition_formula": "",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    }
                ],
            },
        },
    )
    service = CutlistRuntimeService(store=store)

    result = service.build_preview(
        company_id="company-1",
        units=[
            {
                "unit_number": 1,
                "unit_type": "Base Door",
                "height": 780,
                "width": 900,
                "depth": 560,
                "thickness": 16,
                "extra_params": {"num_doors": 2, "num_shelves": 1},
            }
        ],
        use_db_rulesets=True,
    )

    assert result["runtime_mode"] == "ruleset"
    assert result["unit_sources"][0]["source"] == "ruleset"
    assert result["unit_sources"][0]["ruleset_id"] == "company-ruleset"
    assert result["carcass"] == [{"unit_number": 1, "desc": "Company Side", "length": 748, "width": 544, "qty": 2}]
    assert result["validation_warnings"] == []
    assert result["readiness"] == {"cutlist_valid": True, "warning_count": 0}


def test_runtime_service_warns_when_drawer_side_dimension_collapses_to_zero():
    store = FakeRuntimeStore(
        unit_configs={
            (None, "Base Draw"): {
                "id": "global-config",
                "unit_type_key": "Base Draw",
                "variant_config": {"num_drawers": 3, "panel_gap_mm": 3},
            }
        },
        rulesets={
            (None, "Base Draw"): {
                "id": "global-ruleset",
                "unit_type_key": "Base Draw",
                "unit_config_id": "global-config",
                "rows": [
                    {
                        "sort_order": 10,
                        "section": "carcass",
                        "description": "Drawer Side",
                        "length_formula": "drawer_depth",
                        "width_formula": "drawer_side_height",
                        "qty_formula": "num_drawers * 2",
                        "condition_formula": "num_drawers > 0",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                    {
                        "sort_order": 20,
                        "section": "panel",
                        "description": "Drawer Front",
                        "length_formula": "drawer_front_height",
                        "width_formula": "w - panel_gap_mm",
                        "qty_formula": "num_drawers",
                        "condition_formula": "num_drawers > 0",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                ],
            }
        },
    )
    service = CutlistRuntimeService(store=store)

    result = service.build_preview(
        company_id="company-1",
        units=[
            {
                "unit_number": 4,
                "unit_type": "Base Draw",
                "height": 300,
                "width": 600,
                "depth": 560,
                "thickness": 16,
                "extra_params": {"slide_side_length": 500},
            }
        ],
        use_db_rulesets=True,
    )

    assert {"unit_number": 4, "desc": "Drawer Side", "length": 500, "width": 0, "qty": 6} in result["carcass"]
    assert {"unit_number": 4, "desc": "Drawer Front", "length": 97, "width": 597, "qty": 3} in result["panels"]
    assert result["validation_warnings"] == [
        {
            "severity": "warning",
            "source": "unit",
            "unit_number": 4,
            "section": "carcass",
            "row_desc": "Drawer Side",
            "reason": "Width must be greater than 0 mm.",
        }
    ]
    assert result["readiness"] == {"cutlist_valid": False, "warning_count": 1}


def test_runtime_service_uses_legacy_output_for_split_drawer_units():
    store = FakeRuntimeStore(
        unit_configs={
            (None, "Base Draw"): {
                "id": "global-config",
                "unit_type_key": "Base Draw",
                "variant_config": {"num_drawers": 3, "panel_gap_mm": 3},
            }
        },
        rulesets={
            (None, "Base Draw"): {
                "id": "global-ruleset",
                "unit_type_key": "Base Draw",
                "unit_config_id": "global-config",
                "rows": [
                    {
                        "sort_order": 10,
                        "section": "carcass",
                        "description": "Drawer Front/Back",
                        "length_formula": "drawer_width",
                        "width_formula": "drawer_front_back_height",
                        "qty_formula": "num_drawers * 2",
                        "condition_formula": "num_drawers > 0",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                    {
                        "sort_order": 20,
                        "section": "panel",
                        "description": "Drawer Front",
                        "length_formula": "drawer_front_height",
                        "width_formula": "w - panel_gap_mm",
                        "qty_formula": "num_drawers",
                        "condition_formula": "num_drawers > 0",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                ],
            }
        },
    )
    service = CutlistRuntimeService(store=store)

    result = service.build_preview(
        company_id="company-1",
        units=[
            {
                "unit_number": 2,
                "unit_type": "Base Draw",
                "height": 780,
                "width": 600,
                "depth": 580,
                "thickness": 16,
                "extra_params": {
                    "num_drawers": 3,
                    "drawer_split_mode": "manual",
                    "drawer_face_heights": [194, 194, 383],
                    "slide_side_length": 490,
                    "slide_side_clearance_total": 10,
                },
            }
        ],
        use_db_rulesets=True,
    )

    assert result["runtime_mode"] == "legacy"
    assert result["unit_sources"] == [
        {
            "unit_number": 2,
            "unit_type_key": "Base Draw",
            "source": "legacy",
            "ruleset_id": "global-ruleset",
            "unit_config_id": "global-config",
            "note": "Split drawer fronts use legacy strategy output.",
        }
    ]
    assert {"unit_number": 2, "desc": "Drawer Front/Back", "length": 548, "width": 94, "qty": 4} in result["carcass"]
    assert {"unit_number": 2, "desc": "Drawer Front/Back", "length": 548, "width": 283, "qty": 2} in result["carcass"]
    assert {"unit_number": 2, "desc": "Drawer Front", "length": 194, "width": 597, "qty": 2} in result["panels"]
    assert {"unit_number": 2, "desc": "Drawer Front", "length": 383, "width": 597, "qty": 1} in result["panels"]


def test_runtime_service_keeps_conventional_drawer_box_parts():
    service = CutlistRuntimeService(store=FakeRuntimeStore())

    result = service.build_preview(
        company_id="company-1",
        units=[
            {
                "unit_number": 3,
                "unit_type": "Base Draw",
                "height": 780,
                "width": 600,
                "depth": 560,
                "thickness": 16,
                "extra_params": {
                    "num_drawers": 3,
                    "slide_side_length": 500,
                    "slide_side_clearance_total": 26,
                },
            }
        ],
        use_db_rulesets=True,
    )

    assert result["runtime_mode"] == "legacy"
    assert result["unit_sources"][0]["source"] == "legacy"
    assert any(row["desc"] == "Drawer Side" for row in result["carcass"])
    assert any(row["desc"] == "Drawer Front/Back" for row in result["carcass"])
    assert any(row["desc"] == "Drawer Base" for row in result["carcass"])


def test_runtime_service_uses_configured_metal_drawer_system_rows():
    service = CutlistRuntimeService(store=FakeRuntimeStore())

    result = service.build_preview(
        company_id="company-1",
        units=[
            {
                "unit_number": 5,
                "unit_type": "Base Draw",
                "height": 780,
                "width": 600,
                "depth": 560,
                "thickness": 16,
                "extra_params": {
                    "num_drawers": 3,
                    "slide_length": 500,
                    "slide_side_length": 500,
                    "slide_side_clearance_total": 26,
                    "drawer_system_kind": "metal",
                    "drawer_system_config": {
                        "product_family": "Nova Pro Scala",
                        "manufacturer": "Grass",
                        "side_height_mm": 90,
                        "installation_width_mm": 29,
                        "variables": {"use_designer_inset": True},
                        "panel_formulas": [
                            {
                                "name": "Metal Drawer Bottom",
                                "section": "carcass",
                                "length_formula": "inner_w - (2 * installation_width_mm)",
                                "width_formula": "slide_length - 19",
                                "qty_formula": "num_drawers",
                            },
                            {
                                "name": "Cut Board Back",
                                "section": "carcass",
                                "length_formula": "inner_w - (2 * installation_width_mm)",
                                "width_formula": "side_height_mm - 12",
                                "qty_formula": "num_drawers",
                            },
                            {
                                "name": "Designer Inset Panel",
                                "section": "panel",
                                "length_formula": "inner_w - 6",
                                "width_formula": "drawer_front_height - 6",
                                "qty_formula": "num_drawers",
                                "condition_formula": "use_designer_inset",
                            },
                        ],
                    },
                },
            }
        ],
        use_db_rulesets=True,
    )

    assert result["runtime_mode"] == "drawer_system"
    assert result["unit_sources"] == [
        {
            "unit_number": 5,
            "unit_type_key": "Base Draw",
            "source": "drawer_system",
            "ruleset_id": None,
            "unit_config_id": None,
            "note": "Configured metal drawer system output.",
        }
    ]
    suppressed_parts = {"Drawer Side", "Drawer Front/Back", "Drawer Base"}
    assert suppressed_parts.isdisjoint({row["desc"] for row in result["carcass"]})
    assert {"unit_number": 5, "desc": "Metal Drawer Bottom", "length": 510, "width": 481, "qty": 3} in result["carcass"]
    assert {"unit_number": 5, "desc": "Cut Board Back", "length": 510, "width": 78, "qty": 3} in result["carcass"]
    assert {"unit_number": 5, "desc": "Designer Inset Panel", "length": 562, "width": 251, "qty": 3} in result["panels"]
    assert any(row["desc"] == "Drawer Front" for row in result["panels"])


def test_runtime_service_falls_back_to_legacy_when_ruleset_missing():
    store = FakeRuntimeStore()
    service = CutlistRuntimeService(store=store)

    result = service.build_preview(
        company_id="company-1",
        units=[
            {
                "unit_number": 1,
                "unit_type": "Base Door",
                "height": 780,
                "width": 900,
                "depth": 560,
                "thickness": 16,
                "extra_params": {"num_doors": 2, "num_shelves": 1},
            }
        ],
        use_db_rulesets=True,
    )

    assert result["runtime_mode"] == "legacy"
    assert result["unit_sources"][0]["source"] == "legacy"
    assert {"unit_number": 1, "desc": "Side", "length": 748, "width": 544, "qty": 2} in result["carcass"]
    assert {"unit_number": 1, "desc": "Door", "length": 777, "width": 447, "qty": 2} in result["panels"]


def test_runtime_legacy_wall_door_sizing_is_unchanged_without_overhang():
    service = CutlistRuntimeService(store=FakeRuntimeStore())

    result = service.build_preview(
        company_id="company-1",
        units=[_wall_door_unit()],
        use_db_rulesets=False,
    )

    assert {"unit_number": 1, "desc": "Door", "length": 717, "width": 297, "qty": 2} in result["panels"]
    assert all("overhang" not in row["desc"].lower() for row in result["panels"])


def test_runtime_legacy_wall_door_applies_bottom_overhang_to_all_fronts():
    service = CutlistRuntimeService(store=FakeRuntimeStore())

    result = service.build_preview(
        company_id="company-1",
        units=[
            _wall_door_unit(
                extra_params={
                    "num_doors": 2,
                    "num_shelves": 1,
                    "wall_front_overhang": {"mode": "custom", "amount_mm": 20, "edge": "bottom", "apply_to": "all"},
                }
            )
        ],
        use_db_rulesets=False,
    )

    assert result["panels"] == [{"unit_number": 1, "desc": "Door (bottom overhang 20 mm)", "length": 737, "width": 297, "qty": 2}]


def test_runtime_legacy_wall_door_splits_selected_overhang_fronts():
    service = CutlistRuntimeService(store=FakeRuntimeStore())

    result = service.build_preview(
        company_id="company-1",
        units=[
            _wall_door_unit(
                extra_params={
                    "num_doors": 2,
                    "num_shelves": 1,
                    "wall_front_overhang": {
                        "mode": "custom",
                        "amount_mm": 20,
                        "edge": "bottom",
                        "apply_to": "selected",
                        "front_indexes": [2],
                    },
                }
            )
        ],
        use_db_rulesets=False,
    )

    assert result["panels"] == [
        {"unit_number": 1, "desc": "Door", "length": 717, "width": 297, "qty": 1},
        {"unit_number": 1, "desc": "Door (bottom overhang 20 mm)", "length": 737, "width": 297, "qty": 1},
    ]


def test_runtime_ruleset_wall_door_overhang_matches_legacy_path():
    service = CutlistRuntimeService(store=_wall_door_ruleset_store())
    units = [
        _wall_door_unit(
            extra_params={
                "num_doors": 2,
                "num_shelves": 1,
                "wall_front_overhang": {"mode": "custom", "amount_mm": 20, "edge": "bottom", "apply_to": "all"},
            }
        )
    ]

    runtime_result = service.build_preview(company_id="company-1", units=units, use_db_rulesets=True)
    legacy_result = service.build_preview(company_id="company-1", units=units, use_db_rulesets=False)

    assert runtime_result["runtime_mode"] == "ruleset"
    assert runtime_result["panels"] == legacy_result["panels"]
    assert runtime_result["panels"] == [
        {"unit_number": 1, "desc": "Door (bottom overhang 20 mm)", "length": 737, "width": 297, "qty": 2}
    ]


def test_runtime_legacy_output_includes_base_door_top_j_channel():
    service = CutlistRuntimeService(store=FakeRuntimeStore())

    result = service.build_preview(
        company_id="company-1",
        units=[
            {
                "unit_number": 7,
                "unit_type": "Base Door",
                "height": 780,
                "width": 900,
                "depth": 560,
                "thickness": 16,
                "extra_params": {
                    "num_doors": 2,
                    "num_shelves": 1,
                    "base_door_top_j_channel_handle_id": "handle-j",
                    "_profile_handle_lookup": {
                        "handle-j": {"id": "handle-j", "name": "J Rail", "handle_type": "j_channel", "front_reduction_mm": 24}
                    },
                },
            }
        ],
        use_db_rulesets=False,
    )

    assert {"unit_number": 7, "desc": "Door", "length": 753, "width": 447, "qty": 2} in result["panels"]
    assert {"unit_number": 7, "desc": "J Rail top channel", "length": 24, "width": 900, "qty": 1, "item_ref_id": "handle-j"} in result["hardware"]
    assert result["validation_warnings"] == []


def test_runtime_legacy_output_includes_full_length_profile_orientation():
    service = CutlistRuntimeService(store=FakeRuntimeStore())

    result = service.build_preview(
        company_id="company-1",
        units=[
            {
                "unit_number": 8,
                "unit_type": "Base Door",
                "height": 780,
                "width": 900,
                "depth": 560,
                "thickness": 16,
                "extra_params": {
                    "num_doors": 2,
                    "handle_id": "handle-profile",
                    "full_length_handle_orientation": "width",
                    "_profile_handle_lookup": {
                        "handle-profile": {"id": "handle-profile", "name": "Edge Pull", "handle_type": "full_length", "front_reduction_mm": 30}
                    },
                },
            }
        ],
        use_db_rulesets=False,
    )

    assert {"unit_number": 8, "desc": "Door", "length": 747, "width": 447, "qty": 2} in result["panels"]
    assert {"unit_number": 8, "desc": "Edge Pull", "length": 30, "width": 447, "qty": 2, "item_ref_id": "handle-profile"} in result["hardware"]
    assert result["validation_warnings"] == []


def test_runtime_ruleset_path_matches_legacy_for_base_door_fixture():
    store = FakeRuntimeStore(
        unit_configs={
            (None, "Base Door"): {
                "id": "global-config",
                "unit_type_key": "Base Door",
                "variant_config": {"num_doors": 2, "default_shelves": 1, "panel_gap_mm": 3, "shelf_setback": 20},
            }
        },
        rulesets={
            (None, "Base Door"): {
                "id": "global-ruleset",
                "unit_type_key": "Base Door",
                "unit_config_id": "global-config",
                "rows": [
                    {
                        "sort_order": 10,
                        "section": "carcass",
                        "description": "Side",
                        "length_formula": "h - (2 * t)",
                        "width_formula": "d - t",
                        "qty_formula": "2",
                        "condition_formula": "",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                    {
                        "sort_order": 20,
                        "section": "carcass",
                        "description": "Base",
                        "length_formula": "w",
                        "width_formula": "d",
                        "qty_formula": "1",
                        "condition_formula": "",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                    {
                        "sort_order": 30,
                        "section": "carcass",
                        "description": "Rail",
                        "length_formula": "w",
                        "width_formula": "100",
                        "qty_formula": "2",
                        "condition_formula": "",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                    {
                        "sort_order": 40,
                        "section": "carcass",
                        "description": "Backing",
                        "length_formula": "h - (2 * t)",
                        "width_formula": "w",
                        "qty_formula": "1",
                        "condition_formula": "",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                    {
                        "sort_order": 50,
                        "section": "carcass",
                        "description": "Shelf",
                        "length_formula": "w - (2 * t)",
                        "width_formula": "d - t - shelf_setback",
                        "qty_formula": "num_shelves",
                        "condition_formula": "num_shelves > 0",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                    {
                        "sort_order": 100,
                        "section": "panel",
                        "description": "Door",
                        "length_formula": "h - panel_gap_mm",
                        "width_formula": "(w / num_doors) - panel_gap_mm",
                        "qty_formula": "num_doors",
                        "condition_formula": "num_doors > 0",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                ],
            }
        },
    )
    service = CutlistRuntimeService(store=store)
    units = [
        {
            "unit_number": 1,
            "unit_type": "Base Door",
            "height": 780,
            "width": 900,
            "depth": 560,
            "thickness": 16,
            "extra_params": {"num_doors": 2, "num_shelves": 1},
        }
    ]

    runtime_result = service.build_preview(company_id="company-1", units=units, use_db_rulesets=True)
    legacy_result = service.build_preview(company_id="company-1", units=units, use_db_rulesets=False)

    assert runtime_result["runtime_mode"] == "ruleset"
    assert runtime_result["carcass"] == legacy_result["carcass"]
    assert runtime_result["panels"] == legacy_result["panels"]


def _wall_door_unit(*, extra_params: dict | None = None) -> dict:
    return {
        "unit_number": 1,
        "unit_type": "Wall Door",
        "height": 720,
        "width": 600,
        "depth": 330,
        "thickness": 16,
        "extra_params": extra_params or {"num_doors": 2, "num_shelves": 1},
    }


def _wall_door_ruleset_store() -> FakeRuntimeStore:
    return FakeRuntimeStore(
        unit_configs={
            (None, "Wall Door"): {
                "id": "wall-config",
                "unit_type_key": "Wall Door",
                "variant_config": {"num_doors": 2, "default_shelves": 1, "panel_gap_mm": 3, "shelf_setback": 20},
            }
        },
        rulesets={
            (None, "Wall Door"): {
                "id": "wall-ruleset",
                "unit_type_key": "Wall Door",
                "unit_config_id": "wall-config",
                "rows": [
                    {
                        "sort_order": 10,
                        "section": "carcass",
                        "description": "Side",
                        "length_formula": "h - (2 * t)",
                        "width_formula": "d - t",
                        "qty_formula": "2",
                        "condition_formula": "",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                    {
                        "sort_order": 20,
                        "section": "carcass",
                        "description": "Shelf",
                        "length_formula": "w - (2 * t)",
                        "width_formula": "d - t - shelf_setback",
                        "qty_formula": "num_shelves",
                        "condition_formula": "num_shelves > 0",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                    {
                        "sort_order": 100,
                        "section": "panel",
                        "description": "Door",
                        "length_formula": "h - panel_gap_mm",
                        "width_formula": "(w / num_doors) - panel_gap_mm",
                        "qty_formula": "num_doors",
                        "condition_formula": "num_doors > 0",
                        "edge_long_1": False,
                        "edge_long_2": False,
                        "edge_short_1": False,
                        "edge_short_2": False,
                    },
                ],
            }
        },
    )
