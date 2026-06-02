import { customUnitTypeValue, fallbackUnitDefaults, panelPresetFamily, panelPresetKeys } from './constants'
import type {
  PanelPresetKey,
  QuoteCustomPanelAutoConfig,
  QuoteCustomPanelPresetConfig,
  QuoteCustomPanelsState,
  QuoteDraft,
  QuoteRow,
  UnitDefaults,
  UnitDraft,
  UnitPresetKey,
  UnitRow,
} from './types'

export function formatCents(value: number | null): string {
  if (value == null) return '-'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value / 100)
}

export function formatPercentFromBps(bps: number): string {
  return `${(bps / 100).toFixed(2)}%`
}

export function resolvedUnitType(draft: UnitDraft): string {
  if (draft.unit_type_key === customUnitTypeValue) {
    return draft.custom_unit_type_key.trim() || 'Custom Unit'
  }
  return draft.unit_type_key
}

export function unitPayloadFromDraft(draft: UnitDraft) {
  const unitType = resolvedUnitType(draft)
  const isDrawer = unitType.toLowerCase().includes('draw')
  return {
    unit_type_key: unitType,
    height: parsePositiveInteger(draft.height, 780),
    width: parsePositiveInteger(draft.width, 600),
    depth: parsePositiveInteger(draft.depth, 580),
    thickness: parsePositiveInteger(draft.thickness, 16),
    carcass_board_type_id: optionalId(draft.carcass_board_type_id),
    door_board_type_id: optionalId(draft.door_board_type_id),
    extra_params: isDrawer
      ? {
          num_drawers: parsePositiveInteger(draft.num_drawers, 3),
        }
      : {
          num_doors: parsePositiveInteger(draft.num_doors, 2),
          num_shelves: parseNonNegativeInteger(draft.num_shelves, 1),
        },
  }
}

export function quotePayloadFromDraft(draft: QuoteDraft) {
  return {
    name: draft.name.trim(),
    notes: draft.notes.trim(),
    default_carcass_board_type_id: optionalId(draft.default_carcass_board_type_id),
    default_door_board_type_id: optionalId(draft.default_door_board_type_id),
    default_panel_board_type_id: optionalId(draft.default_panel_board_type_id),
    default_slide_id: optionalId(draft.default_slide_id),
    default_hinge_id: optionalId(draft.default_hinge_id),
    default_base_handle_id: optionalId(draft.default_base_handle_id),
    default_wall_handle_id: optionalId(draft.default_wall_handle_id),
    default_tall_handle_id: optionalId(draft.default_tall_handle_id),
    default_drawer_handle_id: optionalId(draft.default_drawer_handle_id),
    unit_defaults: {
      'Base Draw': {
        height: parsePositiveInteger(draft.base_draw_height, fallbackUnitDefaults['Base Draw'].height),
        depth: parsePositiveInteger(draft.base_draw_depth, fallbackUnitDefaults['Base Draw'].depth),
      },
      'Base Door': {
        height: parsePositiveInteger(draft.base_door_height, fallbackUnitDefaults['Base Door'].height),
        depth: parsePositiveInteger(draft.base_door_depth, fallbackUnitDefaults['Base Door'].depth),
      },
      'Wall Door': {
        height: parsePositiveInteger(draft.wall_door_height, fallbackUnitDefaults['Wall Door'].height),
        depth: parsePositiveInteger(draft.wall_door_depth, fallbackUnitDefaults['Wall Door'].depth),
      },
      'Tall Door': {
        height: parsePositiveInteger(draft.tall_door_height, fallbackUnitDefaults['Tall Door'].height),
        depth: parsePositiveInteger(draft.tall_door_depth, fallbackUnitDefaults['Tall Door'].depth),
      },
    },
  }
}

export function toQuoteDraft(quote: QuoteRow): QuoteDraft {
  const baseDraw = resolveDefaultDims(quote.unit_defaults, 'Base Draw')
  const baseDoor = resolveDefaultDims(quote.unit_defaults, 'Base Door')
  const wallDoor = resolveDefaultDims(quote.unit_defaults, 'Wall Door')
  const tallDoor = resolveDefaultDims(quote.unit_defaults, 'Tall Door')

  return {
    name: quote.name,
    notes: quote.notes,
    default_carcass_board_type_id: quote.default_carcass_board_type_id ?? '',
    default_door_board_type_id: quote.default_door_board_type_id ?? '',
    default_panel_board_type_id: quote.default_panel_board_type_id ?? '',
    default_slide_id: quote.default_slide_id ?? '',
    default_hinge_id: quote.default_hinge_id ?? '',
    default_base_handle_id: quote.default_base_handle_id ?? '',
    default_wall_handle_id: quote.default_wall_handle_id ?? '',
    default_tall_handle_id: quote.default_tall_handle_id ?? '',
    default_drawer_handle_id: quote.default_drawer_handle_id ?? '',
    base_draw_height: String(baseDraw.height),
    base_draw_depth: String(baseDraw.depth),
    base_door_height: String(baseDoor.height),
    base_door_depth: String(baseDoor.depth),
    wall_door_height: String(wallDoor.height),
    wall_door_depth: String(wallDoor.depth),
    tall_door_height: String(tallDoor.height),
    tall_door_depth: String(tallDoor.depth),
  }
}

export function resolveDefaultDims(defaults: UnitDefaults, unitType: UnitPresetKey) {
  const row = defaults[unitType]
  if (!row) return fallbackUnitDefaults[unitType]
  return {
    height: row.height > 0 ? row.height : fallbackUnitDefaults[unitType].height,
    depth: row.depth > 0 ? row.depth : fallbackUnitDefaults[unitType].depth,
  }
}

export function countPanelFamilies(units: UnitRow[]): Record<'base' | 'wall' | 'tall', number> {
  const counts: Record<'base' | 'wall' | 'tall', number> = { base: 0, wall: 0, tall: 0 }
  for (const unit of units) {
    const value = unit.unit_type_key.toLowerCase()
    if (value.includes('base')) {
      counts.base += 1
      continue
    }
    if (value.includes('wall')) {
      counts.wall += 1
      continue
    }
    if (value.includes('tall')) {
      counts.tall += 1
    }
  }
  return counts
}

export function normalizeQuoteCustomPanelsState(
  state: QuoteCustomPanelsState | null | undefined,
  quote: QuoteRow | null,
  units: UnitRow[],
): QuoteCustomPanelsState {
  const familyCounts = countPanelFamilies(units)
  const baseDoorDepth = resolveDefaultDims(quote?.unit_defaults ?? fallbackUnitDefaults, 'Base Door').depth
  const wallDoorDepth = resolveDefaultDims(quote?.unit_defaults ?? fallbackUnitDefaults, 'Wall Door').depth
  const defaultPanelBoardId = quote?.default_panel_board_type_id ?? null

  const presets = panelPresetKeys.reduce<Partial<Record<PanelPresetKey, QuoteCustomPanelPresetConfig>>>((accumulator, key) => {
    const family = panelPresetFamily[key]
    const defaultQty = familyCounts[family] > 0 ? 1 : 0
    const source = state?.presets?.[key]
    accumulator[key] = {
      qty: toNonNegativeInteger(source?.qty, defaultQty),
      board_type_id: source?.board_type_id ?? defaultPanelBoardId,
    }
    return accumulator
  }, {})

  const manual = (state?.manual ?? []).map((row) => ({
    name: (row.name || 'Custom Panel').trim() || 'Custom Panel',
    length: toNonNegativeInteger(row.length, 0),
    width: toNonNegativeInteger(row.width, 0),
    qty: toNonNegativeInteger(row.qty, 0),
    board_type_id: row.board_type_id ?? defaultPanelBoardId,
  }))

  const sourceAuto = state?.auto
  const auto: QuoteCustomPanelAutoConfig = {
    kicker_board_type_id: sourceAuto?.kicker_board_type_id ?? defaultPanelBoardId,
    pelmet_board_type_id: sourceAuto?.pelmet_board_type_id ?? defaultPanelBoardId,
    kicker_return_count: toNonNegativeInteger(sourceAuto?.kicker_return_count, 0),
    kicker_return_depth_mm: toNonNegativeInteger(sourceAuto?.kicker_return_depth_mm, baseDoorDepth || 580),
    kicker_override_on: Boolean(sourceAuto?.kicker_override_on),
    kicker_override_qty: toNonNegativeInteger(sourceAuto?.kicker_override_qty, 0),
    kicker_override_length: toNonNegativeInteger(sourceAuto?.kicker_override_length, 0),
    kicker_override_width: toNonNegativeInteger(sourceAuto?.kicker_override_width, 100),
    pelmet_override_on: Boolean(sourceAuto?.pelmet_override_on),
    pelmet_override_qty: toNonNegativeInteger(sourceAuto?.pelmet_override_qty, 0),
    pelmet_override_length: toNonNegativeInteger(sourceAuto?.pelmet_override_length, 0),
    pelmet_override_width: toNonNegativeInteger(sourceAuto?.pelmet_override_width, wallDoorDepth || 330),
  }

  return { presets, manual, auto }
}

export function numberFromExtra(extra: Record<string, unknown>, key: string, fallback: number): number {
  const value = extra[key]
  if (typeof value === 'number' && Number.isFinite(value)) return Math.floor(value)
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return Math.floor(parsed)
  }
  return fallback
}

export function formatExtraParams(extra: Record<string, unknown>): string {
  const entries = Object.entries(extra)
  if (entries.length === 0) return '-'
  return entries
    .map(([key, value]) => `${key}:${String(value)}`)
    .join(', ')
}

export function optionalId(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

export function parsePositiveInteger(value: string, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 1) return fallback
  return Math.floor(parsed)
}

export function parseNonNegativeInteger(value: string, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return fallback
  return Math.floor(parsed)
}

export function toNonNegativeInteger(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value) && value >= 0) return Math.floor(value)
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed) && parsed >= 0) return Math.floor(parsed)
  }
  return fallback
}
