"""
units/base.py
────────────────────────────────────────────────────────────────────────────────
Abstract base class for all cabinet units.

Every concrete unit (DrawerUnit, DoorUnit, WallUnit, TallUnit) inherits from
CabinetUnit.  The class intentionally holds *only* dimensional state — all
cutting calculations live in the cutting engine (cutting/engine.py).

Design notes
────────────
- `get_carcass_list()` is kept here as a convenience shim so that the existing
  Calculator page and cutlist builder continue to work unchanged.  Internally
  it delegates to the CuttingEngine, keeping the unit class thin.
- Subclasses should NOT override `get_carcass_list()` directly; instead they
  should ensure a matching CuttingStrategy is registered in the engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from logic.models import Board

if TYPE_CHECKING:
    # Avoid circular import at runtime; only used for type hints.
    from logic.units.definitions import UnitConfig


class CabinetUnit(ABC):
    """
    Abstract base for all cabinet unit types.

    Attributes:
        h (int):         Overall height in mm.
        w (int):         Overall width in mm.
        d (int):         Overall depth in mm.
        t (int):         Board/panel thickness in mm (default 16).
        config (UnitConfig | None):
                         The UnitConfig that describes this variant.
                         Set automatically by concrete subclasses.
    """

    def __init__(
        self,
        h: int,
        w: int,
        d: int,
        thickness: int = 16,
    ) -> None:
        self.h = h
        self.w = w
        self.d = d
        self.t = thickness

    # ── Abstract interface ─────────────────────────────────────────────────────

    @property
    @abstractmethod
    def unit_type_key(self) -> str:
        """
        The string key that identifies this unit in UNIT_REGISTRY and the DB.
        Must match the key used in UNIT_REGISTRY (e.g. "Draw Unit", "Door Unit").
        """

    # ── Convenience shim (delegates to CuttingEngine) ─────────────────────────

    def get_carcass_list(self) -> list[Board]:
        """
        Return the list of carcass Board objects for this unit.

        Delegates to the CuttingEngine so that all dimension logic stays in
        one place.  Existing call-sites (Calculator page, cutlist builder)
        continue to work without modification.
        """
        # Import here to avoid a circular dependency at module load time.
        from logic.cutting.engine import CuttingEngine
        return CuttingEngine.calculate_carcass(self)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"h={self.h}, w={self.w}, d={self.d}, t={self.t})"
        )
