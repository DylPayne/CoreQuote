"""
cutting/__init__.py
Re-exports the public API for the cutting engine package.
"""

from logic.cutting.engine import CuttingEngine
from logic.cutting.strategies import (
    CuttingStrategy,
    DrawerUnitStrategy,
    DoorUnitStrategy,
    WallUnitStrategy,
    TallUnitStrategy,
)
from logic.cutting.validators import (
    ValidationError,
    validate_dimensions,
    validate_slide_fit,
)

__all__ = [
    "CuttingEngine",
    "CuttingStrategy",
    "DrawerUnitStrategy",
    "DoorUnitStrategy",
    "WallUnitStrategy",
    "TallUnitStrategy",
    "ValidationError",
    "validate_dimensions",
    "validate_slide_fit",
]
