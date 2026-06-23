from corequote_core.hardware_pick_list import build_hardware_pick_list


def test_hardware_pick_list_groups_real_job_hardware_and_extras():
    result = build_hardware_pick_list(
        quote={
            "id": "quote-1",
            "name": "Kitchen Quote",
            "default_slide_id": "slide-1",
            "default_hinge_id": "hinge-1",
            "default_base_handle_id": "handle-base",
            "default_wall_handle_id": "handle-wall",
            "default_drawer_handle_id": "handle-drawer",
        },
        units=[
            unit(1, "Base Draw", height=720, extra_params={"num_drawers": 3, "handle_qty": 3}),
            unit(2, "Base Door", height=720, extra_params={"num_doors": 2}),
            unit(3, "Base Door", height=720, extra_params={"num_doors": 2}),
            unit(4, "Wall Door", height=720, extra_params={"num_doors": 2}),
            unit(5, "Wall Door", height=720, extra_params={"num_doors": 2}),
        ],
        quote_extras=[{"extra_id": "extra-1", "quantity": 1}],
        slide_lookup={
            "slide-1": {
                "id": "slide-1",
                "brand": "Grass",
                "model": "Dynapro",
                "code": "S500",
            }
        },
        hinge_lookup={
            "hinge-1": {
                "id": "hinge-1",
                "brand": "Blum",
                "model": "Clip top",
                "code": "H110",
            }
        },
        handle_lookup={
            "handle-base": {"id": "handle-base", "name": "Base pull", "supplier": "Core", "code": "B128"},
            "handle-wall": {"id": "handle-wall", "name": "Wall pull", "supplier": "Core", "code": "W128"},
            "handle-drawer": {"id": "handle-drawer", "name": "Drawer pull", "supplier": "Core", "code": "D192"},
        },
        extra_lookup={
            "extra-1": {
                "id": "extra-1",
                "name": "Waste removal",
                "category_name": "Site extras",
                "supplier": "Core",
                "code": "WR1",
            }
        },
    )

    items = {item["item_key"]: item for item in result["items"]}

    assert result["warnings"] == []
    assert result["total_item_count"] == 6
    assert result["total_quantity"] == 31

    assert items["slide::slide-1"]["quantity"] == 3
    assert items["slide::slide-1"]["uom"] == "pairs"
    assert items["slide::slide-1"]["supplier"] == "Grass"
    assert items["slide::slide-1"]["code"] == "S500"
    assert items["slide::slide-1"]["used_in"] == ["Unit 1 drawers"]
    assert items["slide::slide-1"]["unit_numbers"] == [1]

    assert items["hinge::hinge-1"]["quantity"] == 16
    assert items["hinge::hinge-1"]["used_in"] == [
        "Unit 2 doors",
        "Unit 3 doors",
        "Unit 4 doors",
        "Unit 5 doors",
    ]
    assert items["hinge::hinge-1"]["unit_numbers"] == [2, 3, 4, 5]

    assert items["handle::handle-drawer"]["quantity"] == 3
    assert items["handle::handle-base"]["quantity"] == 4
    assert items["handle::handle-wall"]["quantity"] == 4

    assert items["extra::extra-1"]["quantity"] == 1
    assert items["extra::extra-1"]["supplier"] == "Core"
    assert items["extra::extra-1"]["code"] == "WR1"
    assert items["extra::extra-1"]["used_in"] == ["Quote extra"]


def test_hardware_pick_list_warns_for_missing_component_choices():
    result = build_hardware_pick_list(
        quote={"id": "quote-1", "name": "Kitchen Quote"},
        units=[
            unit(1, "Base Draw", extra_params={"num_drawers": 2, "handle_qty": 2}),
            unit(2, "Base Door", extra_params={"num_doors": 2}),
        ],
        quote_extras=[],
        slide_lookup={},
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={},
    )

    assert result["items"] == []
    assert [(warning["code"], warning["unit_number"]) for warning in result["warnings"]] == [
        ("missing_slide_selection", 1),
        ("missing_handle_selection", 1),
        ("missing_hinge_selection", 2),
        ("missing_handle_selection", 2),
    ]
    assert result["warnings"][0]["message"] == "Choose a drawer slide for Unit 1 drawers."


def test_hardware_pick_list_prefers_unit_hardware_overrides():
    result = build_hardware_pick_list(
        quote={
            "id": "quote-1",
            "name": "Kitchen Quote",
            "default_slide_id": "slide-default",
            "default_hinge_id": "hinge-default",
            "default_base_handle_id": "handle-default",
            "default_drawer_handle_id": "handle-default",
        },
        units=[
            unit(
                1,
                "Base Draw",
                extra_params={
                    "num_drawers": 2,
                    "handle_qty": 2,
                    "slide_id": "slide-override",
                    "handle_id": "handle-override",
                },
            ),
            unit(
                2,
                "Base Door",
                extra_params={
                    "num_doors": 2,
                    "hinge_id": "hinge-override",
                    "handle_id": "handle-override",
                },
            ),
        ],
        quote_extras=[],
        slide_lookup={
            "slide-default": {"id": "slide-default", "brand": "Default", "model": "Slide", "code": "SD"},
            "slide-override": {"id": "slide-override", "brand": "Override", "model": "Slide", "code": "SO"},
        },
        hinge_lookup={
            "hinge-default": {"id": "hinge-default", "brand": "Default", "model": "Hinge", "code": "HD"},
            "hinge-override": {"id": "hinge-override", "brand": "Override", "model": "Hinge", "code": "HO"},
        },
        handle_lookup={
            "handle-default": {"id": "handle-default", "name": "Default pull", "supplier": "Core", "code": "PD"},
            "handle-override": {"id": "handle-override", "name": "Override pull", "supplier": "Core", "code": "PO"},
        },
        extra_lookup={},
    )

    items = {item["item_key"]: item for item in result["items"]}

    assert result["warnings"] == []
    assert "slide::slide-default" not in items
    assert "hinge::hinge-default" not in items
    assert "handle::handle-default" not in items
    assert items["slide::slide-override"]["unit_numbers"] == [1]
    assert items["hinge::hinge-override"]["unit_numbers"] == [2]
    assert items["handle::handle-override"]["unit_numbers"] == [1, 2]


def test_hardware_pick_list_adds_required_slide_accessory_bundle():
    result = build_hardware_pick_list(
        quote={
            "id": "quote-1",
            "name": "Kitchen Quote",
            "default_slide_id": "slide-dynapro",
        },
        units=[unit(1, "Base Draw", height=720, extra_params={"num_drawers": 3, "handle_qty": 0})],
        quote_extras=[],
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
                            "quantity": 2,
                            "quantity_rule": "per_drawer",
                            "required": True,
                            "uom": "pcs",
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
    )

    items = {item["item_key"]: item for item in result["items"]}

    assert result["warnings"] == []
    assert result["optional_items"] == []
    assert items["slide::slide-dynapro"]["quantity"] == 3
    assert items["extra::extra-locking-plate"]["quantity"] == 6
    assert items["extra::extra-locking-plate"]["item_name"] == "Dynapro 3D locking plate"
    assert items["extra::extra-locking-plate"]["used_in"] == ["Unit 1 drawers"]


def test_hardware_pick_list_defaults_slide_accessories_per_slide_pair():
    result = build_hardware_pick_list(
        quote={
            "id": "quote-1",
            "name": "Kitchen Quote",
            "default_slide_id": "slide-dynapro",
        },
        units=[
            unit(1, "Base Draw", height=720, extra_params={"num_drawers": 1, "handle_qty": 0}),
            unit(2, "Base Draw", height=720, extra_params={"num_drawers": 3, "handle_qty": 0}),
        ],
        quote_extras=[],
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
                            "item_ref_id": "extra-locking-device",
                            "quantity": 1,
                            "required": True,
                            "uom": "pcs",
                        }
                    ]
                },
            }
        },
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={
            "extra-locking-device": {
                "id": "extra-locking-device",
                "name": "Dynapro locking device",
                "category_name": "Drawer accessories",
                "supplier": "Grass",
                "code": "F134",
            }
        },
    )

    items = {item["item_key"]: item for item in result["items"]}

    assert result["warnings"] == []
    assert items["slide::slide-dynapro"]["quantity"] == 4
    assert items["extra::extra-locking-device"]["quantity"] == 4
    assert items["extra::extra-locking-device"]["unit_numbers"] == [1, 2]


def test_hardware_pick_list_adds_required_hinge_accessory_per_hinge():
    result = build_hardware_pick_list(
        quote={
            "id": "quote-1",
            "name": "Kitchen Quote",
            "default_hinge_id": "hinge-110",
            "default_base_handle_id": "handle-base",
        },
        units=[unit(2, "Base Door", height=720, extra_params={"num_doors": 2, "handle_qty": 0})],
        quote_extras=[],
        slide_lookup={},
        hinge_lookup={
            "hinge-110": {
                "id": "hinge-110",
                "brand": "Blum",
                "model": "Clip top",
                "code": "H110",
                "accessory_config": {
                    "accessories": [
                        {
                            "item_type": "extra",
                            "item_ref_id": "extra-mounting-plate",
                            "quantity": 1,
                            "quantity_rule": "per_hinge",
                            "required": True,
                        }
                    ]
                },
            }
        },
        handle_lookup={"handle-base": {"id": "handle-base", "name": "Base pull", "supplier": "Core", "code": "B128"}},
        extra_lookup={
            "extra-mounting-plate": {
                "id": "extra-mounting-plate",
                "name": "Blum mounting plate",
                "category_name": "Hinge accessories",
                "supplier": "Blum",
                "code": "PLT",
            }
        },
    )

    items = {item["item_key"]: item for item in result["items"]}

    assert result["warnings"] == []
    assert items["hinge::hinge-110"]["quantity"] == 4
    assert items["extra::extra-mounting-plate"]["quantity"] == 4
    assert items["extra::extra-mounting-plate"]["unit_numbers"] == [2]


def test_hardware_pick_list_defaults_hinge_accessories_per_hinge():
    result = build_hardware_pick_list(
        quote={
            "id": "quote-1",
            "name": "Kitchen Quote",
            "default_hinge_id": "hinge-110",
            "default_base_handle_id": "handle-base",
        },
        units=[unit(2, "Base Door", height=720, extra_params={"num_doors": 2, "handle_qty": 0})],
        quote_extras=[],
        slide_lookup={},
        hinge_lookup={
            "hinge-110": {
                "id": "hinge-110",
                "brand": "Blum",
                "model": "Clip top",
                "code": "H110",
                "accessory_config": {
                    "accessories": [
                        {
                            "item_type": "extra",
                            "item_ref_id": "extra-mounting-plate",
                            "quantity": 1,
                            "required": True,
                        }
                    ]
                },
            }
        },
        handle_lookup={"handle-base": {"id": "handle-base", "name": "Base pull", "supplier": "Core", "code": "B128"}},
        extra_lookup={
            "extra-mounting-plate": {
                "id": "extra-mounting-plate",
                "name": "Blum mounting plate",
                "category_name": "Hinge accessories",
                "supplier": "Blum",
                "code": "PLT",
            }
        },
    )

    items = {item["item_key"]: item for item in result["items"]}

    assert result["warnings"] == []
    assert items["hinge::hinge-110"]["quantity"] == 4
    assert items["extra::extra-mounting-plate"]["quantity"] == 4
    assert items["extra::extra-mounting-plate"]["unit_numbers"] == [2]


def test_hardware_pick_list_applies_height_condition_per_matching_drawer():
    result = build_hardware_pick_list(
        quote={"id": "quote-1", "name": "Kitchen Quote", "default_slide_id": "slide-scala"},
        units=[
            unit(
                3,
                "Base Draw",
                height=720,
                extra_params={"num_drawers": 3, "drawer_face_heights": [160, 220, 260], "handle_qty": 0},
            )
        ],
        quote_extras=[],
        slide_lookup={
            "slide-scala": {
                "id": "slide-scala",
                "brand": "Grass",
                "model": "Nova Pro Scala",
                "code": "NPS",
                "accessory_config": {
                    "accessories": [
                        {
                            "item_type": "extra",
                            "item_ref_id": "extra-rail",
                            "name": "Scala rail set",
                            "quantity": 1,
                            "quantity_rule": "per_drawer",
                            "condition": {
                                "field": "drawer_front_height",
                                "operator": "greater_than",
                                "value_number": 180,
                            },
                        }
                    ]
                },
            }
        },
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={"extra-rail": {"id": "extra-rail", "name": "Scala rail set", "category_name": "Drawer accessories"}},
    )

    items = {item["item_key"]: item for item in result["items"]}

    assert items["extra::extra-rail"]["quantity"] == 2


def test_hardware_pick_list_keeps_optional_accessories_out_of_totals_until_enabled():
    result = build_hardware_pick_list(
        quote={"id": "quote-1", "name": "Kitchen Quote", "default_slide_id": "slide-1"},
        units=[unit(1, "Base Draw", height=720, extra_params={"num_drawers": 2, "handle_qty": 0})],
        quote_extras=[],
        slide_lookup={
            "slide-1": {
                "id": "slide-1",
                "brand": "Grass",
                "model": "Dynapro",
                "code": "DYN",
                "accessory_config": {
                    "accessories": [
                        {
                            "item_type": "extra",
                            "item_ref_id": "extra-stabiliser",
                            "name": "Wide drawer stabiliser",
                            "quantity": 1,
                            "quantity_rule": "per_unit",
                            "required": False,
                            "enabled": False,
                        }
                    ]
                },
            }
        },
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={"extra-stabiliser": {"id": "extra-stabiliser", "name": "Wide drawer stabiliser", "category_name": "Drawer accessories"}},
    )

    assert [item["item_key"] for item in result["items"]] == ["slide::slide-1"]
    assert result["total_item_count"] == 1
    assert result["total_quantity"] == 2
    assert result["optional_items"][0]["item_key"] == "extra::extra-stabiliser"
    assert result["optional_items"][0]["quantity"] == 2


def test_hardware_pick_list_adds_configured_metal_drawer_system_accessories():
    result = build_hardware_pick_list(
        quote={
            "id": "quote-1",
            "name": "Kitchen Quote",
            "default_slide_id": "slide-metal",
            "default_drawer_handle_id": "handle-drawer",
        },
        units=[unit(1, "Base Draw", height=720, extra_params={"num_drawers": 3, "handle_qty": 3})],
        quote_extras=[],
        slide_lookup={
            "slide-metal": {
                "id": "slide-metal",
                "brand": "Blum",
                "model": "Legrabox",
                "code": "LEG-500",
                "drawer_system_kind": "metal",
                "drawer_system_config": {
                    "hardware_items": [
                        {
                            "item_type": "extra",
                            "item_ref_id": "extra-bracket",
                            "name": "Front bracket set",
                            "quantity_per_drawer": 2,
                            "uom": "pcs",
                        },
                        {
                            "item_type": "extra",
                            "name": "Steel back set",
                            "supplier": "Blum",
                            "code": "BACK-500",
                            "quantity_per_drawer": 1,
                            "uom": "sets",
                        },
                    ]
                },
            }
        },
        hinge_lookup={},
        handle_lookup={
            "handle-drawer": {"id": "handle-drawer", "name": "Drawer pull", "supplier": "Core", "code": "D192"},
        },
        extra_lookup={
            "extra-bracket": {
                "id": "extra-bracket",
                "name": "Catalog bracket",
                "category_name": "Drawer systems",
                "supplier": "Blum",
                "code": "BRK-500",
            }
        },
    )

    items = {item["item_key"]: item for item in result["items"]}

    assert result["warnings"] == []
    assert items["slide::slide-metal"]["quantity"] == 3
    assert items["extra::extra-bracket"]["quantity"] == 6
    assert items["extra::extra-bracket"]["item_name"] == "Catalog bracket"
    assert items["extra::drawer-system:slide-metal:1:steel-back-set"]["quantity"] == 3
    assert items["extra::drawer-system:slide-metal:1:steel-back-set"]["supplier"] == "Blum"
    assert items["extra::drawer-system:slide-metal:1:steel-back-set"]["code"] == "BACK-500"


def test_hardware_pick_list_applies_metal_side_height_accessory_condition():
    result = build_hardware_pick_list(
        quote={"id": "quote-1", "name": "Kitchen Quote", "default_slide_id": "slide-metal"},
        units=[unit(1, "Base Draw", height=760, extra_params={"num_drawers": 2, "handle_qty": 0})],
        quote_extras=[],
        slide_lookup={
            "slide-metal": {
                "id": "slide-metal",
                "brand": "Grass",
                "model": "Nova Pro Scala H186",
                "code": "NPS-500",
                "length": 500,
                "mount_type": "metal_system",
                "product_family": "Nova Pro Scala",
                "drawer_system_kind": "metal",
                "drawer_system_config": {"side_height_mm": 186},
                "accessory_config": {
                    "accessories": [
                        {
                            "item_type": "extra",
                            "item_ref_id": "extra-rail",
                            "name": "Rail set",
                            "quantity": 1,
                            "quantity_rule": "per_drawer",
                            "condition": {
                                "field": "metal_side_height",
                                "operator": "greater_than_or_equal",
                                "value_number": 180,
                            },
                        }
                    ]
                },
            }
        },
        hinge_lookup={},
        handle_lookup={},
        extra_lookup={"extra-rail": {"id": "extra-rail", "name": "Rail set", "category_name": "Drawer systems"}},
    )

    items = {item["item_key"]: item for item in result["items"]}

    assert items["extra::extra-rail"]["quantity"] == 2


def unit(unit_number: int, unit_type_key: str, *, height: int = 780, extra_params: dict | None = None) -> dict:
    return {
        "unit_number": unit_number,
        "unit_type_key": unit_type_key,
        "height": height,
        "extra_params": extra_params or {},
    }
