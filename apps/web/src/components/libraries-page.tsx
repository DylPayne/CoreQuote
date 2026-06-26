import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  CircleDollarSign,
  ClipboardCheck,
  CircleDashed,
  Eye,
  ExternalLink,
  FileSpreadsheet,
  LoaderCircle,
  PackagePlus,
  Percent,
  Plus,
  RefreshCcw,
  Save,
  Search,
  SquareCheckBig,
  Upload,
  XCircle,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent, type ReactNode } from 'react'

import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { ControlGroup, ControlGroupItem } from '@/components/ui/control-group'
import { Dialog } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { apiRequest, upsertPriceItem } from '@/components/libraries/api'
import { defaultBoardDraft, defaultExtraCategoryDraft, defaultExtraDraft, defaultHandleDraft, defaultHingeDraft, defaultItemSupplierDraft, defaultPriceListDraft, defaultSlideRangeDraft, defaultSupplierDraft } from '@/components/libraries/constants'
import { amountStringToCents, bpsToPercentString, buildBoardPayload, buildExtraPayload, buildHandlePayload, buildHingePayload, buildItemSupplierPayload, buildSlidePayload, buildSlideRangePayload, buildSupplierPayload, calculateDiscountedAmountString, centsToAmountString, emptyAccessoryRule, formatBoardLabel, formatCurrencyFromCents, formatDateTime, formatExtraLabel, formatHandleLabel, formatHingeLabel, formatSlideLabel, formatSlideMountType, itemTypeDefaultUom, normalizeAccessoryConfig, percentStringToBps } from '@/components/libraries/helpers'
import { DrawerSystemConfigEditor, HardwareAccessoryConfigEditor, LibraryBoardsTable, LibraryExtraCategoriesTable, LibraryExtrasTable, LibraryHandlesTable, LibraryHingesTable, LibrarySlidesTable } from '@/components/libraries/tables'
import type { HardwareAccessoryOptions } from '@/components/libraries/tables'
import { PricingSettingsEditor } from '@/components/pricing-settings-editor'
import { defaultPricingSettingsDraft, pricingSettingsPayloadFromDraft, pricingSettingsToDraft, type PricingSettingsDraft } from '@/components/pricing-settings'
import { currencyLabel, normalizeCurrencyCode } from '@/lib/currency'
import type { BoardDraft, BoardGrainPolicy, BoardTypeRow, ExtraCategoryDraft, ExtraCategoryRow, ExtraDraft, ExtraRow, GeneratePriceListSummary, HandleDraft, HandleRow, HandleType, HardwareAccessoryConfig, HardwareAccessoryRule, HingeDraft, HingeRow, ItemSupplierDraft, ItemSupplierRow, LibraryBulkUpdateResult, LibraryCatalogBulkResource, LibraryEffectiveStatus, LibraryImportApplyRequest, LibraryImportApplyResult, LibraryImportApplyRowStatus, LibraryImportPreview, LibraryImportPreviewRequest, LibraryImportResource, LibraryImportRowStatus, LibraryImportSourceFormat, LibrarySetupActionTarget, LibrarySetupChecklist, LibrarySetupItemStatus, LibraryTab, PriceItemType, PriceListDraft, PriceListItemRow, PriceListRow, PricingCoverage, PricingCoverageGroup, PricingCoverageRow, PricingCoverageStatus, PricingSettingsRow, SlideMountType, SlideRangeCreateResponse, SlideRangeDraft, SlideRangeLengthDraft, SlideRow, SupplierDiscountSummary, SupplierDraft, SupplierRow } from '@/components/libraries/types'

const priceItemTypes: PriceItemType[] = ['slide', 'hinge', 'handle', 'extra', 'board']

const generationTypeOptions: Array<{ label: string; value: PriceItemType }> = [
  { label: 'Slides', value: 'slide' },
  { label: 'Hinges', value: 'hinge' },
  { label: 'Handles', value: 'handle' },
  { label: 'Extras', value: 'extra' },
  { label: 'Boards', value: 'board' },
]

const handleTypeOptions: Array<{ label: string; value: HandleType }> = [
  { label: 'Standard', value: 'standard' },
  { label: 'Full length', value: 'full_length' },
  { label: 'C channel', value: 'c_channel' },
  { label: 'J channel', value: 'j_channel' },
]

const importResourceOptions: Array<{ label: string; value: LibraryImportResource }> = [
  { label: 'Boards', value: 'boards' },
  { label: 'Slides', value: 'slides' },
  { label: 'Hinges', value: 'hinges' },
  { label: 'Handles', value: 'handles' },
  { label: 'Suppliers', value: 'suppliers' },
  { label: 'Extra categories', value: 'extra_categories' },
  { label: 'Extras', value: 'extras' },
  { label: 'Supplier item costs', value: 'supplier_item_costs' },
  { label: 'Price list rows', value: 'price_list_items' },
]

const importSourceFormatOptions: Array<{ label: string; value: LibraryImportSourceFormat }> = [
  { label: 'CSV', value: 'csv' },
  { label: 'TSV', value: 'tsv' },
  { label: 'XLSX', value: 'xlsx' },
]

const boardGrainPolicyOptions: Array<{ label: string; value: BoardGrainPolicy }> = [
  { label: 'Grain required', value: 'required' },
  { label: 'Optional grain', value: 'optional' },
  { label: 'No grain', value: 'none' },
]

type RecentFilterValue = 'all' | '7' | '30' | '90'
type PriceStatusFilterValue = 'all' | LibraryEffectiveStatus
type PriceTypeFilterValue = 'all' | PriceItemType
type PriceSourceFilterValue = 'all' | PriceListItemRow['cost_source']
type PricingSubTab = 'coverage' | 'settings' | 'lists' | 'quick-update' | 'history' | 'all-prices'
type BulkAccessoryResource = Extract<LibraryCatalogBulkResource, 'slides' | 'hinges'>
type CreateCatalogResource = LibraryCatalogBulkResource | 'extra-categories'
type CatalogBulkMode = 'fields' | 'accessories'
type PricingOption = { label: string; value: string }

type CatalogBulkField = {
  label: string
  value: string
  input: 'text' | 'select' | 'percent' | 'number'
  options?: Array<{ label: string; value: string }>
}

type MissingPriceRow = {
  id: string
  item_type: PriceItemType
  label: string
  components: string[]
}

const recentFilterOptions: Array<{ label: string; value: RecentFilterValue }> = [
  { label: 'Any time', value: 'all' },
  { label: 'Last 7 days', value: '7' },
  { label: 'Last 30 days', value: '30' },
  { label: 'Last 90 days', value: '90' },
]

const priceStatusOptions: Array<{ label: string; value: PriceStatusFilterValue }> = [
  { label: 'All price rows', value: 'all' },
  { label: 'Used for new totals', value: 'current' },
  { label: 'Starts later', value: 'future' },
  { label: 'History only', value: 'retired' },
]

const priceSourceOptions: Array<{ label: string; value: PriceSourceFilterValue }> = [
  { label: 'Any source', value: 'all' },
  { label: 'Manual edit', value: 'manual' },
  { label: 'From supplier cost', value: 'supplier' },
  { label: 'Manual override', value: 'override' },
  { label: 'Imported', value: 'import' },
]

const pricingSubTabs: Array<{ label: string; value: PricingSubTab }> = [
  { label: 'Coverage', value: 'coverage' },
  { label: 'Pricing Settings', value: 'settings' },
  { label: 'Supplier Costs & Lists', value: 'lists' },
  { label: 'Manual Override', value: 'quick-update' },
  { label: 'Price History', value: 'history' },
  { label: 'All Prices', value: 'all-prices' },
]

const priceComponentOptionsByValue: Record<string, PricingOption> = {
  unit: { label: 'Unit', value: 'unit' },
  sqm: { label: 'Square metre', value: 'sqm' },
  sheet: { label: 'Sheet', value: 'sheet' },
  edging_m: { label: 'Edging / m', value: 'edging_m' },
  labour_board: { label: 'Labour / board', value: 'labour_board' },
}

const orderUomOptionsByValue: Record<string, PricingOption> = {
  sheet: { label: 'Sheet', value: 'sheet' },
  m2: { label: 'Square metre', value: 'm2' },
  m: { label: 'Metre', value: 'm' },
  pairs: { label: 'Pairs', value: 'pairs' },
  pcs: { label: 'Pieces', value: 'pcs' },
  each: { label: 'Each', value: 'each' },
  unit: { label: 'Unit', value: 'unit' },
  set: { label: 'Set', value: 'set' },
  day: { label: 'Day', value: 'day' },
  trip: { label: 'Trip', value: 'trip' },
  board: { label: 'Board', value: 'board' },
}

const catalogBulkFields: Record<LibraryCatalogBulkResource, CatalogBulkField[]> = {
  boards: [
    {
      input: 'select',
      label: 'Costing mode',
      options: [
        { label: 'Sheet', value: 'sheet' },
        { label: 'Square metre', value: 'sqm' },
      ],
      value: 'costing_mode',
    },
    {
      input: 'select',
      label: 'Grain',
      options: boardGrainPolicyOptions,
      value: 'grain_policy',
    },
  ],
  slides: [
    { input: 'text', label: 'Brand', value: 'brand' },
    { input: 'text', label: 'Code', value: 'code' },
  ],
  hinges: [
    { input: 'text', label: 'Brand', value: 'brand' },
    { input: 'text', label: 'Code', value: 'code' },
  ],
  handles: [
    { input: 'select', label: 'Supplier', value: 'supplier_id' },
    { input: 'select', label: 'Handle type', options: handleTypeOptions, value: 'handle_type' },
    { input: 'number', label: 'Front reduction (mm)', value: 'front_reduction_mm' },
  ],
  extras: [
    { input: 'select', label: 'Category', value: 'category_id' },
    { input: 'select', label: 'Supplier', value: 'supplier_id' },
    { input: 'text', label: 'Code', value: 'code' },
    { input: 'text', label: 'Notes', value: 'notes' },
  ],
  suppliers: [
    { input: 'text', label: 'Contact', value: 'contact_name' },
    { input: 'text', label: 'Email', value: 'email' },
    { input: 'text', label: 'Phone', value: 'phone' },
    { input: 'text', label: 'Notes', value: 'notes' },
    { input: 'percent', label: 'Default discount', value: 'default_discount_bps' },
  ],
}

const importExampleByResource: Record<LibraryImportResource, string> = {
  boards: 'Brand,Material,Thickness,Length (mm),Width (mm),Costing Mode,Grain Policy\nPG Bison,MelaWood,16,2750,1830,sheet,required',
  slides: 'Brand,Model,Code,Length (mm),Drawer System Kind,Drawer System Config\nGrass,Dynapro,DYN-500,500,conventional,{}',
  hinges: 'Brand,Model,Code,Opening Angle\nBlum,Clip Top,BL-110,110',
  handles: 'Name,Supplier,Handle Type,Front Reduction (mm)\nSlim Bar,Hafele,standard,0',
  suppliers: 'Name,Code,Contact,Email,Default Discount\nGrass ZA,GRASS-ZA,Sales,sales@example.com,30%',
  extra_categories: 'Name\nAppliances',
  extras: 'Name,Category,Supplier,Code\nStove,Appliances,Defy,DFY-600',
  supplier_item_costs: 'Item Type,Brand,Model,Code,Supplier,Order Unit,Unit Cost\nslide,Grass,Dynapro,DYN-500,Grass ZA,pairs,479.49',
  price_list_items: 'Item Type,Name,Supplier,Price Component,Unit,Price\nhandle,Slim Bar,Hafele,unit,pcs,89.00',
}

function searchTextMatches(search: string, parts: Array<string | number | null | undefined>) {
  const query = search.trim().toLowerCase()
  if (!query) return true
  return parts.some((part) => String(part ?? '').toLowerCase().includes(query))
}

function matchesRecent(updatedAt: string, recentDays: RecentFilterValue) {
  if (recentDays === 'all') return true
  const updatedTime = new Date(updatedAt).getTime()
  if (Number.isNaN(updatedTime)) return true
  const cutoff = Date.now() - Number(recentDays) * 24 * 60 * 60 * 1000
  return updatedTime >= cutoff
}

function catalogResourceForTab(tab: LibraryTab): LibraryCatalogBulkResource | null {
  if (tab === 'boards' || tab === 'slides' || tab === 'hinges' || tab === 'handles' || tab === 'extras' || tab === 'suppliers') {
    return tab
  }
  return null
}

function toggleId(ids: string[], itemId: string, checked: boolean) {
  if (checked) return ids.includes(itemId) ? ids : [...ids, itemId]
  return ids.filter((id) => id !== itemId)
}

function onlyVisibleSelected(selectedIds: string[], visibleIds: string[]) {
  const visible = new Set(visibleIds)
  return selectedIds.filter((id) => visible.has(id))
}

function emptyBulkAccessoryConfig(): HardwareAccessoryConfig {
  return { accessories: [emptyAccessoryRule()] }
}

function emptySlideRangeLengthDraft(length = ''): SlideRangeLengthDraft {
  return {
    length,
    code: '',
    side_length: '',
    required_depth_mm: '',
    drawer_depth_deduction_mm: '',
    box_width_deduction_mm: '',
  }
}

function slideRangeNumericValue(value: string, fallback = 0) {
  if (!value.trim()) return fallback
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? Math.floor(parsed) : fallback
}

function slideRangeOptionalNumericValue(value: string) {
  if (!value.trim()) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? Math.floor(parsed) : null
}

function codeFromRangePattern(pattern: string, length: number) {
  const trimmed = pattern.trim()
  if (!trimmed) return ''
  return trimmed.includes('{length}') ? trimmed.replaceAll('{length}', String(length)) : `${trimmed}-${length}`
}

function slideRangePreviewRows(draft: SlideRangeDraft) {
  const clearance = slideRangeNumericValue(draft.side_clearance_total)
  const depthDeduction = slideRangeNumericValue(draft.drawer_depth_deduction_mm)
  const configuredWidthDeduction = slideRangeNumericValue(draft.box_width_deduction_mm)
  const widthDeduction = configuredWidthDeduction > 0 ? configuredWidthDeduction : 2 * clearance
  const requiredDepthDefault = slideRangeNumericValue(draft.required_depth_mm)
  const rows: Array<{ code: string; length: number; model: string; requiredDepth: number; sideLength: number; widthDeduction: number }> = []
  for (const row of draft.lengths) {
    const length = slideRangeOptionalNumericValue(row.length)
    if (!length || length <= 0) continue
    const rowDepthDeduction = slideRangeOptionalNumericValue(row.drawer_depth_deduction_mm) ?? depthDeduction
    const rowWidthDeduction = slideRangeOptionalNumericValue(row.box_width_deduction_mm) ?? widthDeduction
    const sideLength = slideRangeOptionalNumericValue(row.side_length) ?? Math.max(0, length - rowDepthDeduction)
    const requiredDepth = (slideRangeOptionalNumericValue(row.required_depth_mm) ?? requiredDepthDefault) || length
    rows.push({
      code: row.code.trim() || codeFromRangePattern(draft.code_pattern, length),
      length,
      model: `${draft.product_family.trim()} ${length}`.trim(),
      requiredDepth,
      sideLength,
      widthDeduction: rowWidthDeduction > 0 ? rowWidthDeduction : widthDeduction,
    })
  }
  return rows
}

function rangeDraftForMountType(draft: SlideRangeDraft, mountType: SlideMountType): SlideRangeDraft {
  const currentConfig = draft.drawer_system_config ?? {}
  if (mountType === 'metal_system') {
    return {
      ...draft,
      mount_type: mountType,
      side_clearance_total: draft.side_clearance_total || '26',
      drawer_depth_deduction_mm: draft.drawer_depth_deduction_mm || '0',
      box_width_deduction_mm: draft.box_width_deduction_mm === '0' ? '58' : draft.box_width_deduction_mm || '58',
      drawer_system_config: {
        ...currentConfig,
        product_family: currentConfig.product_family || draft.product_family,
        supplied_metal_sides: true,
        cut_bottom_panel: currentConfig.cut_bottom_panel ?? true,
        installation_width_mm: currentConfig.installation_width_mm ?? 29,
      },
    }
  }
  if (mountType === 'undermount') {
    return {
      ...draft,
      mount_type: mountType,
      side_clearance_total: '0',
      drawer_depth_deduction_mm: draft.drawer_depth_deduction_mm === '0' ? '10' : draft.drawer_depth_deduction_mm || '10',
      box_width_deduction_mm: draft.box_width_deduction_mm === '0' ? '42' : draft.box_width_deduction_mm || '42',
      drawer_system_config: {},
    }
  }
  if (mountType === 'side_mount') {
    return {
      ...draft,
      mount_type: mountType,
      side_clearance_total: draft.side_clearance_total === '0' ? '26' : draft.side_clearance_total || '26',
      drawer_depth_deduction_mm: draft.drawer_depth_deduction_mm === '10' ? '0' : draft.drawer_depth_deduction_mm || '0',
      box_width_deduction_mm: draft.box_width_deduction_mm === '42' || draft.box_width_deduction_mm === '58' ? '0' : draft.box_width_deduction_mm || '0',
      drawer_system_config: {},
    }
  }
  return {
    ...draft,
    mount_type: mountType,
    drawer_system_config: {},
  }
}

function accessoryRuleKey(rule: HardwareAccessoryRule) {
  return [
    rule.item_type,
    rule.item_ref_id || 'custom',
    rule.name.trim().toLowerCase(),
    rule.quantity_rule,
    rule.condition.field,
    rule.condition.operator,
    rule.condition.value_number ?? '',
    rule.condition.value_text?.trim().toLowerCase() ?? '',
  ].join('::')
}

function mergeAccessoryConfig(config: HardwareAccessoryConfig | undefined, additions: HardwareAccessoryRule[]): HardwareAccessoryConfig {
  const current = normalizeAccessoryConfig(config)
  const next = [...(current.accessories ?? [])]
  for (const addition of additions) {
    const key = accessoryRuleKey(addition)
    const existingIndex = next.findIndex((rule) => accessoryRuleKey(rule) === key)
    if (existingIndex >= 0) {
      next[existingIndex] = addition
    } else {
      next.push(addition)
    }
  }
  return normalizeAccessoryConfig({ ...current, accessories: next })
}

function priceComponentsForItem(itemType: PriceItemType, row?: BoardTypeRow) {
  if (itemType === 'board') {
    return row?.costing_mode === 'sqm' ? ['sqm'] : ['sheet', 'edging_m', 'labour_board']
  }
  return ['unit']
}

function priceComponentOptionsForItem(itemType: PriceItemType, row?: BoardTypeRow | null): PricingOption[] {
  return priceComponentsForItem(itemType, row ?? undefined).map((component) => priceComponentOptionsByValue[component])
}

function orderUomOptionsForComponent(itemType: PriceItemType, component: string): PricingOption[] {
  if (itemType === 'board') {
    if (component === 'sqm') return [orderUomOptionsByValue.m2]
    if (component === 'edging_m') return [orderUomOptionsByValue.m]
    if (component === 'labour_board') return [orderUomOptionsByValue.board]
    return [orderUomOptionsByValue.sheet]
  }
  if (itemType === 'slide') {
    return [orderUomOptionsByValue.pairs, orderUomOptionsByValue.pcs, orderUomOptionsByValue.each, orderUomOptionsByValue.set]
  }
  if (itemType === 'extra') {
    return [
      orderUomOptionsByValue.pcs,
      orderUomOptionsByValue.each,
      orderUomOptionsByValue.unit,
      orderUomOptionsByValue.set,
      orderUomOptionsByValue.day,
      orderUomOptionsByValue.trip,
    ]
  }
  return [orderUomOptionsByValue.pcs, orderUomOptionsByValue.each, orderUomOptionsByValue.unit, orderUomOptionsByValue.set]
}

function defaultOrderUomForComponent(itemType: PriceItemType, component: string) {
  return orderUomOptionsForComponent(itemType, component)[0]?.value ?? itemTypeDefaultUom(itemType)
}

function componentUomSummary(itemType: PriceItemType, row?: BoardTypeRow | null) {
  return priceComponentsForItem(itemType, row ?? undefined)
    .map((component) => {
      const uom = defaultOrderUomForComponent(itemType, component)
      return `${priceComponentOptionsByValue[component]?.label ?? component} (${orderUomOptionsByValue[uom]?.label ?? uom})`
    })
    .join(', ')
}

function hasCurrentPrice(
  rows: PriceListItemRow[],
  itemType: PriceItemType,
  itemId: string,
  component: string,
) {
  const key = `${itemType}::${itemId}`
  return rows.some(
    (row) =>
      row.is_current &&
      row.item_type === itemType &&
      row.price_component === component &&
      (row.item_ref_id === itemId || row.item_key === key),
  )
}

function _firstItemIdForType(
  itemType: PriceItemType,
  rows: {
    boards: BoardTypeRow[]
    slides: SlideRow[]
    hinges: HingeRow[]
    handles: HandleRow[]
    extras: ExtraRow[]
  },
) {
  if (itemType === 'board') return rows.boards[0]?.id ?? ''
  if (itemType === 'slide') return rows.slides[0]?.id ?? ''
  if (itemType === 'hinge') return rows.hinges[0]?.id ?? ''
  if (itemType === 'handle') return rows.handles[0]?.id ?? ''
  return rows.extras[0]?.id ?? ''
}

function _itemExistsForType(
  itemType: PriceItemType,
  itemId: string,
  rows: {
    boards: BoardTypeRow[]
    slides: SlideRow[]
    hinges: HingeRow[]
    handles: HandleRow[]
    extras: ExtraRow[]
  },
) {
  if (itemType === 'board') return rows.boards.some((item) => item.id === itemId)
  if (itemType === 'slide') return rows.slides.some((item) => item.id === itemId)
  if (itemType === 'hinge') return rows.hinges.some((item) => item.id === itemId)
  if (itemType === 'handle') return rows.handles.some((item) => item.id === itemId)
  return rows.extras.some((item) => item.id === itemId)
}

const setupStatusLabels: Record<LibrarySetupItemStatus, string> = {
  action_needed: 'needs action',
  complete: 'ready',
  missing: 'missing',
  warning: 'check',
}

const importStatusCopy: Record<LibraryImportRowStatus, { help: string; label: string }> = {
  blocked: {
    help: 'CoreQuote cannot save this row yet. Fix the row or column mapping, then preview again.',
    label: 'Needs fixing',
  },
  create: {
    help: 'This row will be added when the import is applied.',
    label: 'Will add',
  },
  duplicate: {
    help: 'This looks like a duplicate row in the same import. Keep one copy, then preview again.',
    label: 'Duplicate',
  },
  skipped: {
    help: 'CoreQuote already has this value, so applying the import leaves it alone.',
    label: 'Already current',
  },
  update: {
    help: 'This row will update the matching library item when the import is applied.',
    label: 'Will update',
  },
}

const importApplyStatusLabels: Record<LibraryImportApplyRowStatus, string> = {
  created: 'Added',
  failed: 'Needs fixing',
  skipped: 'Already current',
  updated: 'Updated',
}

const priceStatusLabels: Record<LibraryEffectiveStatus, string> = {
  current: 'Used for new totals',
  future: 'Starts later',
  retired: 'History only',
}

const priceSourceLabels: Record<PriceListItemRow['cost_source'], string> = {
  import: 'Imported',
  manual: 'Manual',
  override: 'Manual override',
  supplier: 'Supplier cost',
}

const coverageStatusLabels: Record<PricingCoverageStatus, string> = {
  covered: 'Covered',
  missing: 'Missing',
  override: 'Manual override',
  stale: 'Stale supplier cost',
}

const priceItemTypeLabels: Record<PriceItemType, string> = {
  board: 'Board',
  extra: 'Extra',
  handle: 'Handle',
  hinge: 'Hinge',
  slide: 'Drawer hardware',
}

function setupStatusLabel(status: LibrarySetupItemStatus) {
  return setupStatusLabels[status]
}

function setupStatusBadgeVariant(status: LibrarySetupItemStatus) {
  if (status === 'complete') return 'success' as const
  if (status === 'missing' || status === 'warning' || status === 'action_needed') return 'warning' as const
  return 'outline' as const
}

function SetupStatusIcon({ status }: { status: LibrarySetupItemStatus }) {
  if (status === 'complete') return <CheckCircle2 className="h-4 w-4 text-[var(--status-success-foreground)]" aria-hidden="true" />
  if (status === 'warning' || status === 'action_needed') {
    return <AlertTriangle className="h-4 w-4 text-[var(--status-warning-foreground)]" aria-hidden="true" />
  }
  return <CircleDashed className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
}

function importStatusLabel(status: LibraryImportRowStatus) {
  return importStatusCopy[status].label
}

function importStatusHelp(status: LibraryImportRowStatus) {
  return importStatusCopy[status].help
}

function importStatusBadgeVariant(status: LibraryImportRowStatus) {
  if (status === 'create') return 'success' as const
  if (status === 'blocked' || status === 'duplicate') return 'warning' as const
  if (status === 'skipped') return 'outline' as const
  return 'default' as const
}

function importApplyStatusBadgeVariant(status: LibraryImportApplyRowStatus) {
  if (status === 'created') return 'success' as const
  if (status === 'failed') return 'warning' as const
  if (status === 'skipped') return 'outline' as const
  return 'default' as const
}

function importApplyStatusLabel(status: LibraryImportApplyRowStatus) {
  return importApplyStatusLabels[status]
}

function importResourceLabel(resource: LibraryImportResource) {
  return importResourceOptions.find((option) => option.value === resource)?.label ?? resource
}

function importResourceHelp(resource: LibraryImportResource, priceListName?: string | null) {
  if (resource === 'supplier_item_costs') {
    return 'Supplier cost rows connect catalog items to the prices your suppliers charge. They do not change quote selling prices until you generate or import price list rows.'
  }
  if (resource === 'price_list_items') {
    return `Price rows will be checked against ${priceListName ? `"${priceListName}"` : 'the selected price list'}. New quote pricing uses current rows from that list; saved quote evidence stays unchanged.`
  }
  if (resource === 'boards') {
    return 'Board rows become the materials estimators choose for carcasses, doors, drawers, and visible panels.'
  }
  if (resource === 'slides' || resource === 'hinges' || resource === 'handles') {
    return 'Hardware rows become quote defaults and can be priced after the catalog item exists.'
  }
  if (resource === 'extras' || resource === 'extra_categories') {
    return 'Extra rows cover allowances such as site protection or appliances that can be added to quotes.'
  }
  return 'Supplier rows keep contact details and default discounts available for later cost imports.'
}

function catalogResourceLabel(resource: LibraryCatalogBulkResource) {
  if (resource === 'boards') return 'boards'
  if (resource === 'slides') return 'drawer hardware'
  if (resource === 'hinges') return 'hinges'
  if (resource === 'handles') return 'handles'
  if (resource === 'extras') return 'extras'
  return 'suppliers'
}

function catalogBulkResourceLabel(resource: LibraryCatalogBulkResource) {
  if (resource === 'slides') return 'slides'
  return catalogResourceLabel(resource)
}

function bulkAccessoryResourceLabel(resource: BulkAccessoryResource) {
  return resource === 'slides' ? 'slides' : 'hinges'
}

function bulkAccessoryResourceSingularLabel(resource: BulkAccessoryResource) {
  return resource === 'slides' ? 'slide' : 'hinge'
}

function bulkAccessoryResourceCountLabel(resource: BulkAccessoryResource, count: number) {
  return count === 1 ? bulkAccessoryResourceSingularLabel(resource) : bulkAccessoryResourceLabel(resource)
}

function priceStatusLabel(status: LibraryEffectiveStatus) {
  return priceStatusLabels[status]
}

function priceSourceLabel(source: PriceListItemRow['cost_source']) {
  return priceSourceLabels[source]
}

function coverageStatusLabel(status: PricingCoverageStatus) {
  return coverageStatusLabels[status]
}

function coverageStatusBadgeVariant(status: PricingCoverageStatus) {
  if (status === 'covered') return 'success' as const
  if (status === 'missing' || status === 'stale') return 'warning' as const
  return 'outline' as const
}

function priceItemTypeLabel(itemType: PriceItemType) {
  return priceItemTypeLabels[itemType]
}

function priceComponentLabel(component: string) {
  if (component === 'edging_m') return 'Edging per metre'
  if (component === 'labour_board') return 'Labour per board'
  if (component === 'sheet') return 'Sheet'
  if (component === 'sqm') return 'Square metre'
  if (component === 'unit') return 'Unit'
  return component.replaceAll('_', ' ')
}

function parseColumnMapping(text: string): Record<string, string> {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .reduce<Record<string, string>>((mapping, line, index) => {
      const separatorIndex = line.includes('=') ? line.indexOf('=') : line.indexOf(':')
      if (separatorIndex <= 0) {
        throw new Error(`Column mapping line ${index + 1} needs a CoreQuote field and spreadsheet column, for example unit_cost_cents=Net Cost.`)
      }
      const field = line.slice(0, separatorIndex).trim()
      const column = line.slice(separatorIndex + 1).trim()
      if (!field || !column) {
        throw new Error(`Column mapping line ${index + 1} needs both a CoreQuote field and spreadsheet column.`)
      }
      mapping[field] = column
      return mapping
    }, {})
}

function payloadPreview(payload: Record<string, unknown>) {
  const entries = Object.entries(payload).filter(([, value]) => value !== null && value !== '')
  if (entries.length === 0) return '-'
  return entries
    .slice(0, 5)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(', ')
}

function MaintenanceToolbar({
  children,
  onRecentDaysChange,
  onSearchChange,
  recentDays,
  search,
}: {
  children?: ReactNode
  onRecentDaysChange: (value: RecentFilterValue) => void
  onSearchChange: (value: string) => void
  recentDays: RecentFilterValue
  search: string
}) {
  return (
    <div className="grid gap-2 rounded-[var(--control-radius)] border border-border p-3 lg:grid-cols-[minmax(14rem,1fr)_12rem_auto] lg:items-end">
      <Label className="grid gap-1.5">
        Search
        <span className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input className="pl-9" value={search} onChange={(event) => onSearchChange(event.target.value)} />
        </span>
      </Label>
      <Label className="grid gap-1.5">
        Changed
        <Select value={recentDays} onChange={(event) => onRecentDaysChange(event.target.value as RecentFilterValue)}>
          {recentFilterOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </Label>
      {children ? <div className="flex flex-wrap items-end gap-2">{children}</div> : null}
    </div>
  )
}

function FilteredEmptyNotice({ filteredCount, totalCount }: { filteredCount: number; totalCount: number }) {
  if (totalCount === 0 || filteredCount > 0) return null
  return <Alert variant="warning">No visible rows match these filters. Clear the search or choose a wider date range.</Alert>
}

function BulkPreviewRows({ result }: { result: LibraryBulkUpdateResult | null }) {
  if (!result) return null
  return (
    <div className="grid gap-2 rounded-[var(--control-radius)] border border-border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={result.failed_count > 0 ? 'warning' : result.confirm ? 'success' : 'outline'}>
          {result.summary_message}
        </Badge>
        <Badge variant="outline">{result.matched_count} matched</Badge>
        {result.failed_count > 0 ? <Badge variant="warning">{result.failed_count} need fixing</Badge> : null}
      </div>
      <div className="grid gap-1 text-xs text-muted-foreground">
        {result.rows.slice(0, 6).map((row) => (
          <div className="flex flex-wrap items-center gap-2" key={`${row.item_id}-${row.status}`}>
            <Badge variant={row.status === 'failed' ? 'warning' : row.status === 'updated' ? 'success' : 'outline'}>
              {row.status === 'failed' ? 'Needs fixing' : row.status === 'updated' ? 'Updated' : 'Preview'}
            </Badge>
            <span className="font-medium text-foreground">{row.label}</span>
            <span>{row.message}</span>
          </div>
        ))}
      </div>
      {result.rows.length > 6 ? <p className="text-xs text-muted-foreground">Showing 6 of {result.rows.length} preview rows.</p> : null}
    </div>
  )
}

function CatalogBulkPanel({
  accessoryConfig,
  accessoryOptions,
  bulkMode,
  field,
  fields,
  isSaving,
  onAccessoryConfigChange,
  onApply,
  onApplyAccessory,
  onBulkModeChange,
  onClearSelection,
  onFieldChange,
  onPreview,
  onSelectVisible,
  onValueChange,
  preview,
  resource,
  selectedCount,
  value,
  visibleCount,
}: {
  accessoryConfig?: HardwareAccessoryConfig
  accessoryOptions?: HardwareAccessoryOptions
  bulkMode?: CatalogBulkMode
  field: CatalogBulkField | null
  fields: CatalogBulkField[]
  isSaving: boolean
  onAccessoryConfigChange?: (config: HardwareAccessoryConfig) => void
  onApply: () => void
  onApplyAccessory?: () => void
  onBulkModeChange?: (mode: CatalogBulkMode) => void
  onClearSelection: () => void
  onFieldChange: (value: string) => void
  onPreview: () => void
  onSelectVisible: () => void
  onValueChange: (value: string) => void
  preview: LibraryBulkUpdateResult | null
  resource: LibraryCatalogBulkResource
  selectedCount: number
  value: string
  visibleCount: number
}) {
  const hasAccessoryMode = Boolean(accessoryConfig && accessoryOptions && onAccessoryConfigChange && onApplyAccessory && onBulkModeChange)
  const activeMode: CatalogBulkMode = hasAccessoryMode ? bulkMode ?? 'fields' : 'fields'
  const applyDisabled = isSaving || selectedCount === 0 || !preview || preview.confirm || preview.failed_count > 0
  const accessoryRuleCount = accessoryConfig ? normalizeAccessoryConfig(accessoryConfig).accessories?.length ?? 0 : 0
  const accessoryApplyDisabled = isSaving || selectedCount === 0 || accessoryRuleCount === 0
  const accessorySingularLabel = resource === 'slides' || resource === 'hinges' ? bulkAccessoryResourceSingularLabel(resource) : catalogBulkResourceLabel(resource)
  const valueDisabled = field?.input === 'select' && (field.options?.length ?? 0) === 0

  return (
    <div className="grid gap-3 rounded-[var(--control-radius)] border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={selectedCount > 0 ? 'default' : 'outline'}>{selectedCount} selected</Badge>
          <span className="text-sm font-medium">Bulk update selected {catalogBulkResourceLabel(resource)}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button disabled={visibleCount === 0 || isSaving} onClick={onSelectVisible} size="sm" type="button" variant="outline">
            <SquareCheckBig className="h-4 w-4" aria-hidden="true" />
            Select Visible
          </Button>
          <Button disabled={selectedCount === 0 || isSaving} onClick={onClearSelection} size="sm" type="button" variant="outline">
            <XCircle className="h-4 w-4" aria-hidden="true" />
            Clear
          </Button>
        </div>
      </div>
      {hasAccessoryMode ? (
        <ControlGroup className="w-fit" role="group" aria-label={`Choose bulk update type for selected ${catalogBulkResourceLabel(resource)}`}>
          <ControlGroupItem aria-pressed={activeMode === 'fields'} onClick={() => onBulkModeChange?.('fields')}>
            <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
            Fields
          </ControlGroupItem>
          <ControlGroupItem aria-pressed={activeMode === 'accessories'} onClick={() => onBulkModeChange?.('accessories')}>
            <PackagePlus className="h-4 w-4" aria-hidden="true" />
            Accessories
          </ControlGroupItem>
        </ControlGroup>
      ) : null}
      {activeMode === 'fields' ? (
        <>
          <div className="grid gap-3 md:grid-cols-[14rem_1fr_auto_auto] md:items-end">
            <Label className="grid gap-1.5">
              Field
              <Select value={field?.value ?? ''} onChange={(event) => onFieldChange(event.target.value)}>
                {fields.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </Label>
            <Label className="grid gap-1.5">
              Value
              {field?.input === 'select' ? (
                <Select disabled={valueDisabled} value={value} onChange={(event) => onValueChange(event.target.value)}>
                  {(field.options ?? []).map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              ) : (
                <Input min={0} type={field?.input === 'number' ? 'number' : 'text'} value={value} onChange={(event) => onValueChange(event.target.value)} />
              )}
            </Label>
            <Button disabled={isSaving || selectedCount === 0 || valueDisabled} onClick={onPreview} type="button" variant="outline">
              {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
              Preview changes
            </Button>
            <Button disabled={applyDisabled} onClick={onApply} type="button">
              {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
              Apply changes
            </Button>
          </div>
          <Alert>
            Preview first, then apply. Only the selected {catalogBulkResourceLabel(resource)} are changed; pricing and quote totals stay untouched here.
          </Alert>
          <BulkPreviewRows result={preview} />
        </>
      ) : null}
      {activeMode === 'accessories' && accessoryConfig && accessoryOptions && onAccessoryConfigChange && onApplyAccessory ? (
        <div className="grid gap-3">
          <HardwareAccessoryConfigEditor
            config={accessoryConfig}
            onChange={onAccessoryConfigChange}
            options={accessoryOptions}
          />
          <Alert>
            Existing matching accessory rules are updated; new rules are added to each selected {accessorySingularLabel}.
          </Alert>
          <div>
            <Button disabled={accessoryApplyDisabled} onClick={onApplyAccessory} type="button">
              {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <PackagePlus className="h-4 w-4" aria-hidden="true" />}
              Add accessory to selected
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function PriceBulkPanel({
  amount,
  isSaving,
  onAmountChange,
  onApply,
  onClearSelection,
  onPreview,
  onSelectVisible,
  onSourceChange,
  onUomChange,
  preview,
  selectedCount,
  source,
  uom,
  visibleCurrentCount,
}: {
  amount: string
  isSaving: boolean
  onAmountChange: (value: string) => void
  onApply: () => void
  onClearSelection: () => void
  onPreview: () => void
  onSelectVisible: () => void
  onSourceChange: (value: 'no-change' | 'manual' | 'override') => void
  onUomChange: (value: string) => void
  preview: LibraryBulkUpdateResult | null
  selectedCount: number
  source: 'no-change' | 'manual' | 'override'
  uom: string
  visibleCurrentCount: number
}) {
  const applyDisabled = isSaving || selectedCount === 0 || !preview || preview.confirm || preview.failed_count > 0
  return (
    <details className="mb-3 rounded-[var(--control-radius)] border border-border">
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={selectedCount > 0 ? 'default' : 'outline'}>{selectedCount} selected</Badge>
          <span className="text-sm font-medium">Advanced bulk price edits</span>
        </div>
      </summary>
      <div className="grid gap-3 border-t border-border p-3">
        <div className="flex flex-wrap gap-2">
          <Button disabled={visibleCurrentCount === 0 || isSaving} onClick={onSelectVisible} size="sm" type="button" variant="outline">
            <SquareCheckBig className="h-4 w-4" aria-hidden="true" />
            Select Current
          </Button>
          <Button disabled={selectedCount === 0 || isSaving} onClick={onClearSelection} size="sm" type="button" variant="outline">
            <XCircle className="h-4 w-4" aria-hidden="true" />
            Clear
          </Button>
        </div>
        <div className="grid gap-3 lg:grid-cols-[1fr_12rem_12rem_auto_auto] lg:items-end">
          <Label className="grid gap-1.5">
            Price
            <Input value={amount} onChange={(event) => onAmountChange(event.target.value)} />
          </Label>
          <Label className="grid gap-1.5">
            Unit
            <Select value={uom} onChange={(event) => onUomChange(event.target.value)}>
              <option value="">Leave unchanged</option>
              {Object.values(orderUomOptionsByValue).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Label>
          <Label className="grid gap-1.5">
            Source
            <Select value={source} onChange={(event) => onSourceChange(event.target.value as 'no-change' | 'manual' | 'override')}>
              <option value="no-change">Leave source unchanged</option>
              <option value="manual">Manual edit</option>
              <option value="override">Manual override</option>
            </Select>
          </Label>
          <Button disabled={isSaving || selectedCount === 0} onClick={onPreview} type="button" variant="outline">
            {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
            Preview changes
          </Button>
          <Button disabled={applyDisabled} onClick={onApply} type="button">
            {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
            Apply changes
          </Button>
        </div>
        <Alert variant="warning">
          Preview first, then apply. Applying a price change creates a new current price and keeps the old price in history, so past quote evidence stays explainable.
        </Alert>
        <BulkPreviewRows result={preview} />
      </div>
    </details>
  )
}

function MissingPricesPanel({
  missingPriceRows,
  onTypeFilterChange,
  typeFilter,
}: {
  missingPriceRows: MissingPriceRow[]
  onTypeFilterChange: (value: PriceTypeFilterValue) => void
  typeFilter: PriceTypeFilterValue
}) {
  return (
    <div className="grid gap-3 rounded-[var(--control-radius)] border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={missingPriceRows.length > 0 ? 'warning' : 'success'}>{missingPriceRows.length} missing</Badge>
          <span className="text-sm font-medium">Missing Prices</span>
        </div>
        <Label className="grid min-w-40 gap-1.5 text-xs">
          Type
          <Select value={typeFilter} onChange={(event) => onTypeFilterChange(event.target.value as PriceTypeFilterValue)}>
            <option value="all">All types</option>
            {priceItemTypes.map((itemType) => (
              <option key={itemType} value={itemType}>
                {priceItemTypeLabel(itemType)}
              </option>
            ))}
          </Select>
        </Label>
      </div>
      {missingPriceRows.length === 0 ? (
        <p className="text-sm text-muted-foreground">Every visible library item has a current price in this list.</p>
      ) : (
        <div className="grid gap-2 md:grid-cols-2">
          {missingPriceRows.slice(0, 8).map((row) => (
            <div className="rounded-[var(--control-radius)] border border-border px-3 py-2 text-sm" key={`${row.item_type}-${row.id}`}>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{priceItemTypeLabel(row.item_type)}</Badge>
                <span className="font-medium">{row.label}</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Add {row.components.map(priceComponentLabel).join(', ')} using Manual Override, a price import, or supplier price generation.
              </p>
            </div>
          ))}
        </div>
      )}
      {missingPriceRows.length > 8 ? <p className="text-xs text-muted-foreground">Showing 8 of {missingPriceRows.length} missing price rows.</p> : null}
    </div>
  )
}

function PricingCoveragePanel({
  coverage,
  currencyCode,
  isLoading,
  onAddSupplierCost,
  onGenerateFromSupplierCosts,
  onManualOverride,
}: {
  coverage: PricingCoverage | null
  currencyCode: string
  isLoading: boolean
  onAddSupplierCost: (row: PricingCoverageRow) => void
  onGenerateFromSupplierCosts: (row: PricingCoverageRow) => void
  onManualOverride: (row: PricingCoverageRow) => void
}) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-[var(--control-radius)] border border-border p-3 text-sm text-muted-foreground">
        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
        Loading pricing coverage
      </div>
    )
  }

  if (!coverage) {
    return (
      <Alert className="text-sm">
        Select a price list to review quote-used pricing coverage.
      </Alert>
    )
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">{coverage.used_count} quote-used rows</Badge>
        <Badge variant={coverage.missing_count > 0 ? 'warning' : 'success'}>{coverage.missing_count} missing</Badge>
        <Badge variant={coverage.stale_count > 0 ? 'warning' : 'outline'}>{coverage.stale_count} stale</Badge>
        <Badge variant={coverage.override_count > 0 ? 'outline' : 'success'}>{coverage.override_count} manual overrides</Badge>
        <span className="text-xs text-muted-foreground">Updated {formatDateTime(coverage.generated_at)}</span>
      </div>

      {coverage.used_count === 0 ? (
        <Alert className="text-sm">
          No draft, ready, sent, or accepted quotes currently reference priced catalog items.
        </Alert>
      ) : null}

      {coverage.groups.map((group) => (
        <PricingCoverageGroupPanel
          currencyCode={currencyCode}
          group={group}
          key={group.item_type}
          onAddSupplierCost={onAddSupplierCost}
          onGenerateFromSupplierCosts={onGenerateFromSupplierCosts}
          onManualOverride={onManualOverride}
        />
      ))}
    </div>
  )
}

function PricingCoverageGroupPanel({
  currencyCode,
  group,
  onAddSupplierCost,
  onGenerateFromSupplierCosts,
  onManualOverride,
}: {
  currencyCode: string
  group: PricingCoverageGroup
  onAddSupplierCost: (row: PricingCoverageRow) => void
  onGenerateFromSupplierCosts: (row: PricingCoverageRow) => void
  onManualOverride: (row: PricingCoverageRow) => void
}) {
  return (
    <div className="overflow-hidden rounded-[var(--control-radius)] border border-border">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">{group.item_type_label}</span>
          <Badge variant="outline">{group.used_count} used</Badge>
          <Badge variant={group.missing_count > 0 ? 'warning' : 'success'}>{group.missing_count} missing</Badge>
          <Badge variant={group.stale_count > 0 ? 'warning' : 'outline'}>{group.stale_count} stale</Badge>
          <Badge variant="outline">{group.override_count} overrides</Badge>
        </div>
      </div>
      <TableContainer>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Item</TableHead>
              <TableHead>Component</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Quote context</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {group.rows.map((row) => (
              <TableRow key={`${row.item_type}-${row.item_ref_id}-${row.price_component}`}>
                <TableCell>
                  <div className="grid gap-1">
                    <span className="font-medium">{row.item_name}</span>
                    <span className="text-xs text-muted-foreground">{row.item_key}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="grid gap-1">
                    <span>{row.component}</span>
                    <span className="text-xs text-muted-foreground">{row.uom}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant={coverageStatusBadgeVariant(row.status)}>{coverageStatusLabel(row.status)}</Badge>
                    {row.has_supplier_cost ? <Badge variant="outline">supplier cost</Badge> : null}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="grid gap-1 text-xs">
                    <span className="font-medium">{row.quote_count} quote{row.quote_count === 1 ? '' : 's'}</span>
                    {row.used_in.slice(0, 2).map((context) => (
                      <span className="text-muted-foreground" key={`${context.quote_id}-${context.usage_label}`}>
                        {context.quote_number} r{context.revision} · {context.usage_label}
                      </span>
                    ))}
                    {row.used_in.length > 2 ? (
                      <span className="text-muted-foreground">+{row.used_in.length - 2} more uses</span>
                    ) : null}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="grid gap-1">
                    <span>{row.unit_price_cents === null ? 'No current price' : formatCurrencyFromCents(row.unit_price_cents, currencyCode)}</span>
                    {row.cost_source ? <span className="text-xs text-muted-foreground">{priceSourceLabel(row.cost_source)}</span> : null}
                    {row.supplier_unit_cost_cents !== null ? (
                      <span className="text-xs text-muted-foreground">
                        Supplier {formatCurrencyFromCents(row.supplier_unit_cost_cents, currencyCode)}
                      </span>
                    ) : null}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-2">
                    <Button onClick={() => onAddSupplierCost(row)} size="sm" type="button" variant="outline">
                      <PackagePlus className="h-4 w-4" aria-hidden="true" />
                      Supplier cost
                    </Button>
                    <Button disabled={!row.has_supplier_cost} onClick={() => onGenerateFromSupplierCosts(row)} size="sm" type="button" variant="outline">
                      <RefreshCcw className="h-4 w-4" aria-hidden="true" />
                      Generate
                    </Button>
                    <Button onClick={() => onManualOverride(row)} size="sm" type="button" variant="outline">
                      <Save className="h-4 w-4" aria-hidden="true" />
                      Override
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  )
}

function arrayBufferToBase64(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer)
  const chunkSize = 0x8000
  let binary = ''
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize))
  }
  return window.btoa(binary)
}

export function LibrariesPage({
  activeTab,
  authToken,
  currencyCode,
  onActiveTabChange,
  onOpenProjects,
}: {
  activeTab: LibraryTab
  authToken: string
  currencyCode: string
  onActiveTabChange: (tab: LibraryTab) => void
  onOpenProjects: () => void
}) {
  const setActiveTab = onActiveTabChange
  const [activePricingTab, setActivePricingTab] = useState<PricingSubTab>('coverage')

  const [setupChecklist, setSetupChecklist] = useState<LibrarySetupChecklist | null>(null)
  const [boards, setBoards] = useState<BoardTypeRow[]>([])
  const [slides, setSlides] = useState<SlideRow[]>([])
  const [hinges, setHinges] = useState<HingeRow[]>([])
  const [suppliers, setSuppliers] = useState<SupplierRow[]>([])
  const [itemSuppliers, setItemSuppliers] = useState<ItemSupplierRow[]>([])
  const [handles, setHandles] = useState<HandleRow[]>([])
  const [extraCategories, setExtraCategories] = useState<ExtraCategoryRow[]>([])
  const [extras, setExtras] = useState<ExtraRow[]>([])

  const [pricingSettings, setPricingSettings] = useState<PricingSettingsRow | null>(null)
  const [priceLists, setPriceLists] = useState<PriceListRow[]>([])
  const [priceItems, setPriceItems] = useState<PriceListItemRow[]>([])
  const [priceCoverage, setPriceCoverage] = useState<PricingCoverage | null>(null)
  const [selectedPriceListId, setSelectedPriceListId] = useState('')

  const [isLoadingCatalog, setIsLoadingCatalog] = useState(true)
  const [isLoadingPricing, setIsLoadingPricing] = useState(true)
  const [isLoadingChecklist, setIsLoadingChecklist] = useState(true)
  const [isLoadingPriceItems, setIsLoadingPriceItems] = useState(false)
  const [isLoadingCoverage, setIsLoadingCoverage] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isPreviewingImport, setIsPreviewingImport] = useState(false)
  const [isApplyingImport, setIsApplyingImport] = useState(false)

  const [checklistError, setChecklistError] = useState<string | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [pricingError, setPricingError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)
  const [importError, setImportError] = useState<string | null>(null)

  const [boardDraft, setBoardDraft] = useState<BoardDraft>(defaultBoardDraft)
  const [slideRangeDraft, setSlideRangeDraft] = useState<SlideRangeDraft>(defaultSlideRangeDraft)
  const [inlineSlideAccessoryDraft, setInlineSlideAccessoryDraft] = useState<ExtraDraft>(defaultExtraDraft)
  const [hingeDraft, setHingeDraft] = useState<HingeDraft>(defaultHingeDraft)
  const [supplierDraft, setSupplierDraft] = useState<SupplierDraft>(defaultSupplierDraft)
  const [itemSupplierDraft, setItemSupplierDraft] = useState<ItemSupplierDraft>(defaultItemSupplierDraft)
  const [handleDraft, setHandleDraft] = useState<HandleDraft>(defaultHandleDraft)
  const [extraCategoryDraft, setExtraCategoryDraft] = useState<ExtraCategoryDraft>(defaultExtraCategoryDraft)
  const [extraDraft, setExtraDraft] = useState<ExtraDraft>(defaultExtraDraft)
  const [discountSupplierId, setDiscountSupplierId] = useState('')
  const [supplierDiscountPercent, setSupplierDiscountPercent] = useState('0.00')
  const [applyDiscountToCosts, setApplyDiscountToCosts] = useState(true)

  const [editingBoard, setEditingBoard] = useState<BoardTypeRow | null>(null)
  const [editingSlide, setEditingSlide] = useState<SlideRow | null>(null)
  const [editingHinge, setEditingHinge] = useState<HingeRow | null>(null)
  const [editingSupplier, setEditingSupplier] = useState<SupplierRow | null>(null)
  const [editingHandle, setEditingHandle] = useState<HandleRow | null>(null)
  const [editingExtraCategory, setEditingExtraCategory] = useState<ExtraCategoryRow | null>(null)
  const [editingExtra, setEditingExtra] = useState<ExtraRow | null>(null)

  const [pricingSettingsDraft, setPricingSettingsDraft] = useState<PricingSettingsDraft>(defaultPricingSettingsDraft)
  const [priceListDraft, setPriceListDraft] = useState<PriceListDraft>(defaultPriceListDraft)

  const [pricingItemType, setPricingItemType] = useState<PriceItemType>('slide')
  const [pricingItemRefId, setPricingItemRefId] = useState('')
  const [unitPriceAmount, setUnitPriceAmount] = useState('0.00')
  const [sheetPriceAmount, setSheetPriceAmount] = useState('0.00')
  const [edgingPriceAmount, setEdgingPriceAmount] = useState('0.00')
  const [labourPriceAmount, setLabourPriceAmount] = useState('0.00')
  const [sqmPriceAmount, setSqmPriceAmount] = useState('0.00')
  const [generationMode, setGenerationMode] = useState<GeneratePriceListSummary['selection_mode']>('preferred_then_cheapest')
  const [generationItemTypes, setGenerationItemTypes] = useState<PriceItemType[]>(['slide', 'hinge'])
  const [preserveManualOverrides, setPreserveManualOverrides] = useState(true)
  const [generationEffectiveFrom, setGenerationEffectiveFrom] = useState('')
  const [lastGenerationSummary, setLastGenerationSummary] = useState<GeneratePriceListSummary | null>(null)
  const [importResource, setImportResource] = useState<LibraryImportResource>('boards')
  const [importSourceFormat, setImportSourceFormat] = useState<LibraryImportSourceFormat>('csv')
  const [importFilename, setImportFilename] = useState('')
  const [importSheetName, setImportSheetName] = useState('')
  const [importSourceRef, setImportSourceRef] = useState('')
  const [importContent, setImportContent] = useState(importExampleByResource.boards)
  const [importColumnMapping, setImportColumnMapping] = useState('')
  const [importPreview, setImportPreview] = useState<LibraryImportPreview | null>(null)
  const [importApplyResult, setImportApplyResult] = useState<LibraryImportApplyResult | null>(null)
  const [catalogSearch, setCatalogSearch] = useState('')
  const [catalogRecentDays, setCatalogRecentDays] = useState<RecentFilterValue>('all')
  const [extraCategoryFilter, setExtraCategoryFilter] = useState('all')
  const [priceSearch, setPriceSearch] = useState('')
  const [priceStatusFilter, setPriceStatusFilter] = useState<PriceStatusFilterValue>('all')
  const [priceTypeFilter, setPriceTypeFilter] = useState<PriceTypeFilterValue>('all')
  const [priceSourceFilter, setPriceSourceFilter] = useState<PriceSourceFilterValue>('all')
  const [priceRecentDays, setPriceRecentDays] = useState<RecentFilterValue>('all')
  const [missingPriceTypeFilter, setMissingPriceTypeFilter] = useState<PriceTypeFilterValue>('all')
  const [selectedCatalogIds, setSelectedCatalogIds] = useState<Record<LibraryCatalogBulkResource, string[]>>({
    boards: [],
    extras: [],
    handles: [],
    hinges: [],
    slides: [],
    suppliers: [],
  })
  const [selectedPriceItemIds, setSelectedPriceItemIds] = useState<string[]>([])
  const [catalogBulkField, setCatalogBulkField] = useState('')
  const [catalogBulkValue, setCatalogBulkValue] = useState('')
  const [priceBulkAmount, setPriceBulkAmount] = useState('')
  const [priceBulkUom, setPriceBulkUom] = useState('')
  const [priceBulkSource, setPriceBulkSource] = useState<'no-change' | 'manual' | 'override'>('override')
  const [catalogBulkPreview, setCatalogBulkPreview] = useState<LibraryBulkUpdateResult | null>(null)
  const [priceBulkPreview, setPriceBulkPreview] = useState<LibraryBulkUpdateResult | null>(null)
  const [bulkError, setBulkError] = useState<string | null>(null)
  const [isBulkSaving, setIsBulkSaving] = useState(false)
  const [createHardwareResource, setCreateHardwareResource] = useState<CreateCatalogResource | null>(null)
  const [catalogBulkModes, setCatalogBulkModes] = useState<Record<BulkAccessoryResource, CatalogBulkMode>>({
    hinges: 'fields',
    slides: 'fields',
  })
  const [bulkAccessoryConfigs, setBulkAccessoryConfigs] = useState<Record<BulkAccessoryResource, HardwareAccessoryConfig>>(() => ({
    hinges: emptyBulkAccessoryConfig(),
    slides: emptyBulkAccessoryConfig(),
  }))
  const displayCurrencyCode = normalizeCurrencyCode(currencyCode)

  const selectedPriceList = useMemo(
    () => priceLists.find((item) => item.id === selectedPriceListId) ?? null,
    [priceLists, selectedPriceListId],
  )

  const selectedDiscountSupplier = useMemo(
    () => suppliers.find((item) => item.id === discountSupplierId) ?? null,
    [discountSupplierId, suppliers],
  )

  const supplierCostCountsBySupplierId = useMemo(() => {
    const counts = new Map<string, { active: number; total: number }>()
    for (const row of itemSuppliers) {
      const current = counts.get(row.supplier_id) ?? { active: 0, total: 0 }
      current.total += 1
      if (row.active_supplier_item_cost_id) {
        current.active += 1
      }
      counts.set(row.supplier_id, current)
    }
    return counts
  }, [itemSuppliers])

  const selectedBoardForPricing = useMemo(
    () => boards.find((item) => item.id === pricingItemRefId) ?? null,
    [boards, pricingItemRefId],
  )

  const selectedBoardForSupplierCost = useMemo(
    () => itemSupplierDraft.item_type === 'board' ? boards.find((item) => item.id === itemSupplierDraft.item_ref_id) ?? null : null,
    [boards, itemSupplierDraft.item_ref_id, itemSupplierDraft.item_type],
  )

  const supplierPriceComponentOptions = useMemo(
    () => priceComponentOptionsForItem(itemSupplierDraft.item_type, selectedBoardForSupplierCost),
    [itemSupplierDraft.item_type, selectedBoardForSupplierCost],
  )

  const supplierOrderUomOptions = useMemo(
    () => orderUomOptionsForComponent(itemSupplierDraft.item_type, itemSupplierDraft.price_component),
    [itemSupplierDraft.item_type, itemSupplierDraft.price_component],
  )

  const pricingItemOptions = useMemo(() => {
    if (pricingItemType === 'board') {
      return boards.map((item) => ({ id: item.id, label: formatBoardLabel(item) }))
    }
    if (pricingItemType === 'slide') {
      return slides.map((item) => ({ id: item.id, label: formatSlideLabel(item) }))
    }
    if (pricingItemType === 'hinge') {
      return hinges.map((item) => ({ id: item.id, label: formatHingeLabel(item) }))
    }
    if (pricingItemType === 'handle') {
      return handles.map((item) => ({ id: item.id, label: formatHandleLabel(item) }))
    }
    return extras.map((item) => ({ id: item.id, label: formatExtraLabel(item) }))
  }, [boards, extras, handles, hinges, pricingItemType, slides])

  const supplierItemOptions = useMemo(() => {
    if (itemSupplierDraft.item_type === 'board') {
      return boards.map((item) => ({ id: item.id, label: formatBoardLabel(item) }))
    }
    if (itemSupplierDraft.item_type === 'slide') {
      return slides.map((item) => ({ id: item.id, label: formatSlideLabel(item) }))
    }
    if (itemSupplierDraft.item_type === 'hinge') {
      return hinges.map((item) => ({ id: item.id, label: formatHingeLabel(item) }))
    }
    if (itemSupplierDraft.item_type === 'handle') {
      return handles.map((item) => ({ id: item.id, label: formatHandleLabel(item) }))
    }
    return extras.map((item) => ({ id: item.id, label: formatExtraLabel(item) }))
  }, [boards, extras, handles, hinges, itemSupplierDraft.item_type, slides])

  const itemLabelByRef = useMemo(() => {
    const labels = new Map<string, string>()
    for (const row of boards) labels.set(`board:${row.id}`, formatBoardLabel(row))
    for (const row of slides) labels.set(`slide:${row.id}`, formatSlideLabel(row))
    for (const row of hinges) labels.set(`hinge:${row.id}`, formatHingeLabel(row))
    for (const row of handles) labels.set(`handle:${row.id}`, formatHandleLabel(row))
    for (const row of extras) labels.set(`extra:${row.id}`, formatExtraLabel(row))
    return labels
  }, [boards, extras, handles, hinges, slides])

  const currentPriceRows = useMemo(
    () => priceItems.filter((item) => item.is_current),
    [priceItems],
  )
  const futurePriceRows = useMemo(
    () => priceItems.filter((item) => item.effective_status === 'future'),
    [priceItems],
  )
  const retiredPriceRows = useMemo(
    () => priceItems.filter((item) => item.effective_status === 'retired'),
    [priceItems],
  )
  const activeCatalogBulkResource = catalogResourceForTab(activeTab)
  const activeCatalogSelection = activeCatalogBulkResource ? selectedCatalogIds[activeCatalogBulkResource] : []
  const activeCatalogBulkFields = activeCatalogBulkResource
    ? catalogBulkFields[activeCatalogBulkResource].map((field) =>
        field.value === 'category_id'
          ? {
              ...field,
              options: extraCategories.map((category) => ({ label: category.name, value: category.id })),
            }
          : field.value === 'supplier_id'
            ? {
                ...field,
                options: [
                  { label: 'No supplier', value: '' },
                  ...suppliers.map((supplier) => ({ label: supplier.name, value: supplier.id })),
                ],
              }
          : field,
      )
    : []
  const activeCatalogBulkField = activeCatalogBulkFields.find((field) => field.value === catalogBulkField) ?? activeCatalogBulkFields[0] ?? null

  const visibleBoards = useMemo(
    () =>
      boards.filter(
        (row) =>
          searchTextMatches(catalogSearch, [row.brand, row.material, row.thickness, row.length_mm, row.width_mm, row.costing_mode, row.grain_policy]) &&
          matchesRecent(row.updated_at, catalogRecentDays),
      ),
    [boards, catalogRecentDays, catalogSearch],
  )
  const visibleSlides = useMemo(
    () =>
      slides.filter(
        (row) =>
          searchTextMatches(catalogSearch, [
            row.brand,
            row.model,
            row.code,
            row.length,
            row.side_length,
            row.mount_type,
            row.product_family,
            row.required_depth_mm,
            row.box_width_deduction_mm,
            row.drawer_system_kind,
            row.drawer_system_config?.product_family,
            row.drawer_system_config?.manufacturer,
            row.drawer_system_config?.finish,
          ]) &&
          matchesRecent(row.updated_at, catalogRecentDays),
      ),
    [catalogRecentDays, catalogSearch, slides],
  )
  const visibleHinges = useMemo(
    () =>
      hinges.filter(
        (row) =>
          searchTextMatches(catalogSearch, [row.brand, row.model, row.code, row.opening_angle_deg]) &&
          matchesRecent(row.updated_at, catalogRecentDays),
      ),
    [catalogRecentDays, catalogSearch, hinges],
  )
  const accessoryOptions = useMemo<HardwareAccessoryOptions>(
    () => ({
      slide: slides.map((row) => ({ label: formatSlideLabel(row), value: row.id })),
      hinge: hinges.map((row) => ({ label: formatHingeLabel(row), value: row.id })),
      handle: handles.map((row) => ({ label: formatHandleLabel(row), value: row.id })),
      extra: extras.map((row) => ({ label: formatExtraLabel(row), value: row.id })),
    }),
    [extras, handles, hinges, slides],
  )
  const slideRangePreview = useMemo(() => slideRangePreviewRows(slideRangeDraft), [slideRangeDraft])
  const visibleHandles = useMemo(
    () =>
      handles.filter(
        (row) =>
          searchTextMatches(catalogSearch, [row.name, row.supplier_name, row.handle_type]) &&
          matchesRecent(row.updated_at, catalogRecentDays),
      ),
    [catalogRecentDays, catalogSearch, handles],
  )
  const visibleSuppliers = useMemo(
    () =>
      suppliers.filter(
        (row) =>
          searchTextMatches(catalogSearch, [row.name, row.code, row.contact_name, row.email, row.phone, row.notes]) &&
          matchesRecent(row.updated_at, catalogRecentDays),
      ),
    [catalogRecentDays, catalogSearch, suppliers],
  )
  const visibleItemSuppliers = useMemo(
    () =>
      itemSuppliers.filter((row) => {
        const label = itemLabelByRef.get(`${row.item_type}:${row.item_ref_id}`) ?? `${row.item_type} ${row.item_ref_id}`
        return (
          searchTextMatches(catalogSearch, [
            label,
            row.item_type,
            row.supplier_name,
            row.supplier_sku,
            row.supplier_description,
            row.price_component,
            row.order_uom,
          ]) && matchesRecent(row.updated_at, catalogRecentDays)
        )
      }),
    [catalogRecentDays, catalogSearch, itemLabelByRef, itemSuppliers],
  )
  const visibleExtraCategories = useMemo(
    () =>
      extraCategories.filter(
        (row) =>
          searchTextMatches(catalogSearch, [row.name]) &&
          matchesRecent(row.updated_at, catalogRecentDays),
      ),
    [catalogRecentDays, catalogSearch, extraCategories],
  )
  const visibleExtras = useMemo(
    () =>
      extras.filter(
        (row) =>
          (extraCategoryFilter === 'all' || row.category_id === extraCategoryFilter) &&
          searchTextMatches(catalogSearch, [row.name, row.category_name, row.supplier, row.code, row.notes]) &&
          matchesRecent(row.updated_at, catalogRecentDays),
      ),
    [catalogRecentDays, catalogSearch, extraCategoryFilter, extras],
  )
  const visiblePriceRows = useMemo(
    () =>
      priceItems.filter(
        (row) =>
          (priceStatusFilter === 'all' || row.effective_status === priceStatusFilter) &&
          (priceTypeFilter === 'all' || row.item_type === priceTypeFilter) &&
          (priceSourceFilter === 'all' || row.cost_source === priceSourceFilter) &&
          searchTextMatches(priceSearch, [
            row.item_type,
            row.item_key,
            row.price_component,
            row.uom,
            row.cost_source,
            row.item_ref_id ? itemLabelByRef.get(`${row.item_type}:${row.item_ref_id}`) : '',
          ]) &&
          matchesRecent(row.updated_at, priceRecentDays),
      ),
    [itemLabelByRef, priceItems, priceRecentDays, priceSearch, priceSourceFilter, priceStatusFilter, priceTypeFilter],
  )
  const missingPriceRows = useMemo<MissingPriceRow[]>(() => {
    const rows: MissingPriceRow[] = []
    for (const row of boards) {
      const components = priceComponentsForItem('board', row).filter(
        (component) => !hasCurrentPrice(priceItems, 'board', row.id, component),
      )
      if (components.length > 0) rows.push({ components, id: row.id, item_type: 'board', label: formatBoardLabel(row) })
    }
    for (const row of slides) {
      const components = priceComponentsForItem('slide').filter((component) => !hasCurrentPrice(priceItems, 'slide', row.id, component))
      if (components.length > 0) rows.push({ components, id: row.id, item_type: 'slide', label: formatSlideLabel(row) })
    }
    for (const row of hinges) {
      const components = priceComponentsForItem('hinge').filter((component) => !hasCurrentPrice(priceItems, 'hinge', row.id, component))
      if (components.length > 0) rows.push({ components, id: row.id, item_type: 'hinge', label: formatHingeLabel(row) })
    }
    for (const row of handles) {
      const components = priceComponentsForItem('handle').filter((component) => !hasCurrentPrice(priceItems, 'handle', row.id, component))
      if (components.length > 0) rows.push({ components, id: row.id, item_type: 'handle', label: formatHandleLabel(row) })
    }
    for (const row of extras) {
      const components = priceComponentsForItem('extra').filter((component) => !hasCurrentPrice(priceItems, 'extra', row.id, component))
      if (components.length > 0) rows.push({ components, id: row.id, item_type: 'extra', label: formatExtraLabel(row) })
    }
    return rows.filter(
      (row) =>
        (missingPriceTypeFilter === 'all' || row.item_type === missingPriceTypeFilter) &&
        searchTextMatches(priceSearch, [row.label, row.item_type, row.components.join(' ')]),
    )
  }, [boards, extras, handles, hinges, missingPriceTypeFilter, priceItems, priceSearch, slides])
  const currentVisiblePriceRows = useMemo(
    () => visiblePriceRows.filter((row) => row.effective_status === 'current'),
    [visiblePriceRows],
  )
  const historyVisiblePriceRows = useMemo(
    () => visiblePriceRows.filter((row) => row.effective_status !== 'current'),
    [visiblePriceRows],
  )

  const importSummaryItems = useMemo(() => {
    if (!importPreview) return []
    return [
      { label: 'will add', status: 'create' as const, value: importPreview.summary.create_count },
      { label: 'will update', status: 'update' as const, value: importPreview.summary.update_count },
      { label: 'already current', status: 'skipped' as const, value: importPreview.summary.skipped_count },
      { label: 'duplicates', status: 'duplicate' as const, value: importPreview.summary.duplicate_count },
      { label: 'need fixing', status: 'blocked' as const, value: importPreview.summary.blocked_count },
    ]
  }, [importPreview])

  const visibleImportRows = useMemo(() => importPreview?.rows.slice(0, 50) ?? [], [importPreview])

  const importApplySummaryItems = useMemo(() => {
    if (!importApplyResult) return []
    return [
      { label: 'added', status: 'created' as const, value: importApplyResult.summary.created_count },
      { label: 'updated', status: 'updated' as const, value: importApplyResult.summary.updated_count },
      { label: 'already current', status: 'skipped' as const, value: importApplyResult.summary.skipped_count },
      { label: 'need fixing', status: 'failed' as const, value: importApplyResult.summary.failed_count },
    ]
  }, [importApplyResult])

  const visibleImportApplyRows = useMemo(() => importApplyResult?.rows.slice(0, 50) ?? [], [importApplyResult])

  const refreshSetupChecklist = useCallback(async () => {
    setIsLoadingChecklist(true)
    setChecklistError(null)

    try {
      const checklist = await apiRequest<LibrarySetupChecklist>('/api/v1/libraries/setup-checklist', { token: authToken })
      setSetupChecklist(checklist)
    } catch (error) {
      setChecklistError(error instanceof Error ? error.message : 'Could not load the library setup checklist.')
      setSetupChecklist(null)
    } finally {
      setIsLoadingChecklist(false)
    }
  }, [authToken])

  const refreshCatalog = useCallback(async () => {
    setIsLoadingCatalog(true)
    setCatalogError(null)

    try {
      const [nextBoards, nextSlides, nextHinges, nextSuppliers, nextItemSuppliers, nextHandles, nextCategories, nextExtras] = await Promise.all([
        apiRequest<BoardTypeRow[]>('/api/v1/libraries/boards', { token: authToken }),
        apiRequest<SlideRow[]>('/api/v1/libraries/slides', { token: authToken }),
        apiRequest<HingeRow[]>('/api/v1/libraries/hinges', { token: authToken }),
        apiRequest<SupplierRow[]>('/api/v1/libraries/suppliers', { token: authToken }),
        apiRequest<ItemSupplierRow[]>('/api/v1/libraries/item-suppliers', { token: authToken }),
        apiRequest<HandleRow[]>('/api/v1/libraries/handles', { token: authToken }),
        apiRequest<ExtraCategoryRow[]>('/api/v1/libraries/extra-categories', { token: authToken }),
        apiRequest<ExtraRow[]>('/api/v1/libraries/extras', { token: authToken }),
      ])

      setBoards(nextBoards)
      setSlides(nextSlides)
      setHinges(nextHinges)
      setSuppliers(nextSuppliers)
      setItemSuppliers(nextItemSuppliers)
      setHandles(nextHandles)
      setExtraCategories(nextCategories)
      setExtras(nextExtras)
      setExtraDraft((current) => ({
        ...current,
        category_id:
          current.category_id && nextCategories.some((item) => item.id === current.category_id)
            ? current.category_id
            : nextCategories[0]?.id ?? '',
        supplier_id:
          current.supplier_id && nextSuppliers.some((item) => item.id === current.supplier_id)
            ? current.supplier_id
            : '',
      }))
      setItemSupplierDraft((current) => {
        const nextItemRefId =
          current.item_ref_id && _itemExistsForType(current.item_type, current.item_ref_id, {
            boards: nextBoards,
            extras: nextExtras,
            handles: nextHandles,
            hinges: nextHinges,
            slides: nextSlides,
          })
            ? current.item_ref_id
            : _firstItemIdForType(current.item_type, {
                boards: nextBoards,
                extras: nextExtras,
                handles: nextHandles,
                hinges: nextHinges,
                slides: nextSlides,
              })
        const nextSupplierId =
          current.supplier_id && nextSuppliers.some((item) => item.id === current.supplier_id)
            ? current.supplier_id
            : nextSuppliers[0]?.id ?? ''
        const nextSupplier = nextSuppliers.find((item) => item.id === nextSupplierId)
        const discount_percent = bpsToPercentString(nextSupplier?.default_discount_bps ?? 0)
        return {
          ...current,
          item_ref_id: nextItemRefId,
          supplier_id: nextSupplierId,
          discount_percent,
          unit_cost_amount:
            calculateDiscountedAmountString(current.list_price_amount, discount_percent) ?? current.unit_cost_amount,
        }
      })
      setDiscountSupplierId((current) =>
        current && nextSuppliers.some((item) => item.id === current) ? current : nextSuppliers[0]?.id ?? '',
      )
    } catch (error) {
      setCatalogError(error instanceof Error ? error.message : 'Could not load libraries.')
    } finally {
      setIsLoadingCatalog(false)
    }
  }, [authToken])

  const refreshPriceItems = useCallback(
    async (priceListId: string) => {
      setIsLoadingPriceItems(true)
      setPricingError(null)

      try {
        const rows = await apiRequest<PriceListItemRow[]>(`/api/v1/libraries/price-lists/${priceListId}/items?include_history=true`, {
          token: authToken,
        })
        setPriceItems(rows)
      } catch (error) {
        setPricingError(error instanceof Error ? error.message : 'Could not load price list items.')
        setPriceItems([])
      } finally {
        setIsLoadingPriceItems(false)
      }
    },
    [authToken],
  )

  const refreshPriceCoverage = useCallback(
    async (priceListId: string) => {
      setIsLoadingCoverage(true)
      setPricingError(null)

      try {
        const coverage = await apiRequest<PricingCoverage>(`/api/v1/libraries/price-lists/${priceListId}/coverage`, {
          token: authToken,
        })
        setPriceCoverage(coverage)
      } catch (error) {
        setPricingError(error instanceof Error ? error.message : 'Could not load pricing coverage.')
        setPriceCoverage(null)
      } finally {
        setIsLoadingCoverage(false)
      }
    },
    [authToken],
  )

  const refreshPricing = useCallback(async () => {
    setIsLoadingPricing(true)
    setPricingError(null)

    try {
      const [settings, lists] = await Promise.all([
        apiRequest<PricingSettingsRow>('/api/v1/libraries/pricing-settings', { token: authToken }),
        apiRequest<PriceListRow[]>('/api/v1/libraries/price-lists', { token: authToken }),
      ])

      setPricingSettings(settings)
      setPricingSettingsDraft(pricingSettingsToDraft(settings))
      setPriceLists(lists)

      let activeListId = lists.find((item) => item.status === 'active')?.id ?? ''
      if (!activeListId && lists.length > 0) {
        activeListId = lists[0].id
      }

      setSelectedPriceListId(activeListId)
      if (activeListId) {
        await Promise.all([refreshPriceItems(activeListId), refreshPriceCoverage(activeListId)])
      } else {
        setPriceItems([])
        setPriceCoverage(null)
      }
    } catch (error) {
      setPricingError(error instanceof Error ? error.message : 'Could not load pricing settings.')
      setPriceItems([])
      setPriceCoverage(null)
    } finally {
      setIsLoadingPricing(false)
    }
  }, [authToken, refreshPriceCoverage, refreshPriceItems])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void refreshSetupChecklist()
      void refreshCatalog()
      void refreshPricing()
    }, 0)

    return () => window.clearTimeout(handle)
  }, [refreshCatalog, refreshPricing, refreshSetupChecklist])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setPricingItemRefId((current) =>
        current && pricingItemOptions.some((option) => option.id === current)
          ? current
          : pricingItemOptions[0]?.id ?? '',
      )
    }, 0)

    return () => window.clearTimeout(handle)
  }, [pricingItemOptions])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setItemSupplierDraft((current) => ({
        ...current,
        item_ref_id:
          current.item_ref_id && supplierItemOptions.some((option) => option.id === current.item_ref_id)
            ? current.item_ref_id
            : supplierItemOptions[0]?.id ?? '',
      }))
    }, 0)

    return () => window.clearTimeout(handle)
  }, [supplierItemOptions])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setItemSupplierDraft((current) => {
        const board = current.item_type === 'board' ? boards.find((item) => item.id === current.item_ref_id) ?? null : null
        const componentOptions = priceComponentOptionsForItem(current.item_type, board)
        const componentValues = componentOptions.map((option) => option.value)
        const priceComponent = componentValues.includes(current.price_component)
          ? current.price_component
          : componentValues[0] ?? 'unit'
        const uomOptions = orderUomOptionsForComponent(current.item_type, priceComponent)
        const uomValues = uomOptions.map((option) => option.value)
        const orderUom = uomValues.includes(current.order_uom)
          ? current.order_uom
          : defaultOrderUomForComponent(current.item_type, priceComponent)
        if (priceComponent === current.price_component && orderUom === current.order_uom) {
          return current
        }
        return { ...current, price_component: priceComponent, order_uom: orderUom }
      })
    }, 0)

    return () => window.clearTimeout(handle)
  }, [boards, itemSupplierDraft.item_ref_id, itemSupplierDraft.item_type])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setSupplierDiscountPercent(bpsToPercentString(selectedDiscountSupplier?.default_discount_bps ?? 0))
    }, 0)

    return () => window.clearTimeout(handle)
  }, [selectedDiscountSupplier])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (!activeCatalogBulkResource) {
        setCatalogBulkField('')
        setCatalogBulkValue('')
        setCatalogBulkPreview(null)
        return
      }
      const firstField = catalogBulkFields[activeCatalogBulkResource][0]
      setCatalogBulkField(firstField.value)
      if (firstField.input === 'select') {
        const firstOption = firstField.value === 'category_id' ? extraCategories[0]?.id ?? '' : firstField.options?.[0]?.value ?? ''
        setCatalogBulkValue(firstOption)
      } else {
        setCatalogBulkValue('')
      }
      setCatalogBulkPreview(null)
      setBulkError(null)
    }, 0)

    return () => window.clearTimeout(handle)
  }, [activeCatalogBulkResource, extraCategories])

  const lookupPriceCents = useCallback(
    (itemType: PriceItemType, itemRefId: string, priceComponent: string) => {
      const canonicalKey = `${itemType}::${itemRefId}`
      const row = currentPriceRows.find(
        (item) =>
          item.item_type === itemType &&
          item.price_component === priceComponent &&
          (item.item_ref_id === itemRefId || item.item_key === canonicalKey),
      )
      return row?.unit_price_cents ?? 0
    },
    [currentPriceRows],
  )

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (!pricingItemRefId) {
        setUnitPriceAmount('0.00')
        setSheetPriceAmount('0.00')
        setEdgingPriceAmount('0.00')
        setLabourPriceAmount('0.00')
        setSqmPriceAmount('0.00')
        return
      }

      if (pricingItemType === 'board') {
        const board = boards.find((item) => item.id === pricingItemRefId)
        if (board?.costing_mode === 'sqm') {
          setSqmPriceAmount(centsToAmountString(lookupPriceCents('board', pricingItemRefId, 'sqm')))
          setSheetPriceAmount('0.00')
          setEdgingPriceAmount('0.00')
          setLabourPriceAmount('0.00')
        } else {
          setSheetPriceAmount(centsToAmountString(lookupPriceCents('board', pricingItemRefId, 'sheet')))
          setEdgingPriceAmount(centsToAmountString(lookupPriceCents('board', pricingItemRefId, 'edging_m')))
          setLabourPriceAmount(centsToAmountString(lookupPriceCents('board', pricingItemRefId, 'labour_board')))
          setSqmPriceAmount('0.00')
        }
        return
      }

      setUnitPriceAmount(centsToAmountString(lookupPriceCents(pricingItemType, pricingItemRefId, 'unit')))
    }, 0)

    return () => window.clearTimeout(handle)
  }, [boards, lookupPriceCents, pricingItemRefId, pricingItemType])

  async function withActionState(action: () => Promise<void>, successMessage: string | (() => string)) {
    setIsSaving(true)
    setActionError(null)
    setActionSuccess(null)
    try {
      await action()
      await refreshSetupChecklist()
      setActionSuccess(typeof successMessage === 'function' ? successMessage() : successMessage)
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Action failed.')
    } finally {
      setIsSaving(false)
    }
  }

  function handleChecklistAction(actionTarget: LibrarySetupActionTarget) {
    if (actionTarget === 'projects') {
      onOpenProjects()
      return
    }
    setActiveTab(actionTarget)
  }

  function handleCoverageSupplierCost(row: PricingCoverageRow) {
    setActiveTab('suppliers')
    if (suppliers.length === 0) {
      setActionError('Add a supplier before saving supplier costs for this item.')
      return
    }
    const supplierId = itemSupplierDraft.supplier_id && suppliers.some((supplier) => supplier.id === itemSupplierDraft.supplier_id)
      ? itemSupplierDraft.supplier_id
      : suppliers[0]?.id ?? ''
    const supplier = suppliers.find((item) => item.id === supplierId)
    const discountPercent = bpsToPercentString(supplier?.default_discount_bps ?? 0)
    const startingCost = row.supplier_unit_cost_cents ?? row.unit_price_cents ?? 0
    setItemSupplierDraft({
      ...defaultItemSupplierDraft,
      item_type: row.item_type,
      item_ref_id: row.item_ref_id,
      supplier_id: supplierId,
      supplier_description: row.item_name,
      price_component: row.price_component,
      order_uom: row.supplier_order_uom ?? row.uom,
      is_preferred: true,
      list_price_amount: centsToAmountString(startingCost),
      discount_percent: discountPercent,
      unit_cost_amount: calculateDiscountedAmountString(centsToAmountString(startingCost), discountPercent) ?? centsToAmountString(startingCost),
    })
    setActionError(null)
    setActionSuccess(`Supplier cost form prepared for ${row.item_name}.`)
  }

  function handleCoverageGenerate(row: PricingCoverageRow) {
    setActiveTab('pricing')
    setActivePricingTab('lists')
    setGenerationItemTypes([row.item_type])
    setPreserveManualOverrides(true)
    setActionError(null)
    setActionSuccess(`Supplier generation prepared for ${row.item_type_label.toLowerCase()} rows.`)
  }

  function handleCoverageManualOverride(row: PricingCoverageRow) {
    setActiveTab('pricing')
    setActivePricingTab('quick-update')
    setPricingItemType(row.item_type)
    setPricingItemRefId(row.item_ref_id)
    const amount = centsToAmountString(row.unit_price_cents ?? 0)
    if (row.item_type === 'board') {
      if (row.price_component === 'sqm') {
        setSqmPriceAmount(amount)
      } else if (row.price_component === 'sheet') {
        setSheetPriceAmount(amount)
      } else if (row.price_component === 'edging_m') {
        setEdgingPriceAmount(amount)
      } else if (row.price_component === 'labour_board') {
        setLabourPriceAmount(amount)
      }
    } else {
      setUnitPriceAmount(amount)
    }
    setActionError(null)
    setActionSuccess(`Manual override form prepared for ${row.item_name}.`)
  }

  function visibleCatalogIds(resource: LibraryCatalogBulkResource) {
    if (resource === 'boards') return visibleBoards.map((row) => row.id)
    if (resource === 'slides') return visibleSlides.map((row) => row.id)
    if (resource === 'hinges') return visibleHinges.map((row) => row.id)
    if (resource === 'handles') return visibleHandles.map((row) => row.id)
    if (resource === 'extras') return visibleExtras.map((row) => row.id)
    return visibleSuppliers.map((row) => row.id)
  }

  function handleCatalogSelection(resource: LibraryCatalogBulkResource, itemId: string, checked: boolean) {
    setSelectedCatalogIds((current) => ({
      ...current,
      [resource]: toggleId(current[resource], itemId, checked),
    }))
    setCatalogBulkPreview(null)
    setBulkError(null)
  }

  function selectVisibleCatalogRows(resource: LibraryCatalogBulkResource) {
    setSelectedCatalogIds((current) => ({
      ...current,
      [resource]: visibleCatalogIds(resource),
    }))
    setCatalogBulkPreview(null)
    setBulkError(null)
  }

  function clearCatalogSelection(resource: LibraryCatalogBulkResource) {
    setSelectedCatalogIds((current) => ({ ...current, [resource]: [] }))
    setCatalogBulkPreview(null)
    setBulkError(null)
  }

  function handlePriceSelection(itemId: string, checked: boolean) {
    setSelectedPriceItemIds((current) => toggleId(current, itemId, checked))
    setPriceBulkPreview(null)
    setBulkError(null)
  }

  function selectVisiblePriceRows() {
    setSelectedPriceItemIds(currentVisiblePriceRows.map((row) => row.id))
    setPriceBulkPreview(null)
    setBulkError(null)
  }

  function catalogBulkUpdates() {
    if (!activeCatalogBulkField) return null
    if (activeCatalogBulkField.value === 'default_discount_bps') {
      const bps = percentStringToBps(catalogBulkValue)
      if (bps === null) return null
      return { [activeCatalogBulkField.value]: bps }
    }
    if (activeCatalogBulkField.value === 'supplier_id') {
      return { supplier_id: catalogBulkValue || null }
    }
    if (activeCatalogBulkField.value === 'front_reduction_mm') {
      const parsed = Number(catalogBulkValue)
      if (!Number.isFinite(parsed) || parsed < 0) return null
      return { front_reduction_mm: Math.floor(parsed) }
    }
    if (!catalogBulkValue.trim()) return null
    return { [activeCatalogBulkField.value]: catalogBulkValue.trim() }
  }

  async function runCatalogBulkUpdate(confirm: boolean) {
    if (!activeCatalogBulkResource || !activeCatalogBulkField) return
    const itemIds = onlyVisibleSelected(activeCatalogSelection, visibleCatalogIds(activeCatalogBulkResource))
    const updates = catalogBulkUpdates()
    if (itemIds.length === 0) {
      setBulkError('Select at least one visible row before previewing a bulk edit.')
      return
    }
    if (!updates) {
      setBulkError('Choose a valid bulk value before previewing.')
      return
    }

    setIsBulkSaving(true)
    setBulkError(null)
    try {
      const result = await apiRequest<LibraryBulkUpdateResult>('/api/v1/libraries/catalog/bulk-update', {
        body: {
          confirm,
          item_ids: itemIds,
          resource: activeCatalogBulkResource,
          updates,
        },
        method: 'PATCH',
        token: authToken,
      })
      setCatalogBulkPreview(result)
      if (confirm) {
        clearCatalogSelection(activeCatalogBulkResource)
        await refreshCatalog()
        await refreshSetupChecklist()
        setActionSuccess(result.summary_message)
      }
    } catch (error) {
      setBulkError(error instanceof Error ? error.message : 'Bulk catalog update failed.')
    } finally {
      setIsBulkSaving(false)
    }
  }

  function priceBulkPayload() {
    const payload: { cost_source?: 'manual' | 'override'; unit_price_cents?: number; uom?: string } = {}
    if (priceBulkAmount.trim()) {
      const amount = amountStringToCents(priceBulkAmount)
      if (amount === null) return null
      payload.unit_price_cents = amount
    }
    if (priceBulkUom.trim()) payload.uom = priceBulkUom.trim()
    if (priceBulkSource !== 'no-change') payload.cost_source = priceBulkSource
    return Object.keys(payload).length > 0 ? payload : null
  }

  async function runPriceBulkUpdate(confirm: boolean) {
    if (!selectedPriceListId) {
      setBulkError('Select a price list before bulk editing prices.')
      return
    }
    const currentVisibleIds = new Set(currentVisiblePriceRows.map((row) => row.id))
    const itemIds = selectedPriceItemIds.filter((id) => currentVisibleIds.has(id))
    const payload = priceBulkPayload()
    if (itemIds.length === 0) {
      setBulkError('Select at least one current price row before previewing.')
      return
    }
    if (!payload) {
      setBulkError('Enter a price, unit, or source change before previewing.')
      return
    }

    setIsBulkSaving(true)
    setBulkError(null)
    try {
      const result = await apiRequest<LibraryBulkUpdateResult>(
        `/api/v1/libraries/price-lists/${selectedPriceListId}/items/bulk-update`,
        {
          body: {
            ...payload,
            confirm,
            item_ids: itemIds,
          },
          method: 'PATCH',
          token: authToken,
        },
      )
      setPriceBulkPreview(result)
      if (confirm) {
        setSelectedPriceItemIds([])
        await Promise.all([refreshPriceItems(selectedPriceListId), refreshPriceCoverage(selectedPriceListId)])
        await refreshSetupChecklist()
        setActionSuccess(result.summary_message)
      }
    } catch (error) {
      setBulkError(error instanceof Error ? error.message : 'Bulk price update failed.')
    } finally {
      setIsBulkSaving(false)
    }
  }

  function renderCatalogMaintenance(resource: LibraryCatalogBulkResource, totalCount: number, visibleIds: string[], actions?: ReactNode) {
    const selectedCount = onlyVisibleSelected(selectedCatalogIds[resource], visibleIds).length
    const accessoryResource = resource === 'slides' || resource === 'hinges' ? resource : null
    return (
      <div className="grid gap-3">
        <MaintenanceToolbar
          recentDays={catalogRecentDays}
          search={catalogSearch}
          onRecentDaysChange={setCatalogRecentDays}
          onSearchChange={setCatalogSearch}
        >
          {resource === 'extras' ? (
            <Label className="grid min-w-44 gap-1.5">
              Category
              <Select value={extraCategoryFilter} onChange={(event) => setExtraCategoryFilter(event.target.value)}>
                <option value="all">All categories</option>
                {extraCategories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </Select>
            </Label>
          ) : null}
          {actions}
        </MaintenanceToolbar>
        <details className="rounded-[var(--control-radius)] border border-border p-3">
          <summary className="cursor-pointer text-sm font-semibold">
            <span className="inline-flex flex-wrap items-center gap-2">
              Bulk edits and row maintenance
              <Badge variant={selectedCount > 0 ? 'default' : 'outline'}>{selectedCount} selected</Badge>
            </span>
          </summary>
          <div className="mt-3">
            <CatalogBulkPanel
              accessoryConfig={accessoryResource ? bulkAccessoryConfigs[accessoryResource] : undefined}
              accessoryOptions={accessoryResource ? accessoryOptions : undefined}
              bulkMode={accessoryResource ? catalogBulkModes[accessoryResource] : undefined}
              field={activeCatalogBulkField}
              fields={activeCatalogBulkFields}
              isSaving={isBulkSaving}
              onAccessoryConfigChange={accessoryResource
                ? (config) => setBulkAccessoryConfigs((current) => ({ ...current, [accessoryResource]: config }))
                : undefined}
              preview={catalogBulkPreview}
              resource={resource}
              selectedCount={selectedCount}
              value={catalogBulkValue}
              visibleCount={visibleIds.length}
              onApplyAccessory={accessoryResource ? () => void applyBulkAccessory(accessoryResource) : undefined}
              onBulkModeChange={accessoryResource
                ? (mode) => setCatalogBulkModes((current) => ({ ...current, [accessoryResource]: mode }))
                : undefined}
              onApply={() => {
                void runCatalogBulkUpdate(true)
              }}
              onClearSelection={() => clearCatalogSelection(resource)}
              onFieldChange={(fieldValue) => {
                const nextField = activeCatalogBulkFields.find((field) => field.value === fieldValue)
                setCatalogBulkField(fieldValue)
                setCatalogBulkValue(nextField?.options?.[0]?.value ?? '')
                setCatalogBulkPreview(null)
                setBulkError(null)
              }}
              onPreview={() => {
                void runCatalogBulkUpdate(false)
              }}
              onSelectVisible={() => selectVisibleCatalogRows(resource)}
              onValueChange={(value) => {
                setCatalogBulkValue(value)
                setCatalogBulkPreview(null)
                setBulkError(null)
              }}
            />
          </div>
        </details>
        <FilteredEmptyNotice filteredCount={visibleIds.length} totalCount={totalCount} />
      </div>
    )
  }

  function renderPriceRowsTable(rows: PriceListItemRow[], showSelection: boolean) {
    return (
      <TableContainer>
        <Table>
          <TableHeader>
            <TableRow>
              {showSelection ? <TableHead className="w-10">Select</TableHead> : null}
              <TableHead>Type</TableHead>
              <TableHead>Item</TableHead>
              <TableHead>Price part</TableHead>
              <TableHead>Unit</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Starts</TableHead>
              <TableHead>Replaced on</TableHead>
              <TableHead>Price</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={showSelection ? 9 : 8}>
                  <div className="grid gap-1 py-3">
                    <p className="font-medium">{priceItems.length === 0 ? 'Build prices for the active list.' : 'No price rows match the filters.'}</p>
                    <p className="text-sm leading-5 text-muted-foreground">
                      {priceItems.length === 0
                        ? 'Add board, hardware, handle, and extra prices here so quote totals can be trusted.'
                        : 'Clear the search or widen the filters to see the price rows in this list.'}
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow key={row.id}>
                  {showSelection ? (
                    <TableCell>
                      <Checkbox
                        checked={selectedPriceItemIds.includes(row.id)}
                        disabled={row.effective_status !== 'current'}
                        onChange={(event) => handlePriceSelection(row.id, event.target.checked)}
                      />
                    </TableCell>
                  ) : null}
                  <TableCell>{priceItemTypeLabel(row.item_type)}</TableCell>
                  <TableCell>
                    {row.item_ref_id
                      ? itemLabelByRef.get(`${row.item_type}:${row.item_ref_id}`) ?? row.item_key
                      : row.item_key}
                  </TableCell>
                  <TableCell>{priceComponentLabel(row.price_component)}</TableCell>
                  <TableCell>{row.uom}</TableCell>
                  <TableCell>
                    <Badge variant={row.cost_source === 'supplier' ? 'default' : 'outline'}>{priceSourceLabel(row.cost_source)}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="grid gap-1 text-xs">
                      <Badge variant={row.effective_status === 'current' ? 'success' : row.effective_status === 'retired' ? 'warning' : 'outline'}>
                        {priceStatusLabel(row.effective_status)}
                      </Badge>
                      <span className="text-muted-foreground">{formatDateTime(row.effective_from)}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {row.effective_to ? formatDateTime(row.effective_to) : 'Still current'}
                  </TableCell>
                  <TableCell>{formatCurrencyFromCents(row.unit_price_cents, displayCurrencyCode)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    )
  }

  function clearImportResults() {
    setImportPreview(null)
    setImportApplyResult(null)
  }

  function buildImportPreviewPayload(columnMapping: Record<string, string>): LibraryImportPreviewRequest {
    return {
      resource: importResource,
      source_format: importSourceFormat,
      filename: importFilename,
      sheet_name: importSheetName.trim() || null,
      content: importContent,
      column_mapping: columnMapping,
      price_list_id: importResource === 'price_list_items' ? selectedPriceListId || null : null,
    }
  }

  function handleImportResourceChange(nextResource: LibraryImportResource) {
    setImportResource(nextResource)
    clearImportResults()
    setImportError(null)
    if (!importFilename) {
      setImportContent(importExampleByResource[nextResource])
      setImportSourceFormat('csv')
    }
  }

  async function handleImportFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    const filename = file.name
    const extension = filename.split('.').pop()?.toLowerCase()
    const nextFormat: LibraryImportSourceFormat = extension === 'xlsx' ? 'xlsx' : extension === 'tsv' ? 'tsv' : 'csv'

    setImportFilename(filename)
    setImportSourceFormat(nextFormat)
    clearImportResults()
    setImportError(null)

    try {
      if (nextFormat === 'xlsx') {
        setImportContent(arrayBufferToBase64(await file.arrayBuffer()))
      } else {
        setImportContent(await file.text())
      }
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Could not read the selected file.')
    }
  }

  async function previewLibraryImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setImportError(null)
    clearImportResults()

    let columnMapping: Record<string, string>
    try {
      columnMapping = parseColumnMapping(importColumnMapping)
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Column mapping is invalid.')
      return
    }

    if (!importContent.trim()) {
      setImportError('Add pasted rows or upload a file before previewing.')
      return
    }

    const payload = buildImportPreviewPayload(columnMapping)

    setIsPreviewingImport(true)
    try {
      const preview = await apiRequest<LibraryImportPreview>('/api/v1/libraries/imports/preview', {
        body: payload,
        method: 'POST',
        token: authToken,
      })
      setImportPreview(preview)
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Import preview failed.')
    } finally {
      setIsPreviewingImport(false)
    }
  }

  async function applyLibraryImport() {
    setImportError(null)
    setImportApplyResult(null)

    if (!importPreview) {
      setImportError('Preview the import before applying it.')
      return
    }

    let columnMapping: Record<string, string>
    try {
      columnMapping = parseColumnMapping(importColumnMapping)
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Column mapping is invalid.')
      return
    }

    const payload: LibraryImportApplyRequest = {
      ...buildImportPreviewPayload(columnMapping),
      source_ref: importSourceRef.trim(),
    }

    setIsApplyingImport(true)
    try {
      const result = await apiRequest<LibraryImportApplyResult>('/api/v1/libraries/imports/apply', {
        body: payload,
        method: 'POST',
        token: authToken,
      })
      setImportApplyResult(result)
      await refreshSetupChecklist()
      await refreshCatalog()
      await refreshPricing()
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Import apply failed.')
    } finally {
      setIsApplyingImport(false)
    }
  }

  async function handleSavePricingSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const payload = pricingSettingsPayloadFromDraft(pricingSettingsDraft)
    if (!payload) {
      setActionError('Pricing settings must be valid positive numbers.')
      return
    }

    await withActionState(async () => {
      const updated = await apiRequest<PricingSettingsRow>('/api/v1/libraries/pricing-settings', {
        body: payload,
        method: 'PATCH',
        token: authToken,
      })
      setPricingSettings(updated)
      setPricingSettingsDraft(pricingSettingsToDraft(updated))
    }, 'Pricing settings updated.')
  }

  async function handleCreatePriceList(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const name = priceListDraft.name.trim()
    if (!name) {
      setActionError('Price list name is required.')
      return
    }

    await withActionState(async () => {
      const created = await apiRequest<PriceListRow>('/api/v1/libraries/price-lists', {
        body: {
          name,
          status: priceListDraft.status,
          effective_from: null,
          effective_to: null,
        },
        method: 'POST',
        token: authToken,
      })
      const nextLists = [created, ...priceLists]
      setPriceLists(nextLists)
      setPriceListDraft(defaultPriceListDraft)
      setSelectedPriceListId(created.id)
      await Promise.all([refreshPriceItems(created.id), refreshPriceCoverage(created.id)])
    }, 'Price list created.')
  }

  async function handleSelectPriceList(nextPriceListId: string) {
    setSelectedPriceListId(nextPriceListId)
    if (importResource === 'price_list_items') {
      clearImportResults()
    }
    if (nextPriceListId) {
      await Promise.all([refreshPriceItems(nextPriceListId), refreshPriceCoverage(nextPriceListId)])
    } else {
      setPriceItems([])
      setPriceCoverage(null)
    }
  }

  async function handleSaveQuickPrice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedPriceListId) {
      setActionError('Select a price list first.')
      return
    }
    if (!pricingItemRefId) {
      setActionError('Select an item before saving a price.')
      return
    }

    await withActionState(async () => {
      if (pricingItemType === 'board') {
        const board = boards.find((item) => item.id === pricingItemRefId)
        if (!board) {
          throw new Error('Select a board first.')
        }
        if (board.costing_mode === 'sqm') {
          const sqmPrice = amountStringToCents(sqmPriceAmount)
          if (sqmPrice === null) {
            throw new Error('Square metre price must be a valid number.')
          }
          await upsertPriceItem(authToken, selectedPriceListId, {
            item_type: 'board',
            item_ref_id: pricingItemRefId,
            price_component: 'sqm',
            uom: 'm2',
            unit_price_cents: sqmPrice,
          })
        } else {
          const sheetPrice = amountStringToCents(sheetPriceAmount)
          const edgingPrice = amountStringToCents(edgingPriceAmount)
          const labourPrice = amountStringToCents(labourPriceAmount)
          if (sheetPrice === null || edgingPrice === null || labourPrice === null) {
            throw new Error('Board prices must all be valid numbers.')
          }

          await Promise.all([
            upsertPriceItem(authToken, selectedPriceListId, {
              item_type: 'board',
              item_ref_id: pricingItemRefId,
              price_component: 'sheet',
              uom: 'sheet',
              unit_price_cents: sheetPrice,
            }),
            upsertPriceItem(authToken, selectedPriceListId, {
              item_type: 'board',
              item_ref_id: pricingItemRefId,
              price_component: 'edging_m',
              uom: 'm',
              unit_price_cents: edgingPrice,
            }),
            upsertPriceItem(authToken, selectedPriceListId, {
              item_type: 'board',
              item_ref_id: pricingItemRefId,
              price_component: 'labour_board',
              uom: 'board',
              unit_price_cents: labourPrice,
            }),
          ])
        }
      } else {
        const unitPrice = amountStringToCents(unitPriceAmount)
        if (unitPrice === null) {
          throw new Error('Cost price must be a valid number.')
        }
        await upsertPriceItem(authToken, selectedPriceListId, {
          item_type: pricingItemType,
          item_ref_id: pricingItemRefId,
          price_component: 'unit',
          uom: itemTypeDefaultUom(pricingItemType),
          unit_price_cents: unitPrice,
        })
      }

      await Promise.all([refreshPriceItems(selectedPriceListId), refreshPriceCoverage(selectedPriceListId)])
    }, 'Price saved.')
  }

  async function createBoard(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildBoardPayload(boardDraft)
    if (!payload) {
      setActionError('Board values are invalid.')
      return
    }

    await withActionState(async () => {
      await apiRequest('/api/v1/libraries/boards', { body: payload, method: 'POST', token: authToken })
      setBoardDraft(defaultBoardDraft)
      setCreateHardwareResource(null)
      await refreshCatalog()
    }, 'Board added.')
  }

  async function updateBoard(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingBoard) return
    const payload = buildBoardPayload({
      brand: editingBoard.brand,
      material: editingBoard.material,
      thickness: String(editingBoard.thickness),
      length_mm: String(editingBoard.length_mm),
      width_mm: String(editingBoard.width_mm),
      costing_mode: editingBoard.costing_mode,
      grain_policy: editingBoard.grain_policy,
    })
    if (!payload) {
      setActionError('Board values are invalid.')
      return
    }

    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/boards/${editingBoard.id}`, {
        body: payload,
        method: 'PATCH',
        token: authToken,
      })
      setEditingBoard(null)
      await refreshCatalog()
    }, 'Board updated.')
  }

  async function deleteBoard(itemId: string) {
    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/boards/${itemId}`, { method: 'DELETE', token: authToken })
      if (editingBoard?.id === itemId) {
        setEditingBoard(null)
      }
      await refreshCatalog()
    }, 'Board deleted.')
  }

  async function createSlideRange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildSlideRangePayload(slideRangeDraft)
    if (!payload) {
      setActionError('Complete the runner range details and add at least one valid length.')
      return
    }

    await withActionState(async () => {
      const result = await apiRequest<SlideRangeCreateResponse>('/api/v1/libraries/slides/ranges', {
        body: payload,
        method: 'POST',
        token: authToken,
      })
      setSlideRangeDraft(defaultSlideRangeDraft)
      setInlineSlideAccessoryDraft(defaultExtraDraft)
      setCreateHardwareResource(null)
      await refreshCatalog()
      setActionSuccess(`${result.created_count} drawer hardware row${result.created_count === 1 ? '' : 's'} added.`)
    }, 'Drawer hardware range added.')
  }

  async function createInlineSlideAccessory() {
    const categoryId = inlineSlideAccessoryDraft.category_id || extraCategories[0]?.id || ''
    const payload = buildExtraPayload({ ...inlineSlideAccessoryDraft, category_id: categoryId })
    if (!payload) {
      setActionError('Accessory name and category are required.')
      return
    }

    await withActionState(async () => {
      const created = await apiRequest<ExtraRow>('/api/v1/libraries/extras', {
        body: payload,
        method: 'POST',
        token: authToken,
      })
      const condition =
        slideRangeDraft.mount_type === 'metal_system'
          ? {
              field: 'drawer_front_height' as const,
              operator: 'greater_than_or_equal' as const,
              value_number: 180,
              value_text: '',
            }
          : {
              field: 'always' as const,
              operator: 'always' as const,
              value_number: null,
              value_text: '',
            }
      const rule: HardwareAccessoryRule = {
        ...emptyAccessoryRule(),
        item_ref_id: created.id,
        quantity: 1,
        quantity_rule: 'per_drawer',
        required: true,
        enabled: true,
        uom: 'pcs',
        condition,
      }
      setExtras((current) => [created, ...current.filter((item) => item.id !== created.id)])
      setSlideRangeDraft((current) => ({
        ...current,
        accessory_config: mergeAccessoryConfig(current.accessory_config, [rule]),
      }))
      setInlineSlideAccessoryDraft({ ...defaultExtraDraft, category_id: categoryId })
    }, 'Accessory added to this drawer hardware setup.')
  }

  async function updateSlide(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingSlide) return
    const payload = buildSlidePayload({
      brand: editingSlide.brand,
      model: editingSlide.model,
      code: editingSlide.code,
      length: String(editingSlide.length),
      side_length: String(editingSlide.side_length),
      side_clearance_total: String(editingSlide.side_clearance_total),
      side_height_uplift: String(editingSlide.side_height_uplift),
      mount_type: editingSlide.mount_type ?? 'side_mount',
      product_family: editingSlide.product_family ?? '',
      required_depth_mm: String(editingSlide.required_depth_mm ?? 0),
      drawer_depth_deduction_mm: String(editingSlide.drawer_depth_deduction_mm ?? 0),
      box_width_deduction_mm: String(editingSlide.box_width_deduction_mm ?? 0),
      drawer_system_kind: editingSlide.drawer_system_kind ?? 'conventional',
      drawer_system_config: editingSlide.drawer_system_config ?? {},
      accessory_config: editingSlide.accessory_config ?? { accessories: [] },
    })
    if (!payload) {
      setActionError('Slide values are invalid.')
      return
    }

    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/slides/${editingSlide.id}`, {
        body: payload,
        method: 'PATCH',
        token: authToken,
      })
      setEditingSlide(null)
      await refreshCatalog()
    }, 'Slide updated.')
  }

  async function deleteSlide(itemId: string) {
    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/slides/${itemId}`, { method: 'DELETE', token: authToken })
      if (editingSlide?.id === itemId) {
        setEditingSlide(null)
      }
      await refreshCatalog()
    }, 'Slide deleted.')
  }

  async function createHinge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildHingePayload(hingeDraft)
    if (!payload) {
      setActionError('Hinge values are invalid.')
      return
    }

    await withActionState(async () => {
      await apiRequest('/api/v1/libraries/hinges', { body: payload, method: 'POST', token: authToken })
      setHingeDraft(defaultHingeDraft)
      setCreateHardwareResource(null)
      await refreshCatalog()
    }, 'Hinge added.')
  }

  async function updateHinge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingHinge) return
    const payload = buildHingePayload({
      brand: editingHinge.brand,
      model: editingHinge.model,
      code: editingHinge.code,
      opening_angle_deg: String(editingHinge.opening_angle_deg),
      accessory_config: editingHinge.accessory_config ?? { accessories: [] },
    })
    if (!payload) {
      setActionError('Hinge values are invalid.')
      return
    }

    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/hinges/${editingHinge.id}`, {
        body: payload,
        method: 'PATCH',
        token: authToken,
      })
      setEditingHinge(null)
      await refreshCatalog()
    }, 'Hinge updated.')
  }

  async function deleteHinge(itemId: string) {
    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/hinges/${itemId}`, { method: 'DELETE', token: authToken })
      if (editingHinge?.id === itemId) {
        setEditingHinge(null)
      }
      await refreshCatalog()
    }, 'Hinge deleted.')
  }

  async function applyBulkAccessory(resource: BulkAccessoryResource) {
    const visibleIds = resource === 'slides' ? visibleSlides.map((row) => row.id) : visibleHinges.map((row) => row.id)
    const selectedIds = onlyVisibleSelected(selectedCatalogIds[resource], visibleIds)
    const additions = normalizeAccessoryConfig(bulkAccessoryConfigs[resource]).accessories ?? []
    if (selectedIds.length === 0) {
      setActionError('Select at least one visible slide or hinge before adding an accessory.')
      return
    }
    if (additions.length === 0) {
      setActionError('Choose at least one accessory rule before applying it.')
      return
    }

    const selected = new Set(selectedIds)
    await withActionState(async () => {
      if (resource === 'slides') {
        const selectedSlides = slides.filter((row) => selected.has(row.id))
        for (const row of selectedSlides) {
          const payload = buildSlidePayload({
            brand: row.brand,
            model: row.model,
            code: row.code,
            length: String(row.length),
            side_length: String(row.side_length),
            side_clearance_total: String(row.side_clearance_total),
            side_height_uplift: String(row.side_height_uplift),
            mount_type: row.mount_type ?? 'side_mount',
            product_family: row.product_family ?? '',
            required_depth_mm: String(row.required_depth_mm ?? 0),
            drawer_depth_deduction_mm: String(row.drawer_depth_deduction_mm ?? 0),
            box_width_deduction_mm: String(row.box_width_deduction_mm ?? 0),
            drawer_system_kind: row.drawer_system_kind ?? 'conventional',
            drawer_system_config: row.drawer_system_config ?? {},
            accessory_config: mergeAccessoryConfig(row.accessory_config, additions),
          })
          if (!payload) throw new Error(`Slide values are invalid for ${formatSlideLabel(row)}.`)
          await apiRequest(`/api/v1/libraries/slides/${row.id}`, { body: payload, method: 'PATCH', token: authToken })
        }
      } else {
        const selectedHinges = hinges.filter((row) => selected.has(row.id))
        for (const row of selectedHinges) {
          const payload = buildHingePayload({
            brand: row.brand,
            model: row.model,
            code: row.code,
            opening_angle_deg: String(row.opening_angle_deg),
            accessory_config: mergeAccessoryConfig(row.accessory_config, additions),
          })
          if (!payload) throw new Error(`Hinge values are invalid for ${formatHingeLabel(row)}.`)
          await apiRequest(`/api/v1/libraries/hinges/${row.id}`, { body: payload, method: 'PATCH', token: authToken })
        }
      }

      clearCatalogSelection(resource)
      setBulkAccessoryConfigs((current) => ({ ...current, [resource]: emptyBulkAccessoryConfig() }))
      await refreshCatalog()
    }, () => `Accessory bundle added to ${selectedIds.length} selected ${bulkAccessoryResourceCountLabel(resource, selectedIds.length)}.`)
  }

  async function createSupplier(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildSupplierPayload(supplierDraft)
    if (!payload) {
      setActionError('Supplier name and discount must be valid.')
      return
    }

    await withActionState(async () => {
      await apiRequest('/api/v1/libraries/suppliers', { body: payload, method: 'POST', token: authToken })
      setSupplierDraft(defaultSupplierDraft)
      setCreateHardwareResource(null)
      await refreshCatalog()
    }, 'Supplier added.')
  }

  async function updateSupplier(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingSupplier) return
    const payload = buildSupplierPayload(editingSupplier)
    if (!payload) {
      setActionError('Supplier name and discount must be valid.')
      return
    }

    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/suppliers/${editingSupplier.id}`, {
        body: payload,
        method: 'PATCH',
        token: authToken,
      })
      setEditingSupplier(null)
      await refreshCatalog()
    }, 'Supplier updated.')
  }

  async function deleteSupplier(itemId: string) {
    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/suppliers/${itemId}`, { method: 'DELETE', token: authToken })
      if (editingSupplier?.id === itemId) {
        setEditingSupplier(null)
      }
      await refreshCatalog()
    }, 'Supplier deleted.')
  }

  function updateItemSupplierSupplier(nextSupplierId: string) {
    const supplier = suppliers.find((item) => item.id === nextSupplierId)
    const discountPercent = bpsToPercentString(supplier?.default_discount_bps ?? 0)
    setItemSupplierDraft((current) => ({
      ...current,
      supplier_id: nextSupplierId,
      discount_percent: discountPercent,
      unit_cost_amount: calculateDiscountedAmountString(current.list_price_amount, discountPercent) ?? current.unit_cost_amount,
    }))
  }

  function updateItemSupplierListPrice(nextListPriceAmount: string) {
    setItemSupplierDraft((current) => ({
      ...current,
      list_price_amount: nextListPriceAmount,
      unit_cost_amount: calculateDiscountedAmountString(nextListPriceAmount, current.discount_percent) ?? current.unit_cost_amount,
    }))
  }

  function updateItemSupplierDiscount(nextDiscountPercent: string) {
    setItemSupplierDraft((current) => ({
      ...current,
      discount_percent: nextDiscountPercent,
      unit_cost_amount: calculateDiscountedAmountString(current.list_price_amount, nextDiscountPercent) ?? current.unit_cost_amount,
    }))
  }

  async function applySupplierDiscount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!discountSupplierId) {
      setActionError('Select a supplier before applying a discount.')
      return
    }
    const discountBps = percentStringToBps(supplierDiscountPercent)
    if (discountBps === null) {
      setActionError('Supplier discount must be between 0 and 100%.')
      return
    }

    let summary: SupplierDiscountSummary | null = null
    await withActionState(async () => {
      summary = await apiRequest<SupplierDiscountSummary>(`/api/v1/libraries/suppliers/${discountSupplierId}/discount`, {
        body: {
          discount_bps: discountBps,
          apply_to_active_costs: applyDiscountToCosts,
          source: 'supplier-discount',
          source_ref: 'libraries-ui',
          effective_from: null,
        },
        method: 'POST',
        token: authToken,
      })
      await refreshCatalog()
      if (selectedPriceListId) {
        await refreshPriceCoverage(selectedPriceListId)
      }
    }, () => {
      if (!summary) return 'Supplier discount saved.'
      if (!applyDiscountToCosts) return 'Supplier default discount saved.'
      return `Supplier discount saved. Updated ${summary.updated_cost_count} costs; ${summary.unchanged_cost_count} already matched.`
    })
  }

  async function saveItemSupplierCost(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const linkPayload = buildItemSupplierPayload(itemSupplierDraft)
    const listPrice = amountStringToCents(itemSupplierDraft.list_price_amount)
    const discountBps = percentStringToBps(itemSupplierDraft.discount_percent)
    const unitCost = amountStringToCents(itemSupplierDraft.unit_cost_amount)
    if (!linkPayload || listPrice === null || discountBps === null || unitCost === null) {
      setActionError('Supplier item and cost values are invalid.')
      return
    }

    await withActionState(async () => {
      const existingLink = itemSuppliers.find(
        (row) =>
          row.item_type === linkPayload.item_type &&
          row.item_ref_id === linkPayload.item_ref_id &&
          row.supplier_id === linkPayload.supplier_id &&
          row.supplier_sku === linkPayload.supplier_sku &&
          row.price_component === linkPayload.price_component,
      )

      const link = existingLink
        ? await apiRequest<ItemSupplierRow>(`/api/v1/libraries/item-suppliers/${existingLink.id}`, {
            body: linkPayload,
            method: 'PATCH',
            token: authToken,
          })
        : await apiRequest<ItemSupplierRow>('/api/v1/libraries/item-suppliers', {
            body: linkPayload,
            method: 'POST',
            token: authToken,
          })

      await apiRequest(`/api/v1/libraries/item-suppliers/${link.id}/costs/upsert`, {
        body: {
          list_price_cents: listPrice,
          discount_bps: discountBps,
          unit_cost_cents: unitCost,
          currency_code: displayCurrencyCode,
          source: 'manual',
          source_ref: 'libraries-ui',
          effective_from: null,
        },
        method: 'POST',
        token: authToken,
      })

      setItemSupplierDraft((current) => ({
        ...defaultItemSupplierDraft,
        item_type: current.item_type,
        item_ref_id: current.item_ref_id,
        supplier_id: current.supplier_id,
        order_uom: current.order_uom,
        price_component: current.price_component,
      }))
      await refreshCatalog()
      if (selectedPriceListId) {
        await refreshPriceCoverage(selectedPriceListId)
      }
    }, 'Supplier cost saved.')
  }

  async function deleteItemSupplier(itemId: string) {
    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/item-suppliers/${itemId}`, { method: 'DELETE', token: authToken })
      await refreshCatalog()
      if (selectedPriceListId) {
        await refreshPriceCoverage(selectedPriceListId)
      }
    }, 'Supplier source deleted.')
  }

  async function generatePricesFromSupplierCosts(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedPriceListId) {
      setActionError('Select a price list first.')
      return
    }
    if (generationItemTypes.length === 0) {
      setActionError('Select at least one item type to generate.')
      return
    }

    await withActionState(async () => {
      const summary = await apiRequest<GeneratePriceListSummary>(
        `/api/v1/libraries/price-lists/${selectedPriceListId}/generate-from-supplier-costs`,
        {
          body: {
            selection_mode: generationMode,
            item_types: generationItemTypes,
            preserve_manual_overrides: preserveManualOverrides,
            effective_from: generationEffectiveFrom ? new Date(generationEffectiveFrom).toISOString() : null,
          },
          method: 'POST',
          token: authToken,
        },
      )
      setLastGenerationSummary(summary)
      await Promise.all([refreshPriceItems(selectedPriceListId), refreshPriceCoverage(selectedPriceListId)])
    }, 'Price list generated from supplier costs.')
  }

  function toggleGenerationItemType(itemType: PriceItemType, checked: boolean) {
    setGenerationItemTypes((current) => {
      if (checked) return current.includes(itemType) ? current : [...current, itemType]
      return current.filter((value) => value !== itemType)
    })
  }

  function updateSlideRangeLength(index: number, updates: Partial<SlideRangeLengthDraft>) {
    setSlideRangeDraft((current) => ({
      ...current,
      lengths: current.lengths.map((row, rowIndex) => (rowIndex === index ? { ...row, ...updates } : row)),
    }))
  }

  function addSlideRangeLength() {
    setSlideRangeDraft((current) => ({
      ...current,
      lengths: [...current.lengths, emptySlideRangeLengthDraft()],
    }))
  }

  function removeSlideRangeLength(index: number) {
    setSlideRangeDraft((current) => ({
      ...current,
      lengths: current.lengths.length > 1 ? current.lengths.filter((_, rowIndex) => rowIndex !== index) : current.lengths,
    }))
  }

  async function createHandle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildHandlePayload(handleDraft)
    if (!payload) {
      setActionError('Handle name is required.')
      return
    }

    await withActionState(async () => {
      await apiRequest('/api/v1/libraries/handles', { body: payload, method: 'POST', token: authToken })
      setHandleDraft(defaultHandleDraft)
      setCreateHardwareResource(null)
      await refreshCatalog()
    }, 'Handle added.')
  }

  async function updateHandle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingHandle) return
    const payload = buildHandlePayload(editingHandle)
    if (!payload) {
      setActionError('Handle name is required.')
      return
    }

    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/handles/${editingHandle.id}`, {
        body: payload,
        method: 'PATCH',
        token: authToken,
      })
      setEditingHandle(null)
      await refreshCatalog()
    }, 'Handle updated.')
  }

  async function deleteHandle(itemId: string) {
    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/handles/${itemId}`, { method: 'DELETE', token: authToken })
      if (editingHandle?.id === itemId) {
        setEditingHandle(null)
      }
      await refreshCatalog()
    }, 'Handle deleted.')
  }

  async function createExtraCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const name = extraCategoryDraft.name.trim()
    if (!name) {
      setActionError('Category name is required.')
      return
    }

    await withActionState(async () => {
      await apiRequest('/api/v1/libraries/extra-categories', {
        body: { name },
        method: 'POST',
        token: authToken,
      })
      setExtraCategoryDraft(defaultExtraCategoryDraft)
      setCreateHardwareResource(null)
      await refreshCatalog()
    }, 'Category added.')
  }

  async function updateExtraCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingExtraCategory) return
    const name = editingExtraCategory.name.trim()
    if (!name) {
      setActionError('Category name is required.')
      return
    }

    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/extra-categories/${editingExtraCategory.id}`, {
        body: { name },
        method: 'PATCH',
        token: authToken,
      })
      setEditingExtraCategory(null)
      await refreshCatalog()
    }, 'Category updated.')
  }

  async function deleteExtraCategory(itemId: string) {
    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/extra-categories/${itemId}`, { method: 'DELETE', token: authToken })
      if (editingExtraCategory?.id === itemId) {
        setEditingExtraCategory(null)
      }
      await refreshCatalog()
    }, 'Category deleted.')
  }

  async function createExtra(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildExtraPayload(extraDraft)
    if (!payload) {
      setActionError('Extra name and category are required.')
      return
    }

    await withActionState(async () => {
      await apiRequest('/api/v1/libraries/extras', { body: payload, method: 'POST', token: authToken })
      setExtraDraft((current) => ({ ...defaultExtraDraft, category_id: current.category_id }))
      setCreateHardwareResource(null)
      await refreshCatalog()
    }, 'Extra added.')
  }

  async function updateExtra(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!editingExtra) return
    const payload = buildExtraPayload(editingExtra)
    if (!payload) {
      setActionError('Extra name and category are required.')
      return
    }

    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/extras/${editingExtra.id}`, {
        body: payload,
        method: 'PATCH',
        token: authToken,
      })
      setEditingExtra(null)
      await refreshCatalog()
    }, 'Extra updated.')
  }

  async function deleteExtra(itemId: string) {
    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/extras/${itemId}`, { method: 'DELETE', token: authToken })
      if (editingExtra?.id === itemId) {
        setEditingExtra(null)
      }
      await refreshCatalog()
    }, 'Extra deleted.')
  }

  const isLoading = isLoadingCatalog || isLoadingPricing
  const nextSetupItem = setupChecklist?.items.find((item) => item.status !== 'complete') ?? null
  const importPreviewProblemCount = importPreview
    ? importPreview.summary.blocked_count + importPreview.summary.duplicate_count
    : 0
  const importPreviewSaveCount = importPreview
    ? importPreview.summary.create_count + importPreview.summary.update_count
    : 0
  const importHasBlockedRows = (importPreview?.summary.blocked_count ?? 0) > 0

  return (
    <div className="grid min-w-0 gap-4">
      <Dialog
        open={createHardwareResource === 'slides'}
        onOpenChange={(open) => {
          if (!open) setCreateHardwareResource(null)
        }}
        title="Add Drawer Runner Range"
        description="Create length-specific runner rows from one product range."
        size="xwide"
      >
        <form className="flex flex-col gap-5" onSubmit={createSlideRange}>
          <div className="grid gap-3 rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
            <p className="text-sm font-medium">Runner range</p>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              <Label className="grid gap-1.5">
                Runner type
                <Select
                  value={slideRangeDraft.mount_type}
                  onChange={(event) => setSlideRangeDraft((current) => rangeDraftForMountType(current, event.target.value as SlideMountType))}
                >
                  <option value="side_mount">Side mount</option>
                  <option value="undermount">Undermount</option>
                  <option value="metal_system">Metal-sided system</option>
                  <option value="custom">Custom</option>
                </Select>
              </Label>
              <Label className="grid gap-1.5">
                Brand
                <Input value={slideRangeDraft.brand} onChange={(event) => setSlideRangeDraft((current) => ({ ...current, brand: event.target.value }))} />
              </Label>
              <Label className="grid gap-1.5">
                Product range
                <Input
                  value={slideRangeDraft.product_family}
                  onChange={(event) => {
                    const product_family = event.target.value
                    setSlideRangeDraft((current) => ({
                      ...current,
                      product_family,
                      drawer_system_config:
                        current.mount_type === 'metal_system'
                          ? { ...current.drawer_system_config, product_family }
                          : current.drawer_system_config,
                    }))
                  }}
                />
              </Label>
              <Label className="grid gap-1.5">
                Code pattern
                <Input placeholder="DYN-{length}" value={slideRangeDraft.code_pattern} onChange={(event) => setSlideRangeDraft((current) => ({ ...current, code_pattern: event.target.value }))} />
              </Label>
            </div>
            <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-5">
              <Label className="grid gap-1.5">
                Side clearance
                <Input value={slideRangeDraft.side_clearance_total} onChange={(event) => setSlideRangeDraft((current) => ({ ...current, side_clearance_total: event.target.value }))} />
              </Label>
              <Label className="grid gap-1.5">
                Depth deduction
                <Input value={slideRangeDraft.drawer_depth_deduction_mm} onChange={(event) => setSlideRangeDraft((current) => ({ ...current, drawer_depth_deduction_mm: event.target.value }))} />
              </Label>
              <Label className="grid gap-1.5">
                Width deduction
                <Input value={slideRangeDraft.box_width_deduction_mm} onChange={(event) => setSlideRangeDraft((current) => ({ ...current, box_width_deduction_mm: event.target.value }))} />
              </Label>
              <Label className="grid gap-1.5">
                Required depth
                <Input value={slideRangeDraft.required_depth_mm} onChange={(event) => setSlideRangeDraft((current) => ({ ...current, required_depth_mm: event.target.value }))} />
              </Label>
              <Label className="grid gap-1.5">
                Side uplift
                <Input value={slideRangeDraft.side_height_uplift} onChange={(event) => setSlideRangeDraft((current) => ({ ...current, side_height_uplift: event.target.value }))} />
              </Label>
            </div>
          </div>

          {slideRangeDraft.mount_type === 'metal_system' ? (
            <div className="grid gap-3">
              <Alert variant="warning">
                Use accessory rules for rails when metal drawer sides need them above a drawer front or side height.
              </Alert>
              <DrawerSystemConfigEditor
                config={slideRangeDraft.drawer_system_config}
                drawerSystemKind="metal"
                onChange={(drawer_system_config) => setSlideRangeDraft((current) => ({ ...current, drawer_system_config }))}
              />
            </div>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,24rem)]">
            <div className="grid content-start gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">Lengths</p>
                <Button type="button" variant="outline" size="sm" onClick={addSlideRangeLength}>
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  Add Length (mm)
                </Button>
              </div>
              <div className="grid gap-2">
                <div className="hidden gap-2 px-3 text-xs font-medium uppercase text-muted-foreground lg:grid lg:grid-cols-[5rem_minmax(7rem,1fr)_5.5rem_5.5rem_5.5rem_5.5rem_2.25rem]">
                  <span>Length (mm)</span>
                  <span>Code</span>
                  <span>Side</span>
                  <span>Depth</span>
                  <span>Deduct</span>
                  <span>Width</span>
                  <span />
                </div>
                {slideRangeDraft.lengths.map((row, index) => (
                  <div
                    className="grid gap-3 rounded-[var(--card-radius)] border border-border bg-card p-3 lg:grid-cols-[5rem_minmax(7rem,1fr)_5.5rem_5.5rem_5.5rem_5.5rem_2.25rem] lg:items-center lg:gap-2 lg:p-2"
                    key={index}
                  >
                    <Label className="grid gap-1.5 lg:block">
                      <span className="lg:sr-only">Length (mm)</span>
                      <Input value={row.length} onChange={(event) => updateSlideRangeLength(index, { length: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5 lg:block">
                      <span className="lg:sr-only">Code</span>
                      <Input value={row.code} onChange={(event) => updateSlideRangeLength(index, { code: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5 lg:block">
                      <span className="lg:sr-only">Side length</span>
                      <Input value={row.side_length} onChange={(event) => updateSlideRangeLength(index, { side_length: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5 lg:block">
                      <span className="lg:sr-only">Required depth</span>
                      <Input value={row.required_depth_mm} onChange={(event) => updateSlideRangeLength(index, { required_depth_mm: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5 lg:block">
                      <span className="lg:sr-only">Depth deduction</span>
                      <Input value={row.drawer_depth_deduction_mm} onChange={(event) => updateSlideRangeLength(index, { drawer_depth_deduction_mm: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5 lg:block">
                      <span className="lg:sr-only">Width deduction</span>
                      <Input value={row.box_width_deduction_mm} onChange={(event) => updateSlideRangeLength(index, { box_width_deduction_mm: event.target.value })} />
                    </Label>
                    <Button type="button" size="icon" variant="ghost" onClick={() => removeSlideRangeLength(index)} disabled={slideRangeDraft.lengths.length <= 1}>
                      <XCircle className="h-4 w-4" aria-hidden="true" />
                      <span className="sr-only">Remove length</span>
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid content-start gap-3 rounded-[var(--card-radius)] border border-border p-3">
              <p className="text-sm font-medium">Generated rows</p>
              {slideRangePreview.length > 0 ? (
                <div className="grid gap-2">
                  {slideRangePreview.map((row) => (
                    <div className="grid gap-1 rounded-[var(--control-radius)] bg-muted/50 px-3 py-2 text-sm" key={`${row.model}-${row.length}`}>
                      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                        <span className="font-medium">{row.model || `${slideRangeDraft.product_family || 'Runner'} ${row.length}`}</span>
                        <span className="text-muted-foreground">{row.code || '-'}</span>
                      </div>
                      <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                        <span>{formatSlideMountType(slideRangeDraft.mount_type)}</span>
                        <span>{row.sideLength}mm side</span>
                        <span>{row.requiredDepth}mm depth</span>
                        <span>{row.widthDeduction}mm width</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="rounded-[var(--control-radius)] bg-muted/50 px-3 py-2 text-sm text-muted-foreground">Add at least one valid runner length.</p>
              )}
            </div>
          </div>

          <HardwareAccessoryConfigEditor
            config={slideRangeDraft.accessory_config}
            onChange={(accessory_config) => setSlideRangeDraft((current) => ({ ...current, accessory_config }))}
            options={accessoryOptions}
          />

          <details className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3">
            <summary className="cursor-pointer text-sm font-medium">Create accessory item</summary>
            <div className="mt-3 grid gap-3 md:grid-cols-4">
              <Label className="grid gap-1.5">
                Name
                <Input value={inlineSlideAccessoryDraft.name} onChange={(event) => setInlineSlideAccessoryDraft((current) => ({ ...current, name: event.target.value }))} />
              </Label>
              <Label className="grid gap-1.5">
                Category
                <Select
                  value={inlineSlideAccessoryDraft.category_id || extraCategories[0]?.id || ''}
                  onChange={(event) => setInlineSlideAccessoryDraft((current) => ({ ...current, category_id: event.target.value }))}
                >
                  {extraCategories.length === 0 ? <option value="">No categories</option> : null}
                  {extraCategories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </Select>
              </Label>
              <Label className="grid gap-1.5">
                Supplier
                <Select value={inlineSlideAccessoryDraft.supplier_id} onChange={(event) => setInlineSlideAccessoryDraft((current) => ({ ...current, supplier_id: event.target.value }))}>
                  <option value="">No supplier</option>
                  {suppliers.map((supplier) => (
                    <option key={supplier.id} value={supplier.id}>
                      {supplier.name}
                    </option>
                  ))}
                </Select>
              </Label>
              <Label className="grid gap-1.5">
                Code
                <Input value={inlineSlideAccessoryDraft.code} onChange={(event) => setInlineSlideAccessoryDraft((current) => ({ ...current, code: event.target.value }))} />
              </Label>
              <Label className="grid gap-1.5 md:col-span-4">
                Notes
                <Textarea value={inlineSlideAccessoryDraft.notes} onChange={(event) => setInlineSlideAccessoryDraft((current) => ({ ...current, notes: event.target.value }))} />
              </Label>
              <div className="md:col-span-4">
                <Button disabled={isSaving || extraCategories.length === 0} type="button" variant="outline" onClick={() => void createInlineSlideAccessory()}>
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  Add accessory to setup
                </Button>
              </div>
            </div>
          </details>

          <div className="sticky bottom-0 -mx-[var(--card-padding)] -mb-[var(--card-padding)] flex flex-wrap gap-2 border-t border-border bg-card px-[var(--card-padding)] py-3">
            <Button disabled={isSaving} type="submit">
              <Save className="h-4 w-4" aria-hidden="true" />
              Save Runner Range
            </Button>
            <Button type="button" variant="outline" onClick={() => setCreateHardwareResource(null)}>
              Cancel
            </Button>
          </div>
        </form>
      </Dialog>
      <Dialog
        open={createHardwareResource === 'hinges'}
        onOpenChange={(open) => {
          if (!open) setCreateHardwareResource(null)
        }}
        title="Add Hinge"
        description="Create a hinge entry for the hardware library."
        size="wide"
      >
        <form className="grid gap-3 md:grid-cols-4" onSubmit={createHinge}>
          <Label className="grid gap-1.5">
            Brand
            <Input value={hingeDraft.brand} onChange={(event) => setHingeDraft((current) => ({ ...current, brand: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Model
            <Input value={hingeDraft.model} onChange={(event) => setHingeDraft((current) => ({ ...current, model: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Code
            <Input value={hingeDraft.code} onChange={(event) => setHingeDraft((current) => ({ ...current, code: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Opening angle
            <Input value={hingeDraft.opening_angle_deg} onChange={(event) => setHingeDraft((current) => ({ ...current, opening_angle_deg: event.target.value }))} />
          </Label>
          <HardwareAccessoryConfigEditor
            config={hingeDraft.accessory_config}
            onChange={(accessory_config) => setHingeDraft((current) => ({ ...current, accessory_config }))}
            options={accessoryOptions}
          />
          <div className="md:col-span-4 flex flex-wrap gap-2">
            <Button disabled={isSaving} type="submit">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Hinge
            </Button>
            <Button type="button" variant="outline" onClick={() => setCreateHardwareResource(null)}>
              Cancel
            </Button>
          </div>
        </form>
      </Dialog>
      <Dialog
        open={createHardwareResource === 'boards'}
        onOpenChange={(open) => {
          if (!open) setCreateHardwareResource(null)
        }}
        title="Add Board"
        description="Create a board material for carcasses, doors, panels, and quote defaults."
        size="wide"
      >
        <form className="grid gap-3 md:grid-cols-3" onSubmit={createBoard}>
          <Label className="grid gap-1.5">
            Brand
            <Input value={boardDraft.brand} onChange={(event) => setBoardDraft((current) => ({ ...current, brand: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Material
            <Input value={boardDraft.material} onChange={(event) => setBoardDraft((current) => ({ ...current, material: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Costing mode
            <Select value={boardDraft.costing_mode} onChange={(event) => setBoardDraft((current) => ({ ...current, costing_mode: event.target.value as 'sheet' | 'sqm' }))}>
              <option value="sheet">sheet</option>
              <option value="sqm">sqm</option>
            </Select>
          </Label>
          <Label className="grid gap-1.5">
            Grain
            <Select value={boardDraft.grain_policy} onChange={(event) => setBoardDraft((current) => ({ ...current, grain_policy: event.target.value as BoardGrainPolicy }))}>
              {boardGrainPolicyOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Label>
          <Label className="grid gap-1.5">
            Thickness (mm)
            <Input value={boardDraft.thickness} onChange={(event) => setBoardDraft((current) => ({ ...current, thickness: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Length (mm)
            <Input value={boardDraft.length_mm} onChange={(event) => setBoardDraft((current) => ({ ...current, length_mm: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Width (mm)
            <Input value={boardDraft.width_mm} onChange={(event) => setBoardDraft((current) => ({ ...current, width_mm: event.target.value }))} />
          </Label>
          <div className="md:col-span-3 flex flex-wrap gap-2">
            <Button disabled={isSaving} type="submit">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Board
            </Button>
            <Button type="button" variant="outline" onClick={() => setCreateHardwareResource(null)}>
              Cancel
            </Button>
          </div>
        </form>
      </Dialog>
      <Dialog
        open={createHardwareResource === 'suppliers'}
        onOpenChange={(open) => {
          if (!open) setCreateHardwareResource(null)
        }}
        title="Add Supplier"
        description="Create a supplier for contact details, default discounts, and cost sources."
        size="wide"
      >
        <form className="grid gap-3 md:grid-cols-2" onSubmit={createSupplier}>
          <Label className="grid gap-1.5">
            Name
            <Input value={supplierDraft.name} onChange={(event) => setSupplierDraft((current) => ({ ...current, name: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Code
            <Input value={supplierDraft.code} onChange={(event) => setSupplierDraft((current) => ({ ...current, code: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Contact
            <Input value={supplierDraft.contact_name} onChange={(event) => setSupplierDraft((current) => ({ ...current, contact_name: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Email
            <Input value={supplierDraft.email} onChange={(event) => setSupplierDraft((current) => ({ ...current, email: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Phone
            <Input value={supplierDraft.phone} onChange={(event) => setSupplierDraft((current) => ({ ...current, phone: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Default discount (%)
            <Input value={supplierDraft.default_discount_percent} onChange={(event) => setSupplierDraft((current) => ({ ...current, default_discount_percent: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5 md:col-span-2">
            Notes
            <Textarea value={supplierDraft.notes} onChange={(event) => setSupplierDraft((current) => ({ ...current, notes: event.target.value }))} />
          </Label>
          <div className="md:col-span-2 flex flex-wrap gap-2">
            <Button disabled={isSaving} type="submit">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Supplier
            </Button>
            <Button type="button" variant="outline" onClick={() => setCreateHardwareResource(null)}>
              Cancel
            </Button>
          </div>
        </form>
      </Dialog>
      <Dialog
        open={createHardwareResource === 'handles'}
        onOpenChange={(open) => {
          if (!open) setCreateHardwareResource(null)
        }}
        title="Add Handle"
        description="Create a standard handle, full-length profile, or C/J channel profile."
        size="wide"
      >
        <form className="grid gap-3 md:grid-cols-4" onSubmit={createHandle}>
          <Label className="grid gap-1.5">
            Name
            <Input value={handleDraft.name} onChange={(event) => setHandleDraft((current) => ({ ...current, name: event.target.value }))} />
          </Label>
          <Label className="grid gap-1.5">
            Type
            <Select
              value={handleDraft.handle_type}
              onChange={(event) =>
                setHandleDraft((current) => ({
                  ...current,
                  handle_type: event.target.value as HandleType,
                  front_reduction_mm: event.target.value === 'standard' ? '0' : current.front_reduction_mm,
                }))
              }
            >
              {handleTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Label>
          {handleDraft.handle_type !== 'standard' ? (
            <Label className="grid gap-1.5">
              Front reduction (mm)
              <Input
                min={0}
                onChange={(event) => setHandleDraft((current) => ({ ...current, front_reduction_mm: event.target.value }))}
                type="number"
                value={handleDraft.front_reduction_mm}
              />
            </Label>
          ) : null}
          <Label className="grid gap-1.5">
            Supplier
            <Select value={handleDraft.supplier_id} onChange={(event) => setHandleDraft((current) => ({ ...current, supplier_id: event.target.value }))}>
              <option value="">No supplier</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </option>
              ))}
            </Select>
          </Label>
          <div className="md:col-span-4 flex flex-wrap gap-2">
            <Button disabled={isSaving} type="submit">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Handle
            </Button>
            <Button type="button" variant="outline" onClick={() => setCreateHardwareResource(null)}>
              Cancel
            </Button>
          </div>
        </form>
      </Dialog>
      <Dialog
        open={createHardwareResource === 'extra-categories'}
        onOpenChange={(open) => {
          if (!open) setCreateHardwareResource(null)
        }}
        title="Add Extra Category"
        description="Create a category for extras such as delivery, installation, or accessories."
      >
        <form className="grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-end" onSubmit={createExtraCategory}>
          <Label className="grid gap-1.5">
            Category name
            <Input
              value={extraCategoryDraft.name}
              onChange={(event) => setExtraCategoryDraft({ name: event.target.value })}
            />
          </Label>
          <Button disabled={isSaving} type="submit">
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add Category
          </Button>
          <Button type="button" variant="outline" onClick={() => setCreateHardwareResource(null)}>
            Cancel
          </Button>
        </form>
      </Dialog>
      <Dialog
        open={createHardwareResource === 'extras'}
        onOpenChange={(open) => {
          if (!open) setCreateHardwareResource(null)
        }}
        title="Add Extra"
        description="Create an extra line item for quote add-ons and non-board costs."
        size="wide"
      >
        {extraCategories.length === 0 ? (
          <div className="grid gap-3">
            <Alert variant="destructive">Create at least one extra category before adding extras.</Alert>
            <div>
              <Button type="button" variant="outline" onClick={() => setCreateHardwareResource(null)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <form className="grid gap-3 md:grid-cols-2" onSubmit={createExtra}>
            <Label className="grid gap-1.5">
              Name
              <Input value={extraDraft.name} onChange={(event) => setExtraDraft((current) => ({ ...current, name: event.target.value }))} />
            </Label>
            <Label className="grid gap-1.5">
              Category
              <Select
                value={extraDraft.category_id}
                onChange={(event) => setExtraDraft((current) => ({ ...current, category_id: event.target.value }))}
              >
                <option value="">Select a category</option>
                {extraCategories.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </Select>
            </Label>
            <Label className="grid gap-1.5">
              Supplier
              <Select value={extraDraft.supplier_id} onChange={(event) => setExtraDraft((current) => ({ ...current, supplier_id: event.target.value }))}>
                <option value="">No supplier</option>
                {suppliers.map((supplier) => (
                  <option key={supplier.id} value={supplier.id}>
                    {supplier.name}
                  </option>
                ))}
              </Select>
            </Label>
            <Label className="grid gap-1.5">
              Code
              <Input value={extraDraft.code} onChange={(event) => setExtraDraft((current) => ({ ...current, code: event.target.value }))} />
            </Label>
            <Label className="grid gap-1.5 md:col-span-2">
              Notes
              <Textarea value={extraDraft.notes} onChange={(event) => setExtraDraft((current) => ({ ...current, notes: event.target.value }))} />
            </Label>
            <div className="md:col-span-2 flex flex-wrap gap-2">
              <Button disabled={isSaving} type="submit">
                <Plus className="h-4 w-4" aria-hidden="true" />
                Add Extra
              </Button>
              <Button type="button" variant="outline" onClick={() => setCreateHardwareResource(null)}>
                Cancel
              </Button>
            </div>
          </form>
        )}
      </Dialog>
      <div className="flex flex-col gap-2 rounded-[var(--card-radius)] border border-border bg-card px-3 py-2 md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-2 text-sm">
          {setupChecklist ? (
            <Badge variant={setupChecklist.status === 'ready' ? 'success' : 'warning'}>
              {setupChecklist.complete_count}/{setupChecklist.total_count} ready
            </Badge>
          ) : (
            <Badge variant="outline">Checking setup</Badge>
          )}
          {missingPriceRows.length > 0 ? <Badge variant="warning">{missingPriceRows.length} missing prices</Badge> : null}
        </div>
        <Button
          className="w-fit"
          disabled={isLoading || isLoadingChecklist || isSaving}
          onClick={() => {
            void refreshSetupChecklist()
            void refreshCatalog()
            void refreshPricing()
          }}
          size="sm"
          type="button"
          variant="outline"
        >
          {isLoading || isLoadingChecklist ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RefreshCcw className="h-4 w-4" aria-hidden="true" />}
          Refresh
        </Button>
      </div>

      <div className="grid gap-2">
        {catalogError ? <Alert variant="destructive">Could not load the library rows. Refresh and try again. {catalogError}</Alert> : null}
        {pricingError ? <Alert variant="destructive">Could not load pricing rows. Refresh and try again. {pricingError}</Alert> : null}
        {checklistError ? <Alert variant="destructive">Could not check library readiness. Refresh and try again. {checklistError}</Alert> : null}
        {actionError ? <Alert variant="destructive">The change was not saved. Check the details and try again. {actionError}</Alert> : null}
        {bulkError ? <Alert variant="destructive">The bulk edit was not saved. Preview the selected rows and try again. {bulkError}</Alert> : null}
        {actionSuccess ? <Alert>{actionSuccess}</Alert> : null}
      </div>

      {activeTab === 'setup-imports' ? (
        <>
          <Card>
            <CardHeader className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
                  Setup Checklist
                </CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  {setupChecklist?.summary_message ?? 'Checking boards, hardware, supplier costs, pricing, and quote defaults.'}
                </p>
              </div>
              {setupChecklist ? (
                <Badge variant={setupChecklist.status === 'ready' ? 'success' : 'warning'}>
                  {setupChecklist.complete_count}/{setupChecklist.total_count} ready
                </Badge>
              ) : null}
            </CardHeader>
            <CardContent className="grid gap-3">
              {isLoadingChecklist ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Loading setup checklist.
                </div>
              ) : setupChecklist ? (
                <>
                  {nextSetupItem ? (
                    <Alert variant="warning">
                      Next best step: {nextSetupItem.label}. {nextSetupItem.message}
                    </Alert>
                  ) : (
                    <Alert>
                      Setup is ready. New quotes can use the visible libraries and current prices.
                    </Alert>
                  )}
                  <div className="grid gap-2 lg:grid-cols-3">
                    {setupChecklist.items.map((item) => (
                      <div className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3" key={item.id}>
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex min-w-0 items-center gap-2">
                            <SetupStatusIcon status={item.status} />
                            <p className="truncate text-sm font-medium">{item.label}</p>
                          </div>
                          <Badge variant={setupStatusBadgeVariant(item.status)}>{setupStatusLabel(item.status)}</Badge>
                        </div>
                        <p className="text-sm leading-5 text-muted-foreground">{item.message}</p>
                        <Button
                          className="w-fit"
                          onClick={() => handleChecklistAction(item.action_target)}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          {item.action_target === 'projects' ? (
                            <ExternalLink className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <ArrowRight className="h-4 w-4" aria-hidden="true" />
                          )}
                          {item.action_label}
                        </Button>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <Alert variant="warning">The setup checklist is not available right now. Refresh Libraries, then sign in again if it keeps happening.</Alert>
              )}
            </CardContent>
          </Card>

          <details className="rounded-[var(--card-radius)] border border-border p-3">
            <summary className="cursor-pointer text-sm font-semibold">
              Import catalog rows from a supplier sheet or CSV
            </summary>
            <p className="mt-2 text-sm text-muted-foreground">
              Preview imports here when you need bulk setup. Everyday material and hardware edits live in the catalog sections above.
            </p>
            <div className="mt-3">
          <Card>
            <CardHeader className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />
                  Import Preview
                </CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  Preview shows exactly what will be added, changed, ignored, or needs fixing before anything is saved.
                </p>
              </div>
              <Badge variant="outline">preview before saving</Badge>
            </CardHeader>
            <CardContent className="grid gap-4">
              {importError ? <Alert variant="destructive">The import could not be previewed or saved. {importError}</Alert> : null}
              <Alert>{importResourceHelp(importResource, selectedPriceList?.name)}</Alert>
              <form className="grid gap-3" onSubmit={previewLibraryImport}>
                <div className="grid gap-3 lg:grid-cols-4">
                  <Label className="grid gap-1.5">
                    Import type
                    <Select
                      value={importResource}
                      onChange={(event) => handleImportResourceChange(event.target.value as LibraryImportResource)}
                    >
                      {importResourceOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </Label>
                  <Label className="grid gap-1.5">
                    Source
                    <Select
                      value={importSourceFormat}
                      onChange={(event) => {
                        const nextFormat = event.target.value as LibraryImportSourceFormat
                        setImportSourceFormat(nextFormat)
                        clearImportResults()
                        setImportError(null)
                        if (nextFormat !== 'xlsx' && importSourceFormat === 'xlsx') {
                          setImportFilename('')
                          setImportContent(importExampleByResource[importResource])
                        }
                      }}
                    >
                      {importSourceFormatOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </Label>
                  <Label className="grid gap-1.5">
                    Sheet
                    <Input
                      disabled={importSourceFormat !== 'xlsx'}
                      placeholder="Sheet1"
                      value={importSheetName}
                      onChange={(event) => {
                        setImportSheetName(event.target.value)
                        clearImportResults()
                      }}
                    />
                  </Label>
                  <Label className="grid gap-1.5">
                    Upload
                    <Input
                      accept=".csv,.tsv,.xlsx,text/csv,text/tab-separated-values,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                      onChange={(event) => {
                        void handleImportFileChange(event)
                      }}
                      type="file"
                    />
                  </Label>
                </div>
                <Label className="grid gap-1.5">
                  Source reference
                  <Input
                    placeholder="Supplier price list June"
                    value={importSourceRef}
                    onChange={(event) => {
                      setImportSourceRef(event.target.value)
                      setImportApplyResult(null)
                    }}
                  />
                  <span className="text-xs text-muted-foreground">Use a short note you will recognize later, such as the supplier price list month.</span>
                </Label>

                {importSourceFormat === 'xlsx' ? (
                  <Alert>
                    {importFilename ? `${importFilename} is ready to preview.` : 'Choose an XLSX workbook before previewing.'}
                  </Alert>
                ) : (
                  <Label className="grid gap-1.5">
                    Rows
                    <Textarea
                      className="min-h-32 font-mono text-xs"
                      value={importContent}
                      onChange={(event) => {
                        setImportContent(event.target.value)
                        setImportFilename('')
                        clearImportResults()
                      }}
                    />
                  </Label>
                )}

                <Label className="grid gap-1.5">
                  Column mapping
                  <Textarea
                    className="min-h-20 font-mono text-xs"
                    placeholder="unit_cost_cents=Net Cost"
                    value={importColumnMapping}
                    onChange={(event) => {
                      setImportColumnMapping(event.target.value)
                      clearImportResults()
                    }}
                  />
                  <span className="text-xs text-muted-foreground">
                    Optional. Use this only when a supplier sheet uses different headings, for example unit_cost_cents=Net Cost.
                  </span>
                </Label>

                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    disabled={isPreviewingImport || isApplyingImport || (importSourceFormat === 'xlsx' && !importFilename)}
                    type="submit"
                  >
                    {isPreviewingImport ? (
                      <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Eye className="h-4 w-4" aria-hidden="true" />
                    )}
                    Preview Import
                  </Button>
                  <Button
                    disabled={!importPreview || importHasBlockedRows || isPreviewingImport || isApplyingImport || (importSourceFormat === 'xlsx' && !importFilename)}
                    onClick={() => {
                      void applyLibraryImport()
                    }}
                    type="button"
                    variant="outline"
                  >
                    {isApplyingImport ? (
                      <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Upload className="h-4 w-4" aria-hidden="true" />
                    )}
                    Apply Import
                  </Button>
                  {importFilename ? <Badge variant="outline">{importFilename}</Badge> : null}
                  {importResource === 'price_list_items' && selectedPriceList ? (
                    <Badge variant="outline">{selectedPriceList.name}</Badge>
                  ) : null}
                </div>
                {importPreview ? (
                  importPreviewProblemCount > 0 ? (
                    <Alert variant="warning">
                      Review before applying: {importPreviewProblemCount} rows need attention. Rows marked Needs fixing must be corrected before Apply Import is available; duplicate rows will be skipped.
                    </Alert>
                  ) : importPreviewSaveCount === 0 ? (
                    <Alert>
                      Nothing new to save. Every row in this preview is already current in CoreQuote.
                    </Alert>
                  ) : (
                    <Alert>
                      Safe to apply: CoreQuote will save {importPreviewSaveCount} rows marked Will add or Will update, and leave Already current rows alone.
                    </Alert>
                  )
                ) : null}
              </form>

              {importPreview ? (
                <div className="grid gap-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{importResourceLabel(importPreview.resource)}</Badge>
                    <Badge variant="outline">{importPreview.summary.total_rows} rows</Badge>
                    {importSummaryItems.map((item) => (
                      <Badge key={item.status} variant={importStatusBadgeVariant(item.status)}>
                        {item.value} {item.label}
                      </Badge>
                    ))}
                  </div>

                  <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                    {importPreview.mapped_fields
                      .filter((field) => field.source_column || field.required)
                      .map((field) => (
                        <div className="rounded-[var(--control-radius)] border border-border px-3 py-2 text-sm" key={field.field}>
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium">{field.label}</span>
                            {field.required ? <Badge variant="outline">required</Badge> : null}
                          </div>
                          <p className="mt-1 break-words text-xs text-muted-foreground">
                            {field.source_column || 'not mapped'}
                          </p>
                        </div>
                      ))}
                  </div>

                  <TableContainer>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Row</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Matched item</TableHead>
                          <TableHead>What CoreQuote read</TableHead>
                          <TableHead>What to do</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {visibleImportRows.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={5}>
                              <div className="py-3 text-sm text-muted-foreground">No import rows were found.</div>
                            </TableCell>
                          </TableRow>
                        ) : (
                          visibleImportRows.map((row) => (
                            <TableRow key={`${row.row_number}-${row.identity || row.status}`}>
                              <TableCell>{row.row_number}</TableCell>
                              <TableCell>
                                <div className="grid gap-1">
                                  <Badge className="w-fit" variant={importStatusBadgeVariant(row.status)}>{importStatusLabel(row.status)}</Badge>
                                  <span className="max-w-56 text-xs text-muted-foreground">{importStatusHelp(row.status)}</span>
                                </div>
                              </TableCell>
                              <TableCell className="max-w-64 break-words text-xs">{row.identity || 'New library row'}</TableCell>
                              <TableCell className="max-w-80 break-words text-xs">{payloadPreview(row.payload)}</TableCell>
                              <TableCell className="min-w-72">
                                <div className="grid gap-1 text-xs">
                                  <span>{row.message}</span>
                                  {row.problems.map((problem) => (
                                    <span className="text-muted-foreground" key={`${row.row_number}-${problem.field}-${problem.code}`}>
                                      {problem.message} {problem.suggestion}
                                    </span>
                                  ))}
                                </div>
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  {importPreview.rows.length > visibleImportRows.length ? (
                    <p className="text-xs text-muted-foreground">
                      Showing first {visibleImportRows.length} of {importPreview.rows.length} rows.
                    </p>
                  ) : null}
                </div>
              ) : null}

              {importApplyResult ? (
                <div className="grid gap-4 rounded-[var(--control-radius)] border border-border p-3">
                  <Alert variant={importApplyResult.summary.failed_count > 0 ? 'warning' : undefined}>
                    {importApplyResult.summary.failed_count > 0
                      ? 'Some rows were not saved. Fix rows marked Needs fixing, then preview the import again.'
                      : 'Import applied. Added and updated rows are now available in Libraries and Pricing.'}
                  </Alert>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">Import receipt {importApplyResult.batch_id}</Badge>
                    <Badge variant="outline">{importApplyResult.summary.total_rows} rows</Badge>
                    {importApplySummaryItems.map((item) => (
                      <Badge key={item.status} variant={importApplyStatusBadgeVariant(item.status)}>
                        {item.value} {item.label}
                      </Badge>
                    ))}
                  </div>
                  <TableContainer>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Row</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Saved item</TableHead>
                          <TableHead>What happened</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {visibleImportApplyRows.map((row) => (
                          <TableRow key={`${row.row_number}-${row.status}-${row.target_id}`}>
                            <TableCell>{row.row_number}</TableCell>
                            <TableCell>
                              <Badge variant={importApplyStatusBadgeVariant(row.status)}>{importApplyStatusLabel(row.status)}</Badge>
                            </TableCell>
                            <TableCell className="max-w-64 break-words text-xs">{row.identity || row.target_id || '-'}</TableCell>
                            <TableCell className="min-w-72">
                              <div className="grid gap-1 text-xs">
                                <span>{row.message}</span>
                                {row.problems.map((problem) => (
                                  <span className="text-muted-foreground" key={`${row.row_number}-${problem.field}-${problem.code}`}>
                                    {problem.message} {problem.suggestion}
                                  </span>
                                ))}
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                  {importApplyResult.rows.length > visibleImportApplyRows.length ? (
                    <p className="text-xs text-muted-foreground">
                      Showing first {visibleImportApplyRows.length} of {importApplyResult.rows.length} rows.
                    </p>
                  ) : null}
                </div>
              ) : null}
            </CardContent>
          </Card>
            </div>
          </details>
        </>
      ) : null}

      {isLoading ? (
        <Card>
          <CardContent className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
            <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
            Loading libraries and pricing data.
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && activeTab === 'pricing' ? (
        <>
          <Card>
            <CardContent className="overflow-x-auto p-3">
              <ControlGroup className="min-w-max" role="tablist" aria-label="Pricing tabs">
                {pricingSubTabs.map((tab) => (
                  <ControlGroupItem
                    aria-pressed={activePricingTab === tab.value}
                    key={tab.value}
                    onClick={() => setActivePricingTab(tab.value)}
                  >
                    {tab.label}
                  </ControlGroupItem>
                ))}
              </ControlGroup>
            </CardContent>
          </Card>

          {activePricingTab === 'coverage' ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Pricing Coverage</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  Quote-used catalog rows are checked against {selectedPriceList?.name ?? 'the selected price list'}.
                </p>
              </CardHeader>
              <CardContent>
                <PricingCoveragePanel
                  coverage={priceCoverage}
                  currencyCode={displayCurrencyCode}
                  isLoading={isLoadingCoverage}
                  onAddSupplierCost={handleCoverageSupplierCost}
                  onGenerateFromSupplierCosts={handleCoverageGenerate}
                  onManualOverride={handleCoverageManualOverride}
                />
              </CardContent>
            </Card>
          ) : null}

          {activePricingTab === 'settings' ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CircleDollarSign className="h-4 w-4" aria-hidden="true" />
                Pricing Settings
                <Badge variant="outline">{displayCurrencyCode}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <PricingSettingsEditor
                currencyCode={displayCurrencyCode}
                draft={pricingSettingsDraft}
                isSaving={isSaving}
                onDraftChange={setPricingSettingsDraft}
                onSubmit={handleSavePricingSettings}
              />
              {pricingSettings ? (
                <p className="mt-3 text-xs text-muted-foreground">
                  Last updated: {formatDateTime(pricingSettings.updated_at)} · {currencyLabel(displayCurrencyCode)}
                </p>
              ) : null}
            </CardContent>
          </Card>
          ) : null}

          {activePricingTab === 'lists' ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Supplier Costs & Price Lists</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                <Label className="grid gap-1.5">
                  Active working list
                  <Select
                    onChange={(event) => {
                      void handleSelectPriceList(event.target.value)
                    }}
                    value={selectedPriceListId}
                  >
                    <option value="">Select a price list</option>
                    {priceLists.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.name} ({row.status === 'active' ? 'active' : row.status})
                      </option>
                    ))}
                  </Select>
                </Label>
                {selectedPriceList ? (
                  <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                    <Badge variant={selectedPriceList.status === 'active' ? 'default' : 'outline'}>{selectedPriceList.status}</Badge>
                    <span>{selectedPriceList.name}</span>
                    <span>New quote totals use prices from this list.</span>
                  </div>
                ) : null}
                {priceLists.length === 0 ? (
                  <Alert className="text-xs">
                    Create a price list before adding prices. Most shops keep one active trade list and update it as supplier costs change.
                  </Alert>
                ) : null}
                <form className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3" onSubmit={handleCreatePriceList}>
                  <p className="text-sm font-medium">Create a new price list</p>
                  <Label className="grid gap-1.5">
                    Name
                    <Input
                      placeholder="Trade Price List"
                      value={priceListDraft.name}
                      onChange={(event) => setPriceListDraft((current) => ({ ...current, name: event.target.value }))}
                    />
                  </Label>
                  <Label className="grid gap-1.5">
                    Status
                    <Select
                      value={priceListDraft.status}
                      onChange={(event) =>
                        setPriceListDraft((current) => ({ ...current, status: event.target.value as PriceListDraft['status'] }))
                      }
                    >
                      <option value="draft">draft</option>
                      <option value="active">active</option>
                    </Select>
                  </Label>
                  <Button disabled={isSaving} type="submit">
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    Create
                  </Button>
                </form>
                <form className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3" onSubmit={generatePricesFromSupplierCosts}>
                  <p className="text-sm font-medium">Generate from supplier costs</p>
                  <Alert variant="warning">
                    Generating prices creates or updates current price rows from supplier costs. Existing quote evidence stays unchanged; new and recalculated totals use the new current prices.
                  </Alert>
                  <Label className="grid gap-1.5">
                    Source selection
                    <Select
                      value={generationMode}
                      onChange={(event) => setGenerationMode(event.target.value as GeneratePriceListSummary['selection_mode'])}
                    >
                      <option value="preferred_then_cheapest">Preferred supplier, otherwise cheapest active cost</option>
                      <option value="preferred_only">Preferred supplier only</option>
                      <option value="cheapest">Cheapest active supplier cost</option>
                    </Select>
                  </Label>
                  <Label className="grid gap-1.5">
                    Starts from
                    <Input
                      type="datetime-local"
                      value={generationEffectiveFrom}
                      onChange={(event) => setGenerationEffectiveFrom(event.target.value)}
                    />
                  </Label>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {generationTypeOptions.map((option) => (
                      <Label className="flex items-center gap-2 text-sm font-normal" key={option.value}>
                        <Checkbox
                          checked={generationItemTypes.includes(option.value)}
                          onChange={(event) => toggleGenerationItemType(option.value, event.target.checked)}
                        />
                        {option.label}
                      </Label>
                    ))}
                  </div>
                  <Label className="flex items-center gap-2 text-sm font-normal">
                    <Checkbox
                      checked={preserveManualOverrides}
                      onChange={(event) => setPreserveManualOverrides(event.target.checked)}
                    />
                    Keep manual override prices
                  </Label>
                  <Button disabled={isSaving || isLoadingPriceItems || !selectedPriceListId} type="submit">
                    <RefreshCcw className="h-4 w-4" aria-hidden="true" />
                    Generate
                  </Button>
                  {lastGenerationSummary ? (
                    <p className="text-xs text-muted-foreground">
                      Supplier cost generation finished: {lastGenerationSummary.created_count} added, {lastGenerationSummary.updated_count} replaced, {lastGenerationSummary.unchanged_count} already current, and {lastGenerationSummary.skipped_override_count} manual overrides left alone.
                    </p>
                  ) : null}
                </form>
              </CardContent>
            </Card>
          ) : null}

          {activePricingTab === 'quick-update' ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Manual Price Override</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                <Alert variant="warning">
                  Saving a manual override replaces the current price for future quote totals and keeps the old price in history.
                </Alert>
                <form className="grid gap-3" onSubmit={handleSaveQuickPrice}>
                  <Label className="grid gap-1.5">
                    Item type
                    <Select
                      value={pricingItemType}
                      onChange={(event) => setPricingItemType(event.target.value as PriceItemType)}
                    >
                      {priceItemTypes.map((itemType) => (
                        <option key={itemType} value={itemType}>
                          {priceItemTypeLabel(itemType)}
                        </option>
                      ))}
                    </Select>
                  </Label>
                  <Label className="grid gap-1.5">
                    Item
                    <Select
                      value={pricingItemRefId}
                      onChange={(event) => setPricingItemRefId(event.target.value)}
                    >
                      <option value="">Select an item</option>
                      {pricingItemOptions.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </Label>

                  {pricingItemRefId ? (
                    <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                      <Badge variant="outline">Locked component/unit</Badge>
                      <span>{componentUomSummary(pricingItemType, selectedBoardForPricing)}</span>
                    </div>
                  ) : null}

                  {pricingItemType === 'board' && selectedBoardForPricing?.costing_mode === 'sheet' ? (
                    <div className="grid gap-3 md:grid-cols-3">
                      <Label className="grid gap-1.5">
                        Sheet price ({displayCurrencyCode})
                        <Input value={sheetPriceAmount} onChange={(event) => setSheetPriceAmount(event.target.value)} />
                      </Label>
                      <Label className="grid gap-1.5">
                        Edging price / m ({displayCurrencyCode})
                        <Input value={edgingPriceAmount} onChange={(event) => setEdgingPriceAmount(event.target.value)} />
                      </Label>
                      <Label className="grid gap-1.5">
                        Labour / board ({displayCurrencyCode})
                        <Input value={labourPriceAmount} onChange={(event) => setLabourPriceAmount(event.target.value)} />
                      </Label>
                    </div>
                  ) : null}

                  {pricingItemType === 'board' && selectedBoardForPricing?.costing_mode === 'sqm' ? (
                    <Label className="grid gap-1.5">
                      Square metre price ({displayCurrencyCode})
                      <Input value={sqmPriceAmount} onChange={(event) => setSqmPriceAmount(event.target.value)} />
                    </Label>
                  ) : null}

                  {pricingItemType !== 'board' ? (
                    <Label className="grid gap-1.5">
                      Selling price ({displayCurrencyCode})
                      <Input value={unitPriceAmount} onChange={(event) => setUnitPriceAmount(event.target.value)} />
                    </Label>
                  ) : null}

                  {pricingItemOptions.length === 0 ? (
                    <Alert className="text-xs">
                      Add at least one {priceItemTypeLabel(pricingItemType).toLowerCase()} in the library before saving prices for this item type.
                    </Alert>
                  ) : null}

                  <Button disabled={isSaving || isLoadingPriceItems} type="submit">
                    <Save className="h-4 w-4" aria-hidden="true" />
                    Save Override
                  </Button>
                </form>
              </CardContent>
            </Card>
          ) : null}

          {activePricingTab === 'history' ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Price History</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Future prices wait until their start date. History-only prices remain for audit.
              </p>
            </CardHeader>
            <CardContent>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge variant="outline">{futurePriceRows.length} start later</Badge>
                <Badge variant="warning">{retiredPriceRows.length} history only</Badge>
              </div>
              <div className="mb-3 grid gap-3">
                <MaintenanceToolbar
                  recentDays={priceRecentDays}
                  search={priceSearch}
                  onRecentDaysChange={setPriceRecentDays}
                  onSearchChange={setPriceSearch}
                >
                  <Label className="grid min-w-36 gap-1.5">
                    Status
                    <Select value={priceStatusFilter} onChange={(event) => setPriceStatusFilter(event.target.value as PriceStatusFilterValue)}>
                      {priceStatusOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </Label>
                  <Label className="grid min-w-32 gap-1.5">
                    Type
                    <Select value={priceTypeFilter} onChange={(event) => setPriceTypeFilter(event.target.value as PriceTypeFilterValue)}>
                      <option value="all">All types</option>
                      {priceItemTypes.map((itemType) => (
                        <option key={itemType} value={itemType}>
                          {priceItemTypeLabel(itemType)}
                        </option>
                      ))}
                    </Select>
                  </Label>
                  <Label className="grid min-w-36 gap-1.5">
                    Source
                    <Select value={priceSourceFilter} onChange={(event) => setPriceSourceFilter(event.target.value as PriceSourceFilterValue)}>
                      {priceSourceOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </Label>
                </MaintenanceToolbar>
                <FilteredEmptyNotice filteredCount={historyVisiblePriceRows.length} totalCount={priceItems.length} />
              </div>
              {renderPriceRowsTable(historyVisiblePriceRows, false)}
            </CardContent>
          </Card>
          ) : null}

          {activePricingTab === 'all-prices' ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">All Prices</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Current prices are used for new or recalculated totals. Select current rows here for bulk changes.
              </p>
            </CardHeader>
            <CardContent>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge variant="default">{currentPriceRows.length} used for new totals</Badge>
                <Badge variant="outline">{futurePriceRows.length} start later</Badge>
                <Badge variant="warning">{retiredPriceRows.length} history only</Badge>
              </div>
              <div className="mb-3 grid gap-3">
                <MaintenanceToolbar
                  recentDays={priceRecentDays}
                  search={priceSearch}
                  onRecentDaysChange={setPriceRecentDays}
                  onSearchChange={setPriceSearch}
                >
                  <Label className="grid min-w-36 gap-1.5">
                    Status
                    <Select value={priceStatusFilter} onChange={(event) => setPriceStatusFilter(event.target.value as PriceStatusFilterValue)}>
                      {priceStatusOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </Label>
                  <Label className="grid min-w-32 gap-1.5">
                    Type
                    <Select value={priceTypeFilter} onChange={(event) => setPriceTypeFilter(event.target.value as PriceTypeFilterValue)}>
                      <option value="all">All types</option>
                      {priceItemTypes.map((itemType) => (
                        <option key={itemType} value={itemType}>
                          {priceItemTypeLabel(itemType)}
                        </option>
                      ))}
                    </Select>
                  </Label>
                  <Label className="grid min-w-36 gap-1.5">
                    Source
                    <Select value={priceSourceFilter} onChange={(event) => setPriceSourceFilter(event.target.value as PriceSourceFilterValue)}>
                      {priceSourceOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </Label>
                </MaintenanceToolbar>
                <MissingPricesPanel
                  missingPriceRows={missingPriceRows}
                  typeFilter={missingPriceTypeFilter}
                  onTypeFilterChange={setMissingPriceTypeFilter}
                />
                <PriceBulkPanel
                  amount={priceBulkAmount}
                  isSaving={isBulkSaving}
                  preview={priceBulkPreview}
                  selectedCount={selectedPriceItemIds.length}
                  source={priceBulkSource}
                  uom={priceBulkUom}
                  visibleCurrentCount={currentVisiblePriceRows.length}
                  onAmountChange={(value) => {
                    setPriceBulkAmount(value)
                    setPriceBulkPreview(null)
                    setBulkError(null)
                  }}
                  onApply={() => {
                    void runPriceBulkUpdate(true)
                  }}
                  onClearSelection={() => {
                    setSelectedPriceItemIds([])
                    setPriceBulkPreview(null)
                    setBulkError(null)
                  }}
                  onPreview={() => {
                    void runPriceBulkUpdate(false)
                  }}
                  onSelectVisible={selectVisiblePriceRows}
                  onSourceChange={(value) => {
                    setPriceBulkSource(value)
                    setPriceBulkPreview(null)
                    setBulkError(null)
                  }}
                  onUomChange={(value) => {
                    setPriceBulkUom(value)
                    setPriceBulkPreview(null)
                    setBulkError(null)
                  }}
                />
                <FilteredEmptyNotice filteredCount={visiblePriceRows.length} totalCount={priceItems.length} />
              </div>
              {renderPriceRowsTable(visiblePriceRows, true)}
            </CardContent>
          </Card>
          ) : null}
        </>
      ) : null}

      {!isLoading && activeTab === 'boards' ? (
        <>
          {renderCatalogMaintenance(
            'boards',
            boards.length,
            visibleBoards.map((row) => row.id),
            <Button disabled={isSaving} type="button" onClick={() => setCreateHardwareResource('boards')}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Board
            </Button>,
          )}

          <LibraryBoardsTable
            boards={visibleBoards}
            editingBoard={editingBoard}
            isSaving={isSaving}
            onDelete={deleteBoard}
            onEdit={setEditingBoard}
            onEditChange={setEditingBoard}
            onSelectionChange={(itemId, checked) => handleCatalogSelection('boards', itemId, checked)}
            onUpdate={updateBoard}
            selectedIds={selectedCatalogIds.boards}
          />
        </>
      ) : null}

      {!isLoading && activeTab === 'slides' ? (
        <>
          {renderCatalogMaintenance(
            'slides',
            slides.length,
            visibleSlides.map((row) => row.id),
            <Button disabled={isSaving} type="button" onClick={() => setCreateHardwareResource('slides')}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Drawer Hardware
            </Button>,
          )}

          <LibrarySlidesTable
            accessoryOptions={accessoryOptions}
            editingSlide={editingSlide}
            isSaving={isSaving}
            onDelete={deleteSlide}
            onEdit={setEditingSlide}
            onEditChange={setEditingSlide}
            onSelectionChange={(itemId, checked) => handleCatalogSelection('slides', itemId, checked)}
            onUpdate={updateSlide}
            selectedIds={selectedCatalogIds.slides}
            slides={visibleSlides}
          />
        </>
      ) : null}

      {!isLoading && activeTab === 'hinges' ? (
        <>
          {renderCatalogMaintenance(
            'hinges',
            hinges.length,
            visibleHinges.map((row) => row.id),
            <Button disabled={isSaving} type="button" onClick={() => setCreateHardwareResource('hinges')}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Hinge
            </Button>,
          )}

          <LibraryHingesTable
            accessoryOptions={accessoryOptions}
            editingHinge={editingHinge}
            hinges={visibleHinges}
            isSaving={isSaving}
            onDelete={deleteHinge}
            onEdit={setEditingHinge}
            onEditChange={setEditingHinge}
            onSelectionChange={(itemId, checked) => handleCatalogSelection('hinges', itemId, checked)}
            onUpdate={updateHinge}
            selectedIds={selectedCatalogIds.hinges}
          />
        </>
      ) : null}

      {!isLoading && activeTab === 'suppliers' ? (
        <>
          <section className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Supplier Discount</CardTitle>
              </CardHeader>
              <CardContent>
                {suppliers.length === 0 ? (
                  <Alert className="text-xs">
                    Add a supplier first, then save their default discount so supplier costs can be updated quickly.
                  </Alert>
                ) : (
                  <form className="grid gap-3 md:grid-cols-2" onSubmit={applySupplierDiscount}>
                    <Label className="grid gap-1.5">
                      Supplier
                      <Select value={discountSupplierId} onChange={(event) => setDiscountSupplierId(event.target.value)}>
                        <option value="">Select a supplier</option>
                        {suppliers.map((supplier) => {
                          const counts = supplierCostCountsBySupplierId.get(supplier.id)
                          return (
                            <option key={supplier.id} value={supplier.id}>
                              {supplier.name}{counts ? ` (${counts.active}/${counts.total})` : ''}
                            </option>
                          )
                        })}
                      </Select>
                    </Label>
                    <Label className="grid gap-1.5">
                      Discount (%)
                      <Input value={supplierDiscountPercent} onChange={(event) => setSupplierDiscountPercent(event.target.value)} />
                    </Label>
                    <Label className="flex items-center gap-2 text-sm font-normal md:col-span-2">
                      <Checkbox
                        checked={applyDiscountToCosts}
                        onChange={(event) => setApplyDiscountToCosts(event.target.checked)}
                      />
                      Apply to active supplier costs
                    </Label>
                    <div className="md:col-span-2">
                      <Button disabled={isSaving || !selectedDiscountSupplier} type="submit" variant="outline">
                        <Percent className="h-4 w-4" aria-hidden="true" />
                        Apply Discount
                      </Button>
                    </div>
                  </form>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Supplier Cost Source</CardTitle>
              </CardHeader>
              <CardContent>
                {suppliers.length === 0 ? (
                  <Alert className="text-xs">
                    Add suppliers before linking supplier costs. Supplier costs can later generate a price list for quote selling prices.
                  </Alert>
                ) : (
                  <form className="grid gap-3 md:grid-cols-2" onSubmit={saveItemSupplierCost}>
                    <Label className="grid gap-1.5">
                      Item type
                      <Select
                        value={itemSupplierDraft.item_type}
                        onChange={(event) =>
                          setItemSupplierDraft((current) => ({ ...current, item_type: event.target.value as PriceItemType }))
                        }
                      >
                        {priceItemTypes.map((itemType) => (
                          <option key={itemType} value={itemType}>
                            {itemType}
                          </option>
                        ))}
                      </Select>
                    </Label>
                    <Label className="grid gap-1.5">
                      Item
                      <Select
                        value={itemSupplierDraft.item_ref_id}
                        onChange={(event) => setItemSupplierDraft((current) => ({ ...current, item_ref_id: event.target.value }))}
                      >
                        <option value="">Select an item</option>
                        {supplierItemOptions.map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.label}
                          </option>
                        ))}
                      </Select>
                    </Label>
                    <Label className="grid gap-1.5">
                      Supplier
                      <Select
                        value={itemSupplierDraft.supplier_id}
                        onChange={(event) => updateItemSupplierSupplier(event.target.value)}
                      >
                        <option value="">Select a supplier</option>
                        {suppliers.map((supplier) => (
                          <option key={supplier.id} value={supplier.id}>
                            {supplier.name}
                          </option>
                        ))}
                      </Select>
                    </Label>
                    <Label className="grid gap-1.5">
                      Supplier SKU
                      <Input value={itemSupplierDraft.supplier_sku} onChange={(event) => setItemSupplierDraft((current) => ({ ...current, supplier_sku: event.target.value }))} />
                    </Label>
                    <Label className="grid gap-1.5 md:col-span-2">
                      Supplier description
                      <Input value={itemSupplierDraft.supplier_description} onChange={(event) => setItemSupplierDraft((current) => ({ ...current, supplier_description: event.target.value }))} />
                    </Label>
                    <Label className="grid gap-1.5">
                      Price component
                      <Select
                        value={itemSupplierDraft.price_component}
                        onChange={(event) => {
                          const priceComponent = event.target.value
                          setItemSupplierDraft((current) => ({
                            ...current,
                            price_component: priceComponent,
                            order_uom: defaultOrderUomForComponent(current.item_type, priceComponent),
                          }))
                        }}
                      >
                        {supplierPriceComponentOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </Select>
                      <span className="text-xs text-muted-foreground">
                        Controls how this supplier cost is applied when prices are generated.
                      </span>
                    </Label>
                    <Label className="grid gap-1.5">
                      Order unit
                      <Select
                        value={itemSupplierDraft.order_uom}
                        onChange={(event) => setItemSupplierDraft((current) => ({ ...current, order_uom: event.target.value }))}
                      >
                        {supplierOrderUomOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </Select>
                      <span className="text-xs text-muted-foreground">
                        Matches the supplier quantity that becomes the generated price row unit.
                      </span>
                    </Label>
                    <Label className="grid gap-1.5">
                      List price ({displayCurrencyCode})
                      <Input value={itemSupplierDraft.list_price_amount} onChange={(event) => updateItemSupplierListPrice(event.target.value)} />
                    </Label>
                    <Label className="grid gap-1.5">
                      Discount (%)
                      <Input value={itemSupplierDraft.discount_percent} onChange={(event) => updateItemSupplierDiscount(event.target.value)} />
                    </Label>
                    <Label className="grid gap-1.5">
                      Net cost ({displayCurrencyCode})
                      <Input value={itemSupplierDraft.unit_cost_amount} onChange={(event) => setItemSupplierDraft((current) => ({ ...current, unit_cost_amount: event.target.value }))} />
                    </Label>
                    <Label className="flex items-center gap-2 text-sm font-normal">
                      <Checkbox
                        checked={itemSupplierDraft.is_preferred}
                        onChange={(event) => setItemSupplierDraft((current) => ({ ...current, is_preferred: event.target.checked }))}
                      />
                      Preferred source
                    </Label>
                    <Label className="grid gap-1.5 md:col-span-2">
                      Notes
                      <Textarea value={itemSupplierDraft.notes} onChange={(event) => setItemSupplierDraft((current) => ({ ...current, notes: event.target.value }))} />
                    </Label>
                    <div className="md:col-span-2">
                      <Button disabled={isSaving || !itemSupplierDraft.item_ref_id || !itemSupplierDraft.supplier_id} type="submit">
                        <Save className="h-4 w-4" aria-hidden="true" />
                        Save Supplier Cost
                      </Button>
                    </div>
                  </form>
                )}
              </CardContent>
            </Card>
          </section>

          {renderCatalogMaintenance(
            'suppliers',
            suppliers.length,
            visibleSuppliers.map((row) => row.id),
            <Button disabled={isSaving} type="button" onClick={() => setCreateHardwareResource('suppliers')}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Supplier
            </Button>,
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Suppliers</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <TableContainer>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-10">Select</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Code</TableHead>
                      <TableHead>Contact</TableHead>
                      <TableHead>Discount</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleSuppliers.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6}>
                          <div className="grid gap-1 py-3">
                            <p className="font-medium">Add your main board or hardware supplier.</p>
                            <p className="text-sm leading-5 text-muted-foreground">
                              Supplier records keep contact details, default discounts, and cost sources together.
                            </p>
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : (
                      visibleSuppliers.map((row) => (
                        <TableRow key={row.id}>
                          <TableCell>
                            <Checkbox
                              checked={selectedCatalogIds.suppliers.includes(row.id)}
                              onChange={(event) => handleCatalogSelection('suppliers', row.id, event.target.checked)}
                            />
                          </TableCell>
                          <TableCell>{row.name}</TableCell>
                          <TableCell>{row.code || '-'}</TableCell>
                          <TableCell>{row.contact_name || row.email || row.phone || '-'}</TableCell>
                          <TableCell>{bpsToPercentString(row.default_discount_bps)}%</TableCell>
                          <TableCell className="flex gap-2">
                            <Button size="sm" variant="outline" onClick={() => setEditingSupplier({ ...row })}>
                              Edit
                            </Button>
                            <Button size="sm" variant="destructive" onClick={() => void deleteSupplier(row.id)}>
                              Delete
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>

              <Dialog
                open={Boolean(editingSupplier)}
                onOpenChange={(open) => {
                  if (!open) setEditingSupplier(null)
                }}
                title="Edit Supplier"
                description={editingSupplier?.name}
                size="wide"
              >
                {editingSupplier ? (
                  <form className="grid gap-3 md:grid-cols-3" onSubmit={updateSupplier}>
                    <Label className="grid gap-1.5">
                      Name
                      <Input value={editingSupplier.name} onChange={(event) => setEditingSupplier({ ...editingSupplier, name: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5">
                      Code
                      <Input value={editingSupplier.code} onChange={(event) => setEditingSupplier({ ...editingSupplier, code: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5">
                      Contact
                      <Input value={editingSupplier.contact_name} onChange={(event) => setEditingSupplier({ ...editingSupplier, contact_name: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5">
                      Email
                      <Input value={editingSupplier.email} onChange={(event) => setEditingSupplier({ ...editingSupplier, email: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5">
                      Phone
                      <Input value={editingSupplier.phone} onChange={(event) => setEditingSupplier({ ...editingSupplier, phone: event.target.value })} />
                    </Label>
                    <Label className="grid gap-1.5">
                      Default discount (%)
                      <Input
                        value={bpsToPercentString(editingSupplier.default_discount_bps)}
                        onChange={(event) => setEditingSupplier({ ...editingSupplier, default_discount_bps: percentStringToBps(event.target.value) ?? 0 })}
                      />
                    </Label>
                    <Label className="grid gap-1.5 md:col-span-3">
                      Notes
                      <Textarea value={editingSupplier.notes} onChange={(event) => setEditingSupplier({ ...editingSupplier, notes: event.target.value })} />
                    </Label>
                    <div className="md:col-span-3 flex flex-wrap gap-2">
                      <Button disabled={isSaving} type="submit">
                        <Save className="h-4 w-4" aria-hidden="true" />
                        Save Changes
                      </Button>
                      <Button type="button" variant="outline" onClick={() => setEditingSupplier(null)}>
                        Cancel
                      </Button>
                    </div>
                  </form>
                ) : null}
              </Dialog>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Supplier Sources</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <FilteredEmptyNotice filteredCount={visibleItemSuppliers.length} totalCount={itemSuppliers.length} />
              <TableContainer>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Item</TableHead>
                      <TableHead>Supplier</TableHead>
                      <TableHead>SKU</TableHead>
                      <TableHead>Component</TableHead>
                      <TableHead>Discount</TableHead>
                      <TableHead>Cost</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleItemSuppliers.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7}>
                          <div className="grid gap-1 py-3">
                            <p className="font-medium">Link supplier costs when you are ready to automate pricing.</p>
                            <p className="text-sm leading-5 text-muted-foreground">
                              Connect a board, hardware item, handle, or extra to a supplier price so CoreQuote can generate selling prices.
                            </p>
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : (
                      visibleItemSuppliers.map((row) => (
                        <TableRow key={row.id}>
                          <TableCell>
                            {itemLabelByRef.get(`${row.item_type}:${row.item_ref_id}`) ?? `${row.item_type} ${row.item_ref_id}`}
                            {row.is_preferred ? <Badge className="ml-2">preferred</Badge> : null}
                          </TableCell>
                          <TableCell>{row.supplier_name}</TableCell>
                          <TableCell>{row.supplier_sku || '-'}</TableCell>
                          <TableCell>{row.price_component}</TableCell>
                          <TableCell>{row.active_discount_bps === null ? '-' : `${bpsToPercentString(row.active_discount_bps)}%`}</TableCell>
                          <TableCell>
                            {row.active_unit_cost_cents === null
                              ? '-'
                              : formatCurrencyFromCents(row.active_unit_cost_cents, row.active_currency_code ?? displayCurrencyCode)}
                          </TableCell>
                          <TableCell>
                            <Button size="sm" variant="destructive" onClick={() => void deleteItemSupplier(row.id)}>
                              Delete
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </>
      ) : null}

      {!isLoading && activeTab === 'handles' ? (
        <>
          {renderCatalogMaintenance(
            'handles',
            handles.length,
            visibleHandles.map((row) => row.id),
            <Button disabled={isSaving} type="button" onClick={() => setCreateHardwareResource('handles')}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Handle
            </Button>,
          )}

          <LibraryHandlesTable
            editingHandle={editingHandle}
            handles={visibleHandles}
            isSaving={isSaving}
            onDelete={deleteHandle}
            onEdit={setEditingHandle}
            onEditChange={setEditingHandle}
            onSelectionChange={(itemId, checked) => handleCatalogSelection('handles', itemId, checked)}
            onUpdate={updateHandle}
            selectedIds={selectedCatalogIds.handles}
            suppliers={suppliers}
          />
        </>
      ) : null}

      {!isLoading && activeTab === 'extra-categories' ? (
        <>
          <div className="grid gap-3">
            <MaintenanceToolbar
              recentDays={catalogRecentDays}
              search={catalogSearch}
              onRecentDaysChange={setCatalogRecentDays}
              onSearchChange={setCatalogSearch}
            >
              <Button disabled={isSaving} type="button" onClick={() => setCreateHardwareResource('extra-categories')}>
                <Plus className="h-4 w-4" aria-hidden="true" />
                Add Extra Category
              </Button>
            </MaintenanceToolbar>
            <FilteredEmptyNotice filteredCount={visibleExtraCategories.length} totalCount={extraCategories.length} />
          </div>

          <LibraryExtraCategoriesTable
            categories={visibleExtraCategories}
            editingCategory={editingExtraCategory}
            isSaving={isSaving}
            onDelete={deleteExtraCategory}
            onEdit={setEditingExtraCategory}
            onEditChange={setEditingExtraCategory}
            onUpdate={updateExtraCategory}
          />
        </>
      ) : null}

      {!isLoading && activeTab === 'extras' ? (
        <>
          {renderCatalogMaintenance(
            'extras',
            extras.length,
            visibleExtras.map((row) => row.id),
            <Button disabled={isSaving} type="button" onClick={() => setCreateHardwareResource('extras')}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add Extra
            </Button>,
          )}

          <LibraryExtrasTable
            categories={extraCategories}
            editingExtra={editingExtra}
            extras={visibleExtras}
            isSaving={isSaving}
            onDelete={deleteExtra}
            onEdit={setEditingExtra}
            onEditChange={setEditingExtra}
            onSelectionChange={(itemId, checked) => handleCatalogSelection('extras', itemId, checked)}
            onUpdate={updateExtra}
            selectedIds={selectedCatalogIds.extras}
            suppliers={suppliers}
          />
        </>
      ) : null}
    </div>
  )
}
