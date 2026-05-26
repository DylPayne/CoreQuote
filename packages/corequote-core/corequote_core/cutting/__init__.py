"""
cutting/__init__.py
Re-exports the public API for the cutting engine package.
"""

from corequote_core.cutting.engine import CuttingEngine
from corequote_core.cutting.strategies import (
    CuttingStrategy,
    DrawerUnitStrategy,
    DoorUnitStrategy,
    WallUnitStrategy,
    TallUnitStrategy,
)
from corequote_core.cutting.validators import (
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
