import type { BoardDraft, BoardTypeRow, ExtraDraft, ExtraRow, HandleDraft, HandleRow, HingeDraft, HingeRow, PriceItemType, SlideDraft, SlideRow } from './types'
export { formatCurrencyFromCents } from '@/lib/currency'

export function formatBoardLabel(row: BoardTypeRow) {
  return `${row.brand} ${row.material} ${row.thickness}mm (${row.length_mm}x${row.width_mm})`
}

export function formatSlideLabel(row: SlideRow) {
  return `${row.brand} ${row.model}${row.code ? ` (${row.code})` : ''}`
}

export function formatHingeLabel(row: HingeRow) {
  return `${row.brand} ${row.model}${row.code ? ` (${row.code})` : ''}`
}

export function formatHandleLabel(row: HandleRow) {
  return row.supplier ? `${row.name} (${row.supplier})` : row.name
}

export function formatExtraLabel(row: ExtraRow) {
  return `${row.name} (${row.category_name})`
}

export function centsToAmountString(cents: number) {
  return ((cents || 0) / 100).toFixed(2)
}

export function amountStringToCents(value: string): number | null {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.round(parsed * 100)
}

export function bpsToPercentString(bps: number) {
  return (bps / 100).toFixed(2)
}

export function percentStringToBps(value: string): number | null {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.round(parsed * 100)
}

export function parsePositiveInteger(value: string) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) return null
  return Math.floor(parsed)
}

export function parseNonNegativeInteger(value: string) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.floor(parsed)
}

export function buildBoardPayload(draft: BoardDraft) {
  const brand = draft.brand.trim()
  const material = draft.material.trim()
  const thickness = parsePositiveInteger(draft.thickness)
  const length_mm = parsePositiveInteger(draft.length_mm)
  const width_mm = parsePositiveInteger(draft.width_mm)
  if (!brand || !material || thickness === null || length_mm === null || width_mm === null) {
    return null
  }
  return {
    brand,
    material,
    thickness,
    length_mm,
    width_mm,
    costing_mode: draft.costing_mode,
  }
}

export function buildSlidePayload(draft: SlideDraft) {
  const brand = draft.brand.trim()
  const model = draft.model.trim()
  const length = parseNonNegativeInteger(draft.length)
  const side_length = parseNonNegativeInteger(draft.side_length)
  const side_clearance_total = parseNonNegativeInteger(draft.side_clearance_total)
  const side_height_uplift = parseNonNegativeInteger(draft.side_height_uplift)
  if (
    !brand ||
    !model ||
    length === null ||
    side_length === null ||
    side_clearance_total === null ||
    side_height_uplift === null
  ) {
    return null
  }
  return {
    brand,
    model,
    code: draft.code.trim(),
    length,
    side_length,
    side_clearance_total,
    side_height_uplift,
  }
}

export function buildHingePayload(draft: HingeDraft) {
  const brand = draft.brand.trim()
  const model = draft.model.trim()
  const opening_angle_deg = parseNonNegativeInteger(draft.opening_angle_deg)
  if (!brand || !model || opening_angle_deg === null) {
    return null
  }
  return {
    brand,
    model,
    code: draft.code.trim(),
    opening_angle_deg,
  }
}

export function buildHandlePayload(draft: HandleDraft | HandleRow) {
  const name = draft.name.trim()
  if (!name) {
    return null
  }
  return {
    name,
    supplier: draft.supplier.trim(),
    code: draft.code.trim(),
  }
}

export function buildExtraPayload(draft: ExtraDraft | ExtraRow) {
  const name = draft.name.trim()
  if (!name || !draft.category_id) {
    return null
  }
  return {
    name,
    category_id: draft.category_id,
    supplier: draft.supplier.trim(),
    code: draft.code.trim(),
    notes: draft.notes.trim(),
  }
}

export function itemTypeDefaultUom(itemType: PriceItemType) {
  if (itemType === 'slide') return 'pairs'
  return 'pcs'
}

export function formatDateTime(value: string) {
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}
