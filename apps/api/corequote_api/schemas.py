from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corequote_api.authorization import Role


UnitType = str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class DatabaseHealthResponse(HealthResponse):
    database: str


class AuthRegisterRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "company_name": "Core Cabinets",
                    "name": "Dylan Payne",
                    "email": "dylan@example.com",
                    "password": "correct-horse-battery-staple",
                }
            ]
        },
    )

    company_name: str = Field(
        min_length=2,
        max_length=120,
        description="Company tenant to create. All future quotes, boards, extras, and pricing data are scoped to this company.",
    )
    name: str = Field(
        min_length=2,
        max_length=120,
        description="Display name for the first company owner user.",
    )
    email: str = Field(
        min_length=3,
        max_length=320,
        description="Globally unique login email. The API stores it normalized to lowercase.",
    )
    password: str = Field(
        min_length=12,
        max_length=256,
        description="Plain-text password sent only over HTTPS. The API stores a PBKDF2-SHA256 hash.",
    )


class AuthLoginRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "email": "dylan@example.com",
                    "password": "correct-horse-battery-staple",
                }
            ]
        },
    )

    email: str = Field(
        min_length=3,
        max_length=320,
        description="Login email. Matching is case-insensitive.",
    )
    password: str = Field(
        min_length=1,
        max_length=256,
        description="Plain-text password sent only over HTTPS.",
    )


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="User UUID.")
    company_id: str = Field(description="Company UUID used to scope tenant-owned API data.")
    company_name: str = Field(description="Company display name.")
    name: str = Field(description="User display name.")
    email: str = Field(description="Normalized login email.")
    role: Role = Field(description="Company-level role.")


class AuthTokenResponse(BaseModel):
    access_token: str = Field(description="Opaque bearer token. Store client-side and send in the Authorization header.")
    token_type: Literal["bearer"] = Field(default="bearer", description="Always `bearer`.")
    expires_at: datetime = Field(description="UTC timestamp when the bearer session expires.")
    user: AuthUserResponse = Field(description="Authenticated user and company context.")


class AuthLogoutResponse(BaseModel):
    status: Literal["ok"]


class CompanyCreateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"name": "Core Cabinets"}]},
    )

    name: str = Field(min_length=2, max_length=120, description="Company display name.")


class CompanyUpdateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"name": "Core Cabinets Ltd"}]},
    )

    name: str = Field(min_length=2, max_length=120, description="Updated company display name.")


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Company UUID.")
    name: str = Field(description="Company display name.")
    slug: str = Field(description="URL-safe company slug.")
    created_at: datetime = Field(description="UTC timestamp when the company was created.")
    updated_at: datetime = Field(description="UTC timestamp when the company was last updated.")


class UnitDefaultsDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height: int = Field(gt=0)
    depth: int = Field(gt=0)


class ProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    client: str = Field(default="", max_length=160)
    address: str = Field(default="", max_length=320)
    description: str = Field(default="", max_length=2000)


class ProjectResponse(ProjectRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    quote_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    notes: str = Field(default="", max_length=4000)
    default_carcass_board_type_id: str | None = None
    default_door_board_type_id: str | None = None
    default_panel_board_type_id: str | None = None
    default_slide_id: str | None = None
    default_hinge_id: str | None = None
    default_base_handle_id: str | None = None
    default_wall_handle_id: str | None = None
    default_tall_handle_id: str | None = None
    default_drawer_handle_id: str | None = None
    unit_defaults: dict[str, UnitDefaultsDimensions] = Field(default_factory=dict)


class QuoteResponse(QuoteRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    project_id: str
    unit_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class QuoteUnitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_type_key: str = Field(min_length=1, max_length=120)
    height: int = Field(gt=0)
    width: int = Field(gt=0)
    depth: int = Field(gt=0)
    thickness: int = Field(default=16, gt=0)
    carcass_board_type_id: str | None = None
    door_board_type_id: str | None = None
    extra_params: dict[str, Any] = Field(default_factory=dict)


class QuoteUnitResponse(QuoteUnitRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    quote_id: str
    unit_number: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class CutlistUnitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_number: int = Field(ge=1)
    unit_type: UnitType = Field(min_length=1, max_length=120)
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


class CutlistRuntimeRowResponse(CutlistRowResponse):
    section: Literal["carcass", "panel", "hardware", "extra_panel"]
    edge_long_1: bool = False
    edge_long_2: bool = False
    edge_short_1: bool = False
    edge_short_2: bool = False


class CutlistUnitSourceResponse(BaseModel):
    unit_number: int
    unit_type_key: str
    source: Literal["ruleset", "legacy"]
    ruleset_id: str | None = None
    unit_config_id: str | None = None
    note: str | None = None


class CutlistPreviewResponse(BaseModel):
    carcass: list[CutlistRowResponse]
    panels: list[CutlistRowResponse]
    hardware: list[CutlistRowResponse] = Field(default_factory=list)
    extras: list[CutlistRowResponse] = Field(default_factory=list)
    runtime_rows: list[CutlistRuntimeRowResponse] = Field(default_factory=list)
    runtime_mode: Literal["legacy", "ruleset", "mixed"] = "legacy"
    unit_sources: list[CutlistUnitSourceResponse] = Field(default_factory=list)


UnitConfigCategory = Literal["base", "wall", "tall", "custom"]
UnitConfigVariantType = Literal["drawer", "door", "wall", "tall", "custom"]
CuttingConfigStatus = Literal["draft", "active", "archived"]
CuttingRuleSection = Literal["carcass", "panel", "hardware", "extra_panel"]
GrainDirection = Literal["none", "length", "width"]


class UnitConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str | None
    unit_type_key: str
    label: str
    category: UnitConfigCategory
    variant_type: UnitConfigVariantType
    version: int
    status: CuttingConfigStatus
    is_default: bool
    variant_config: dict[str, Any]
    default_height: int
    default_width: int
    default_depth: int
    height_min: int
    height_max: int
    width_min: int
    width_max: int
    depth_min: int
    depth_max: int
    created_at: datetime
    updated_at: datetime


class UnitConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_type_key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    category: UnitConfigCategory = "custom"
    variant_type: UnitConfigVariantType = "custom"
    version: int = Field(default=1, gt=0)
    status: CuttingConfigStatus = "active"
    is_default: bool = False
    variant_config: dict[str, Any] = Field(default_factory=dict)
    default_height: int = Field(gt=0)
    default_width: int = Field(gt=0)
    default_depth: int = Field(gt=0)
    height_min: int = Field(gt=0)
    height_max: int = Field(gt=0)
    width_min: int = Field(gt=0)
    width_max: int = Field(gt=0)
    depth_min: int = Field(gt=0)
    depth_max: int = Field(gt=0)


class CuttingRuleRowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort_order: int = Field(gt=0)
    section: CuttingRuleSection
    description: str = Field(min_length=1, max_length=160)
    length_formula: str = Field(default="", max_length=500)
    width_formula: str = Field(default="", max_length=500)
    qty_formula: str = Field(default="1", min_length=1, max_length=500)
    condition_formula: str = Field(default="", max_length=500)
    grain_direction: GrainDirection = "none"
    can_rotate: bool = True
    edge_long_1: bool = False
    edge_long_2: bool = False
    edge_short_1: bool = False
    edge_short_2: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class CuttingRuleRowResponse(CuttingRuleRowRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class CuttingRulesetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_config_id: str | None = None
    unit_type_key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    status: CuttingConfigStatus = "draft"
    version: int = Field(default=1, gt=0)
    is_default: bool = False
    rows: list[CuttingRuleRowRequest] = Field(min_length=1)


class CuttingRulesetSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str | None
    unit_config_id: str | None
    unit_type_key: str
    name: str
    description: str
    status: CuttingConfigStatus
    version: int
    is_default: bool
    created_at: datetime
    updated_at: datetime


class CuttingRulesetResponse(CuttingRulesetSummaryResponse):
    rows: list[CuttingRuleRowResponse]


class BoardTypeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand: str = Field(min_length=1, max_length=120)
    material: str = Field(min_length=1, max_length=120)
    thickness: int = Field(gt=0)
    length_mm: int = Field(gt=0)
    width_mm: int = Field(gt=0)
    costing_mode: Literal["sheet", "sqm"] = "sheet"


class BoardTypeResponse(BoardTypeRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class SlideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    code: str = Field(default="", max_length=120)
    length: int = Field(ge=0)
    side_length: int = Field(ge=0)
    side_clearance_total: int = Field(ge=0)
    side_height_uplift: int = Field(default=0, ge=0)


class SlideResponse(SlideRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class HingeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    code: str = Field(default="", max_length=120)
    opening_angle_deg: int = Field(ge=0)


class HingeResponse(HingeRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class HandleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    supplier: str = Field(default="", max_length=120)
    code: str = Field(default="", max_length=120)


class HandleResponse(HandleRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ExtraCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)


class ExtraCategoryResponse(ExtraCategoryRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ExtraRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    category_id: str = Field(description="Extra category UUID in the current company.")
    supplier: str = Field(default="", max_length=120)
    code: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=1000)


class ExtraResponse(ExtraRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category_name: str
    created_at: datetime
    updated_at: datetime


class PriceListRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    status: Literal["draft", "active", "archived"] = "draft"
    effective_from: date | None = None
    effective_to: date | None = None


class PriceListResponse(PriceListRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class PricingSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vat_rate_bps: int = Field(default=1500, ge=0)
    default_markup_bps: int = Field(default=2500, ge=0)


class PricingSettingsResponse(PricingSettingsRequest):
    model_config = ConfigDict(from_attributes=True)

    company_id: str
    created_at: datetime
    updated_at: datetime


class PriceListItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: Literal["board", "slide", "hinge", "handle", "extra"]
    item_ref_id: str | None = Field(default=None, description="Optional UUID of the library item this price applies to.")
    item_key: str | None = Field(
        default=None,
        max_length=240,
        description="Optional stable item identity key, without the price component. If item_ref_id is provided the API derives this automatically.",
    )
    price_component: str = Field(default="unit", min_length=1, max_length=80)
    uom: str = Field(min_length=1, max_length=40)
    unit_price_cents: int = Field(ge=0)
    effective_from: datetime | None = Field(
        default=None,
        description="Optional UTC timestamp for when this price becomes active. Defaults to now.",
    )


class PriceListItemResponse(PriceListItemRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    price_list_id: str
    item_key: str
    effective_from: datetime
    effective_to: datetime | None
    replaces_id: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
