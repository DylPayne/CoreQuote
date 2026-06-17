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
