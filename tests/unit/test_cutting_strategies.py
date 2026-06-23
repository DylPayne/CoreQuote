import pytest

from corequote_core.cutting.engine import CuttingEngine
from corequote_core.models import Slide
from corequote_core.units.types import DoorUnit, DrawerUnit, TallUnit


def _board_map(result_rows):
    return {(b.name, b.length, b.width): b.qty for b in result_rows}


def test_drawer_strategy_groups_front_heights_and_applies_side_uplift():
    slide = Slide(
        brand="Grass",
        model="Dynapro",
        code="D500",
        length=500,
        side_length=490,
        side_clearance_total=10,
        side_height_uplift=5,
    )
    unit = DrawerUnit(
        h=780,
        w=600,
        d=580,
        slide=slide,
        num_drawers=3,
        drawer_face_heights=[194, 194, 383],
        thickness=16,
    )

    boards = CuttingEngine.calculate_carcass(unit)
    by_shape = _board_map(boards)

    # Front/back heights are (face - 100): 94, 94, 283 => grouped qty 4 and qty 2.
    assert by_shape[("Drawer Front/Back", 548, 94)] == 4
    assert by_shape[("Drawer Front/Back", 548, 283)] == 2

    # Side heights include +5 uplift: 99, 99, 288 => grouped qty 4 and qty 2.
    assert by_shape[("Drawer Side", 490, 99)] == 4
    assert by_shape[("Drawer Side", 490, 288)] == 2


def _profile_params(*, top_j: bool = False, middle_c: bool = False, lower_c: bool = False, base_top_j: bool = False, tall_vertical: bool = False, full_length: bool = False, orientation: str = "length"):
    lookup = {}
    params = {}
    if top_j:
        params["top_j_channel_handle_id"] = "handle-j"
        lookup["handle-j"] = {"id": "handle-j", "name": "J Rail", "handle_type": "j_channel", "front_reduction_mm": 24}
    if middle_c:
        params["middle_c_channel_handle_id"] = "handle-c"
        lookup["handle-c"] = {"id": "handle-c", "name": "C Rail", "handle_type": "c_channel", "front_reduction_mm": 30}
    if lower_c:
        params["between_lower_c_channel_handle_id"] = "handle-c"
        lookup["handle-c"] = {"id": "handle-c", "name": "C Rail", "handle_type": "c_channel", "front_reduction_mm": 30}
    if base_top_j:
        params["base_door_top_j_channel_handle_id"] = "handle-j"
        lookup["handle-j"] = {"id": "handle-j", "name": "J Rail", "handle_type": "j_channel", "front_reduction_mm": 24}
    if tall_vertical:
        params["tall_vertical_channel_handle_id"] = "handle-j"
        lookup["handle-j"] = {"id": "handle-j", "name": "J Rail", "handle_type": "j_channel", "front_reduction_mm": 40}
    if full_length:
        params["handle_id"] = "handle-profile"
        params["full_length_handle_orientation"] = orientation
        lookup["handle-profile"] = {"id": "handle-profile", "name": "Edge Pull", "handle_type": "full_length", "front_reduction_mm": 30}
    if lookup:
        params["_profile_handle_lookup"] = lookup
    return params


@pytest.mark.parametrize(
    "num_drawers, profile_params, expected_shapes",
    [
        pytest.param(1, _profile_params(top_j=True), {(753, 597): 1}, id="one-drawer-top-j"),
        pytest.param(2, _profile_params(top_j=True, middle_c=True), {(363, 597): 1, (357, 597): 1}, id="two-drawer-j-c"),
        pytest.param(3, _profile_params(top_j=True, lower_c=True), {(233, 597): 1, (257, 597): 1, (227, 597): 1}, id="three-drawer-j-c"),
    ],
)
def test_drawer_strategy_adjusts_front_heights_for_channel_profiles(num_drawers, profile_params, expected_shapes):
    slide = Slide(
        brand="Grass",
        model="Dynapro",
        code="D500",
        length=500,
        side_length=490,
        side_clearance_total=10,
    )
    unit = DrawerUnit(
        h=780,
        w=600,
        d=580,
        slide=slide,
        num_drawers=num_drawers,
        drawer_face_ratios=[1, 1, 1],
        profile_handles=profile_params,
        thickness=16,
    )

    panels = CuttingEngine.calculate_panels(unit)

    assert _board_map(panels) == {("Drawer Front", length, width): qty for (length, width), qty in expected_shapes.items()}


def test_base_door_strategy_supports_top_j_channel_profile():
    unit = DoorUnit(
        h=780,
        w=900,
        d=580,
        num_doors=2,
        profile_handles=_profile_params(base_top_j=True),
        thickness=16,
    )

    door = CuttingEngine.calculate_panels(unit)[0]

    assert door.name == "Door"
    assert door.length == 753
    assert door.width == 447
    assert door.qty == 2


def test_tall_strategy_supports_vertical_channel_profiles():
    unit = TallUnit(
        h=2400,
        w=900,
        d=580,
        num_doors=2,
        profile_handles=_profile_params(tall_vertical=True),
        thickness=16,
    )

    door = CuttingEngine.calculate_panels(unit)[0]

    assert door.name == "Door"
    assert door.length == 2397
    assert door.width == 427
    assert door.qty == 2


@pytest.mark.parametrize(
    "orientation, expected_length, expected_width",
    [
        pytest.param("length", 777, 417, id="vertical-profile"),
        pytest.param("width", 747, 447, id="horizontal-profile"),
    ],
)
def test_door_strategy_supports_full_length_profile_orientation(orientation, expected_length, expected_width):
    unit = DoorUnit(
        h=780,
        w=900,
        d=580,
        num_doors=2,
        profile_handles=_profile_params(full_length=True, orientation=orientation),
        thickness=16,
    )

    door = CuttingEngine.calculate_panels(unit)[0]

    assert door.name == "Door"
    assert door.length == expected_length
    assert door.width == expected_width
    assert door.qty == 2


def test_tall_pantry_strategy_adds_mid_rail_and_double_door_qty():
    unit = TallUnit(
        h=2400,
        w=600,
        d=580,
        num_doors=2,
        num_shelves=6,
        is_pantry=True,
        thickness=16,
    )

    carcass = CuttingEngine.calculate_carcass(unit)
    panels = CuttingEngine.calculate_panels(unit)

    carcass_map = _board_map(carcass)
    assert carcass_map[("Mid-Rail", 600, 100)] == 1

    door = panels[0]
    assert door.name == "Door"
    assert door.qty == 4  # 2 doors x upper/lower rows
    assert door.length == int((2400 / 2) - 3)
