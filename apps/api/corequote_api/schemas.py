from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from corequote_api.authorization import Role


UnitType = str
LibrarySetupStatus = Literal["ready", "needs_attention"]
LibrarySetupItemStatus = Literal["complete", "missing", "warning", "action_needed"]
LibrarySetupActionTarget = Literal[
    "pricing",
    "boards",
    "slides",
    "hinges",
    "suppliers",
    "handles",
    "extra-categories",
    "extras",
    "projects",
]
LibraryImportResource = Literal[
    "boards",
    "slides",
    "hinges",
    "handles",
    "suppliers",
    "extra_categories",
    "extras",
    "supplier_item_costs",
    "price_list_items",
]
LibraryImportSourceFormat = Literal["csv", "tsv", "xlsx"]
LibraryImportRowStatus = Literal["create", "update", "skipped", "duplicate", "blocked"]
LibraryImportApplyRowStatus = Literal["created", "updated", "skipped", "failed"]
LibraryImportProblemSeverity = Literal["error", "warning"]
LibraryEffectiveStatus = Literal["current", "future", "retired"]
LibraryCatalogBulkResource = Literal["boards", "slides", "hinges", "handles", "extras", "suppliers"]
LibraryBulkRowStatus = Literal["preview", "updated", "failed"]
QuoteStatus = Literal["draft", "ready", "sent", "accepted", "rejected", "revised", "expired"]
QuoteReadinessStatus = Literal["ready", "needs_attention"]
QuoteReadinessSeverity = Literal["pass", "warning", "error"]
QuoteReadinessActionTarget = Literal[
    "project",
    "quote",
    "units",
    "panels",
    "cutting-lists",
    "production",
    "pricing",
    "outputs",
    "libraries-pricing",
]
QuoteOutputActionId = Literal[
    "client_quote_pdf",
    "workshop_schedule",
    "production_handoff_csv",
    "production_handoff_xlsx",
    "material_summary",
    "hardware_pick_list",
]
QuoteOutputGroup = Literal["client", "workshop"]
MaterialRole = Literal["carcass", "door_panel", "visible_panel"]
ProductionGrainDirection = Literal["none", "length", "width"]
ProductionRotationGuidance = Literal["none", "allow_rotation", "no_rotation"]
BoardGrainPolicy = Literal["none", "optional", "required"]
MaterialSummaryWarningCode = Literal["missing_board_selection", "missing_board_record", "missing_board_dimensions"]
ProductionBoardRequirementWarningCode = Literal[
    "missing_board_selection",
    "missing_board_record",
    "missing_board_dimensions",
    "invalid_part_dimensions",
    "incomplete_material_data",
]
HardwarePickListItemType = Literal["slide", "hinge", "handle", "extra"]
HardwarePickListWarningCode = Literal[
    "missing_slide_selection",
    "missing_hinge_selection",
    "missing_handle_selection",
    "missing_catalog_item",
]
HardwareAccessoryQuantityRule = Literal["fixed", "per_unit", "per_drawer", "per_slide_pair", "per_hinge", "per_door"]
HardwareAccessoryConditionField = Literal[
    "always",
    "drawer_front_height",
    "drawer_side_height",
    "unit_width",
    "unit_height",
    "unit_depth",
    "num_drawers",
    "door_count",
    "hinge_count",
    "hardware_variant",
    "load_class",
]
HardwareAccessoryConditionOperator = Literal[
    "always",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "equals",
    "not_equals",
]
DrawerSystemKind = Literal["conventional", "metal"]
DrawerSystemPanelSection = Literal["carcass", "panel", "extra_panel"]


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
    company_currency_code: str = Field(description="Company ISO 4217 currency code used for quote pricing display.")
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
        json_schema_extra={"examples": [{"name": "Core Cabinets Ltd", "currency_code": "USD"}]},
    )

    name: str | None = Field(default=None, min_length=2, max_length=120, description="Updated company display name.")
    currency_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        pattern="^[A-Z]{3}$",
        description="Updated ISO 4217 currency code. Only company owners may change this field.",
    )

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, value):
        if value is None:
            return None
        return str(value).strip().upper()


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Company UUID.")
    name: str = Field(description="Company display name.")
    slug: str = Field(description="URL-safe company slug.")
    currency_code: str = Field(description="ISO 4217 currency code used for quote pricing display.")
    created_at: datetime = Field(description="UTC timestamp when the company was created.")
    updated_at: datetime = Field(description="UTC timestamp when the company was last updated.")


class UnitDefaultsDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height: int = Field(gt=0)
    depth: int = Field(gt=0)


class ProductionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_banding: str = Field(default="", max_length=500)
    grain_direction: ProductionGrainDirection = "none"
    rotation: ProductionRotationGuidance = "none"
    notes: str = Field(default="", max_length=1000)


class ProductionMetadataByRole(BaseModel):
    model_config = ConfigDict(extra="forbid")

    carcass: ProductionMetadata = Field(default_factory=ProductionMetadata)
    door_panel: ProductionMetadata = Field(default_factory=ProductionMetadata)
    visible_panel: ProductionMetadata = Field(default_factory=ProductionMetadata)


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
    production_metadata: ProductionMetadataByRole = Field(default_factory=ProductionMetadataByRole)


class QuoteStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: QuoteStatus


class QuoteResponse(QuoteRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    project_id: str
    status: QuoteStatus = "draft"
    quote_number: str
    revision: int = Field(ge=1)
    previous_revision_id: str | None = None
    previous_revision_quote_number: str | None = None
    previous_revision_revision: int | None = Field(default=None, ge=1)
    unit_count: int = Field(default=0, ge=0)
    custom_panels: "QuoteCustomPanelsRequest" = Field(default_factory=lambda: QuoteCustomPanelsRequest())
    created_at: datetime
    updated_at: datetime


class QuoteUnitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_type_key: str = Field(min_length=1, max_length=120)
    height: int = Field(gt=0)
    width: int = Field(gt=0)
    depth: int = Field(gt=0)
    carcass_board_type_id: str | None = None
    door_board_type_id: str | None = None
    slide_id: str | None = None
    hinge_id: str | None = None
    extra_params: dict[str, Any] = Field(default_factory=dict)
    production_metadata: ProductionMetadataByRole = Field(default_factory=ProductionMetadataByRole)


class QuoteUnitResponse(QuoteUnitRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    quote_id: str
    unit_number: int = Field(ge=1)
    thickness: int = Field(gt=0)
    created_at: datetime
    updated_at: datetime


class QuoteUnitBulkRowRequest(QuoteUnitRequest):
    id: str | None = None


class QuoteUnitBulkSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    units: list[QuoteUnitBulkRowRequest] = Field(min_length=1)


class QuoteUnitBulkApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_ids: list[str] = Field(min_length=1)
    carcass_board_type_id: str | None = None
    door_board_type_id: str | None = None
    handle_id: str | None = None
    slide_id: str | None = None
    hinge_id: str | None = None
    height: int | None = Field(default=None, gt=0)
    depth: int | None = Field(default=None, gt=0)


class QuoteUnitReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_ids: list[str] = Field(min_length=1)


class QuoteExtraSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extra_id: str = Field(min_length=1, description="Extra library UUID in the current company.")
    quantity: int = Field(default=1, ge=1)


class QuoteExtrasRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[QuoteExtraSelectionRequest] = Field(default_factory=list)


class QuoteExtraSelectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    extra_id: str
    quantity: int = Field(ge=1)


class QuoteExtrasResponse(BaseModel):
    quote_id: str
    items: list[QuoteExtraSelectionResponse] = Field(default_factory=list)


QuoteCustomPanelPresetKey = Literal[
    "base_side_panel",
    "base_side_filler",
    "wall_side_panel",
    "wall_side_filler",
    "tall_side_panel",
    "tall_side_filler",
]


class QuoteCustomPanelPresetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qty: int = Field(default=0, ge=0)
    board_type_id: str | None = None
    production_metadata: ProductionMetadata = Field(default_factory=ProductionMetadata)


class QuoteCustomPanelManualRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Custom Panel", min_length=1, max_length=120)
    length: int = Field(default=0, ge=0)
    width: int = Field(default=0, ge=0)
    qty: int = Field(default=0, ge=0)
    board_type_id: str | None = None
    production_metadata: ProductionMetadata = Field(default_factory=ProductionMetadata)


class QuoteCustomPanelAutoConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kicker_board_type_id: str | None = None
    pelmet_board_type_id: str | None = None
    kicker_return_count: int = Field(default=0, ge=0)
    kicker_return_depth_mm: int = Field(default=0, ge=0)
    kicker_override_on: bool = False
    kicker_override_qty: int = Field(default=0, ge=0)
    kicker_override_length: int = Field(default=0, ge=0)
    kicker_override_width: int = Field(default=100, ge=0)
    pelmet_override_on: bool = False
    pelmet_override_qty: int = Field(default=0, ge=0)
    pelmet_override_length: int = Field(default=0, ge=0)
    pelmet_override_width: int = Field(default=330, ge=0)
    production_metadata: ProductionMetadata = Field(default_factory=ProductionMetadata)


class QuoteCustomPanelsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    presets: dict[QuoteCustomPanelPresetKey, QuoteCustomPanelPresetConfig] = Field(default_factory=dict)
    manual: list[QuoteCustomPanelManualRow] = Field(default_factory=list)
    auto: QuoteCustomPanelAutoConfig = Field(default_factory=QuoteCustomPanelAutoConfig)


class QuoteCustomPanelComputedRowResponse(BaseModel):
    desc: str
    length: int = Field(ge=0)
    width: int = Field(ge=0)
    qty: int = Field(ge=0)
    board_type_id: str | None = None
    production_metadata: ProductionMetadata = Field(default_factory=ProductionMetadata)


class QuoteCustomPanelsResponse(BaseModel):
    quote_id: str
    custom_panels: QuoteCustomPanelsRequest
    computed_rows: list[QuoteCustomPanelComputedRowResponse] = Field(default_factory=list)


class CutlistUnitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_number: int = Field(ge=1)
    unit_type: UnitType = Field(min_length=1, max_length=120)
    height: int = Field(gt=0)
    width: int = Field(gt=0)
    depth: int = Field(gt=0)
    board_type_id: str = Field(min_length=1)
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
    grain_direction: ProductionGrainDirection = "none"
    can_rotate: bool = True
    board_type_id: str | None = None


class CutlistValidationWarningResponse(BaseModel):
    severity: Literal["warning"] = "warning"
    source: Literal["unit", "quote_panel"]
    unit_number: int = Field(ge=0)
    section: Literal["carcass", "panel", "hardware", "extra_panel"]
    row_desc: str
    reason: str


class CutlistReadinessResponse(BaseModel):
    cutlist_valid: bool = True
    warning_count: int = Field(default=0, ge=0)


class CutlistUnitSourceResponse(BaseModel):
    unit_number: int
    unit_type_key: str
    source: Literal["ruleset", "legacy", "drawer_system"]
    ruleset_id: str | None = None
    unit_config_id: str | None = None
    note: str | None = None


class CutlistPreviewResponse(BaseModel):
    carcass: list[CutlistRowResponse]
    panels: list[CutlistRowResponse]
    hardware: list[CutlistRowResponse] = Field(default_factory=list)
    extras: list[CutlistRowResponse] = Field(default_factory=list)
    runtime_rows: list[CutlistRuntimeRowResponse] = Field(default_factory=list)
    runtime_mode: Literal["legacy", "ruleset", "drawer_system", "mixed"] = "legacy"
    unit_sources: list[CutlistUnitSourceResponse] = Field(default_factory=list)
    validation_warnings: list[CutlistValidationWarningResponse] = Field(default_factory=list)
    readiness: CutlistReadinessResponse = Field(default_factory=CutlistReadinessResponse)


class QuoteCuttingListResponse(CutlistPreviewResponse):
    quote_id: str


class QuoteReadinessCheckResponse(BaseModel):
    id: str
    severity: QuoteReadinessSeverity
    title: str
    message: str
    action_label: str
    action_target: QuoteReadinessActionTarget


class QuoteReadinessResponse(BaseModel):
    quote_id: str
    status: QuoteReadinessStatus
    is_ready: bool
    summary_title: str
    summary_message: str
    warning_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    checks: list[QuoteReadinessCheckResponse] = Field(default_factory=list)


class QuoteOutputStatusResponse(BaseModel):
    id: str
    label: str
    status: QuoteReadinessStatus
    severity: QuoteReadinessSeverity
    message: str


class QuoteOutputActionResponse(BaseModel):
    id: QuoteOutputActionId
    group: QuoteOutputGroup
    label: str
    description: str
    enabled: bool
    warning: str | None = None
    hides_internal_costs: bool = False
    action_target: QuoteReadinessActionTarget


class QuotePricingLineResponse(BaseModel):
    item_type: Literal[
        "board",
        "slide",
        "hinge",
        "handle",
        "extra",
        "labour",
        "consumable",
        "installation",
        "delivery",
        "adjustment",
    ]
    item_key: str
    price_component: str
    bucket: str = "other"
    description: str
    qty: float
    uom: str
    unit_price_cents: int | None = None
    unit_cost_cents: int | None = None
    cost_total_cents: int | None = None
    markup_bps: int = 0
    sell_total_cents: int | None = None
    line_total_cents: int | None = None
    profit_cents: int | None = None
    missing: bool = False


class PricingBucketTotalResponse(BaseModel):
    bucket: str
    cost_total_cents: int = 0
    sell_total_cents: int = 0
    profit_cents: int = 0


class MaterialSummaryWarningResponse(BaseModel):
    severity: Literal["warning"] = "warning"
    code: MaterialSummaryWarningCode
    material_role: MaterialRole
    role_label: str
    unit_number: int = Field(ge=0)
    row_desc: str
    board_type_id: str | None = None
    message: str


class MaterialSummaryGroupResponse(BaseModel):
    board_type_id: str
    material_role: MaterialRole
    role_label: str
    board_name: str
    brand: str
    material: str
    thickness: int | None = Field(default=None, ge=0)
    length_mm: int | None = Field(default=None, ge=0)
    width_mm: int | None = Field(default=None, ge=0)
    costing_mode: str = "sheet"
    piece_count: int = Field(default=0, ge=0)
    area_m2: float = Field(default=0, ge=0)
    edge_m: float = Field(default=0, ge=0)
    sheet_area_m2: float | None = Field(default=None, ge=0)
    estimated_sheets: int | None = Field(default=None, ge=0)
    price_component: str | None = None
    pricing_qty: float | None = Field(default=None, ge=0)
    pricing_uom: str | None = None
    cost_total_cents: int | None = Field(default=None, ge=0)
    sell_total_cents: int | None = Field(default=None, ge=0)
    missing_price: bool = False


class MaterialSummaryResponse(BaseModel):
    groups: list[MaterialSummaryGroupResponse] = Field(default_factory=list)
    warnings: list[MaterialSummaryWarningResponse] = Field(default_factory=list)
    total_area_m2: float = Field(default=0, ge=0)
    total_piece_count: int = Field(default=0, ge=0)
    total_edge_m: float = Field(default=0, ge=0)
    total_estimated_sheets: int | None = Field(default=None, ge=0)


class HardwarePickListItemResponse(BaseModel):
    item_type: HardwarePickListItemType
    type_label: str
    item_key: str
    item_ref_id: str
    item_name: str
    supplier: str = ""
    code: str = ""
    quantity: int = Field(ge=0)
    uom: str
    unit_numbers: list[int] = Field(default_factory=list)
    used_in: list[str] = Field(default_factory=list)
    usage_label: str = ""


class HardwarePickListWarningResponse(BaseModel):
    severity: Literal["warning"] = "warning"
    code: HardwarePickListWarningCode
    item_type: HardwarePickListItemType
    unit_number: int = Field(ge=0)
    item_ref_id: str | None = None
    message: str


class HardwarePickListResponse(BaseModel):
    items: list[HardwarePickListItemResponse] = Field(default_factory=list)
    optional_items: list[HardwarePickListItemResponse] = Field(default_factory=list)
    warnings: list[HardwarePickListWarningResponse] = Field(default_factory=list)
    total_item_count: int = Field(default=0, ge=0)
    total_quantity: int = Field(default=0, ge=0)


ProductionSourceType = Literal["unit", "quote_panel"]
ProductionSection = Literal["carcass", "panel", "extra_panel"]


class ProductionHandoffRowResponse(BaseModel):
    part_id: str
    project_id: str
    project_name: str
    quote_id: str
    quote_name: str
    quote_number: str
    revision: int = Field(ge=1)
    source_type: ProductionSourceType
    unit_number: int = Field(ge=0)
    unit_label: str
    unit_type_key: str = ""
    section: ProductionSection
    section_label: str
    material_role: MaterialRole
    role_label: str
    board_type_id: str | None = None
    board_name: str
    brand: str = ""
    material: str = ""
    thickness: int | None = Field(default=None, ge=0)
    sheet_length_mm: int | None = Field(default=None, ge=0)
    sheet_width_mm: int | None = Field(default=None, ge=0)
    desc: str
    length: int = Field(ge=0)
    width: int = Field(ge=0)
    quantity: int = Field(ge=0)
    edge_sides: list[str] = Field(default_factory=list)
    edge_sides_label: str = "None"
    edge_banding: str = ""
    grain_direction: ProductionGrainDirection = "none"
    grain_label: str = "Unspecified"
    can_rotate: bool = True
    rotation: ProductionRotationGuidance = "none"
    rotation_label: str = "Unspecified"
    production_notes: str = ""
    warning_count: int = Field(default=0, ge=0)
    warning_messages: list[str] = Field(default_factory=list)


class ProductionHandoffGroupResponse(BaseModel):
    group_key: str
    board_type_id: str | None = None
    board_name: str
    brand: str = ""
    material: str = ""
    thickness: int | None = Field(default=None, ge=0)
    sheet_length_mm: int | None = Field(default=None, ge=0)
    sheet_width_mm: int | None = Field(default=None, ge=0)
    material_role: MaterialRole
    role_label: str
    unit_number: int = Field(ge=0)
    unit_label: str
    section: ProductionSection
    section_label: str
    row_count: int = Field(default=0, ge=0)
    piece_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    production_warning_count: int = Field(default=0, ge=0)
    part_ids: list[str] = Field(default_factory=list)
    rows: list[ProductionHandoffRowResponse] = Field(default_factory=list)


class ProductionHandoffMaterialGroupResponse(BaseModel):
    board_type_id: str
    material_role: MaterialRole
    role_label: str
    board_name: str
    brand: str = ""
    material: str = ""
    thickness: int | None = Field(default=None, ge=0)
    length_mm: int | None = Field(default=None, ge=0)
    width_mm: int | None = Field(default=None, ge=0)
    piece_count: int = Field(default=0, ge=0)
    area_m2: float = Field(default=0, ge=0)
    edge_m: float = Field(default=0, ge=0)
    estimated_sheets: int | None = Field(default=None, ge=0)
    part_ids: list[str] = Field(default_factory=list)


class ProductionHandoffMaterialSummaryResponse(BaseModel):
    groups: list[ProductionHandoffMaterialGroupResponse] = Field(default_factory=list)
    warnings: list[MaterialSummaryWarningResponse] = Field(default_factory=list)
    total_area_m2: float = Field(default=0, ge=0)
    total_piece_count: int = Field(default=0, ge=0)
    total_edge_m: float = Field(default=0, ge=0)
    total_estimated_sheets: int | None = Field(default=None, ge=0)


class ProductionBoardRequirementWarningResponse(BaseModel):
    severity: Literal["warning"] = "warning"
    code: ProductionBoardRequirementWarningCode
    material_role: MaterialRole
    role_label: str
    unit_number: int = Field(ge=0)
    row_desc: str
    board_type_id: str | None = None
    part_id: str = ""
    message: str


class ProductionBoardRequirementGroupResponse(BaseModel):
    requirement_key: str
    board_type_id: str | None = None
    board_name: str
    brand: str = ""
    material: str = ""
    thickness: int | None = Field(default=None, ge=0)
    sheet_length_mm: int | None = Field(default=None, ge=0)
    sheet_width_mm: int | None = Field(default=None, ge=0)
    material_role: MaterialRole
    role_label: str
    row_count: int = Field(default=0, ge=0)
    piece_count: int = Field(default=0, ge=0)
    area_m2: float = Field(default=0, ge=0)
    edge_m: float = Field(default=0, ge=0)
    sheet_area_m2: float | None = Field(default=None, ge=0)
    estimated_sheets: int | None = Field(default=None, ge=0)
    estimated_sheet_area_m2: float | None = Field(default=None, ge=0)
    waste_area_m2: float | None = Field(default=None, ge=0)
    waste_percent: float | None = Field(default=None, ge=0)
    sheet_estimate_label: str
    waste_allowance_label: str
    part_ids: list[str] = Field(default_factory=list)
    source_labels: list[str] = Field(default_factory=list)
    warning_count: int = Field(default=0, ge=0)
    warning_messages: list[str] = Field(default_factory=list)


class ProductionBoardRequirementsResponse(BaseModel):
    estimate_label: str = "Sheet counts are estimates only; CoreQuote has not optimized board nesting."
    groups: list[ProductionBoardRequirementGroupResponse] = Field(default_factory=list)
    warnings: list[ProductionBoardRequirementWarningResponse] = Field(default_factory=list)
    total_area_m2: float = Field(default=0, ge=0)
    total_piece_count: int = Field(default=0, ge=0)
    total_edge_m: float = Field(default=0, ge=0)
    total_estimated_sheets: int | None = Field(default=None, ge=0)
    total_estimated_sheet_area_m2: float | None = Field(default=None, ge=0)
    total_waste_area_m2: float | None = Field(default=None, ge=0)
    warning_count: int = Field(default=0, ge=0)


class ProductionHandoffHardwareItemResponse(BaseModel):
    part_id: str
    item_type: HardwarePickListItemType
    type_label: str
    item_key: str
    item_ref_id: str
    item_name: str
    supplier: str = ""
    code: str = ""
    quantity: int = Field(ge=0)
    uom: str
    unit_numbers: list[int] = Field(default_factory=list)
    used_in: list[str] = Field(default_factory=list)
    usage_label: str = ""
    related_part_ids: list[str] = Field(default_factory=list)


class ProductionHandoffHardwarePickListResponse(BaseModel):
    items: list[ProductionHandoffHardwareItemResponse] = Field(default_factory=list)
    optional_items: list[HardwarePickListItemResponse] = Field(default_factory=list)
    warnings: list[HardwarePickListWarningResponse] = Field(default_factory=list)
    total_item_count: int = Field(default=0, ge=0)
    total_quantity: int = Field(default=0, ge=0)


class ProductionHandoffLabelResponse(BaseModel):
    part_id: str
    label: str
    source_type: ProductionSourceType
    unit_number: int = Field(ge=0)
    unit_label: str
    section: ProductionSection
    desc: str
    dimensions_label: str
    material_label: str
    quantity: int = Field(ge=0)
    warning_count: int = Field(default=0, ge=0)
    edge_sides_label: str = "None"
    grain_label: str = "Unspecified"
    rotation_label: str = "Unspecified"


class QuoteProductionHandoffResponse(BaseModel):
    quote_id: str
    quote_name: str
    quote_status: QuoteStatus = "draft"
    quote_number: str
    revision: int = Field(ge=1)
    project_id: str
    project_name: str
    row_count: int = Field(default=0, ge=0)
    group_count: int = Field(default=0, ge=0)
    label_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    groups: list[ProductionHandoffGroupResponse] = Field(default_factory=list)
    rows: list[ProductionHandoffRowResponse] = Field(default_factory=list)
    material_summary: ProductionHandoffMaterialSummaryResponse = Field(default_factory=ProductionHandoffMaterialSummaryResponse)
    board_requirements: ProductionBoardRequirementsResponse = Field(default_factory=ProductionBoardRequirementsResponse)
    hardware_pick_list: ProductionHandoffHardwarePickListResponse = Field(default_factory=ProductionHandoffHardwarePickListResponse)
    labels: list[ProductionHandoffLabelResponse] = Field(default_factory=list)


class QuoteOutputReviewResponse(BaseModel):
    quote_id: str
    quote_name: str
    project_id: str
    project_name: str
    quote_status: QuoteStatus = "draft"
    quote_number: str
    revision: int = Field(ge=1)
    currency_code: str = Field(description="Company ISO 4217 currency code used to display customer totals.")
    client_quote_total_cents: int = Field(default=0, ge=0)
    pricing_missing_price_count: int = Field(default=0, ge=0)
    cutlist_row_count: int = Field(default=0, ge=0)
    cutlist_warning_count: int = Field(default=0, ge=0)
    material_warning_count: int = Field(default=0, ge=0)
    hardware_warning_count: int = Field(default=0, ge=0)
    readiness: QuoteReadinessResponse
    client_quote: QuoteOutputStatusResponse
    internal_pricing: QuoteOutputStatusResponse
    workshop_schedule: QuoteOutputStatusResponse
    material_status: QuoteOutputStatusResponse
    hardware_status: QuoteOutputStatusResponse
    material_summary: MaterialSummaryResponse = Field(default_factory=MaterialSummaryResponse)
    hardware_pick_list: HardwarePickListResponse = Field(default_factory=HardwarePickListResponse)
    actions: list[QuoteOutputActionResponse] = Field(default_factory=list)


class MissingPriceResponse(BaseModel):
    item_type: Literal[
        "board",
        "slide",
        "hinge",
        "handle",
        "extra",
        "labour",
        "consumable",
        "installation",
        "delivery",
        "adjustment",
    ]
    item_type_label: str
    item_key: str
    item_ref_id: str
    price_component: str
    component: str
    bucket: str = "other"
    item_name: str
    uom: str
    quantity: float
    used_in: list[str] = Field(default_factory=list)
    usage_label: str
    affected_quote_id: str
    affected_quote_name: str
    library_area: str = "pricing"
    action_label: str
    message: str
    library_target: str = "pricing"
    library_target_label: str = "Pricing"
    catalog_target: str | None = None
    catalog_target_label: str | None = None
    guidance_action_label: str = "Open Pricing"
    guidance_message: str = ""


class LibrarySetupChecklistItemResponse(BaseModel):
    id: str
    label: str
    status: LibrarySetupItemStatus
    count: int = Field(default=0, ge=0)
    message: str
    action_label: str
    action_target: LibrarySetupActionTarget


class LibrarySetupChecklistResponse(BaseModel):
    status: LibrarySetupStatus
    summary_title: str
    summary_message: str
    complete_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    items: list[LibrarySetupChecklistItemResponse] = Field(default_factory=list)


class LibraryImportPreviewRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "resource": "boards",
                    "source_format": "csv",
                    "filename": "boards.csv",
                    "content": "Brand,Material,Thickness,Length,Width\\nPG Bison,MelaWood,16,2750,1830\\n",
                    "column_mapping": {"thickness": "Thickness"},
                }
            ]
        },
    )

    resource: LibraryImportResource
    source_format: LibraryImportSourceFormat = "csv"
    filename: str = Field(default="", max_length=240)
    sheet_name: str | None = Field(default=None, max_length=120)
    content: str = Field(
        min_length=1,
        max_length=8_000_000,
        description="CSV/TSV text, or base64-encoded XLSX bytes when source_format is xlsx.",
    )
    column_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Optional canonical-field to source-column overrides, such as {'brand': 'Supplier Brand'}.",
    )
    price_list_id: str | None = Field(
        default=None,
        description="Optional active price list UUID used when previewing price_list_items.",
    )


class LibraryImportMappedFieldResponse(BaseModel):
    field: str
    label: str
    source_column: str
    required: bool = False


class LibraryImportProblemResponse(BaseModel):
    field: str
    code: str
    severity: LibraryImportProblemSeverity
    message: str
    suggestion: str


class LibraryImportPreviewRowResponse(BaseModel):
    row_number: int = Field(ge=1)
    status: LibraryImportRowStatus
    identity: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    problems: list[LibraryImportProblemResponse] = Field(default_factory=list)


class LibraryImportPreviewSummaryResponse(BaseModel):
    total_rows: int = Field(ge=0)
    create_count: int = Field(ge=0)
    update_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)


class LibraryImportPreviewResponse(BaseModel):
    resource: LibraryImportResource
    source_format: LibraryImportSourceFormat
    sheet_name: str | None = None
    columns: list[str] = Field(default_factory=list)
    mapped_fields: list[LibraryImportMappedFieldResponse] = Field(default_factory=list)
    summary: LibraryImportPreviewSummaryResponse
    rows: list[LibraryImportPreviewRowResponse] = Field(default_factory=list)


class LibraryImportApplyRequest(LibraryImportPreviewRequest):
    source_ref: str = Field(
        default="",
        max_length=240,
        description="Optional human source reference such as supplier sheet, email, or spreadsheet tab.",
    )


class LibraryImportApplySummaryResponse(BaseModel):
    total_rows: int = Field(ge=0)
    created_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)


class LibraryImportApplyRowResponse(BaseModel):
    row_number: int = Field(ge=1)
    status: LibraryImportApplyRowStatus
    identity: str
    message: str
    target_id: str = ""
    problems: list[LibraryImportProblemResponse] = Field(default_factory=list)


class LibraryImportApplyResponse(BaseModel):
    batch_id: str
    resource: LibraryImportResource
    source_format: LibraryImportSourceFormat
    summary: LibraryImportApplySummaryResponse
    rows: list[LibraryImportApplyRowResponse] = Field(default_factory=list)


class LibraryBulkUpdateRowResponse(BaseModel):
    item_id: str
    label: str
    status: LibraryBulkRowStatus
    message: str
    changed_fields: list[str] = Field(default_factory=list)


class LibraryBulkUpdateResponse(BaseModel):
    resource: str
    confirm: bool
    requested_count: int = Field(ge=0)
    matched_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    summary_message: str
    rows: list[LibraryBulkUpdateRowResponse] = Field(default_factory=list)


class LibraryCatalogBulkUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource: LibraryCatalogBulkResource
    item_ids: list[str] = Field(min_length=1, max_length=100)
    updates: dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False


class PriceListItemBulkUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_ids: list[str] = Field(min_length=1, max_length=100)
    unit_price_cents: int | None = Field(default=None, ge=0)
    uom: str | None = Field(default=None, min_length=1, max_length=40)
    cost_source: Literal["manual", "override"] | None = None
    confirm: bool = False


class PricingSettingsFields(BaseModel):
    vat_rate_bps: int = Field(default=1500, ge=0)
    default_markup_bps: int = Field(default=2500, ge=0)
    carcass_markup_bps: int = Field(default=2500, ge=0)
    door_panel_markup_bps: int = Field(default=2500, ge=0)
    component_markup_bps: int = Field(default=2500, ge=0)
    handle_markup_bps: int = Field(default=2500, ge=0)
    extras_markup_bps: int = Field(default=2500, ge=0)
    fabrication_markup_bps: int = Field(default=2500, ge=0)
    install_markup_bps: int = Field(default=2500, ge=0)
    delivery_markup_bps: int = Field(default=2500, ge=0)
    joinery_commission_bps: int = Field(default=0, ge=0)
    labour_cents_per_m2: int = Field(default=2000, ge=0)
    consumables_cents_per_m2: int = Field(default=1000, ge=0)
    install_day_cost_cents: int = Field(default=190000, ge=0)
    delivery_base_cents: int = Field(default=95000, ge=0)
    install_units_per_day: int = Field(default=3, ge=1)
    delivery_units_per_trip: int = Field(default=20, ge=1)
    minimum_install_days_bps: int = Field(default=5000, ge=0)
    minimum_delivery_trips_bps: int = Field(default=5000, ge=0)


class ProjectPricingSettingsResponse(PricingSettingsFields):
    model_config = ConfigDict(from_attributes=True)

    company_id: str
    project_id: str
    created_at: datetime
    updated_at: datetime


class QuotePricingSettingsResponse(PricingSettingsFields):
    model_config = ConfigDict(from_attributes=True)

    company_id: str
    quote_id: str
    created_at: datetime
    updated_at: datetime


class QuotePricingSummaryResponse(BaseModel):
    quote_id: str
    quote_name: str
    quote_status: QuoteStatus = "draft"
    quote_number: str
    revision: int = Field(ge=1)
    previous_revision_id: str | None = None
    previous_revision_quote_number: str | None = None
    previous_revision_revision: int | None = Field(default=None, ge=1)
    vat_rate_bps: int = Field(ge=0)
    markup_bps: int = Field(ge=0)
    active_price_list_id: str | None = None
    pricing_as_of: datetime | None = None
    pricing_settings: QuotePricingSettingsResponse
    is_complete: bool
    missing_items: list[str] = Field(default_factory=list)
    cutlist_warnings: list[CutlistValidationWarningResponse] = Field(default_factory=list)
    missing_prices: list[MissingPriceResponse] = Field(default_factory=list)
    material_summary: MaterialSummaryResponse = Field(default_factory=MaterialSummaryResponse)
    hardware_pick_list: HardwarePickListResponse = Field(default_factory=HardwarePickListResponse)
    subtotal_cents: int = 0
    cost_total_cents: int = 0
    sell_before_vat_cents: int = 0
    vat_cents: int = 0
    grand_total_cents: int = 0
    profit_cents: int = 0
    bucket_totals: list[PricingBucketTotalResponse] = Field(default_factory=list)
    lines: list[QuotePricingLineResponse] = Field(default_factory=list)


class ProjectPricingResponse(BaseModel):
    project_id: str
    project_name: str
    active_price_list_id: str | None = None
    currency_code: str = Field(description="Company ISO 4217 currency code used to display monetary totals.")
    vat_rate_bps: int = Field(ge=0)
    markup_bps: int = Field(ge=0)
    pricing_settings: ProjectPricingSettingsResponse
    is_complete: bool
    missing_prices: list[MissingPriceResponse] = Field(default_factory=list)
    subtotal_cents: int = 0
    cost_total_cents: int = 0
    sell_before_vat_cents: int = 0
    vat_cents: int = 0
    grand_total_cents: int = 0
    profit_cents: int = 0
    bucket_totals: list[PricingBucketTotalResponse] = Field(default_factory=list)
    quotes: list[QuotePricingSummaryResponse] = Field(default_factory=list)


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
    grain_policy: BoardGrainPolicy = "required"


class BoardTypeResponse(BoardTypeRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class DrawerSystemFormulaRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    section: DrawerSystemPanelSection = "carcass"
    length_formula: str = Field(min_length=1, max_length=500)
    width_formula: str = Field(min_length=1, max_length=500)
    qty_formula: str = Field(default="num_drawers", min_length=1, max_length=500)
    condition_formula: str = Field(default="", max_length=500)
    edge_long_1: bool = False
    edge_long_2: bool = False
    edge_short_1: bool = False
    edge_short_2: bool = False
    grain_direction: ProductionGrainDirection = "none"
    can_rotate: bool = True


class DrawerSystemHardwareItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: HardwarePickListItemType = "extra"
    item_ref_id: str = Field(default="", max_length=120)
    name: str = Field(min_length=1, max_length=160)
    supplier: str = Field(default="", max_length=160)
    code: str = Field(default="", max_length=120)
    quantity: int = Field(default=0, ge=0)
    quantity_per_drawer: int = Field(default=1, ge=0)
    uom: str = Field(default="pcs", min_length=1, max_length=40)


class HardwareAccessoryCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: HardwareAccessoryConditionField = "always"
    operator: HardwareAccessoryConditionOperator = "always"
    value_number: float | None = None
    value_text: str = Field(default="", max_length=160)


class HardwareAccessoryRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: HardwarePickListItemType = "extra"
    item_ref_id: str = Field(default="", max_length=120)
    name: str = Field(min_length=1, max_length=160)
    supplier: str = Field(default="", max_length=160)
    code: str = Field(default="", max_length=120)
    quantity: int = Field(default=1, ge=0)
    quantity_rule: HardwareAccessoryQuantityRule = "per_unit"
    required: bool = True
    enabled: bool = False
    uom: str = Field(default="pcs", min_length=1, max_length=40)
    condition: HardwareAccessoryCondition = Field(default_factory=HardwareAccessoryCondition)


class HardwareAccessoryConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    accessories: list[HardwareAccessoryRule] = Field(default_factory=list)


class DrawerSystemConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    product_family: str = Field(default="", max_length=160)
    manufacturer: str = Field(default="", max_length=160)
    finish: str = Field(default="", max_length=120)
    side_height_mm: int | None = Field(default=None, ge=0)
    load_class: str = Field(default="", max_length=120)
    installation_width_mm: int | None = Field(default=None, ge=0)
    compatible_side_thicknesses: list[int] = Field(default_factory=list)
    compatible_nominal_lengths: list[int] = Field(default_factory=list)
    min_internal_width_mm: int | None = Field(default=None, ge=0)
    max_internal_width_mm: int | None = Field(default=None, ge=0)
    min_depth_mm: int | None = Field(default=None, ge=0)
    min_front_height_mm: int | None = Field(default=None, ge=0)
    max_front_height_mm: int | None = Field(default=None, ge=0)
    supplied_metal_sides: bool = True
    supplied_steel_back: bool = False
    cut_board_back: bool = False
    cut_bottom_panel: bool = True
    cut_inset_panel: bool = False
    variables: dict[str, int | float | bool] = Field(default_factory=dict)
    panel_formulas: list[DrawerSystemFormulaRow] = Field(default_factory=list)
    hardware_items: list[DrawerSystemHardwareItem] = Field(default_factory=list)


class SlideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    code: str = Field(default="", max_length=120)
    length: int = Field(ge=0)
    side_length: int = Field(ge=0)
    side_clearance_total: int = Field(ge=0)
    side_height_uplift: int = Field(default=0, ge=0)
    drawer_system_kind: DrawerSystemKind = "conventional"
    drawer_system_config: DrawerSystemConfig = Field(default_factory=DrawerSystemConfig)
    accessory_config: HardwareAccessoryConfig = Field(default_factory=HardwareAccessoryConfig)

    @field_validator("drawer_system_config", mode="before")
    @classmethod
    def normalize_drawer_system_config(cls, value):
        if value in (None, ""):
            return {}
        return value

    @field_validator("accessory_config", mode="before")
    @classmethod
    def normalize_accessory_config(cls, value):
        if value in (None, ""):
            return {}
        return value


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
    accessory_config: HardwareAccessoryConfig = Field(default_factory=HardwareAccessoryConfig)

    @field_validator("accessory_config", mode="before")
    @classmethod
    def normalize_accessory_config(cls, value):
        if value in (None, ""):
            return {}
        return value


class HingeResponse(HingeRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class SupplierRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    code: str = Field(default="", max_length=120)
    contact_name: str = Field(default="", max_length=160)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=1000)
    default_discount_bps: int = Field(default=0, ge=0, le=10000)


class SupplierResponse(SupplierRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class SupplierDiscountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discount_bps: int = Field(default=0, ge=0, le=10000)
    apply_to_active_costs: bool = True
    source: str = Field(default="supplier-discount", min_length=1, max_length=80)
    source_ref: str = Field(default="", max_length=240)
    effective_from: datetime | None = Field(default=None)


class SupplierDiscountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    supplier_id: str
    discount_bps: int = Field(ge=0, le=10000)
    matched_item_supplier_count: int = Field(ge=0)
    updated_cost_count: int = Field(ge=0)
    unchanged_cost_count: int = Field(ge=0)
    skipped_without_active_cost_count: int = Field(ge=0)


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
    supplier_id: str | None = Field(default=None, description="Optional supplier UUID in the current company.")
    code: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=1000)

    @field_validator("supplier_id", mode="before")
    @classmethod
    def normalize_supplier_id(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        return value


class ExtraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category_id: str
    category_name: str
    supplier_id: str | None = None
    supplier: str = ""
    code: str
    notes: str
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


class PricingSettingsRequest(PricingSettingsFields):
    model_config = ConfigDict(extra="forbid")


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
    source_supplier_item_cost_id: str | None = Field(
        default=None,
        description="Supplier cost UUID used to generate this row, if any.",
    )
    cost_source: Literal["manual", "supplier", "override", "import"] = "manual"
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
    is_current: bool
    effective_status: LibraryEffectiveStatus
    created_at: datetime
    updated_at: datetime


class ItemSupplierRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: Literal["board", "slide", "hinge", "handle", "extra"]
    item_ref_id: str = Field(min_length=1, description="Catalog item UUID in the current company.")
    supplier_id: str = Field(min_length=1, description="Supplier UUID in the current company.")
    supplier_sku: str = Field(default="", max_length=160)
    supplier_description: str = Field(default="", max_length=500)
    price_component: str = Field(default="unit", min_length=1, max_length=80)
    order_uom: str = Field(default="pcs", min_length=1, max_length=40)
    is_preferred: bool = False
    notes: str = Field(default="", max_length=1000)


class ItemSupplierResponse(ItemSupplierRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    supplier_name: str
    active_supplier_item_cost_id: str | None = None
    active_list_price_cents: int | None = None
    active_discount_bps: int | None = None
    active_unit_cost_cents: int | None = None
    active_currency_code: str | None = None
    created_at: datetime
    updated_at: datetime


class SupplierItemCostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    list_price_cents: int = Field(default=0, ge=0)
    discount_bps: int = Field(default=0, ge=0, le=10000)
    unit_cost_cents: int = Field(ge=0)
    currency_code: str = Field(default="ZAR", min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    source: str = Field(default="manual", min_length=1, max_length=80)
    source_ref: str = Field(default="", max_length=240)
    effective_from: datetime | None = Field(default=None)

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, value):
        return str(value or "ZAR").strip().upper()


class SupplierItemCostResponse(SupplierItemCostRequest):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_supplier_id: str
    effective_from: datetime
    effective_to: datetime | None
    replaces_id: str | None = None
    is_active: bool
    is_current: bool
    effective_status: LibraryEffectiveStatus
    created_at: datetime
    updated_at: datetime


class GeneratePriceListFromSupplierCostsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selection_mode: Literal["preferred_then_cheapest", "preferred_only", "cheapest"] = "preferred_then_cheapest"
    item_types: list[Literal["board", "slide", "hinge", "handle", "extra"]] = Field(default_factory=list)
    preserve_manual_overrides: bool = True
    effective_from: datetime | None = Field(
        default=None,
        description="Optional UTC timestamp for when refreshed price rows become current. Defaults to now.",
    )


class GeneratePriceListFromSupplierCostsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price_list_id: str
    selection_mode: str
    generated_count: int = Field(ge=0)
    created_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    unchanged_count: int = Field(ge=0)
    skipped_override_count: int = Field(ge=0)
    missing_price_count: int = Field(ge=0)
