"""
cutting/engine.py
────────────────────────────────────────────────────────────────────────────────
The CuttingEngine is the single entry-point for all cutting-schedule logic.

It acts as a Strategy Dispatcher:
  1. Receives a CabinetUnit.
  2. Looks up the correct CuttingStrategy from its internal registry.
  3. Delegates the calculation to that strategy.
  4. Returns the result.

The engine itself contains zero dimension maths — all formulas live in
strategies.py.  This means:
  • Adding a new unit type = adding one strategy + one registry entry.
  • Changing a formula = editing one strategy class, nothing else.
  • The engine never needs to be modified.

USAGE
─────
    from logic.cutting.engine import CuttingEngine

    boards = CuttingEngine.calculate_carcass(my_drawer_unit)
    panels = CuttingEngine.calculate_panels(my_door_unit)

    # Or get everything at once:
    result = CuttingEngine.calculate(my_unit)
    result.carcass_boards  # list[Board]
    result.panel_boards    # list[Board]

EXTENDING THE ENGINE
────────────────────
To support a new unit type (e.g. "Corner Unit"):
    1. Create CornerUnitStrategy in cutting/strategies.py.
    2. Add it to _STRATEGY_MAP below:
           "Corner Unit": CornerUnitStrategy(),
    3. Done — no other files need to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from logic.models import Board
from logic.cutting.strategies import (
    CuttingStrategy,
    DrawerUnitStrategy,
    DoorUnitStrategy,
    WallUnitStrategy,
    TallUnitStrategy,
)

if TYPE_CHECKING:
    from logic.units.base import CabinetUnit


# ── Result container ───────────────────────────────────────────────────────────

@dataclass
class CuttingResult:
    """
    Holds the full cutting schedule for a single cabinet unit.

    Attributes:
        carcass_boards: Structural boards (sides, base, rails, shelves, etc.)
        panel_boards:   Visible face panels (doors, drawer fronts).
    """
    carcass_boards: list[Board]
    panel_boards:   list[Board]


# ── Engine ─────────────────────────────────────────────────────────────────────

class CuttingEngine:
    """
    Stateless strategy dispatcher for cutting-schedule calculations.

    All methods are class-methods so the engine can be used without
    instantiation:  CuttingEngine.calculate(unit)
    """

    # ── Strategy registry ──────────────────────────────────────────────────────
    #
    # Maps unit_type_key → strategy instance.
    # Keys must match the `unit_type_key` property on each CabinetUnit subclass
    # AND the keys in UNIT_REGISTRY (units/definitions.py).
    #
    # Drawer variants all share DrawerUnitStrategy because the number of drawers
    # is stored on the unit object, not encoded in the strategy.
    # Same pattern applies to door/wall/tall variants.

    _STRATEGY_MAP: dict[str, CuttingStrategy] = {
        # Base — drawer units
        "Base 1 Draw": DrawerUnitStrategy(),
        "Base 2 Draw": DrawerUnitStrategy(),
        "Base 3 Draw": DrawerUnitStrategy(),
        "Base 4 Draw": DrawerUnitStrategy(),

        # Base — door units
        "Base 1 Door": DoorUnitStrategy(),
        "Base 2 Door": DoorUnitStrategy(),

        # Wall units
        "Wall 1 Door": WallUnitStrategy(),
        "Wall 2 Door": WallUnitStrategy(),

        # Tall units
        "Tall Standard": TallUnitStrategy(),
        "Tall Pantry":   TallUnitStrategy(),
    }

    # ── Public API ─────────────────────────────────────────────────────────────

    @classmethod
    def calculate(cls, unit: "CabinetUnit") -> CuttingResult:
        """
        Run the full cutting schedule for a unit.

        Args:
            unit: Any CabinetUnit subclass.

        Returns:
            CuttingResult with carcass_boards and panel_boards populated.

        Raises:
            KeyError: If no strategy is registered for the unit's type key.
        """
        strategy = cls._get_strategy(unit)
        return CuttingResult(
            carcass_boards = strategy.get_carcass_boards(unit),
            panel_boards   = strategy.get_panel_boards(unit),
        )

    @classmethod
    def calculate_carcass(cls, unit: "CabinetUnit") -> list[Board]:
        """
        Return only the carcass boards for a unit.

        This is the method called by CabinetUnit.get_carcass_list() so that
        existing code continues to work without modification.
        """
        return cls._get_strategy(unit).get_carcass_boards(unit)

    @classmethod
    def calculate_panels(cls, unit: "CabinetUnit") -> list[Board]:
        """
        Return only the panel boards (doors / drawer fronts) for a unit.
        """
        return cls._get_strategy(unit).get_panel_boards(unit)

    # ── Registration (for runtime extension / custom units) ───────────────────

    @classmethod
    def register_strategy(cls, unit_type_key: str, strategy: CuttingStrategy) -> None:
        """
        Register a new (or override an existing) cutting strategy at runtime.

        This is the extension point for future "Custom Units" — a custom
        strategy can be injected without modifying this file.

        Args:
            unit_type_key: The string key used in UNIT_REGISTRY and the DB.
            strategy:      An instance of a CuttingStrategy subclass.

        Example:
            class CornerUnitStrategy(CuttingStrategy):
                ...

            CuttingEngine.register_strategy("Corner Unit", CornerUnitStrategy())
        """
        cls._STRATEGY_MAP[unit_type_key] = strategy

    # ── Internal helpers ───────────────────────────────────────────────────────

    @classmethod
    def _get_strategy(cls, unit: "CabinetUnit") -> CuttingStrategy:
        """
        Look up the strategy for a unit, raising a clear error if missing.

        Args:
            unit: The cabinet unit whose strategy is needed.

        Returns:
            The registered CuttingStrategy instance.

        Raises:
            KeyError: With a helpful message listing all registered keys.
        """
        key = unit.unit_type_key
        strategy = cls._STRATEGY_MAP.get(key)
        if strategy is None:
            registered = ", ".join(f'"{k}"' for k in cls._STRATEGY_MAP)
            raise KeyError(
                f"No cutting strategy registered for unit type '{key}'.  "
                f"Registered types: [{registered}].  "
                f"Add a strategy in cutting/strategies.py and register it in "
                f"CuttingEngine._STRATEGY_MAP."
            )
        return strategy
