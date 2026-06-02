export type LibraryTab =
  | 'pricing'
  | 'boards'
  | 'slides'
  | 'hinges'
  | 'suppliers'
  | 'handles'
  | 'extra-categories'
  | 'extras'

export type PriceItemType = 'board' | 'slide' | 'hinge' | 'handle' | 'extra'

export type BoardTypeRow = {
  id: string
  brand: string
  material: string
  thickness: number
  length_mm: number
  width_mm: number
  costing_mode: 'sheet' | 'sqm'
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
  created_at: string
  updated_at: string
}

export type HingeRow = {
  id: string
  brand: string
  model: string
  code: string
  opening_angle_deg: number
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
  supplier: string
  code: string
  notes: string
  created_at: string
  updated_at: string
}

export type PricingSettingsRow = {
  company_id: string
  vat_rate_bps: number
  default_markup_bps: number
  carcass_markup_bps: number
  door_panel_markup_bps: number
  component_markup_bps: number
  handle_markup_bps: number
  extras_markup_bps: number
  fabrication_markup_bps: number
  install_markup_bps: number
  delivery_markup_bps: number
  joinery_commission_bps: number
  labour_cents_per_m2: number
  consumables_cents_per_m2: number
  install_day_cost_cents: number
  delivery_base_cents: number
  install_units_per_day: number
  delivery_units_per_trip: number
  minimum_install_days_bps: number
  minimum_delivery_trips_bps: number
  created_at: string
  updated_at: string
}

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

export type BoardDraft = {
  brand: string
  material: string
  thickness: string
  length_mm: string
  width_mm: string
  costing_mode: 'sheet' | 'sqm'
}

export type SlideDraft = {
  brand: string
  model: string
  code: string
  length: string
  side_length: string
  side_clearance_total: string
  side_height_uplift: string
}

export type HingeDraft = {
  brand: string
  model: string
  code: string
  opening_angle_deg: string
}

export type SupplierDraft = {
  name: string
  code: string
  contact_name: string
  email: string
  phone: string
  notes: string
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
  supplier: string
  code: string
  notes: string
}

export type PriceListDraft = {
  name: string
  status: 'draft' | 'active'
}

export type ApiMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'
