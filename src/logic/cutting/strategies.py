"""
cutting/strategies.py
────────────────────────────────────────────────────────────────────────────────
Strategy Pattern implementation for cutting-schedule calculations.

Each strategy class is responsible for ONE unit family.  It knows how to
translate a unit's h/w/d/t (and any extra state) into:
  • A list of carcass Board objects  (get_carcass_boards)
  • A list of panel Board objects    (get_panel_boards)

WHY A STRATEGY PER UNIT TYPE?
──────────────────────────────
- Changing a unit's dimensions automatically triggers a fresh calculation
  because strategies are stateless — they receive the unit object and compute
  on the fly.
- Adding a new unit type never requires touching existing strategies.
- Each strategy can be unit-tested in complete isolation.

HOW TO ADD A NEW STRATEGY
──────────────────────────
1. Subclass CuttingStrategy.
2. Implement `get_carcass_boards` and `get_panel_boards`.
3. Register it in CuttingEngine._STRATEGY_MAP (cutting/engine.py).

DIMENSION CONVENTIONS (all measurements in mm)
───────────────────────────────────────────────
  h  = overall cabinet height
  w  = overall cabinet width
  d  = overall cabinet depth
  t  = board/panel thickness (typically 16 mm)

  Internal width  = w  (sides sit inside top/bottom, not outside)
  Internal height = h - (2 × t)   (top and bottom panels consume height)
  Internal depth  = d - t          (backing panel consumes depth)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from logic.models import Board

if TYPE_CHECKING:
    from logic.units.base import CabinetUnit


# ── Abstract base strategy ─────────────────────────────────────────────────────

class CuttingStrategy(ABC):
    """
    Abstract base for all cutting strategies.

    Subclasses must implement:
        get_carcass_boards(unit) → list[Board]
        get_panel_boards(unit)   → list[Board]
    """

    @abstractmethod
    def get_carcass_boards(self, unit: "CabinetUnit") -> list[Board]:
        """Return all structural carcass boards for the given unit."""

    @abstractmethod
    def get_panel_boards(self, unit: "CabinetUnit") -> list[Board]:
        """Return all visible face panels (doors / drawer fronts) for the unit."""


# ── Shared carcass helper ──────────────────────────────────────────────────────

def _base_carcass(unit: "CabinetUnit") -> list[Board]:
    """
    Build the four boards that every floor-standing carcass shares:
      • 2 × Side panels
      • 1 × Base panel
      • 2 × Rails (top-front and top-back)
      • 1 × Backing panel

    Args:
        unit: Any CabinetUnit with h, w, d, t attributes.

    Returns:
        List of Board objects for the shared carcass components.

    Dimension derivations:
        side_height  = h - (2 × t)   — sits between top rail and base
        side_depth   = d - t          — backing panel sits in a rebate
        base_length  = w              — full width, sits on the floor
        base_depth   = d              — full depth
        rail_length  = w              — full width
        rail_width   = 100            — standard 100 mm rail height
        backing_h    = h - (2 × t)   — same as side height
        backing_w    = w              — full width
    """
    h, w, d, t = unit.h, unit.w, unit.d, unit.t

    side_height = h - (2 * t)
    side_depth  = d - t

    return [
        Board(name="Side",    length=side_height, width=side_depth, qty=2),
        Board(name="Base",    length=w,           width=d,          qty=1),
        Board(name="Rail",    length=w,           width=100,        qty=2),
        Board(name="Backing", length=side_height, width=w,          qty=1),
    ]


def _wall_carcass(unit: "CabinetUnit") -> list[Board]:
    """
    Build the carcass boards for a wall-hung unit.

    Wall units have a top panel instead of rails (no toe-kick, no base).

    Dimension derivations:
        side_height  = h - (2 × t)   — sits between top and bottom panels
        side_depth   = d - t          — backing rebate
        top/bottom   = w × d          — full width and depth
        backing_h    = h - (2 × t)
        backing_w    = w
    """
    h, w, d, t = unit.h, unit.w, unit.d, unit.t

    side_height = h - (2 * t)
    side_depth  = d - t

    return [
        Board(name="Side",    length=side_height, width=side_depth, qty=2),
        Board(name="Top",     length=w,           width=d,          qty=1),
        Board(name="Bottom",  length=w,           width=d,          qty=1),
        Board(name="Backing", length=side_height, width=w,          qty=1),
    ]


# ── Drawer Unit Strategy ───────────────────────────────────────────────────────

class DrawerUnitStrategy(CuttingStrategy):
    """
    Cutting schedule for a base unit fitted entirely with drawers.

    ┌─────────────────────────────────────────────────────────────────────┐
    │  3-DRAWER BASE UNIT — WORKED EXAMPLE                                │
    │  Inputs:  h=720, w=600, d=560, t=16, num_drawers=3                 │
    │  Slide:   Grass Dynapro 500 mm  (side_length=490, clearance=10)    │
    │                                                                     │
    │  CARCASS                                                            │
    │  ─────────────────────────────────────────────────────────────────  │
    │  Side        : (720 - 32) × (560 - 16) = 688 × 544 mm  qty 2      │
    │  Base        : 600 × 560 mm                              qty 1      │
    │  Rail        : 600 × 100 mm                              qty 2      │
    │  Backing     : 688 × 600 mm                              qty 1      │
    │                                                                     │
    │  DRAWER BOXES  (per drawer, qty = num_drawers)                      │
    │  ─────────────────────────────────────────────────────────────────  │
    │  drawer_depth = slide.side_length = 490 mm                         │
    │  drawer_width = w - slide.side_clearance_total = 600 - 10 = 590 mm │
    │  side_rebate  = 10 mm  (drawer base sits in a 10 mm rebate)        │
    │                                                                     │
    │  Drawer Side      : 490 × 200 mm  qty 6  (2 per drawer)            │
    │  Drawer Front/Back: 590 × 174 mm  qty 6  (2 per drawer)            │
    │  Drawer Base      : (590 + 10) × 490 = 600 × 490 mm  qty 3        │
    │                                                                     │
    │  PANELS (drawer fronts)                                             │
    │  ─────────────────────────────────────────────────────────────────  │
    │  panel_height = (720 / 3) - 3 = 237 mm                             │
    │  panel_width  = 600 - 3 = 597 mm                                   │
    │  Drawer Front : 237 × 597 mm  qty 3                                 │
    └─────────────────────────────────────────────────────────────────────┘
    """

    def get_carcass_boards(self, unit: "CabinetUnit") -> list[Board]:
        """
        Return carcass + drawer-box boards for a DrawerUnit.

        Drawer-box dimensions are derived from the slide specification:
          - drawer_depth  = slide.side_length
                            (the actual running length of the drawer box)
          - drawer_width  = cabinet_width - slide.side_clearance_total
                            (internal box width after accounting for slide bodies)
          - side_rebate   = 10 mm
                            (the drawer base sits in a 10 mm groove in the sides)
          - drawer_base_w = drawer_width + side_rebate
                            (base is wider than the box interior to fill the groove)
          - drawer_side_h = 200 mm (standard Grass/Blum box height)
          - drawer_front_back_h = 174 mm (box height minus top/bottom material)
        """
        boards = _base_carcass(unit)

        slide        = unit.slide                          # type: ignore[attr-defined]
        num_drawers  = unit.num_drawers                    # type: ignore[attr-defined]

        drawer_depth  = slide.side_length
        drawer_width  = unit.w - slide.side_clearance_total
        side_rebate   = 10   # mm — drawer base sits in a 10 mm groove

        drawer_side_h          = 200   # mm — standard box side height
        drawer_front_back_h    = 174   # mm — box height minus top/bottom material

        boards += [
            Board(
                name   = "Drawer Side",
                length = drawer_depth,
                width  = drawer_side_h,
                qty    = 2 * num_drawers,   # 2 sides per drawer
            ),
            Board(
                name   = "Drawer Front/Back",
                length = drawer_width,
                width  = drawer_front_back_h,
                qty    = 2 * num_drawers,   # front + back per drawer
            ),
            Board(
                name   = "Drawer Base",
                length = drawer_width + side_rebate,
                width  = drawer_depth,
                qty    = num_drawers,
            ),
        ]
        return boards

    def get_panel_boards(self, unit: "CabinetUnit") -> list[Board]:
        """
        Return the visible drawer-front panels.

        Each front is sized to fill its equal share of the cabinet height,
        minus a 3 mm gap between adjacent fronts.

        panel_height = (cabinet_height / num_drawers) - gap_mm
        panel_width  = cabinet_width - gap_mm
        """
        num_drawers = unit.num_drawers   # type: ignore[attr-defined]
        gap_mm      = 3

        panel_height = (unit.h / num_drawers) - gap_mm
        panel_width  = unit.w - gap_mm

        return [
            Board(
                name   = "Drawer Front",
                length = int(panel_height),
                width  = int(panel_width),
                qty    = num_drawers,
            )
        ]


# ── Door Unit Strategy ─────────────────────────────────────────────────────────

class DoorUnitStrategy(CuttingStrategy):
    """
    Cutting schedule for a base unit fitted with hinged doors.

    Shelf setback (20 mm) keeps shelves clear of the door hinge mechanism.
    """

    def get_carcass_boards(self, unit: "CabinetUnit") -> list[Board]:
        """
        Return carcass + shelf boards for a DoorUnit.

        shelf_depth = cabinet_depth - board_thickness - shelf_setback
                    = d - t - 20
        shelf_width = cabinet_width - (2 × board_thickness)
                    = w - (2 × t)   [sits between the two side panels]
        """
        boards = _base_carcass(unit)

        num_shelves  = unit.num_shelves   # type: ignore[attr-defined]
        shelf_setback = 20   # mm — clearance behind door hinge

        shelf_depth = unit.d - unit.t - shelf_setback
        shelf_width = unit.w - (2 * unit.t)

        if num_shelves > 0:
            boards.append(
                Board(
                    name   = "Shelf",
                    length = shelf_width,
                    width  = shelf_depth,
                    qty    = num_shelves,
                )
            )
        return boards

    def get_panel_boards(self, unit: "CabinetUnit") -> list[Board]:
        """
        Return the visible door panels.

        Each door fills its equal share of the cabinet width, minus a 3 mm gap.

        panel_width  = (cabinet_width / num_doors) - gap_mm
        panel_height = cabinet_height - gap_mm
        """
        num_doors = unit.num_doors   # type: ignore[attr-defined]
        gap_mm    = 3

        panel_width  = (unit.w / num_doors) - gap_mm
        panel_height = unit.h - gap_mm

        return [
            Board(
                name   = "Door",
                length = int(panel_height),
                width  = int(panel_width),
                qty    = num_doors,
            )
        ]


# ── Wall Unit Strategy ─────────────────────────────────────────────────────────

class WallUnitStrategy(CuttingStrategy):
    """
    Cutting schedule for a wall-hung unit.

    Uses a top+bottom panel carcass (no base/rail) and the same door-panel
    formula as DoorUnitStrategy.
    """

    def get_carcass_boards(self, unit: "CabinetUnit") -> list[Board]:
        boards = _wall_carcass(unit)

        num_shelves   = unit.num_shelves   # type: ignore[attr-defined]
        shelf_setback = 20

        shelf_depth = unit.d - unit.t - shelf_setback
        shelf_width = unit.w - (2 * unit.t)

        if num_shelves > 0:
            boards.append(
                Board(
                    name   = "Shelf",
                    length = shelf_width,
                    width  = shelf_depth,
                    qty    = num_shelves,
                )
            )
        return boards

    def get_panel_boards(self, unit: "CabinetUnit") -> list[Board]:
        num_doors = unit.num_doors   # type: ignore[attr-defined]
        gap_mm    = 3

        panel_width  = (unit.w / num_doors) - gap_mm
        panel_height = unit.h - gap_mm

        return [
            Board(
                name   = "Door",
                length = int(panel_height),
                width  = int(panel_width),
                qty    = num_doors,
            )
        ]


# ── Tall Unit Strategy ─────────────────────────────────────────────────────────

class TallUnitStrategy(CuttingStrategy):
    """
    Cutting schedule for a tall or pantry unit.

    Tall units share the same base carcass structure as floor-standing units
    but add a mid-rail for pantry variants and carry more shelves.

    Pantry variant adds:
        • 1 × Mid-Rail (same dimensions as a standard rail) to divide the
          carcass into upper and lower door zones.
    """

    def get_carcass_boards(self, unit: "CabinetUnit") -> list[Board]:
        boards = _base_carcass(unit)

        num_shelves   = unit.num_shelves   # type: ignore[attr-defined]
        is_pantry     = unit.is_pantry     # type: ignore[attr-defined]
        shelf_setback = 20

        shelf_depth = unit.d - unit.t - shelf_setback
        shelf_width = unit.w - (2 * unit.t)

        if num_shelves > 0:
            boards.append(
                Board(
                    name   = "Shelf",
                    length = shelf_width,
                    width  = shelf_depth,
                    qty    = num_shelves,
                )
            )

        # Pantry units get an extra horizontal mid-rail to split the door zone.
        if is_pantry:
            boards.append(
                Board(
                    name   = "Mid-Rail",
                    length = unit.w,
                    width  = 100,
                    qty    = 1,
                )
            )

        return boards

    def get_panel_boards(self, unit: "CabinetUnit") -> list[Board]:
        """
        Tall units typically have two doors stacked vertically.

        For a pantry (is_pantry=True) the doors are split at the mid-rail,
        so each door covers half the height.  For a standard tall unit the
        doors cover the full height split by width.
        """
        num_doors = unit.num_doors   # type: ignore[attr-defined]
        is_pantry = unit.is_pantry   # type: ignore[attr-defined]
        gap_mm    = 3

        if is_pantry:
            # Two rows of doors (upper + lower), each row has num_doors doors.
            panel_height = (unit.h / 2) - gap_mm
            panel_width  = (unit.w / num_doors) - gap_mm
            return [
                Board(
                    name   = "Door",
                    length = int(panel_height),
                    width  = int(panel_width),
                    qty    = num_doors * 2,   # upper + lower row
                )
            ]
        else:
            panel_height = unit.h - gap_mm
            panel_width  = (unit.w / num_doors) - gap_mm
            return [
                Board(
                    name   = "Door",
                    length = int(panel_height),
                    width  = int(panel_width),
                    qty    = num_doors,
                )
            ]
