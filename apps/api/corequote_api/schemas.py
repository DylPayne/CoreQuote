from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


UnitType = Literal[
    "Base Drawer",
    "Base 1 Draw",
    "Base 2 Draw",
    "Base 3 Draw",
    "Base 4 Draw",
    "Base Door",
    "Base 1 Door",
    "Base 2 Door",
    "Wall Door",
    "Wall 1 Door",
    "Wall 2 Door",
    "Tall Standard",
    "Tall Pantry",
]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class DatabaseHealthResponse(HealthResponse):
    database: str


class CutlistUnitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_number: int = Field(ge=1)
    unit_type: UnitType
    height: int = Field(gt=0)
    width: int = Field(gt=0)
    depth: int = Field(gt=0)
    thickness: int = Field(default=16, gt=0)
    extra_params: dict[str, Any] = Field(default_factory=dict)


class CutlistPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    units: list[CutlistUnitRequest] = Field(min_length=1)


class CutlistRowResponse(BaseModel):
    unit_number: int
    desc: str
    length: int
    width: int
    qty: int


class CutlistPreviewResponse(BaseModel):
    carcass: list[CutlistRowResponse]
    panels: list[CutlistRowResponse]
