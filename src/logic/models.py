from dataclasses import dataclass, field
from typing import List

@dataclass
class Board:
    name: str
    length: int
    width: int
    qty: int

@dataclass
class Slide:
    brand: str
    model: str
    code: str
    length: int
    side_length: int
    side_clearance_total: int
