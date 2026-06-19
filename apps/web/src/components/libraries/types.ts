import type { CompanyPricingSettingsRow } from '@/components/pricing-settings'

export type LibraryTab =
  | 'setup-imports'
  | 'pricing'
  | 'boards'
  | 'slides'
  | 'hinges'
  | 'suppliers'
  | 'handles'
  | 'extra-categories'
  | 'extras'

export type PriceItemType = 'board' | 'slide' | 'hinge' | 'handle' | 'extra'
export type LibraryEffectiveStatus = 'current' | 'future' | 'retired'
export type LibrarySetupStatus = 'ready' | 'needs_attention'
export type LibrarySetupItemStatus = 'complete' | 'missing' | 'warning' | 'action_needed'
export type LibrarySetupActionTarget = LibraryTab | 'projects'
export type LibraryImportResource =
  | 'boards'
  | 'slides'
  | 'hinges'
  | 'handles'
  | 'suppliers'
  | 'extra_categories'
  | 'extras'
  | 'supplier_item_costs'
  | 'price_list_items'
export type LibraryImportSourceFormat = 'csv' | 'tsv' | 'xlsx'
export type LibraryImportRowStatus = 'create' | 'update' | 'skipped' | 'duplicate' | 'blocked'
export type LibraryImportApplyRowStatus = 'created' | 'updated' | 'skipped' | 'failed'
export type LibraryImportProblemSeverity = 'error' | 'warning'
export type LibraryCatalogBulkResource = 'boards' | 'slides' | 'hinges' | 'handles' | 'extras' | 'suppliers'
export type LibraryBulkRowStatus = 'preview' | 'updated' | 'failed'
export type BoardGrainPolicy = 'none' | 'optional' | 'required'

export type LibrarySetupChecklistItem = {
  id: string
  label: string
  status: LibrarySetupItemStatus
  count: number
  message: string
  action_label: string
  action_target: LibrarySetupActionTarget
}

export type LibrarySetupChecklist = {
  status: LibrarySetupStatus
  summary_title: string
  summary_message: string
  complete_count: number
  total_count: number
  items: LibrarySetupChecklistItem[]
}

export type LibraryImportPreviewRequest = {
  resource: LibraryImportResource
  source_format: LibraryImportSourceFormat
  filename: string
  sheet_name: string | null
  content: string
  column_mapping: Record<string, string>
  price_list_id: string | null
}

export type LibraryImportApplyRequest = LibraryImportPreviewRequest & {
  source_ref: string
}

export type LibraryImportMappedField = {
  field: string
  label: string
  source_column: string
  required: boolean
}

export type LibraryImportProblem = {
  field: string
  code: string
  severity: LibraryImportProblemSeverity
  message: string
  suggestion: string
}

export type LibraryImportPreviewRow = {
  row_number: number
  status: LibraryImportRowStatus
  identity: string
  message: string
  payload: Record<string, unknown>
  problems: LibraryImportProblem[]
}

export type LibraryImportPreviewSummary = {
  total_rows: number
  create_count: number
  update_count: number
  skipped_count: number
  duplicate_count: number
  blocked_count: number
}

export type LibraryImportPreview = {
  resource: LibraryImportResource
  source_format: LibraryImportSourceFormat
  sheet_name: string | null
  columns: string[]
  mapped_fields: LibraryImportMappedField[]
  summary: LibraryImportPreviewSummary
  rows: LibraryImportPreviewRow[]
}

export type LibraryImportApplySummary = {
  total_rows: number
  created_count: number
  updated_count: number
  skipped_count: number
  failed_count: number
}

export type LibraryImportApplyRow = {
  row_number: number
  status: LibraryImportApplyRowStatus
  identity: string
  message: string
  target_id: string
  problems: LibraryImportProblem[]
}

export type LibraryImportApplyResult = {
  batch_id: string
  resource: LibraryImportResource
  source_format: LibraryImportSourceFormat
  summary: LibraryImportApplySummary
  rows: LibraryImportApplyRow[]
}

export type LibraryBulkUpdateRow = {
  item_id: string
  label: string
  status: LibraryBulkRowStatus
  message: string
  changed_fields: string[]
}

export type LibraryBulkUpdateResult = {
  resource: string
  confirm: boolean
  requested_count: number
  matched_count: number
  updated_count: number
  failed_count: number
  summary_message: string
  rows: LibraryBulkUpdateRow[]
}

export type BoardTypeRow = {
  id: string
  brand: string
  material: string
  thickness: number
  length_mm: number
  width_mm: number
  costing_mode: 'sheet' | 'sqm'
  grain_policy: BoardGrainPolicy
  created_at: string
  updated_at: string
}

export type SlideRow = {
  id: string
  brand: string
  model: string
  code: string
  length: number
  side_length: number
  side_clearance_total: number
  side_height_uplift: number
  drawer_system_kind: DrawerSystemKind
  drawer_system_config: DrawerSystemConfig
  accessory_config: HardwareAccessoryConfig
  created_at: string
  updated_at: string
}

export type HingeRow = {
  id: string
  brand: string
  model: string
  code: string
  opening_angle_deg: number
  accessory_config: HardwareAccessoryConfig
  created_at: string
  updated_at: string
}

export type SupplierRow = {
  id: string
  name: string
  code: string
  contact_name: string
  email: string
  phone: string
  notes: string
  default_discount_bps: number
  created_at: string
  updated_at: string
}

export type HandleRow = {
  id: string
  name: string
  supplier: string
  code: string
  created_at: string
  updated_at: string
}

export type ExtraCategoryRow = {
  id: string
  name: string
  created_at: string
  updated_at: string
}

export type ExtraRow = {
  id: string
  name: string
  category_id: string
  category_name: string
  supplier_id: string | null
  supplier: string
  code: string
  notes: string
  created_at: string
  updated_at: string
}

export type PricingSettingsRow = CompanyPricingSettingsRow

export type PriceListRow = {
  id: string
  name: string
  status: 'draft' | 'active' | 'archived'
  effective_from: string | null
  effective_to: string | null
  created_at: string
  updated_at: string
}

export type PriceListItemRow = {
  id: string
  price_list_id: string
  item_type: PriceItemType
  item_ref_id: string | null
  item_key: string
  price_component: string
  uom: string
  unit_price_cents: number
  source_supplier_item_cost_id: string | null
  cost_source: 'manual' | 'supplier' | 'override' | 'import'
  effective_from: string
  effective_to: string | null
  replaces_id: string | null
  is_active: boolean
  is_current: boolean
  effective_status: LibraryEffectiveStatus
  created_at: string
  updated_at: string
}

export type ItemSupplierRow = {
  id: string
  item_type: PriceItemType
  item_ref_id: string
  supplier_id: string
  supplier_name: string
  supplier_sku: string
  supplier_description: string
  price_component: string
  order_uom: string
  is_preferred: boolean
  notes: string
  active_supplier_item_cost_id: string | null
  active_list_price_cents: number | null
  active_discount_bps: number | null
  active_unit_cost_cents: number | null
  active_currency_code: string | null
  created_at: string
  updated_at: string
}

export type GeneratePriceListSummary = {
  price_list_id: string
  selection_mode: 'preferred_then_cheapest' | 'preferred_only' | 'cheapest'
  generated_count: number
  created_count: number
  updated_count: number
  unchanged_count: number
  skipped_override_count: number
  missing_price_count: number
}

export type SupplierDiscountSummary = {
  supplier_id: string
  discount_bps: number
  matched_item_supplier_count: number
  updated_cost_count: number
  unchanged_cost_count: number
  skipped_without_active_cost_count: number
}

export type BoardDraft = {
  brand: string
  material: string
  thickness: string
  length_mm: string
  width_mm: string
  costing_mode: 'sheet' | 'sqm'
  grain_policy: BoardGrainPolicy
}

export type SlideDraft = {
  brand: string
  model: string
  code: string
  length: string
  side_length: string
  side_clearance_total: string
  side_height_uplift: string
  drawer_system_kind: DrawerSystemKind
  drawer_system_config: DrawerSystemConfig
  accessory_config: HardwareAccessoryConfig
}

export type DrawerSystemKind = 'conventional' | 'metal'
export type DrawerSystemHardwareItemType = Exclude<PriceItemType, 'board'>
export type HardwareAccessoryQuantityRule = 'fixed' | 'per_unit' | 'per_drawer' | 'per_slide_pair' | 'per_hinge' | 'per_door'
export type HardwareAccessoryConditionField =
  | 'always'
  | 'drawer_front_height'
  | 'drawer_side_height'
  | 'unit_width'
  | 'unit_height'
  | 'unit_depth'
  | 'num_drawers'
  | 'door_count'
  | 'hinge_count'
  | 'hardware_variant'
  | 'load_class'
export type HardwareAccessoryConditionOperator =
  | 'always'
  | 'greater_than'
  | 'greater_than_or_equal'
  | 'less_than'
  | 'less_than_or_equal'
  | 'equals'
  | 'not_equals'

export type HardwareAccessoryCondition = {
  field: HardwareAccessoryConditionField
  operator: HardwareAccessoryConditionOperator
  value_number?: number | null
  value_text?: string
}

export type HardwareAccessoryRule = {
  item_type: DrawerSystemHardwareItemType
  item_ref_id: string
  name: string
  supplier?: string
  code?: string
  quantity: number
  quantity_rule: HardwareAccessoryQuantityRule
  required: boolean
  enabled: boolean
  uom: string
  condition: HardwareAccessoryCondition
}

export type HardwareAccessoryConfig = {
  accessories?: HardwareAccessoryRule[]
  [key: string]: unknown
}

export type DrawerSystemFormulaRow = {
  name: string
  section?: 'carcass' | 'panel' | 'extra_panel'
  length_formula: string
  width_formula: string
  qty_formula?: string
  condition_formula?: string
  edge_long_1?: boolean
  edge_long_2?: boolean
  edge_short_1?: boolean
  edge_short_2?: boolean
  grain_direction?: 'none' | 'length' | 'width'
  can_rotate?: boolean
}

export type DrawerSystemHardwareItem = {
  item_type?: DrawerSystemHardwareItemType
  item_ref_id?: string
  name: string
  supplier?: string
  code?: string
  quantity?: number
  quantity_per_drawer?: number
  uom?: string
}

export type DrawerSystemConfig = {
  product_family?: string
  manufacturer?: string
  finish?: string
  side_height_mm?: number | null
  load_class?: string
  installation_width_mm?: number | null
  compatible_side_thicknesses?: number[]
  compatible_nominal_lengths?: number[]
  min_internal_width_mm?: number | null
  max_internal_width_mm?: number | null
  min_depth_mm?: number | null
  min_front_height_mm?: number | null
  max_front_height_mm?: number | null
  supplied_metal_sides?: boolean
  supplied_steel_back?: boolean
  cut_board_back?: boolean
  cut_bottom_panel?: boolean
  cut_inset_panel?: boolean
  variables?: Record<string, number | boolean>
  panel_formulas?: DrawerSystemFormulaRow[]
  hardware_items?: DrawerSystemHardwareItem[]
  [key: string]: unknown
}

export type HingeDraft = {
  brand: string
  model: string
  code: string
  opening_angle_deg: string
  accessory_config: HardwareAccessoryConfig
}

export type SupplierDraft = {
  name: string
  code: string
  contact_name: string
  email: string
  phone: string
  notes: string
  default_discount_percent: string
}

export type ItemSupplierDraft = {
  item_type: PriceItemType
  item_ref_id: string
  supplier_id: string
  supplier_sku: string
  supplier_description: string
  price_component: string
  order_uom: string
  is_preferred: boolean
  notes: string
  list_price_amount: string
  discount_percent: string
  unit_cost_amount: string
}

export type HandleDraft = {
  name: string
  supplier: string
  code: string
}

export type ExtraCategoryDraft = {
  name: string
}

export type ExtraDraft = {
  name: string
  category_id: string
  supplier_id: string
  code: string
  notes: string
}

export type PriceListDraft = {
  name: string
  status: 'draft' | 'active'
}

export type ApiMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'
