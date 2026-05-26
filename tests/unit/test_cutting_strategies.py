from corequote_core.cutting.engine import CuttingEngine
from corequote_core.models import Slide
from corequote_core.units.types import DrawerUnit, TallUnit


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
