export type LibraryTab =
  | 'pricing'
  | 'boards'
  | 'slides'
  | 'hinges'
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
  effective_from: string
  effective_to: string | null
  replaces_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
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
