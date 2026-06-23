import type { BoardDraft, BoardGrainPolicy, BoardTypeRow, DrawerSystemConfig, DrawerSystemFormulaRow, DrawerSystemKind, ExtraDraft, ExtraRow, HandleDraft, HandleRow, HandleType, HardwareAccessoryConfig, HardwareAccessoryRule, HingeDraft, HingeRow, ItemSupplierDraft, PriceItemType, SlideDraft, SlideMountType, SlideRangeDraft, SlideRow, SupplierDraft, SupplierRow } from './types'
export { formatCurrencyFromCents } from '@/lib/currency'

export function formatBoardLabel(row: BoardTypeRow) {
  return `${row.brand} ${row.material} ${row.thickness}mm (${row.length_mm}x${row.width_mm})`
}

export function formatBoardGrainPolicy(value: BoardGrainPolicy) {
  if (value === 'none') return 'No grain'
  if (value === 'optional') return 'Optional grain'
  return 'Grain required'
}

export function formatSlideLabel(row: SlideRow) {
  const rangeSuffix = row.product_family ? ` · ${row.product_family}` : ''
  const mountSuffix = row.mount_type && row.mount_type !== 'side_mount' ? ` · ${formatSlideMountType(row.mount_type)}` : ''
  return `${row.brand} ${row.model}${row.code ? ` (${row.code})` : ''}${rangeSuffix}${mountSuffix}`
}

export function formatDrawerSystemKind(value: DrawerSystemKind) {
  if (value === 'custom') return 'Custom system'
  return value === 'metal' ? 'Metal system' : 'Conventional slide'
}

export function formatSlideMountType(value: SlideMountType) {
  if (value === 'undermount') return 'Undermount'
  if (value === 'metal_system') return 'Metal-sided system'
  if (value === 'custom') return 'Custom'
  return 'Side mount'
}

export function formatHingeLabel(row: HingeRow) {
  return `${row.brand} ${row.model}${row.code ? ` (${row.code})` : ''}`
}

export function formatHandleLabel(row: HandleRow) {
  const typeSuffix = row.handle_type && row.handle_type !== 'standard' ? ` · ${formatHandleType(row.handle_type)}` : ''
  return `${row.supplier_name ? `${row.name} (${row.supplier_name})` : row.name}${typeSuffix}`
}

export function formatHandleType(value: HandleType) {
  if (value === 'full_length') return 'Full length'
  if (value === 'c_channel') return 'C channel'
  if (value === 'j_channel') return 'J channel'
  return 'Standard'
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
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) return null
  return Math.round(parsed * 100)
}

export function calculateDiscountedCostCents(listPriceCents: number, discountBps: number) {
  return Math.round(listPriceCents * (1 - discountBps / 10000))
}

export function calculateDiscountedAmountString(listPriceAmount: string, discountPercent: string) {
  const listPriceCents = amountStringToCents(listPriceAmount)
  const discountBps = percentStringToBps(discountPercent)
  if (listPriceCents === null || discountBps === null) return null
  return centsToAmountString(calculateDiscountedCostCents(listPriceCents, discountBps))
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

export function parseOptionalNonNegativeInteger(value: string) {
  if (!value.trim()) return 0
  return parseNonNegativeInteger(value)
}

export function normalizeAccessoryConfig(config: HardwareAccessoryConfig | undefined): HardwareAccessoryConfig {
  const accessories = Array.isArray(config?.accessories) ? config.accessories : []
  return {
    ...(config ?? {}),
    accessories: accessories.map(normalizeAccessoryRule).filter((rule) => rule.item_ref_id || rule.name.trim()),
  }
}

export function emptyAccessoryRule(): HardwareAccessoryRule {
  return {
    item_type: 'extra',
    item_ref_id: '',
    name: '',
    supplier: '',
    code: '',
    quantity: 1,
    quantity_rule: 'per_unit',
    required: true,
    enabled: false,
    uom: 'pcs',
    condition: {
      field: 'always',
      operator: 'always',
      value_number: null,
      value_text: '',
    },
  }
}

export function normalizeDrawerSystemConfig(config: DrawerSystemConfig | undefined, drawerSystemKind: DrawerSystemKind): DrawerSystemConfig {
  if (drawerSystemKind !== 'metal') {
    return {}
  }
  const source = config ?? {}
  const next: DrawerSystemConfig = {
    ...source,
    product_family: stringValue(source.product_family),
    manufacturer: stringValue(source.manufacturer),
    finish: stringValue(source.finish),
    side_height_mm: nullableNonNegativeNumber(source.side_height_mm),
    load_class: stringValue(source.load_class),
    installation_width_mm: nullableNonNegativeNumber(source.installation_width_mm),
    compatible_side_thicknesses: numberListValue(source.compatible_side_thicknesses),
    compatible_nominal_lengths: numberListValue(source.compatible_nominal_lengths),
    min_internal_width_mm: nullableNonNegativeNumber(source.min_internal_width_mm),
    max_internal_width_mm: nullableNonNegativeNumber(source.max_internal_width_mm),
    min_depth_mm: nullableNonNegativeNumber(source.min_depth_mm),
    min_front_height_mm: nullableNonNegativeNumber(source.min_front_height_mm),
    max_front_height_mm: nullableNonNegativeNumber(source.max_front_height_mm),
    supplied_metal_sides: Boolean(source.supplied_metal_sides ?? true),
    supplied_steel_back: Boolean(source.supplied_steel_back ?? false),
    cut_board_back: Boolean(source.cut_board_back ?? false),
    cut_bottom_panel: Boolean(source.cut_bottom_panel ?? true),
    cut_inset_panel: Boolean(source.cut_inset_panel ?? false),
    variables: typeof source.variables === 'object' && source.variables ? source.variables : {},
  }
  next.panel_formulas = drawerSystemFormulaRows(next)
  return next
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
    grain_policy: draft.grain_policy,
  }
}

export function buildSlidePayload(draft: SlideDraft) {
  const brand = draft.brand.trim()
  const model = draft.model.trim()
  const length = parseNonNegativeInteger(draft.length)
  const side_length = parseNonNegativeInteger(draft.side_length)
  const side_clearance_total = parseNonNegativeInteger(draft.side_clearance_total)
  const side_height_uplift = parseNonNegativeInteger(draft.side_height_uplift)
  const required_depth_mm = parseOptionalNonNegativeInteger(draft.required_depth_mm)
  const drawer_depth_deduction_mm = parseOptionalNonNegativeInteger(draft.drawer_depth_deduction_mm)
  const box_width_deduction_mm = parseOptionalNonNegativeInteger(draft.box_width_deduction_mm)
  if (
    !brand ||
    !model ||
    length === null ||
    side_length === null ||
    side_clearance_total === null ||
    side_height_uplift === null ||
    required_depth_mm === null ||
    drawer_depth_deduction_mm === null ||
    box_width_deduction_mm === null
  ) {
    return null
  }
  const drawer_system_kind = draft.drawer_system_kind === 'metal' || draft.drawer_system_kind === 'custom' ? draft.drawer_system_kind : 'conventional'
  const drawer_system_config = normalizeDrawerSystemConfig(draft.drawer_system_config, drawer_system_kind)
  return {
    brand,
    model,
    code: draft.code.trim(),
    length,
    side_length,
    side_clearance_total,
    side_height_uplift,
    mount_type: draft.mount_type,
    product_family: draft.product_family.trim(),
    required_depth_mm,
    drawer_depth_deduction_mm,
    box_width_deduction_mm,
    drawer_system_kind,
    drawer_system_config,
    accessory_config: normalizeAccessoryConfig(draft.accessory_config),
  }
}

export function buildSlideRangePayload(draft: SlideRangeDraft) {
  const brand = draft.brand.trim()
  const product_family = draft.product_family.trim()
  const side_clearance_total = parseOptionalNonNegativeInteger(draft.side_clearance_total)
  const side_height_uplift = parseOptionalNonNegativeInteger(draft.side_height_uplift)
  const drawer_depth_deduction_mm = parseOptionalNonNegativeInteger(draft.drawer_depth_deduction_mm)
  const box_width_deduction_mm = parseOptionalNonNegativeInteger(draft.box_width_deduction_mm)
  const required_depth_mm = parseOptionalNonNegativeInteger(draft.required_depth_mm)
  let hasInvalidLengthRow = false
  const lengths = draft.lengths
    .flatMap((row) => {
      if (!row.length.trim()) return []
      const length = parsePositiveInteger(row.length)
      const side_length = parseOptionalNonNegativeInteger(row.side_length)
      const row_required_depth_mm = parseOptionalNonNegativeInteger(row.required_depth_mm)
      const row_depth_deduction = parseOptionalNonNegativeInteger(row.drawer_depth_deduction_mm)
      const row_box_width_deduction = parseOptionalNonNegativeInteger(row.box_width_deduction_mm)
      if (
        length === null ||
        side_length === null ||
        row_required_depth_mm === null ||
        row_depth_deduction === null ||
        row_box_width_deduction === null
      ) {
        hasInvalidLengthRow = true
        return []
      }
      return [{
        length,
        code: row.code.trim(),
        ...(row.side_length.trim() ? { side_length } : {}),
        ...(row.required_depth_mm.trim() ? { required_depth_mm: row_required_depth_mm } : {}),
        ...(row.drawer_depth_deduction_mm.trim() ? { drawer_depth_deduction_mm: row_depth_deduction } : {}),
        ...(row.box_width_deduction_mm.trim() ? { box_width_deduction_mm: row_box_width_deduction } : {}),
      }]
    })
  if (
    !brand ||
    !product_family ||
    hasInvalidLengthRow ||
    !lengths.length ||
    side_clearance_total === null ||
    side_height_uplift === null ||
    drawer_depth_deduction_mm === null ||
    box_width_deduction_mm === null ||
    required_depth_mm === null
  ) {
    return null
  }
  const drawer_system_kind = draft.mount_type === 'metal_system' ? 'metal' : draft.mount_type === 'custom' ? 'custom' : 'conventional'
  return {
    brand,
    product_family,
    mount_type: draft.mount_type,
    code_pattern: draft.code_pattern.trim(),
    lengths,
    side_clearance_total,
    side_height_uplift,
    drawer_depth_deduction_mm,
    box_width_deduction_mm,
    required_depth_mm,
    drawer_system_kind,
    drawer_system_config: normalizeDrawerSystemConfig(draft.drawer_system_config, drawer_system_kind),
    accessory_config: normalizeAccessoryConfig(draft.accessory_config),
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
    accessory_config: normalizeAccessoryConfig(draft.accessory_config),
  }
}

function normalizeAccessoryRule(rule: HardwareAccessoryRule): HardwareAccessoryRule {
  const quantity = Number(rule.quantity)
  const item_ref_id = stringValue(rule.item_ref_id)
  return {
    ...emptyAccessoryRule(),
    ...rule,
    item_type: rule.item_type ?? 'extra',
    item_ref_id,
    name: item_ref_id ? '' : stringValue(rule.name),
    supplier: '',
    code: '',
    quantity: Number.isFinite(quantity) && quantity >= 0 ? Math.floor(quantity) : 0,
    quantity_rule: rule.quantity_rule ?? 'per_unit',
    required: Boolean(rule.required),
    enabled: Boolean(rule.enabled),
    uom: stringValue(rule.uom) || 'pcs',
    condition: {
      field: rule.condition?.field ?? 'always',
      operator: rule.condition?.operator ?? 'always',
      value_number: nullableNumber(rule.condition?.value_number),
      value_text: stringValue(rule.condition?.value_text),
    },
  }
}

function drawerSystemFormulaRows(config: DrawerSystemConfig): DrawerSystemFormulaRow[] {
  const rows: DrawerSystemFormulaRow[] = []
  const installationWidthFormula = 'inner_w - (2 * installation_width_mm)'
  if (config.cut_bottom_panel) {
    rows.push({
      name: 'Metal Drawer Bottom',
      section: 'carcass',
      length_formula: installationWidthFormula,
      width_formula: 'slide_length - 19',
      qty_formula: 'num_drawers',
    })
  }
  if (config.cut_board_back) {
    rows.push({
      name: 'Cut Board Back',
      section: 'carcass',
      length_formula: installationWidthFormula,
      width_formula: config.side_height_mm ? 'side_height_mm - 12' : 'drawer_side_height',
      qty_formula: 'num_drawers',
    })
  }
  if (config.cut_inset_panel) {
    rows.push({
      name: 'Designer Inset Panel',
      section: 'panel',
      length_formula: 'inner_w - 6',
      width_formula: 'drawer_front_height - 6',
      qty_formula: 'num_drawers',
    })
  }
  return rows
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}

function nullableNumber(value: unknown) {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function nullableNonNegativeNumber(value: unknown) {
  const parsed = nullableNumber(value)
  return parsed === null || parsed < 0 ? null : Math.floor(parsed)
}

function numberListValue(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.map((entry) => nullableNonNegativeNumber(entry)).filter((entry): entry is number => entry !== null)
}

export function buildSupplierPayload(draft: SupplierDraft | SupplierRow) {
  const name = draft.name.trim()
  const default_discount_bps =
    'default_discount_percent' in draft
      ? percentStringToBps(draft.default_discount_percent)
      : draft.default_discount_bps
  if (!name) {
    return null
  }
  if (default_discount_bps === null || default_discount_bps < 0 || default_discount_bps > 10000) {
    return null
  }
  return {
    name,
    code: draft.code.trim(),
    contact_name: draft.contact_name.trim(),
    email: draft.email.trim(),
    phone: draft.phone.trim(),
    notes: draft.notes.trim(),
    default_discount_bps,
  }
}

export function buildItemSupplierPayload(draft: ItemSupplierDraft) {
  const item_ref_id = draft.item_ref_id.trim()
  const supplier_id = draft.supplier_id.trim()
  const price_component = draft.price_component.trim().toLowerCase()
  const order_uom = draft.order_uom.trim().toLowerCase()
  if (!item_ref_id || !supplier_id || !price_component || !order_uom) {
    return null
  }
  return {
    item_type: draft.item_type,
    item_ref_id,
    supplier_id,
    supplier_sku: draft.supplier_sku.trim(),
    supplier_description: draft.supplier_description.trim(),
    price_component,
    order_uom,
    is_preferred: draft.is_preferred,
    notes: draft.notes.trim(),
  }
}

export function buildHandlePayload(draft: HandleDraft | HandleRow) {
  const name = draft.name.trim()
  if (!name) {
    return null
  }
  const handleType = draft.handle_type === 'full_length' || draft.handle_type === 'c_channel' || draft.handle_type === 'j_channel'
    ? draft.handle_type
    : 'standard'
  const rawReduction = typeof draft.front_reduction_mm === 'number' ? draft.front_reduction_mm : Number(draft.front_reduction_mm)
  const frontReductionMm = Number.isFinite(rawReduction) && rawReduction > 0 ? Math.floor(rawReduction) : 0
  return {
    name,
    supplier_id: draft.supplier_id || null,
    handle_type: handleType,
    front_reduction_mm: handleType === 'standard' ? 0 : frontReductionMm,
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
    supplier_id: draft.supplier_id || null,
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
