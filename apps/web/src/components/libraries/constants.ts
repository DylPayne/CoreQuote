import type { BoardDraft, ExtraCategoryDraft, ExtraDraft, HandleDraft, HingeDraft, LibraryTab, PriceListDraft, SlideDraft } from './types'

export const libraryTabs: Array<{ label: string; value: LibraryTab }> = [
  { label: 'Pricing', value: 'pricing' },
  { label: 'Boards', value: 'boards' },
  { label: 'Slides', value: 'slides' },
  { label: 'Hinges', value: 'hinges' },
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
}

export const defaultSlideDraft: SlideDraft = {
  brand: '',
  model: '',
  code: '',
  length: '500',
  side_length: '500',
  side_clearance_total: '26',
  side_height_uplift: '0',
}

export const defaultHingeDraft: HingeDraft = {
  brand: '',
  model: '',
  code: '',
  opening_angle_deg: '110',
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
