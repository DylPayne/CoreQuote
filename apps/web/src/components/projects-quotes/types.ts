import type { ProjectPricingSettingsRow, QuotePricingSettingsRow } from '@/components/pricing-settings'

export type UnitDefaults = Record<string, { height: number; depth: number }>
export type QuoteStatus = 'draft' | 'ready' | 'sent' | 'accepted' | 'rejected' | 'revised' | 'expired'

export type ProjectRow = {
  id: string
  company_id: string
  name: string
  client: string
  address: string
  description: string
  quote_count: number
  created_at: string
  updated_at: string
}

export type QuoteRow = {
  id: string
  company_id: string
  project_id: string
  name: string
  notes: string
  status: QuoteStatus
  quote_number: string
  revision: number
  previous_revision_id: string | null
  previous_revision_quote_number: string | null
  previous_revision_revision: number | null
  default_carcass_board_type_id: string | null
  default_door_board_type_id: string | null
  default_panel_board_type_id: string | null
  default_slide_id: string | null
  default_hinge_id: string | null
  default_base_handle_id: string | null
  default_wall_handle_id: string | null
  default_tall_handle_id: string | null
  default_drawer_handle_id: string | null
  unit_defaults: UnitDefaults
  unit_count: number
  created_at: string
  updated_at: string
}

export type UnitRow = {
  id: string
  company_id: string
  quote_id: string
  unit_number: number
  unit_type_key: string
  height: number
  width: number
  depth: number
  thickness: number
  carcass_board_type_id: string | null
  door_board_type_id: string | null
  extra_params: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type BoardRow = {
  id: string
  brand: string
  material: string
  thickness: number
  length_mm: number
  width_mm: number
}

export type SlideRow = {
  id: string
  brand: string
  model: string
  code: string
  length: number
}

export type HingeRow = {
  id: string
  brand: string
  model: string
  code: string
  opening_angle_deg: number
}

export type HandleRow = {
  id: string
  name: string
  supplier: string
  code: string
}

export type ExtraRow = {
  id: string
  name: string
  category_id: string
  category_name: string
  supplier: string
  code: string
  notes: string
}

export type CutlistRow = {
  unit_number: number
  desc: string
  length: number
  width: number
  qty: number
}

export type CutlistValidationWarning = {
  severity: 'warning'
  source: 'unit' | 'quote_panel'
  unit_number: number
  section: 'carcass' | 'panel' | 'hardware' | 'extra_panel'
  row_desc: string
  reason: string
}

export type CutlistReadiness = {
  cutlist_valid: boolean
  warning_count: number
}

export type QuoteCuttingList = {
  quote_id: string
  carcass: CutlistRow[]
  panels: CutlistRow[]
  hardware: CutlistRow[]
  extras: CutlistRow[]
  validation_warnings: CutlistValidationWarning[]
  readiness: CutlistReadiness
}

export type QuoteReadinessSeverity = 'pass' | 'warning' | 'error'
export type QuoteReadinessStatus = 'ready' | 'needs_attention'
export type QuoteReadinessActionTarget = 'project' | 'quote' | 'units' | 'panels' | 'cutting-lists' | 'pricing' | 'outputs'

export type QuoteReadinessCheck = {
  id: string
  severity: QuoteReadinessSeverity
  title: string
  message: string
  action_label: string
  action_target: QuoteReadinessActionTarget
}

export type QuoteReadiness = {
  quote_id: string
  status: QuoteReadinessStatus
  is_ready: boolean
  summary_title: string
  summary_message: string
  warning_count: number
  error_count: number
  checks: QuoteReadinessCheck[]
}

export type QuoteExtrasResponse = {
  quote_id: string
  items: Array<{ extra_id: string; quantity: number }>
}

export type PanelPresetKey =
  | 'base_side_panel'
  | 'base_side_filler'
  | 'wall_side_panel'
  | 'wall_side_filler'
  | 'tall_side_panel'
  | 'tall_side_filler'

export type QuoteCustomPanelPresetConfig = {
  qty: number
  board_type_id: string | null
}

export type QuoteCustomPanelManualRow = {
  name: string
  length: number
  width: number
  qty: number
  board_type_id: string | null
}

export type QuoteCustomPanelAutoConfig = {
  kicker_board_type_id: string | null
  pelmet_board_type_id: string | null
  kicker_return_count: number
  kicker_return_depth_mm: number
  kicker_override_on: boolean
  kicker_override_qty: number
  kicker_override_length: number
  kicker_override_width: number
  pelmet_override_on: boolean
  pelmet_override_qty: number
  pelmet_override_length: number
  pelmet_override_width: number
}

export type QuoteCustomPanelsState = {
  presets: Partial<Record<PanelPresetKey, QuoteCustomPanelPresetConfig>>
  manual: QuoteCustomPanelManualRow[]
  auto: QuoteCustomPanelAutoConfig
}

export type QuoteCustomPanelComputedRow = {
  desc: string
  length: number
  width: number
  qty: number
  board_type_id: string | null
}

export type QuoteCustomPanelsResponse = {
  quote_id: string
  custom_panels: QuoteCustomPanelsState
  computed_rows: QuoteCustomPanelComputedRow[]
}

export type PricingLine = {
  item_type: 'board' | 'slide' | 'hinge' | 'handle' | 'extra' | 'labour' | 'consumable' | 'installation' | 'delivery' | 'adjustment'
  item_key: string
  price_component: string
  bucket: string
  description: string
  qty: number
  uom: string
  unit_price_cents: number | null
  unit_cost_cents: number | null
  cost_total_cents: number | null
  markup_bps: number
  sell_total_cents: number | null
  line_total_cents: number | null
  profit_cents: number | null
  missing: boolean
}

export type PricingBucketTotal = {
  bucket: string
  cost_total_cents: number
  sell_total_cents: number
  profit_cents: number
}

export type MaterialRole = 'carcass' | 'door_panel' | 'visible_panel'

export type MaterialSummaryWarning = {
  severity: 'warning'
  code: 'missing_board_selection' | 'missing_board_record' | 'missing_board_dimensions'
  material_role: MaterialRole
  role_label: string
  unit_number: number
  row_desc: string
  board_type_id: string | null
  message: string
}

export type MaterialSummaryGroup = {
  board_type_id: string
  material_role: MaterialRole
  role_label: string
  board_name: string
  brand: string
  material: string
  thickness: number | null
  length_mm: number | null
  width_mm: number | null
  costing_mode: string
  piece_count: number
  area_m2: number
  edge_m: number
  sheet_area_m2: number | null
  estimated_sheets: number | null
  price_component: string | null
  pricing_qty: number | null
  pricing_uom: string | null
  cost_total_cents: number | null
  sell_total_cents: number | null
  missing_price: boolean
}

export type MaterialSummary = {
  groups: MaterialSummaryGroup[]
  warnings: MaterialSummaryWarning[]
  total_area_m2: number
  total_piece_count: number
  total_edge_m: number
  total_estimated_sheets: number | null
}

export type HardwarePickListItemType = 'slide' | 'hinge' | 'handle' | 'extra'

export type HardwarePickListItem = {
  item_type: HardwarePickListItemType
  type_label: string
  item_key: string
  item_ref_id: string
  item_name: string
  supplier: string
  code: string
  quantity: number
  uom: string
  unit_numbers: number[]
  used_in: string[]
  usage_label: string
}

export type HardwarePickListWarning = {
  severity: 'warning'
  code: 'missing_slide_selection' | 'missing_hinge_selection' | 'missing_handle_selection' | 'missing_catalog_item'
  item_type: HardwarePickListItemType
  unit_number: number
  item_ref_id: string | null
  message: string
}

export type HardwarePickList = {
  items: HardwarePickListItem[]
  warnings: HardwarePickListWarning[]
  total_item_count: number
  total_quantity: number
}

export type MissingPrice = {
  item_type: 'board' | 'slide' | 'hinge' | 'handle' | 'extra' | 'labour' | 'consumable' | 'installation' | 'delivery' | 'adjustment'
  item_type_label: string
  item_key: string
  item_ref_id: string
  price_component: string
  component: string
  bucket: string
  item_name: string
  uom: string
  quantity: number
  used_in: string[]
  usage_label: string
  affected_quote_id: string
  affected_quote_name: string
  library_area: string
  action_label: string
  message: string
}

export type QuotePricingSummary = {
  quote_id: string
  quote_name: string
  quote_status: QuoteStatus
  quote_number: string
  revision: number
  previous_revision_id: string | null
  previous_revision_quote_number: string | null
  previous_revision_revision: number | null
  vat_rate_bps: number
  markup_bps: number
  pricing_settings: QuotePricingSettingsRow
  is_complete: boolean
  missing_items: string[]
  cutlist_warnings: CutlistValidationWarning[]
  missing_prices: MissingPrice[]
  material_summary: MaterialSummary
  hardware_pick_list: HardwarePickList
  subtotal_cents: number
  cost_total_cents: number
  sell_before_vat_cents: number
  vat_cents: number
  grand_total_cents: number
  profit_cents: number
  bucket_totals: PricingBucketTotal[]
  lines: PricingLine[]
}

export type ProjectPricingSummary = {
  project_id: string
  project_name: string
  active_price_list_id: string | null
  currency_code: string
  vat_rate_bps: number
  markup_bps: number
  pricing_settings: ProjectPricingSettingsRow
  is_complete: boolean
  missing_prices: MissingPrice[]
  subtotal_cents: number
  cost_total_cents: number
  sell_before_vat_cents: number
  vat_cents: number
  grand_total_cents: number
  profit_cents: number
  bucket_totals: PricingBucketTotal[]
  quotes: QuotePricingSummary[]
}

export type ApiMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
export type UnitPresetKey = 'Base Draw' | 'Base Door' | 'Wall Door' | 'Tall Door'
export type ProjectWorkspaceTab = 'quotes' | 'pricing'
export type PricingWorkspaceTab = 'overview' | 'settings' | 'quotes'
export type QuoteWorkspaceTab = 'readiness' | 'units' | 'panels' | 'cutting-lists' | 'extras' | 'pricing'
export type CuttingListViewTab = 'carcass' | 'panels' | 'extras'

export type ProjectDraft = {
  name: string
  client: string
  address: string
  description: string
}

export type QuoteDraft = {
  name: string
  notes: string
  default_carcass_board_type_id: string
  default_door_board_type_id: string
  default_panel_board_type_id: string
  default_slide_id: string
  default_hinge_id: string
  default_base_handle_id: string
  default_wall_handle_id: string
  default_tall_handle_id: string
  default_drawer_handle_id: string
  base_draw_height: string
  base_draw_depth: string
  base_door_height: string
  base_door_depth: string
  wall_door_height: string
  wall_door_depth: string
  tall_door_height: string
  tall_door_depth: string
}

export type UnitDraft = {
  unit_type_key: string
  custom_unit_type_key: string
  height: string
  width: string
  depth: string
  carcass_board_type_id: string
  door_board_type_id: string
  num_drawers: string
  num_doors: string
  num_shelves: string
}
