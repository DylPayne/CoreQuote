"""
units/types.py
────────────────────────────────────────────────────────────────────────────────
Concrete cabinet unit classes.

Each class is intentionally thin — it stores only the extra state that the
cutting engine needs beyond the base h/w/d/t dimensions.  All panel and
carcass calculations live in cutting/strategies.py.

HOW TO ADD A NEW UNIT TYPE
──────────────────────────
1. Subclass CabinetUnit.
2. Set `unit_type_key` to match the key in UNIT_REGISTRY.
3. Store any extra state the cutting strategy will need (e.g. slide, num_drawers).
4. Register a CuttingStrategy in cutting/strategies.py.
"""

from __future__ import annotations

from corequote_core.models import Board, Slide
from corequote_core.units.base import CabinetUnit
from typing import Any, Mapping, Sequence


# ── Base Units ─────────────────────────────────────────────────────────────────

class DrawerUnit(CabinetUnit):
    """
    A base unit fitted entirely with drawers.

    Extra state beyond h/w/d/t:
        num_drawers (int):  Number of drawer boxes (1–4).
        slide (Slide):      The drawer slide hardware being used.
                            Required for depth validation and drawer-box sizing.
    """

    def __init__(
        self,
        h: int,
        w: int,
        d: int,
        slide: Slide,
        num_drawers: int = 3,
        drawer_face_ratios: Sequence[float] | None = None,
        drawer_face_heights: Sequence[int] | None = None,
        profile_handles: Mapping[str, Any] | None = None,
        thickness: int = 16,
    ) -> None:
        super().__init__(h, w, d, thickness)
        self.num_drawers = num_drawers
        self.slide = slide
        self.drawer_face_ratios = list(drawer_face_ratios) if drawer_face_ratios is not None else None
        self.drawer_face_heights = [int(v) for v in drawer_face_heights] if drawer_face_heights is not None else None
        self.profile_handles = dict(profile_handles or {})

    @property
    def unit_type_key(self) -> str:
        return "Base 3 Draw"

    # ── Validation ─────────────────────────────────────────────────────────────

    def validate_slide(self) -> tuple[bool, str]:
        """
        Check that the selected slide fits within the cabinet depth.

        Returns:
            (True, "")                  — slide is valid.
            (False, "<reason string>")  — slide is too long.
        """
        available_depth = self.d - self.t
        if self.slide.length > available_depth:
            return (
                False,
                f"Slide length ({self.slide.length} mm) exceeds available "
                f"cabinet depth ({available_depth} mm).",
            )
        return True, ""


class DoorUnit(CabinetUnit):
    """
    A base unit fitted with hinged doors and optional fixed shelves.

    Extra state beyond h/w/d/t:
        num_doors (int):    Number of doors (1–2).
        num_shelves (int):  Number of fixed shelves inside the carcass.
    """

    def __init__(
        self,
        h: int,
        w: int,
        d: int,
        num_doors: int = 2,
        num_shelves: int = 1,
        profile_handles: Mapping[str, Any] | None = None,
        thickness: int = 16,
    ) -> None:
        super().__init__(h, w, d, thickness)
        self.num_doors = num_doors
        self.num_shelves = num_shelves
        self.profile_handles = dict(profile_handles or {})

    @property
    def unit_type_key(self) -> str:
        return "Base 2 Door"


# ── Wall Units ─────────────────────────────────────────────────────────────────

class WallUnit(CabinetUnit):
    """
    A wall-hung unit with hinged doors and optional shelves.

    Structurally identical to DoorUnit but shallower by convention and
    uses a different cutting strategy (no toe-kick, different rail placement).

    Extra state beyond h/w/d/t:
        num_doors (int):    Number of doors (1–2).
        num_shelves (int):  Number of fixed shelves.
    """

    def __init__(
        self,
        h: int,
        w: int,
        d: int,
        num_doors: int = 2,
        num_shelves: int = 1,
        profile_handles: Mapping[str, Any] | None = None,
        thickness: int = 16,
    ) -> None:
        super().__init__(h, w, d, thickness)
        self.num_doors = num_doors
        self.num_shelves = num_shelves
        self.profile_handles = dict(profile_handles or {})

    @property
    def unit_type_key(self) -> str:
        return "Wall 2 Door"


# ── Tall Units ─────────────────────────────────────────────────────────────────

class TallUnit(CabinetUnit):
    """
    A floor-to-ceiling tall or pantry unit.

    Extra state beyond h/w/d/t:
        num_doors (int):    Number of doors (typically 2).
        num_shelves (int):  Number of fixed shelves.
        is_pantry (bool):   True → pantry variant (extra mid-rail, more shelves).
    """

    def __init__(
        self,
        h: int,
        w: int,
        d: int,
        num_doors: int = 2,
        num_shelves: int = 4,
        is_pantry: bool = False,
        profile_handles: Mapping[str, Any] | None = None,
        thickness: int = 16,
    ) -> None:
        super().__init__(h, w, d, thickness)
        self.num_doors = num_doors
        self.num_shelves = num_shelves
        self.is_pantry = is_pantry
        self.profile_handles = dict(profile_handles or {})

    @property
    def unit_type_key(self) -> str:
        return "Tall Pantry" if self.is_pantry else "Tall Standard"
