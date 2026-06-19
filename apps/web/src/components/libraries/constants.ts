import type { BoardDraft, ExtraCategoryDraft, ExtraDraft, HandleDraft, HingeDraft, ItemSupplierDraft, LibraryTab, PriceListDraft, SlideDraft, SupplierDraft } from './types'

export const libraryTabs: Array<{ label: string; value: LibraryTab }> = [
  { label: 'Setup & Imports', value: 'setup-imports' },
  { label: 'Pricing', value: 'pricing' },
  { label: 'Boards', value: 'boards' },
  { label: 'Drawer Hardware', value: 'slides' },
  { label: 'Hinges', value: 'hinges' },
  { label: 'Suppliers', value: 'suppliers' },
  { label: 'Handles', value: 'handles' },
  { label: 'Extra Categories', value: 'extra-categories' },
  { label: 'Extras', value: 'extras' },
]

export const defaultBoardDraft: BoardDraft = {
  brand: '',
  material: '',
  thickness: '16',
  length_mm: '2750',
  width_mm: '1830',
  costing_mode: 'sheet',
  grain_policy: 'required',
}

export const defaultSlideDraft: SlideDraft = {
  brand: '',
  model: '',
  code: '',
  length: '500',
  side_length: '500',
  side_clearance_total: '26',
  side_height_uplift: '0',
  drawer_system_kind: 'conventional',
  drawer_system_config: {},
  accessory_config: { accessories: [] },
}

export const defaultHingeDraft: HingeDraft = {
  brand: '',
  model: '',
  code: '',
  opening_angle_deg: '110',
  accessory_config: { accessories: [] },
}

export const defaultSupplierDraft: SupplierDraft = {
  name: '',
  code: '',
  contact_name: '',
  email: '',
  phone: '',
  notes: '',
  default_discount_percent: '0.00',
}

export const defaultItemSupplierDraft: ItemSupplierDraft = {
  item_type: 'slide',
  item_ref_id: '',
  supplier_id: '',
  supplier_sku: '',
  supplier_description: '',
  price_component: 'unit',
  order_uom: 'pairs',
  is_preferred: true,
  notes: '',
  list_price_amount: '0.00',
  discount_percent: '0.00',
  unit_cost_amount: '0.00',
}

export const defaultHandleDraft: HandleDraft = {
  name: '',
  supplier: '',
  code: '',
}

export const defaultExtraCategoryDraft: ExtraCategoryDraft = {
  name: '',
}

export const defaultExtraDraft: ExtraDraft = {
  name: '',
  category_id: '',
  supplier: '',
  code: '',
  notes: '',
}

export const defaultPriceListDraft: PriceListDraft = {
  name: '',
  status: 'draft',
}
