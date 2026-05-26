"""
logic.py
────────────────────────────────────────────────────────────────────────────────
Legacy panel-calculation helpers.

These functions are kept for backward compatibility with the Calculator page
(_Calculator.py) which calls them directly.  They now delegate to the
CuttingEngine so the formulas live in exactly one place.

New code should use CuttingEngine.calculate_panels(unit) directly.
"""

from __future__ import annotations

from corequote_core.models import Slide
from corequote_core.units.types import DrawerUnit, DoorUnit
from corequote_core.cutting.engine import CuttingEngine


def get_door_panel_list(height: int, width: int, num_doors: int) -> list[dict]:
    """
    Calculate door panel dimensions for a door unit.

    Delegates to DoorUnitStrategy via the CuttingEngine.

    Args:
        height:    Cabinet height in mm.
        width:     Cabinet width in mm.
        num_doors: Number of doors (1 or 2).

    Returns:
        List of dicts with keys "L", "W", "Qty".
    """
    # Build a minimal DoorUnit so the engine can dispatch correctly.
    unit   = DoorUnit(h=height, w=width, d=560, num_doors=num_doors, num_shelves=0)
    boards = CuttingEngine.calculate_panels(unit)
    return [{"L": b.length, "W": b.width, "Qty": b.qty} for b in boards]


def get_draw_panel_list(height: int, width: int, num_draws: int) -> list[dict]:
    """
    Calculate drawer-front panel dimensions for a drawer unit.

    Delegates to DrawerUnitStrategy via the CuttingEngine.

    Args:
        height:    Cabinet height in mm.
        width:     Cabinet width in mm.
        num_draws: Number of drawers (1–4).

    Returns:
        List of dicts with keys "L", "W", "Qty".
    """
    # Build a minimal DrawerUnit with a dummy slide (panels don't use slide data).
    dummy_slide = Slide(
        brand="", model="", code="",
        length=0, side_length=0, side_clearance_total=0,
    )
    unit   = DrawerUnit(h=height, w=width, d=560, slide=dummy_slide,
                        num_drawers=num_draws)
    boards = CuttingEngine.calculate_panels(unit)
    return [{"L": b.length, "W": b.width, "Qty": b.qty} for b in boards]
