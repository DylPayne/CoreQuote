import {
  AlertTriangle,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  CircleDollarSign,
  ClipboardList,
  Copy,
  Download,
  FileSpreadsheet,
  FileText,
  GitBranch,
  Hammer,
  LoaderCircle,
  Pencil,
  Plus,
  Trash2,
  XCircle,
  type LucideIcon,
} from 'lucide-react'
import { Fragment, useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'

import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { ControlGroup, ControlGroupItem } from '@/components/ui/control-group'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { apiRequest, apiRequestBlob } from '@/components/projects-quotes/api'
import type { LibraryTab } from '@/components/libraries/types'
import { customUnitTypeValue, defaultProjectDraft, defaultProductionMetadata, defaultQuoteDraft, defaultUnitDraft, fallbackUnitDefaults, quoteStatusLabels, quoteStatusOptions, unitPresets } from '@/components/projects-quotes/constants'
import { QuotePanelsEditor } from '@/components/projects-quotes/quote-panels-editor'
import { CutlistSection, LibrarySelect, ModalCard, QuoteDefaultDimensionGrid } from '@/components/projects-quotes/shared-ui'
import { countPanelFamilies, formatCents, formatExtraParams, formatPercentFromBps, isBaseDoorUnitType, isDrawerUnitType, isHingedUnitType, isTallUnitType, normalizeQuoteCustomPanelsState, numberFromExtra, previousQuoteRevisionLabel, quotePayloadFromDraft, quoteRevisionLabel, quoteStatusBadgeVariant, resolveDefaultDims, resolvedUnitType, toQuoteDraft, unitPayloadFromDraft } from '@/components/projects-quotes/helpers'
import { PricingSettingsEditor } from '@/components/pricing-settings-editor'
import { defaultPricingSettingsDraft, pricingSettingsPayloadFromDraft, pricingSettingsToDraft, type PricingSettingsDraft, type ProjectPricingSettingsRow, type QuotePricingSettingsRow } from '@/components/pricing-settings'
import type { BoardRow, CutlistValidationWarning, CuttingListViewTab, DrawerSplitMode, ExtraRow, HandleRow, HingeRow, HardwarePickList, MaterialSummary, MaterialSummaryGroup, MissingPrice, PricingWorkspaceTab, ProductionGrainDirection, ProductionMetadata, ProductionRotationGuidance, ProjectDraft, ProjectPricingSummary, ProjectRow, ProjectWorkspaceTab, QuoteCuttingList, QuoteCustomPanelComputedRow, QuoteCustomPanelsState, QuoteCustomPanelsResponse, QuoteDraft, QuoteExtrasResponse, QuoteOutputAction, QuoteOutputReview, QuoteOutputStatus, QuoteProductionHandoff, QuoteReadiness, QuoteReadinessCheck, QuoteReadinessSeverity, QuoteRow, QuoteStatus, QuoteWorkspaceTab, SlideRow, UnitDraft, UnitPresetKey, UnitRow } from '@/components/projects-quotes/types'

type ProductionExportFormat = 'csv' | 'xlsx'

function formatBucketLabel(bucket: string) {
  return bucket
    .split(/[_-]/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ')
}

function formatPricingQty(qty: number) {
  return Number.isInteger(qty) ? String(qty) : qty.toFixed(2)
}

function formatMaterialArea(value: number) {
  return `${formatPricingQty(value)} m2`
}

function formatEstimatedSheets(value: number | null) {
  if (value === null) return 'Needs dimensions'
  return `${formatPricingQty(value)} est. ${value === 1 ? 'sheet' : 'sheets'}`
}

function formatSheetSize(group: MaterialSummaryGroup) {
  if (!group.length_mm || !group.width_mm) return 'No sheet size'
  return `${group.length_mm} x ${group.width_mm} mm`
}

function formatCutlistWarningSource(warning: CutlistValidationWarning) {
  return warning.source === 'quote_panel' ? 'Quote panel' : `Unit ${warning.unit_number}`
}

function readinessBadgeVariant(severity: QuoteReadinessSeverity): 'outline' | 'success' | 'warning' {
  if (severity === 'pass') return 'success'
  if (severity === 'warning') return 'warning'
  return 'outline'
}

function readinessLabel(severity: QuoteReadinessSeverity) {
  if (severity === 'pass') return 'Pass'
  if (severity === 'warning') return 'Warning'
  return 'Error'
}

function formatReadinessCount(count: number, label: string) {
  return `${count} ${count === 1 ? label : `${label}s`}`
}

function ReadinessIcon({ severity }: { severity: QuoteReadinessSeverity }) {
  if (severity === 'pass') {
    return <CheckCircle2 className="h-4 w-4 text-[var(--status-success-foreground)]" aria-hidden="true" />
  }
  if (severity === 'warning') {
    return <AlertTriangle className="h-4 w-4 text-[var(--status-warning-foreground)]" aria-hidden="true" />
  }
  return <XCircle className="h-4 w-4 text-destructive" aria-hidden="true" />
}

function missingPriceRowKey(row: MissingPrice) {
  return `${row.affected_quote_id}:${row.item_type}:${row.item_key}:${row.price_component}`
}

function missingPriceGroups(rows: MissingPrice[]) {
  const groups = new Map<string, MissingPrice[]>()
  rows.forEach((row) => {
    groups.set(row.item_type_label, [...(groups.get(row.item_type_label) ?? []), row])
  })
  return Array.from(groups.entries()).map(([label, items]) => ({ label, items }))
}

function formatMissingPriceCount(count: number) {
  return `${count} missing ${count === 1 ? 'price' : 'prices'}`
}

function formatPickListCount(count: number) {
  return `${count} ${count === 1 ? 'line' : 'lines'}`
}

type QuoteWorkflowStep = {
  description: string
  icon: LucideIcon
  label: string
  step: string
  target: QuoteWorkspaceTab
}

type QuoteBuildTab = {
  description: string
  label: string
  target: QuoteWorkspaceTab
}

const quoteBuildTargets: QuoteWorkspaceTab[] = ['units', 'panels', 'cutting-lists', 'extras']

const quoteWorkflowSteps: QuoteWorkflowStep[] = [
  {
    description: 'Add units, panels, extras, and the work needed to build the job.',
    icon: ClipboardList,
    label: 'Build quote',
    step: '1',
    target: 'units',
  },
  {
    description: 'See what is complete and what still needs attention.',
    icon: CheckCircle2,
    label: 'Check quote',
    step: '2',
    target: 'readiness',
  },
  {
    description: 'Review the selling total, missing prices, and quote price setup.',
    icon: CircleDollarSign,
    label: 'Review price',
    step: '3',
    target: 'pricing',
  },
  {
    description: 'Prepare customer and workshop documents.',
    icon: FileText,
    label: 'Customer and workshop outputs',
    step: '4',
    target: 'outputs',
  },
  {
    description: 'Hand the job to production when it is ready to make.',
    icon: Hammer,
    label: 'Production handoff',
    step: '5',
    target: 'production',
  },
]

const quoteBuildTabs: QuoteBuildTab[] = [
  {
    description: 'Cabinet and built-in units for the quote.',
    label: 'Units',
    target: 'units',
  },
  {
    description: 'Visible panels, fillers, and quote-level board work.',
    label: 'Panels and fillers',
    target: 'panels',
  },
  {
    description: 'Cutting rows generated from the quote.',
    label: 'Cutting list',
    target: 'cutting-lists',
  },
  {
    description: 'Delivery, installation, accessories, and other add-ons.',
    label: 'Extras',
    target: 'extras',
  },
]

function isBuildQuoteTab(tab: QuoteWorkspaceTab) {
  return quoteBuildTargets.includes(tab)
}

function isQuoteWorkflowStepActive(target: QuoteWorkspaceTab, activeTab: QuoteWorkspaceTab) {
  if (target === 'units') return isBuildQuoteTab(activeTab)
  return activeTab === target
}

function quoteWorkspaceTitle(activeTab: QuoteWorkspaceTab) {
  if (isBuildQuoteTab(activeTab)) return 'Build quote'
  if (activeTab === 'readiness') return 'Check quote'
  if (activeTab === 'pricing') return 'Review price'
  if (activeTab === 'outputs') return 'Customer and workshop outputs'
  if (activeTab === 'production') return 'Production handoff'
  return 'Build quote'
}

function quoteWorkspaceDescription(activeTab: QuoteWorkspaceTab) {
  if (isBuildQuoteTab(activeTab)) return 'Add the units, panels, cutting list details, and extras that make up this quote.'
  if (activeTab === 'readiness') return 'Check whether this quote is complete enough to trust and see the next action to take.'
  if (activeTab === 'pricing') return 'Review this quote price setup, missing prices, and priced line breakdown.'
  if (activeTab === 'outputs') return 'Review client and workshop outputs before generating documents.'
  if (activeTab === 'production') return 'Review grouped workshop rows with stable part traceability.'
  return 'Choose the next quoting task.'
}

type BulkUnitGridRow = UnitDraft & {
  id: string | null
  rowKey: string
}

type BulkUnitTemplate = {
  unit_type_key: UnitPresetKey
  width: string
}

type DrawerSplitPreset = {
  mode: DrawerSplitMode
  label: string
}

type BulkApplyDraft = {
  apply_carcass_board_type_id: boolean
  carcass_board_type_id: string
  apply_door_board_type_id: boolean
  door_board_type_id: string
  apply_handle_id: boolean
  handle_id: string
  apply_slide_id: boolean
  slide_id: string
  apply_hinge_id: boolean
  hinge_id: string
  apply_height: boolean
  height: string
  apply_depth: boolean
  depth: string
}

const smithKitchenBulkTemplates: BulkUnitTemplate[] = [
  { unit_type_key: 'Base Door', width: '600' },
  { unit_type_key: 'Base Door', width: '600' },
  { unit_type_key: 'Base Draw', width: '900' },
  { unit_type_key: 'Wall Door', width: '600' },
  { unit_type_key: 'Wall Door', width: '600' },
  { unit_type_key: 'Tall Door', width: '600' },
]

const drawerPanelGapMm = 3
const drawerSplitPresets: DrawerSplitPreset[] = [
  { mode: 'equal', label: 'Equal' },
  { mode: 'ratio', label: 'Deep bottom' },
  { mode: 'manual', label: 'Custom' },
]

function positiveIntegerFromValue(value: string | number, fallback: number) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 1) return fallback
  return Math.floor(parsed)
}

function drawerSystemRequiredDepth(slide: SlideRow) {
  const minDepth = Number(slide.drawer_system_config?.min_depth_mm ?? 0)
  const normalizedMinDepth = Number.isFinite(minDepth) && minDepth > 0 ? Math.floor(minDepth) : 0
  const requiredDepth = Number(slide.required_depth_mm ?? 0)
  const normalizedRequiredDepth = Number.isFinite(requiredDepth) && requiredDepth > 0 ? Math.floor(requiredDepth) : 0
  return Math.max(slide.length || 0, normalizedMinDepth, normalizedRequiredDepth)
}

function drawerSystemFamilyLabel(slide: SlideRow) {
  const family = typeof slide.drawer_system_config?.product_family === 'string' ? slide.drawer_system_config.product_family.trim() : ''
  const productFamily = typeof slide.product_family === 'string' ? slide.product_family.trim() : ''
  return family || productFamily || (slide.drawer_system_kind === 'metal' ? 'Metal system' : '')
}

function drawerCountFromDraft(draft: Pick<UnitDraft, 'num_drawers'>) {
  return positiveIntegerFromValue(draft.num_drawers, 3)
}

function drawerAvailableFaceHeight(height: string | number, numDrawers: string | number) {
  const cabinetHeight = positiveIntegerFromValue(height, 780)
  const drawers = positiveIntegerFromValue(numDrawers, 3)
  return Math.max(0, cabinetHeight - drawerPanelGapMm * drawers)
}

function drawerRatiosForMode(mode: DrawerSplitMode, numDrawers: number) {
  if (mode === 'equal' || numDrawers <= 1) return Array.from({ length: numDrawers }, () => '1')
  return Array.from({ length: numDrawers }, (_, index) => (index === numDrawers - 1 ? '2' : '1'))
}

function drawerHeightsForRatios(height: string | number, numDrawers: string | number, ratios: Array<string | number>) {
  const drawers = positiveIntegerFromValue(numDrawers, 3)
  const available = drawerAvailableFaceHeight(height, drawers)
  const safeRatios = Array.from({ length: drawers }, (_, index) => {
    const parsed = Number(ratios[index])
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 1
  })
  const ratioTotal = safeRatios.reduce((total, value) => total + value, 0) || drawers
  const raw = safeRatios.map((ratio) => (ratio / ratioTotal) * available)
  const floors = raw.map((value) => Math.floor(value))
  const remainder = available - floors.reduce((total, value) => total + value, 0)
  const order = raw
    .map((value, index) => ({ index, fraction: value - floors[index] }))
    .sort((left, right) => right.fraction - left.fraction)
  for (let index = 0; index < remainder && order.length > 0; index += 1) {
    floors[order[index % order.length].index] += 1
  }
  return floors
}

function drawerEqualHeights(height: string | number, numDrawers: string | number) {
  const drawers = positiveIntegerFromValue(numDrawers, 3)
  return drawerHeightsForRatios(height, drawers, Array.from({ length: drawers }, () => 1)).map(String)
}

function fitDrawerList(values: string[], length: number, fallback: string[]) {
  const next = values.slice(0, length)
  while (next.length < length) next.push(fallback[next.length] ?? fallback[fallback.length - 1] ?? '')
  return next
}

function drawerSplitModeFromValue(value: unknown): DrawerSplitMode {
  return value === 'manual' || value === 'ratio' || value === 'equal' ? value : 'equal'
}

function drawerArrayFromExtra(extra: Record<string, unknown>, key: string) {
  const value = extra[key]
  return Array.isArray(value) ? value.map((item) => String(item)) : []
}

function idFromExtra(extra: Record<string, unknown>, key: string) {
  const value = extra[key]
  return typeof value === 'string' ? value : ''
}

function profileHandleDraftFromExtra(extra: Record<string, unknown>): Pick<
  UnitDraft,
  | 'top_j_channel_handle_id'
  | 'middle_c_channel_handle_id'
  | 'between_lower_c_channel_handle_id'
  | 'base_door_top_j_channel_handle_id'
  | 'tall_vertical_channel_handle_id'
  | 'full_length_handle_orientation'
> {
  return {
    top_j_channel_handle_id: idFromExtra(extra, 'top_j_channel_handle_id'),
    middle_c_channel_handle_id: idFromExtra(extra, 'middle_c_channel_handle_id'),
    between_lower_c_channel_handle_id: idFromExtra(extra, 'between_lower_c_channel_handle_id'),
    base_door_top_j_channel_handle_id: idFromExtra(extra, 'base_door_top_j_channel_handle_id'),
    tall_vertical_channel_handle_id: idFromExtra(extra, 'tall_vertical_channel_handle_id'),
    full_length_handle_orientation: extra.full_length_handle_orientation === 'width' ? 'width' : 'length',
  }
}

function drawerSplitDraftFromExtra(extra: Record<string, unknown>, height: string, numDrawers: string) {
  const drawers = positiveIntegerFromValue(numDrawers, 3)
  const storedMode = drawerSplitModeFromValue(extra.drawer_split_mode)
  const mode: DrawerSplitMode = Array.isArray(extra.drawer_face_heights)
    ? 'manual'
    : Array.isArray(extra.drawer_face_ratios)
      ? storedMode === 'manual'
        ? 'ratio'
        : storedMode
      : storedMode
  const equalHeights = drawerEqualHeights(height, drawers)
  const ratios = mode === 'equal'
    ? drawerRatiosForMode('equal', drawers)
    : fitDrawerList(drawerArrayFromExtra(extra, 'drawer_face_ratios'), drawers, drawerRatiosForMode('ratio', drawers))
  return {
    drawer_split_mode: mode,
    drawer_face_heights: fitDrawerList(drawerArrayFromExtra(extra, 'drawer_face_heights'), drawers, equalHeights),
    drawer_face_ratios: ratios,
  }
}

function syncDrawerSplitDraft<T extends UnitDraft>(draft: T, reason: 'mode' | 'count' | 'height' | 'type' | 'none' = 'none'): T {
  const mode = drawerSplitModeFromValue(draft.drawer_split_mode)
  const drawers = drawerCountFromDraft(draft)
  const equalHeights = drawerEqualHeights(draft.height, drawers)
  const shouldReset = reason === 'mode' || reason === 'count' || reason === 'type'
  return {
    ...draft,
    drawer_split_mode: mode,
    drawer_face_heights: shouldReset || draft.drawer_face_heights.length !== drawers
      ? equalHeights
      : fitDrawerList(draft.drawer_face_heights, drawers, equalHeights),
    drawer_face_ratios: shouldReset || draft.drawer_face_ratios.length !== drawers
      ? drawerRatiosForMode(mode, drawers)
      : fitDrawerList(draft.drawer_face_ratios, drawers, drawerRatiosForMode(mode, drawers)),
  }
}

function drawerManualHeights(draft: UnitDraft) {
  return fitDrawerList(draft.drawer_face_heights, drawerCountFromDraft(draft), drawerEqualHeights(draft.height, draft.num_drawers))
}

function drawerComputedFaceHeights(draft: UnitDraft) {
  if (draft.drawer_split_mode === 'manual') {
    return drawerManualHeights(draft).map((value) => positiveIntegerFromValue(value, 1))
  }
  const ratios = draft.drawer_split_mode === 'equal'
    ? drawerRatiosForMode('equal', drawerCountFromDraft(draft))
    : fitDrawerList(draft.drawer_face_ratios, drawerCountFromDraft(draft), drawerRatiosForMode('ratio', drawerCountFromDraft(draft)))
  return drawerHeightsForRatios(draft.height, draft.num_drawers, ratios)
}

function drawerSplitValidationMessage(draft: UnitDraft) {
  const drawers = drawerCountFromDraft(draft)
  if (draft.drawer_split_mode === 'manual') {
    const heights = drawerManualHeights(draft).map((value) => Number(value))
    if (heights.some((value) => !Number.isInteger(value) || value <= 0)) {
      return 'Drawer face heights must be positive whole millimetres.'
    }
    const available = drawerAvailableFaceHeight(draft.height, drawers)
    const total = heights.reduce((sum, value) => sum + value, 0)
    if (total !== available) {
      return `Drawer face heights must total ${available} mm.`
    }
  }
  if (draft.drawer_split_mode === 'ratio') {
    const ratios = fitDrawerList(draft.drawer_face_ratios, drawers, drawerRatiosForMode('ratio', drawers)).map((value) => Number(value))
    if (ratios.some((value) => !Number.isFinite(value) || value <= 0)) {
      return 'Drawer ratios must be positive numbers.'
    }
  }
  return null
}

let bulkUnitRowCounter = 0

function nextBulkUnitRowKey() {
  bulkUnitRowCounter += 1
  return `bulk-unit-${bulkUnitRowCounter}`
}

function defaultBulkApplyDraft(): BulkApplyDraft {
  return {
    apply_carcass_board_type_id: false,
    carcass_board_type_id: '',
    apply_door_board_type_id: false,
    door_board_type_id: '',
    apply_handle_id: false,
    handle_id: '',
    apply_slide_id: false,
    slide_id: '',
    apply_hinge_id: false,
    hinge_id: '',
    apply_height: false,
    height: '',
    apply_depth: false,
    depth: '',
  }
}

function formatSupplierCode(supplier: string, code: string) {
  if (supplier && code) return `${supplier} / ${code}`
  return supplier || code || '-'
}

function downloadBlob(blob: Blob, filename: string | null, fallbackFilename: string) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename ?? fallbackFilename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

function HardwarePickListReview({ pickList }: { pickList?: HardwarePickList }) {
  if (!pickList) return null
  const optionalItems = pickList.optional_items ?? []
  if (pickList.items.length === 0 && optionalItems.length === 0 && pickList.warnings.length === 0) return null

  return (
    <div className="grid gap-3 border-y border-border py-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Hardware pick list</p>
          <Badge variant="outline">{formatPickListCount(pickList.total_item_count)}</Badge>
          <Badge variant={pickList.warnings.length > 0 ? 'warning' : 'outline'}>
            {`${pickList.total_quantity} ${pickList.total_quantity === 1 ? 'item' : 'items'}`}
          </Badge>
        </div>
        {pickList.warnings.length > 0 ? <Badge variant="warning">{`${pickList.warnings.length} warnings`}</Badge> : null}
      </div>

      {pickList.warnings.length > 0 ? (
        <div className="grid gap-2">
          {pickList.warnings.map((warning) => (
            <Alert className="flex items-start gap-2 text-xs" key={`${warning.code}:${warning.item_type}:${warning.unit_number}:${warning.item_ref_id ?? ''}`} variant="warning">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{warning.message}</span>
            </Alert>
          ))}
        </div>
      ) : null}

      {pickList.items.length > 0 ? (
        <TableContainer>
          <Table className="min-w-[780px] text-xs">
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Item</TableHead>
                <TableHead>Supplier / Code</TableHead>
                <TableHead>Used in</TableHead>
                <TableHead className="text-right">Qty</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pickList.items.map((item) => (
                <TableRow key={item.item_key}>
                  <TableCell>{item.type_label}</TableCell>
                  <TableCell>{item.item_name}</TableCell>
                  <TableCell>{formatSupplierCode(item.supplier, item.code)}</TableCell>
                  <TableCell>{item.usage_label || '-'}</TableCell>
                  <TableCell className="text-right">{`${formatPricingQty(item.quantity)} ${item.uom}`}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null}

      {optionalItems.length > 0 ? (
        <TableContainer>
          <Table className="min-w-[780px] text-xs">
            <TableHeader>
              <TableRow>
                <TableHead>Optional</TableHead>
                <TableHead>Item</TableHead>
                <TableHead>Supplier / Code</TableHead>
                <TableHead>Used in</TableHead>
                <TableHead className="text-right">Qty</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {optionalItems.map((item) => (
                <TableRow key={`optional:${item.item_key}`}>
                  <TableCell>{item.type_label}</TableCell>
                  <TableCell>{item.item_name}</TableCell>
                  <TableCell>{formatSupplierCode(item.supplier, item.code)}</TableCell>
                  <TableCell>{item.usage_label || '-'}</TableCell>
                  <TableCell className="text-right">{`${formatPricingQty(item.quantity)} ${item.uom}`}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null}
    </div>
  )
}

function MaterialSummaryReview({ currencyCode, summary }: { currencyCode: string; summary?: MaterialSummary }) {
  if (!summary) return null
  if (summary.groups.length === 0 && summary.warnings.length === 0) return null

  return (
    <div className="grid gap-3 border-y border-border py-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Material summary</p>
          <Badge variant="outline">{formatMaterialArea(summary.total_area_m2)}</Badge>
          <Badge variant={summary.total_estimated_sheets === null ? 'warning' : 'outline'}>
            {formatEstimatedSheets(summary.total_estimated_sheets)}
          </Badge>
        </div>
        <Badge variant="outline">{`${summary.total_piece_count} ${summary.total_piece_count === 1 ? 'piece' : 'pieces'}`}</Badge>
      </div>

      {summary.warnings.length > 0 ? (
        <div className="grid gap-2">
          {summary.warnings.map((warning) => (
            <Alert className="flex items-start gap-2 text-xs" key={`${warning.code}:${warning.material_role}:${warning.unit_number}:${warning.row_desc}`} variant="warning">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{warning.message}</span>
            </Alert>
          ))}
        </div>
      ) : null}

      {summary.groups.length > 0 ? (
        <TableContainer>
          <Table className="min-w-[900px] text-xs">
            <TableHeader>
              <TableRow>
                <TableHead>Role</TableHead>
                <TableHead>Board</TableHead>
                <TableHead>Sheet</TableHead>
                <TableHead className="text-right">Pieces</TableHead>
                <TableHead className="text-right">Area</TableHead>
                <TableHead className="text-right">Est. sheets</TableHead>
                <TableHead className="text-right">Cost</TableHead>
                <TableHead className="text-right">Sell</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {summary.groups.map((group) => (
                <TableRow key={`${group.board_type_id}:${group.material_role}`}>
                  <TableCell>{group.role_label}</TableCell>
                  <TableCell>
                    <div className="grid gap-1">
                      <span>{group.board_name}</span>
                      <span className="text-muted-foreground">{group.costing_mode === 'sqm' ? 'Priced by area' : 'Priced by sheet'}</span>
                    </div>
                  </TableCell>
                  <TableCell>{formatSheetSize(group)}</TableCell>
                  <TableCell className="text-right">{group.piece_count}</TableCell>
                  <TableCell className="text-right">{formatMaterialArea(group.area_m2)}</TableCell>
                  <TableCell className="text-right">{formatEstimatedSheets(group.estimated_sheets)}</TableCell>
                  <TableCell className="text-right">{formatCents(group.cost_total_cents, currencyCode)}</TableCell>
                  <TableCell className="text-right">
                    <span>{formatCents(group.sell_total_cents, currencyCode)}</span>
                    {group.missing_price ? <Badge className="ml-2" variant="warning">Missing</Badge> : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null}
    </div>
  )
}

function MissingPriceGuidance({
  includeQuote,
  missingPrices,
  onOpenLibraries,
}: {
  includeQuote: boolean
  missingPrices: MissingPrice[]
  onOpenLibraries: (target?: LibraryTab) => void
}) {
  if (missingPrices.length === 0) return null

  return (
    <div className="grid gap-3 border-y border-border py-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Missing prices</p>
          <Badge variant="warning">{formatMissingPriceCount(missingPrices.length)}</Badge>
        </div>
        <Button onClick={() => onOpenLibraries('pricing')} size="sm" type="button" variant="outline">
          <CircleDollarSign className="h-4 w-4" aria-hidden="true" />
          Open Pricing
        </Button>
      </div>
      <Alert variant="warning">
        These catalog items are already on the quote. Add their missing rows to the active price list, or add supplier costs first and generate prices from Libraries.
      </Alert>

      {missingPriceGroups(missingPrices).map((group) => (
        <div className="grid gap-2" key={group.label}>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge variant="outline">{group.label}</Badge>
            <span className="text-muted-foreground">{formatMissingPriceCount(group.items.length)}</span>
          </div>
          <TableContainer>
            <Table className="min-w-[780px] text-xs">
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead>Component</TableHead>
                  <TableHead>Used in</TableHead>
                  {includeQuote ? <TableHead>Quote</TableHead> : null}
                  <TableHead>Fix in</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {group.items.map((row) => (
                  <TableRow key={missingPriceRowKey(row)}>
                    <TableCell>
                      <div className="grid gap-1">
                        <span>{row.action_label}</span>
                        <span className="text-muted-foreground">{row.guidance_message || row.message}</span>
                        {row.catalog_target_label ? (
                          <span className="text-muted-foreground">{`Catalog item: ${row.catalog_target_label}`}</span>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>{row.component}</TableCell>
                    <TableCell>{row.usage_label}</TableCell>
                    {includeQuote ? <TableCell>{row.affected_quote_name}</TableCell> : null}
                    <TableCell>
                      <Button onClick={() => onOpenLibraries(row.library_target)} size="sm" type="button" variant="outline">
                        <CircleDollarSign className="h-4 w-4" aria-hidden="true" />
                        {row.guidance_action_label}
                      </Button>
                    </TableCell>
                    <TableCell className="text-right">{`${formatPricingQty(row.quantity)} ${row.uom}`}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </div>
      ))}
    </div>
  )
}

function ActivePriceListGuidance({
  activePriceListId,
  onOpenLibraries,
}: {
  activePriceListId: string | null
  onOpenLibraries: (target?: LibraryTab) => void
}) {
  if (activePriceListId) return null

  return (
    <Alert className="flex flex-wrap items-center justify-between gap-3" variant="warning">
      <span>There is no active price list for this pricing view. Open Libraries &gt; Pricing and activate a price list before reviewing totals.</span>
      <Button onClick={() => onOpenLibraries('pricing')} size="sm" type="button" variant="outline">
        <CircleDollarSign className="h-4 w-4" aria-hidden="true" />
        Open Pricing
      </Button>
    </Alert>
  )
}

function OutputStatusSummary({ status }: { status: QuoteOutputStatus }) {
  return (
    <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
      <div className="flex items-start gap-2">
        <ReadinessIcon severity={status.severity} />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold">{status.label}</p>
            <Badge variant={readinessBadgeVariant(status.severity)}>
              {status.status === 'ready' ? 'Ready' : 'Needs attention'}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{status.message}</p>
        </div>
      </div>
    </div>
  )
}

function OutputActionIcon({ action }: { action: QuoteOutputAction }) {
  if (action.id === 'client_quote_pdf') return <FileText className="h-4 w-4" aria-hidden="true" />
  if (action.id === 'workshop_schedule') return <Hammer className="h-4 w-4" aria-hidden="true" />
  if (action.id === 'production_handoff_csv' || action.id === 'production_handoff_xlsx') {
    return <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />
  }
  return <ClipboardList className="h-4 w-4" aria-hidden="true" />
}

function outputActionDownloadLabel(action: QuoteOutputAction) {
  if (action.id === 'client_quote_pdf' || action.id === 'workshop_schedule') return 'PDF'
  if (action.id === 'production_handoff_csv') return 'CSV'
  if (action.id === 'production_handoff_xlsx') return 'XLSX'
  return null
}

function OutputActionCard({
  action,
  generatingActionId,
  onGenerateAction,
  onReviewAction,
}: {
  action: QuoteOutputAction
  generatingActionId: QuoteOutputAction['id'] | null
  onGenerateAction: (action: QuoteOutputAction) => void
  onReviewAction: (action: QuoteOutputAction) => void
}) {
  const downloadLabel = outputActionDownloadLabel(action)
  const isGenerating = generatingActionId === action.id
  const actionBadgeLabel = action.enabled
    ? action.warning
      ? 'Generates with warnings'
      : 'Ready to generate'
    : 'Needs attention'

  return (
    <div className="rounded-[var(--card-radius)] border border-border bg-card p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <OutputActionIcon action={action} />
            <p className="text-sm font-semibold">{action.label}</p>
            <Badge variant={action.enabled && !action.warning ? 'success' : 'warning'}>
              {actionBadgeLabel}
            </Badge>
            {action.hides_internal_costs ? <Badge variant="outline">Hides internal costs</Badge> : null}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{action.description}</p>
          {action.warning ? (
            <p className="mt-2 text-xs text-[var(--status-warning-foreground)]">{action.warning}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-wrap justify-end gap-2">
          <Button
            disabled={!action.enabled || isGenerating}
            onClick={() => (downloadLabel ? onGenerateAction(action) : onReviewAction(action))}
            size="sm"
            type="button"
          >
            {isGenerating ? (
              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : downloadLabel ? (
              <Download className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            )}
            {downloadLabel ? (isGenerating ? `Generating ${downloadLabel}` : `Download ${downloadLabel}`) : 'Review output'}
          </Button>
          {action.warning ? (
            <Button onClick={() => onReviewAction(action)} size="sm" type="button" variant="outline">
              Review source
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function OutputReviewPanel({
  currencyCode,
  generatingActionId,
  onGenerateAction,
  onReviewAction,
  review,
}: {
  currencyCode: string
  generatingActionId: QuoteOutputAction['id'] | null
  onGenerateAction: (action: QuoteOutputAction) => void
  onReviewAction: (action: QuoteOutputAction) => void
  review: QuoteOutputReview
}) {
  const clientActions = review.actions.filter((action) => action.group === 'client')
  const workshopActions = review.actions.filter((action) => action.group === 'workshop')
  const readinessWarnings = review.readiness.checks.filter((check) => check.severity !== 'pass')

  return (
    <div className="grid gap-5">
      <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <ReadinessIcon severity={review.readiness.is_ready ? 'pass' : review.readiness.error_count > 0 ? 'error' : 'warning'} />
              <p className="text-sm font-semibold">{review.readiness.summary_title}</p>
              <Badge variant={review.readiness.is_ready ? 'success' : 'warning'}>
                {review.readiness.is_ready ? 'Ready' : 'Needs attention'}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{review.readiness.summary_message}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{formatReadinessCount(review.readiness.warning_count, 'warning')}</Badge>
            <Badge variant="outline">{formatReadinessCount(review.readiness.error_count, 'error')}</Badge>
          </div>
        </div>
      </div>

      {readinessWarnings.length > 0 ? (
        <Alert className="text-xs" variant="warning">
          <div className="grid gap-1">
            {readinessWarnings.map((check) => (
              <p key={check.id}>{`${check.title}: ${check.message}`}</p>
            ))}
          </div>
        </Alert>
      ) : null}

      <section className="grid gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm font-semibold">Client quote</p>
            <p className="text-xs text-muted-foreground">Customer-facing output keeps cost, margin, and workshop detail internal.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={quoteStatusBadgeVariant(review.quote_status)}>{quoteStatusLabels[review.quote_status]}</Badge>
            <Badge variant="outline">{`${review.quote_number} rev ${review.revision}`}</Badge>
            <Badge variant="outline">{review.currency_code}</Badge>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">Client total</p>
            <p className="text-base font-semibold">{formatCents(review.client_quote_total_cents, currencyCode)}</p>
          </div>
          <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">Missing prices</p>
            <p className="text-base font-semibold">{review.pricing_missing_price_count}</p>
          </div>
          <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">Cutlist warnings</p>
            <p className="text-base font-semibold">{review.cutlist_warning_count}</p>
          </div>
          <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">Output actions</p>
            <p className="text-base font-semibold">{review.actions.length}</p>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <OutputStatusSummary status={review.client_quote} />
          <OutputStatusSummary status={review.internal_pricing} />
        </div>

        <div className="grid gap-2">
          {clientActions.map((action) => (
            <OutputActionCard
              action={action}
              generatingActionId={generatingActionId}
              key={action.id}
              onGenerateAction={onGenerateAction}
              onReviewAction={onReviewAction}
            />
          ))}
        </div>
      </section>

      <section className="grid gap-3 border-t border-border pt-4">
        <div>
          <p className="text-sm font-semibold">Workshop package</p>
          <p className="text-xs text-muted-foreground">Internal outputs for cutting, material ordering, and hardware picking.</p>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <OutputStatusSummary status={review.workshop_schedule} />
          <OutputStatusSummary status={review.material_status} />
          <OutputStatusSummary status={review.hardware_status} />
        </div>

        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">Workshop rows</p>
            <p className="text-base font-semibold">{review.cutlist_row_count}</p>
          </div>
          <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">Material pieces</p>
            <p className="text-base font-semibold">{review.material_summary.total_piece_count}</p>
          </div>
          <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">Material area</p>
            <p className="text-base font-semibold">{formatMaterialArea(review.material_summary.total_area_m2)}</p>
          </div>
          <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">Hardware quantity</p>
            <p className="text-base font-semibold">{review.hardware_pick_list.total_quantity}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          <Badge variant={review.material_warning_count > 0 ? 'warning' : 'outline'}>
            {review.material_warning_count > 0
              ? `${review.material_warning_count} material warnings`
              : formatEstimatedSheets(review.material_summary.total_estimated_sheets)}
          </Badge>
          <Badge variant={review.hardware_warning_count > 0 ? 'warning' : 'outline'}>
            {review.hardware_warning_count > 0
              ? `${review.hardware_warning_count} hardware warnings`
              : formatPickListCount(review.hardware_pick_list.total_item_count)}
          </Badge>
        </div>

        <div className="grid gap-2">
          {workshopActions.map((action) => (
            <OutputActionCard
              action={action}
              generatingActionId={generatingActionId}
              key={action.id}
              onGenerateAction={onGenerateAction}
              onReviewAction={onReviewAction}
            />
          ))}
        </div>
      </section>
    </div>
  )
}

function formatProductionSheet(length: number | null, width: number | null) {
  if (!length || !width) return 'No sheet size'
  return `${length} x ${width} mm`
}

function formatPartIdList(partIds: string[], maxVisible = 3) {
  if (partIds.length === 0) return '-'
  if (partIds.length <= maxVisible) return partIds.join(', ')
  return `${partIds.slice(0, maxVisible).join(', ')} +${partIds.length - maxVisible}`
}

function ProductionMetadataControls({
  label,
  value,
  onChange,
}: {
  label: string
  value: ProductionMetadata
  onChange: (next: ProductionMetadata) => void
}) {
  return (
    <div className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <Label className="grid gap-1.5">
        Edge banding
        <Input
          onChange={(event) => onChange({ ...value, edge_banding: event.target.value })}
          placeholder="1mm ABS on exposed edges"
          value={value.edge_banding}
        />
      </Label>
      <div className="grid gap-3 md:grid-cols-2">
        <Label className="grid gap-1.5">
          Grain
          <Select
            onChange={(event) => onChange({ ...value, grain_direction: event.target.value as ProductionGrainDirection })}
            value={value.grain_direction}
          >
            <option value="none">Unspecified</option>
            <option value="length">Length grain</option>
            <option value="width">Width grain</option>
          </Select>
        </Label>
        <Label className="grid gap-1.5">
          Rotation
          <Select
            onChange={(event) => onChange({ ...value, rotation: event.target.value as ProductionRotationGuidance })}
            value={value.rotation}
          >
            <option value="none">Unspecified</option>
            <option value="allow_rotation">Can rotate</option>
            <option value="no_rotation">No rotation</option>
          </Select>
        </Label>
      </div>
      <Label className="grid gap-1.5">
        Notes
        <Textarea
          onChange={(event) => onChange({ ...value, notes: event.target.value })}
          rows={2}
          value={value.notes}
        />
      </Label>
    </div>
  )
}

function ProductionCollapsibleSection({
  children,
  id,
  isOpen,
  onToggle,
  summary,
  title,
}: {
  children: ReactNode
  id: string
  isOpen: boolean
  onToggle: () => void
  summary?: ReactNode
  title: string
}) {
  const contentId = `${id}-content`

  return (
    <section className="grid gap-3 border-t border-border pt-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button
          aria-controls={contentId}
          aria-expanded={isOpen}
          className="-ml-2 h-8 justify-start px-2 text-xs font-semibold uppercase text-muted-foreground"
          onClick={onToggle}
          type="button"
          variant="ghost"
        >
          {isOpen ? <ChevronDown className="h-4 w-4" aria-hidden="true" /> : <ChevronRight className="h-4 w-4" aria-hidden="true" />}
          <span>{title}</span>
        </Button>
        {summary ? <div className="flex flex-wrap items-center gap-2">{summary}</div> : null}
      </div>
      {isOpen ? (
        <div className="grid gap-3" id={contentId}>
          {children}
        </div>
      ) : null}
    </section>
  )
}

function ProductionBoardRequirementsReview({
  isOpen,
  onToggle,
  requirements,
}: {
  isOpen: boolean
  onToggle: () => void
  requirements: QuoteProductionHandoff['board_requirements']
}) {
  if (requirements.groups.length === 0 && requirements.warnings.length === 0) return null

  return (
    <ProductionCollapsibleSection
      id="production-board-requirements"
      isOpen={isOpen}
      onToggle={onToggle}
      summary={
        <>
          <Badge variant="outline">{formatMaterialArea(requirements.total_area_m2)}</Badge>
          <Badge variant={requirements.total_estimated_sheets === null ? 'warning' : 'outline'}>
            {formatEstimatedSheets(requirements.total_estimated_sheets)}
          </Badge>
          <Badge variant="outline">{`${requirements.total_piece_count} ${requirements.total_piece_count === 1 ? 'piece' : 'pieces'}`}</Badge>
          <Badge variant={requirements.warning_count > 0 ? 'warning' : 'outline'}>
            {requirements.warning_count > 0 ? `${requirements.warning_count} warnings` : 'Estimate ready'}
          </Badge>
        </>
      }
      title="Board requirements"
    >

      <Alert className="flex items-start gap-2 text-xs" variant="warning">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>{requirements.estimate_label}</span>
      </Alert>

      {requirements.warnings.length > 0 ? (
        <div className="grid gap-2">
          {requirements.warnings.map((warning) => (
            <Alert className="flex items-start gap-2 text-xs" key={`${warning.code}:${warning.part_id}:${warning.unit_number}:${warning.row_desc}`} variant="warning">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{warning.message}</span>
            </Alert>
          ))}
        </div>
      ) : null}

      {requirements.groups.length > 0 ? (
        <TableContainer>
          <Table className="min-w-[1020px] text-xs">
            <TableHeader>
              <TableRow>
                <TableHead>Board</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Sources</TableHead>
                <TableHead>Sheet</TableHead>
                <TableHead className="text-right">Pieces</TableHead>
                <TableHead className="text-right">Area</TableHead>
                <TableHead className="text-right">Est. sheets</TableHead>
                <TableHead>Waste allowance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {requirements.groups.map((group) => (
                <TableRow key={group.requirement_key}>
                  <TableCell>
                    <div className="grid gap-1">
                      <span>{group.board_name}</span>
                      <span className="text-muted-foreground">{formatPartIdList(group.part_ids, 2)}</span>
                    </div>
                  </TableCell>
                  <TableCell>{group.role_label}</TableCell>
                  <TableCell>{group.source_labels.join(', ') || '-'}</TableCell>
                  <TableCell>{formatProductionSheet(group.sheet_length_mm, group.sheet_width_mm)}</TableCell>
                  <TableCell className="text-right">{group.piece_count}</TableCell>
                  <TableCell className="text-right">{formatMaterialArea(group.area_m2)}</TableCell>
                  <TableCell className="text-right">
                    <div className="grid gap-1 justify-items-end">
                      <span>{formatEstimatedSheets(group.estimated_sheets)}</span>
                      <span className="text-muted-foreground">{group.sheet_estimate_label}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap items-center gap-2">
                      <span>{group.waste_allowance_label}</span>
                      {group.warning_count > 0 ? <Badge variant="warning">{`${group.warning_count} review`}</Badge> : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null}
    </ProductionCollapsibleSection>
  )
}

function ProductionHandoffPanel({
  exportingFormat,
  handoff,
  onDownloadExport,
}: {
  exportingFormat: ProductionExportFormat | null
  handoff: QuoteProductionHandoff
  onDownloadExport: (format: ProductionExportFormat) => void
}) {
  const warningRows = handoff.rows.filter((row) => row.warning_count > 0)
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({})

  function toggleSection(sectionId: string) {
    setOpenSections((current) => ({ ...current, [sectionId]: !current[sectionId] }))
  }

  return (
    <div className="grid gap-5">
      <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Hammer className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <p className="text-sm font-semibold">{handoff.project_name}</p>
              <Badge variant={quoteStatusBadgeVariant(handoff.quote_status)}>{quoteStatusLabels[handoff.quote_status]}</Badge>
              <Badge variant="outline">{`${handoff.quote_number} rev ${handoff.revision}`}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{handoff.quote_name}</p>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Badge variant="outline">{`${handoff.group_count} ${handoff.group_count === 1 ? 'group' : 'groups'}`}</Badge>
            <Badge variant="outline">{`${handoff.row_count} ${handoff.row_count === 1 ? 'row' : 'rows'}`}</Badge>
            <Badge variant={handoff.warning_count > 0 ? 'warning' : 'outline'}>
              {handoff.warning_count > 0 ? `${handoff.warning_count} warnings` : `${handoff.label_count} labels`}
            </Badge>
            <Button
              disabled={handoff.row_count === 0 || exportingFormat !== null}
              onClick={() => onDownloadExport('csv')}
              size="sm"
              type="button"
              variant="outline"
            >
              {exportingFormat === 'csv' ? (
                <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Download className="h-4 w-4" aria-hidden="true" />
              )}
              CSV
            </Button>
            <Button
              disabled={handoff.row_count === 0 || exportingFormat !== null}
              onClick={() => onDownloadExport('xlsx')}
              size="sm"
              type="button"
              variant="outline"
            >
              {exportingFormat === 'xlsx' ? (
                <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />
              )}
              XLSX
            </Button>
          </div>
        </div>
      </div>

      {warningRows.length > 0 ? (
        <Alert className="text-xs" variant="warning">
          <div className="grid gap-1">
            {warningRows.map((row) => (
              <p key={row.part_id}>{`${row.part_id}: ${row.warning_messages.join(' ')}`}</p>
            ))}
          </div>
        </Alert>
      ) : null}

      <ProductionBoardRequirementsReview
        isOpen={Boolean(openSections.boardRequirements)}
        onToggle={() => toggleSection('boardRequirements')}
        requirements={handoff.board_requirements}
      />

      <ProductionCollapsibleSection
        id="production-grouped-schedule"
        isOpen={Boolean(openSections.groupedSchedule)}
        onToggle={() => toggleSection('groupedSchedule')}
        summary={
          <>
          <Badge variant="outline">{`${handoff.material_summary.total_piece_count} pieces`}</Badge>
          <Badge variant={handoff.material_summary.total_estimated_sheets === null ? 'warning' : 'outline'}>
            {formatEstimatedSheets(handoff.material_summary.total_estimated_sheets)}
          </Badge>
          </>
        }
        title="Grouped cutting schedule"
      >
        {handoff.groups.length > 0 ? (
          <div className="grid gap-3">
            {handoff.groups.map((group) => (
              <div className="grid gap-2" key={group.group_key}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{group.board_name}</Badge>
                    <Badge variant="outline">{group.role_label}</Badge>
                    <Badge variant="outline">{group.unit_label}</Badge>
                    <Badge variant="outline">{group.section_label}</Badge>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>{`${group.piece_count} ${group.piece_count === 1 ? 'piece' : 'pieces'}`}</span>
                    <span>{formatProductionSheet(group.sheet_length_mm, group.sheet_width_mm)}</span>
                  </div>
                </div>
                <TableContainer>
                  <Table className="min-w-[1180px] text-xs">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Part ID</TableHead>
                        <TableHead>Unit</TableHead>
                        <TableHead>Part</TableHead>
                        <TableHead>Material</TableHead>
                        <TableHead className="text-right">L</TableHead>
                        <TableHead className="text-right">W</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead>Edge</TableHead>
                        <TableHead>Grain</TableHead>
                        <TableHead>Rotation</TableHead>
                        <TableHead>State</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {group.rows.map((row) => (
                        <TableRow key={row.part_id}>
                          <TableCell className="font-mono text-[11px]">{row.part_id}</TableCell>
                          <TableCell>{row.unit_label}</TableCell>
                          <TableCell>
                            <div className="grid gap-1">
                              <span>{row.desc}</span>
                              <span className="text-muted-foreground">{row.section_label}</span>
                            </div>
                          </TableCell>
                          <TableCell>{row.board_name}</TableCell>
                          <TableCell className="text-right">{row.length}</TableCell>
                          <TableCell className="text-right">{row.width}</TableCell>
                          <TableCell className="text-right">{row.quantity}</TableCell>
                          <TableCell>
                            <div className="grid gap-1">
                              <span>{row.edge_banding || row.edge_sides_label}</span>
                              {row.edge_banding && row.edge_sides_label !== 'None' ? (
                                <span className="text-muted-foreground">{row.edge_sides_label}</span>
                              ) : null}
                            </div>
                          </TableCell>
                          <TableCell>{row.grain_label}</TableCell>
                          <TableCell>{row.rotation_label}</TableCell>
                          <TableCell>
                            <Badge variant={row.warning_count > 0 ? 'warning' : 'outline'}>
                              {row.warning_count > 0 ? 'Review' : 'Ready'}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </div>
            ))}
          </div>
        ) : (
          <Alert className="text-xs">Production rows appear after the quote has a cutting schedule.</Alert>
        )}
      </ProductionCollapsibleSection>

      {handoff.material_summary.groups.length > 0 ? (
        <ProductionCollapsibleSection
          id="production-material-summary"
          isOpen={Boolean(openSections.materialSummary)}
          onToggle={() => toggleSection('materialSummary')}
          summary={
            <>
            <Badge variant="outline">{formatMaterialArea(handoff.material_summary.total_area_m2)}</Badge>
            <Badge variant="outline">{`${handoff.material_summary.total_piece_count} pieces`}</Badge>
            </>
          }
          title="Material summary"
        >
          <TableContainer>
            <Table className="min-w-[900px] text-xs">
              <TableHeader>
                <TableRow>
                  <TableHead>Board</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Parts</TableHead>
                  <TableHead>Sheet</TableHead>
                  <TableHead className="text-right">Pieces</TableHead>
                  <TableHead className="text-right">Area</TableHead>
                  <TableHead className="text-right">Est. sheets</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {handoff.material_summary.groups.map((group) => (
                  <TableRow key={`${group.board_type_id}:${group.material_role}`}>
                    <TableCell>{group.board_name}</TableCell>
                    <TableCell>{group.role_label}</TableCell>
                    <TableCell className="font-mono text-[11px]">{formatPartIdList(group.part_ids)}</TableCell>
                    <TableCell>{formatProductionSheet(group.length_mm, group.width_mm)}</TableCell>
                    <TableCell className="text-right">{group.piece_count}</TableCell>
                    <TableCell className="text-right">{formatMaterialArea(group.area_m2)}</TableCell>
                    <TableCell className="text-right">{formatEstimatedSheets(group.estimated_sheets)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          {(handoff.hardware_pick_list.optional_items ?? []).length > 0 ? (
            <TableContainer>
              <Table className="min-w-[900px] text-xs">
                <TableHeader>
                  <TableRow>
                    <TableHead>Optional</TableHead>
                    <TableHead>Item</TableHead>
                    <TableHead>Supplier / Code</TableHead>
                    <TableHead>Used in</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(handoff.hardware_pick_list.optional_items ?? []).map((item) => (
                    <TableRow key={`optional:${item.item_key}`}>
                      <TableCell>{item.type_label}</TableCell>
                      <TableCell>{item.item_name}</TableCell>
                      <TableCell>{formatSupplierCode(item.supplier, item.code)}</TableCell>
                      <TableCell>{item.usage_label || '-'}</TableCell>
                      <TableCell className="text-right">{`${formatPricingQty(item.quantity)} ${item.uom}`}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : null}
        </ProductionCollapsibleSection>
      ) : null}

      {handoff.hardware_pick_list.items.length > 0 ? (
        <ProductionCollapsibleSection
          id="production-hardware-pick-list"
          isOpen={Boolean(openSections.hardwarePickList)}
          onToggle={() => toggleSection('hardwarePickList')}
          summary={
            <>
            <Badge variant="outline">{formatPickListCount(handoff.hardware_pick_list.total_item_count)}</Badge>
            <Badge variant="outline">{`${handoff.hardware_pick_list.total_quantity} ${handoff.hardware_pick_list.total_quantity === 1 ? 'item' : 'items'}`}</Badge>
            </>
          }
          title="Hardware pick list"
        >
          <TableContainer>
            <Table className="min-w-[900px] text-xs">
              <TableHeader>
                <TableRow>
                  <TableHead>Part ID</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Item</TableHead>
                  <TableHead>Supplier / Code</TableHead>
                  <TableHead>Used in</TableHead>
                  <TableHead>Related parts</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {handoff.hardware_pick_list.items.map((item) => (
                  <TableRow key={item.part_id}>
                    <TableCell className="font-mono text-[11px]">{item.part_id}</TableCell>
                    <TableCell>{item.type_label}</TableCell>
                    <TableCell>{item.item_name}</TableCell>
                    <TableCell>{formatSupplierCode(item.supplier, item.code)}</TableCell>
                    <TableCell>{item.usage_label || '-'}</TableCell>
                    <TableCell className="font-mono text-[11px]">{formatPartIdList(item.related_part_ids)}</TableCell>
                    <TableCell className="text-right">{`${formatPricingQty(item.quantity)} ${item.uom}`}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </ProductionCollapsibleSection>
      ) : null}

      {handoff.labels.length > 0 ? (
        <ProductionCollapsibleSection
          id="production-labels"
          isOpen={Boolean(openSections.labels)}
          onToggle={() => toggleSection('labels')}
          summary={
            <Badge variant="outline">{`${handoff.label_count} ${handoff.label_count === 1 ? 'label' : 'labels'}`}</Badge>
          }
          title="Labels"
        >
          <TableContainer>
            <Table className="min-w-[760px] text-xs">
              <TableHeader>
                <TableRow>
                  <TableHead>Part ID</TableHead>
                  <TableHead>Part</TableHead>
                  <TableHead>Material</TableHead>
                  <TableHead>Dimensions</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {handoff.labels.map((label) => (
                  <TableRow key={label.part_id}>
                    <TableCell className="font-mono text-[11px]">{label.part_id}</TableCell>
                    <TableCell>{label.desc}</TableCell>
                    <TableCell>{label.material_label}</TableCell>
                    <TableCell>{label.dimensions_label}</TableCell>
                    <TableCell className="text-right">{label.quantity}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </ProductionCollapsibleSection>
      ) : null}
    </div>
  )
}

export function ProjectsQuotesPage({
  authToken,
  currencyCode,
  onOpenLibraries,
}: {
  authToken: string
  currencyCode: string
  onOpenLibraries: (target?: LibraryTab) => void
}) {
  const [projects, setProjects] = useState<ProjectRow[]>([])
  const [quotes, setQuotes] = useState<QuoteRow[]>([])
  const [units, setUnits] = useState<UnitRow[]>([])

  const [boards, setBoards] = useState<BoardRow[]>([])
  const [slides, setSlides] = useState<SlideRow[]>([])
  const [hinges, setHinges] = useState<HingeRow[]>([])
  const [handles, setHandles] = useState<HandleRow[]>([])
  const [extras, setExtras] = useState<ExtraRow[]>([])

  const [quoteCuttingList, setQuoteCuttingList] = useState<QuoteCuttingList | null>(null)
  const [quoteReadiness, setQuoteReadiness] = useState<QuoteReadiness | null>(null)
  const [quoteOutputReview, setQuoteOutputReview] = useState<QuoteOutputReview | null>(null)
  const [quoteProductionHandoff, setQuoteProductionHandoff] = useState<QuoteProductionHandoff | null>(null)
  const [quoteExtrasSelection, setQuoteExtrasSelection] = useState<Record<string, number>>({})
  const [quoteCustomPanels, setQuoteCustomPanels] = useState<QuoteCustomPanelsState | null>(null)
  const [quoteCustomPanelRows, setQuoteCustomPanelRows] = useState<QuoteCustomPanelComputedRow[]>([])
  const [projectPricing, setProjectPricing] = useState<ProjectPricingSummary | null>(null)
  const [projectPricingSettings, setProjectPricingSettings] = useState<ProjectPricingSettingsRow | null>(null)
  const [quotePricingSettings, setQuotePricingSettings] = useState<QuotePricingSettingsRow | null>(null)

  const [currentView, setCurrentView] = useState<'projects' | 'project-workspace'>('projects')
  const [activeProjectTab, setActiveProjectTab] = useState<ProjectWorkspaceTab>('quotes')
  const [activePricingTab, setActivePricingTab] = useState<PricingWorkspaceTab>('overview')
  const [activeQuoteTab, setActiveQuoteTab] = useState<QuoteWorkspaceTab>('readiness')
  const [activeCuttingListViewTab, setActiveCuttingListViewTab] = useState<CuttingListViewTab>('carcass')
  const [search, setSearch] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [selectedQuoteId, setSelectedQuoteId] = useState<string | null>(null)
  const [selectedUnitIds, setSelectedUnitIds] = useState<string[]>([])

  const [projectDraft, setProjectDraft] = useState<ProjectDraft>(defaultProjectDraft)
  const [quoteDraft, setQuoteDraft] = useState<QuoteDraft>(defaultQuoteDraft)
  const [unitDraft, setUnitDraft] = useState<UnitDraft>(defaultUnitDraft)
  const [bulkUnitRows, setBulkUnitRows] = useState<BulkUnitGridRow[]>([])
  const [bulkUnitErrors, setBulkUnitErrors] = useState<Record<string, string>>({})
  const [bulkApplyDraft, setBulkApplyDraft] = useState<BulkApplyDraft>(defaultBulkApplyDraft)
  const [projectPricingSettingsDraft, setProjectPricingSettingsDraft] = useState<PricingSettingsDraft>(defaultPricingSettingsDraft)
  const [quotePricingSettingsDraft, setQuotePricingSettingsDraft] = useState<PricingSettingsDraft>(defaultPricingSettingsDraft)

  const [projectEditId, setProjectEditId] = useState<string | null>(null)
  const [quoteEditId, setQuoteEditId] = useState<string | null>(null)
  const [unitEditId, setUnitEditId] = useState<string | null>(null)

  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false)
  const [isQuoteModalOpen, setIsQuoteModalOpen] = useState(false)
  const [isUnitModalOpen, setIsUnitModalOpen] = useState(false)
  const [isBulkUnitModalOpen, setIsBulkUnitModalOpen] = useState(false)
  const [isBulkApplyModalOpen, setIsBulkApplyModalOpen] = useState(false)

  const [isLoadingProjects, setIsLoadingProjects] = useState(true)
  const [isLoadingQuotes, setIsLoadingQuotes] = useState(false)
  const [isLoadingUnits, setIsLoadingUnits] = useState(false)
  const [isLoadingCuttingList, setIsLoadingCuttingList] = useState(false)
  const [isLoadingQuoteReadiness, setIsLoadingQuoteReadiness] = useState(false)
  const [isLoadingQuoteOutputReview, setIsLoadingQuoteOutputReview] = useState(false)
  const [isLoadingQuoteProductionHandoff, setIsLoadingQuoteProductionHandoff] = useState(false)
  const [isLoadingQuoteExtras, setIsLoadingQuoteExtras] = useState(false)
  const [isLoadingQuoteCustomPanels, setIsLoadingQuoteCustomPanels] = useState(false)
  const [isLoadingProjectPricing, setIsLoadingProjectPricing] = useState(false)
  const [isLoadingProjectPricingSettings, setIsLoadingProjectPricingSettings] = useState(false)
  const [isLoadingQuotePricingSettings, setIsLoadingQuotePricingSettings] = useState(false)
  const [isLoadingLibraries, setIsLoadingLibraries] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isSavingQuoteStatus, setIsSavingQuoteStatus] = useState(false)
  const [isCreatingQuoteRevision, setIsCreatingQuoteRevision] = useState(false)
  const [duplicatingQuoteId, setDuplicatingQuoteId] = useState<string | null>(null)
  const [duplicatingUnitId, setDuplicatingUnitId] = useState<string | null>(null)
  const [isReorderingUnits, setIsReorderingUnits] = useState(false)
  const [isSavingBulkUnits, setIsSavingBulkUnits] = useState(false)
  const [isSavingBulkApply, setIsSavingBulkApply] = useState(false)
  const [isSavingQuoteExtras, setIsSavingQuoteExtras] = useState(false)
  const [isSavingQuoteCustomPanels, setIsSavingQuoteCustomPanels] = useState(false)
  const [isSavingProjectPricingSettings, setIsSavingProjectPricingSettings] = useState(false)
  const [isSavingQuotePricingSettings, setIsSavingQuotePricingSettings] = useState(false)
  const [generatingOutputActionId, setGeneratingOutputActionId] = useState<QuoteOutputAction['id'] | null>(null)
  const [isQuoteExtrasDirty, setIsQuoteExtrasDirty] = useState(false)
  const [isQuoteCustomPanelsDirty, setIsQuoteCustomPanelsDirty] = useState(false)

  const [error, setError] = useState<string | null>(null)
  const [modalError, setModalError] = useState<string | null>(null)

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  )
  const selectedQuote = useMemo(
    () => quotes.find((quote) => quote.id === selectedQuoteId) ?? null,
    [quotes, selectedQuoteId],
  )
  const selectedQuotePricing = useMemo(
    () => projectPricing?.quotes.find((quote) => quote.quote_id === selectedQuoteId) ?? null,
    [projectPricing, selectedQuoteId],
  )
  const selectedQuotePricingGroups = useMemo(() => {
    if (!selectedQuotePricing) return []
    const groups = new Map<string, typeof selectedQuotePricing.lines>()
    selectedQuotePricing.lines.forEach((line) => {
      const bucket = line.bucket || 'other'
      groups.set(bucket, [...(groups.get(bucket) ?? []), line])
    })
    return Array.from(groups.entries()).map(([bucket, lines]) => ({ bucket, lines }))
  }, [selectedQuotePricing])
  const pricingCurrencyCode = projectPricing?.currency_code ?? currencyCode

  const boardLabel = useCallback(
    (boardId: string | null) => {
      if (!boardId) return 'None'
      const board = boards.find((row) => row.id === boardId)
      if (!board) return 'Unknown'
      return `${board.brand} ${board.material} (${board.thickness}mm)`
    },
    [boards],
  )
  const slideLabel = useCallback(
    (slideId: string | null) => {
      if (!slideId) return 'None'
      const slide = slides.find((row) => row.id === slideId)
      if (!slide) return 'Unknown slide'
      const family = drawerSystemFamilyLabel(slide)
      const systemLabel = family ? ` · ${family}` : ''
      return `${slide.brand} ${slide.model}${slide.code ? ` (${slide.code})` : ''}${systemLabel} · ${slide.length}mm`
    },
    [slides],
  )
  const hingeLabel = useCallback(
    (hingeId: string | null) => {
      if (!hingeId) return 'None'
      const hinge = hinges.find((row) => row.id === hingeId)
      if (!hinge) return 'Unknown hinge'
      return `${hinge.brand} ${hinge.model} (${hinge.opening_angle_deg}deg)`
    },
    [hinges],
  )
  const handleLabel = useCallback(
    (handleId: string | null) => {
      if (!handleId) return 'None'
      const handle = handles.find((row) => row.id === handleId)
      if (!handle) return 'Unknown handle'
      const typeLabel = handle.handle_type === 'full_length'
        ? 'Full length'
        : handle.handle_type === 'c_channel'
          ? 'C channel'
          : handle.handle_type === 'j_channel'
            ? 'J channel'
            : ''
      const typeSuffix = typeLabel ? ` · ${typeLabel}` : ''
      const reductionSuffix = handle.handle_type !== 'standard' ? ` · ${handle.front_reduction_mm} mm reduction` : ''
      return `${handle.name}${handle.supplier_name ? ` · ${handle.supplier_name}` : ''}${typeSuffix}${reductionSuffix}`
    },
    [handles],
  )

  const unitDraftType = resolvedUnitType(unitDraft)
  const isDrawerUnitDraft = isDrawerUnitType(unitDraftType)
  const isHingedUnitDraft = isHingedUnitType(unitDraftType)
  const isBaseDoorUnitDraft = isBaseDoorUnitType(unitDraftType)
  const isTallUnitDraft = isTallUnitType(unitDraftType)
  const unitDraftDrawerCount = positiveIntegerFromValue(unitDraft.num_drawers, 3)
  const standardHandles = handles.filter((handle) => handle.handle_type === 'standard')
  const doorHandles = handles.filter((handle) => handle.handle_type === 'standard' || handle.handle_type === 'full_length')
  const jChannelHandles = handles.filter((handle) => handle.handle_type === 'j_channel')
  const cChannelHandles = handles.filter((handle) => handle.handle_type === 'c_channel')
  const tallChannelHandles = handles.filter((handle) => handle.handle_type === 'c_channel' || handle.handle_type === 'j_channel')
  const defaultDoorHandleId = isTallUnitDraft
    ? selectedQuote?.default_tall_handle_id
    : unitDraftType.toLowerCase().includes('wall')
      ? selectedQuote?.default_wall_handle_id
      : selectedQuote?.default_base_handle_id
  const effectiveDoorHandle = doorHandles.find((handle) => handle.id === defaultDoorHandleId)
  const showFullLengthOrientation = isHingedUnitDraft && effectiveDoorHandle?.handle_type === 'full_length'
  const drawerAvailableHeight = drawerAvailableFaceHeight(unitDraft.height, unitDraft.num_drawers)
  const drawerHeightValues = drawerManualHeights(unitDraft)
  const drawerHeightTotal = drawerHeightValues.reduce((total, value) => total + positiveIntegerFromValue(value, 0), 0)
  const drawerHeightRemaining = drawerAvailableHeight - drawerHeightTotal
  const drawerSplitError = isDrawerUnitDraft ? drawerSplitValidationMessage(unitDraft) : null
  const drawerPreviewHeights = useMemo(() => drawerComputedFaceHeights(unitDraft), [unitDraft])
  const effectiveUnitSlideId = unitDraft.slide_id || selectedQuote?.default_slide_id || ''
  const effectiveUnitSlide = effectiveUnitSlideId ? slides.find((slide) => slide.id === effectiveUnitSlideId) ?? null : null
  const unitDepthNumber = Number(unitDraft.depth)
  const requiredDrawerHardwareDepth = effectiveUnitSlide ? drawerSystemRequiredDepth(effectiveUnitSlide) : 0
  const slideDepthError = isDrawerUnitDraft && effectiveUnitSlide && Number.isFinite(unitDepthNumber) && unitDepthNumber < requiredDrawerHardwareDepth
    ? `Selected drawer hardware requires a carcass depth of at least ${requiredDrawerHardwareDepth} mm internally.`
    : null
  const cutlistRowCount = quoteCuttingList
    ? quoteCuttingList.carcass.length +
      quoteCuttingList.panels.length +
      quoteCuttingList.hardware.length +
      quoteCuttingList.extras.length
    : 0
  const cutlistWarnings = quoteCuttingList?.validation_warnings ?? []
  const projectCutlistWarningCount = projectPricing?.quotes.reduce(
    (total, quotePricing) => total + quotePricing.cutlist_warnings.length,
    0,
  ) ?? 0
  const panelFamilyCounts = useMemo(() => countPanelFamilies(units), [units])
  const visibleUnitIds = useMemo(() => new Set(units.map((unit) => unit.id)), [units])
  const visibleSelectedUnitIds = useMemo(
    () => selectedUnitIds.filter((unitId) => visibleUnitIds.has(unitId)),
    [selectedUnitIds, visibleUnitIds],
  )
  const selectedUnitCount = visibleSelectedUnitIds.length

  const loadLibraries = useCallback(async () => {
    setIsLoadingLibraries(true)
    try {
      const [boardRows, slideRows, hingeRows, handleRows, extraRows] = await Promise.all([
        apiRequest<BoardRow[]>('/api/v1/libraries/boards', { token: authToken }),
        apiRequest<SlideRow[]>('/api/v1/libraries/slides', { token: authToken }),
        apiRequest<HingeRow[]>('/api/v1/libraries/hinges', { token: authToken }),
        apiRequest<HandleRow[]>('/api/v1/libraries/handles', { token: authToken }),
        apiRequest<ExtraRow[]>('/api/v1/libraries/extras', { token: authToken }),
      ])
      setBoards(boardRows)
      setSlides(slideRows)
      setHinges(hingeRows)
      setHandles(handleRows)
      setExtras(extraRows)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load library defaults.')
    } finally {
      setIsLoadingLibraries(false)
    }
  }, [authToken])

  const loadProjects = useCallback(
    async (searchValue?: string) => {
      setIsLoadingProjects(true)
      setError(null)
      try {
        const query = (searchValue ?? search).trim()
        const path = query ? `/api/v1/projects?search=${encodeURIComponent(query)}` : '/api/v1/projects'
        const rows = await apiRequest<ProjectRow[]>(path, { token: authToken })
        setProjects(rows)
        setSelectedProjectId((current) => (current && rows.some((row) => row.id === current) ? current : rows[0]?.id ?? null))
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load projects.')
      } finally {
        setIsLoadingProjects(false)
      }
    },
    [authToken, search],
  )

  const loadQuotes = useCallback(
    async (projectId: string) => {
      setIsLoadingQuotes(true)
      setError(null)
      try {
        const rows = await apiRequest<QuoteRow[]>(`/api/v1/projects/${projectId}/quotes`, { token: authToken })
        setQuotes(rows)
        setSelectedQuoteId((current) => (current && rows.some((row) => row.id === current) ? current : rows[0]?.id ?? null))
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load quotes.')
      } finally {
        setIsLoadingQuotes(false)
      }
    },
    [authToken],
  )

  const loadUnits = useCallback(
    async (quoteId: string) => {
      setIsLoadingUnits(true)
      setError(null)
      try {
        const rows = await apiRequest<UnitRow[]>(`/api/v1/quotes/${quoteId}/units`, { token: authToken })
        setUnits(rows)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load units.')
      } finally {
        setIsLoadingUnits(false)
      }
    },
    [authToken],
  )

  const loadQuoteCuttingList = useCallback(
    async (quoteId: string) => {
      setIsLoadingCuttingList(true)
      setError(null)
      try {
        const payload = await apiRequest<QuoteCuttingList>(`/api/v1/quotes/${quoteId}/cutting-list`, { token: authToken })
        setQuoteCuttingList(payload)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not build cutting list.')
      } finally {
        setIsLoadingCuttingList(false)
      }
    },
    [authToken],
  )

  const loadQuoteReadiness = useCallback(
    async (quoteId: string) => {
      setIsLoadingQuoteReadiness(true)
      setError(null)
      try {
        const payload = await apiRequest<QuoteReadiness>(`/api/v1/quotes/${quoteId}/readiness`, { token: authToken })
        setQuoteReadiness(payload)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not check quote readiness.')
      } finally {
        setIsLoadingQuoteReadiness(false)
      }
    },
    [authToken],
  )

  const loadQuoteOutputReview = useCallback(
    async (quoteId: string) => {
      setIsLoadingQuoteOutputReview(true)
      setError(null)
      try {
        const payload = await apiRequest<QuoteOutputReview>(`/api/v1/quotes/${quoteId}/output-review`, { token: authToken })
        setQuoteOutputReview(payload)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not review quote outputs.')
      } finally {
        setIsLoadingQuoteOutputReview(false)
      }
    },
    [authToken],
  )

  const loadQuoteProductionHandoff = useCallback(
    async (quoteId: string) => {
      setIsLoadingQuoteProductionHandoff(true)
      setError(null)
      try {
        const payload = await apiRequest<QuoteProductionHandoff>(`/api/v1/quotes/${quoteId}/production-handoff`, { token: authToken })
        setQuoteProductionHandoff(payload)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not build the production handoff.')
      } finally {
        setIsLoadingQuoteProductionHandoff(false)
      }
    },
    [authToken],
  )

  const downloadCustomerQuotePdf = useCallback(
    async (quoteId: string) => {
      setGeneratingOutputActionId('client_quote_pdf')
      setError(null)
      try {
        const { blob, filename } = await apiRequestBlob(`/api/v1/quotes/${quoteId}/customer-quote.pdf`, { token: authToken })
        downloadBlob(blob, filename, 'customer-quote.pdf')
        await loadQuoteOutputReview(quoteId)
      } catch (downloadError) {
        setError(downloadError instanceof Error ? downloadError.message : 'Could not download the customer quote PDF.')
        void loadQuoteOutputReview(quoteId)
      } finally {
        setGeneratingOutputActionId(null)
      }
    },
    [authToken, loadQuoteOutputReview],
  )

  const downloadWorkshopSchedulePdf = useCallback(
    async (quoteId: string) => {
      setGeneratingOutputActionId('workshop_schedule')
      setError(null)
      try {
        const { blob, filename } = await apiRequestBlob(`/api/v1/quotes/${quoteId}/workshop-schedule.pdf`, { token: authToken })
        downloadBlob(blob, filename, 'workshop-schedule.pdf')
        await loadQuoteOutputReview(quoteId)
      } catch (downloadError) {
        setError(downloadError instanceof Error ? downloadError.message : 'Could not download the workshop schedule PDF.')
        void loadQuoteOutputReview(quoteId)
      } finally {
        setGeneratingOutputActionId(null)
      }
    },
    [authToken, loadQuoteOutputReview],
  )

  const downloadProductionHandoffExport = useCallback(
    async (quoteId: string, format: ProductionExportFormat) => {
      const actionId: QuoteOutputAction['id'] = format === 'csv' ? 'production_handoff_csv' : 'production_handoff_xlsx'
      setGeneratingOutputActionId(actionId)
      setError(null)
      try {
        const { blob, filename } = await apiRequestBlob(`/api/v1/quotes/${quoteId}/production-handoff.${format}`, { token: authToken })
        downloadBlob(blob, filename, `production-handoff.${format}`)
        await loadQuoteOutputReview(quoteId)
      } catch (downloadError) {
        setError(downloadError instanceof Error ? downloadError.message : 'Could not download the production handoff export.')
        void loadQuoteOutputReview(quoteId)
      } finally {
        setGeneratingOutputActionId(null)
      }
    },
    [authToken, loadQuoteOutputReview],
  )

  const loadQuoteExtras = useCallback(
    async (quoteId: string) => {
      setIsLoadingQuoteExtras(true)
      setError(null)
      try {
        const payload = await apiRequest<QuoteExtrasResponse>(`/api/v1/quotes/${quoteId}/extras`, { token: authToken })
        const nextSelection = payload.items.reduce<Record<string, number>>((accumulator, item) => {
          accumulator[item.extra_id] = item.quantity
          return accumulator
        }, {})
        setQuoteExtrasSelection(nextSelection)
        setIsQuoteExtrasDirty(false)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load selected extras.')
      } finally {
        setIsLoadingQuoteExtras(false)
      }
    },
    [authToken],
  )

  const loadQuoteCustomPanels = useCallback(
    async (quoteId: string) => {
      setIsLoadingQuoteCustomPanels(true)
      setError(null)
      try {
        const payload = await apiRequest<QuoteCustomPanelsResponse>(`/api/v1/quotes/${quoteId}/custom-panels`, { token: authToken })
        setQuoteCustomPanels(normalizeQuoteCustomPanelsState(payload.custom_panels, selectedQuote, units))
        setQuoteCustomPanelRows(payload.computed_rows)
        setIsQuoteCustomPanelsDirty(false)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load quote panels.')
      } finally {
        setIsLoadingQuoteCustomPanels(false)
      }
    },
    [authToken, selectedQuote, units],
  )

  const loadProjectPricing = useCallback(
    async (projectId: string) => {
      setIsLoadingProjectPricing(true)
      setError(null)
      try {
        const payload = await apiRequest<ProjectPricingSummary>(`/api/v1/projects/${projectId}/pricing`, { token: authToken })
        setProjectPricing(payload)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load project pricing.')
      } finally {
        setIsLoadingProjectPricing(false)
      }
    },
    [authToken],
  )

  const loadProjectPricingSettings = useCallback(
    async (projectId: string) => {
      setIsLoadingProjectPricingSettings(true)
      setError(null)
      try {
        const payload = await apiRequest<ProjectPricingSettingsRow>(`/api/v1/projects/${projectId}/pricing-settings`, { token: authToken })
        setProjectPricingSettings(payload)
        setProjectPricingSettingsDraft(pricingSettingsToDraft(payload))
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load project pricing defaults.')
      } finally {
        setIsLoadingProjectPricingSettings(false)
      }
    },
    [authToken],
  )

  const loadQuotePricingSettings = useCallback(
    async (quoteId: string) => {
      setIsLoadingQuotePricingSettings(true)
      setError(null)
      try {
        const payload = await apiRequest<QuotePricingSettingsRow>(`/api/v1/quotes/${quoteId}/pricing-settings`, { token: authToken })
        setQuotePricingSettings(payload)
        setQuotePricingSettingsDraft(pricingSettingsToDraft(payload))
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load quote pricing settings.')
      } finally {
        setIsLoadingQuotePricingSettings(false)
      }
    },
    [authToken],
  )

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadLibraries()
      void loadProjects('')
    }, 0)
    return () => window.clearTimeout(handle)
  }, [loadLibraries, loadProjects])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (!selectedProjectId) {
        setQuotes([])
        setSelectedQuoteId(null)
        setProjectPricing(null)
        setProjectPricingSettings(null)
        setProjectPricingSettingsDraft(defaultPricingSettingsDraft)
        return
      }
      void loadQuotes(selectedProjectId)
      void loadProjectPricingSettings(selectedProjectId)
    }, 0)
    return () => window.clearTimeout(handle)
  }, [loadProjectPricingSettings, loadQuotes, selectedProjectId])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (!selectedQuoteId) {
        setUnits([])
        setQuoteCuttingList(null)
        setQuoteReadiness(null)
        setQuoteOutputReview(null)
        setQuoteProductionHandoff(null)
        setQuoteExtrasSelection({})
        setQuoteCustomPanels(null)
        setQuoteCustomPanelRows([])
        setQuotePricingSettings(null)
        setQuotePricingSettingsDraft(defaultPricingSettingsDraft)
        setIsQuoteExtrasDirty(false)
        setIsQuoteCustomPanelsDirty(false)
        return
      }
      void loadUnits(selectedQuoteId)
      void loadQuoteReadiness(selectedQuoteId)
      void loadQuotePricingSettings(selectedQuoteId)
    }, 0)
    return () => window.clearTimeout(handle)
  }, [loadQuotePricingSettings, loadQuoteReadiness, loadUnits, selectedQuoteId])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (selectedQuoteId && activeProjectTab === 'quotes' && activeQuoteTab === 'outputs') {
        void loadQuoteOutputReview(selectedQuoteId)
      }
    }, 0)
    return () => window.clearTimeout(handle)
  }, [activeProjectTab, activeQuoteTab, loadQuoteOutputReview, selectedQuoteId])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (selectedQuoteId && activeProjectTab === 'quotes' && activeQuoteTab === 'production') {
        void loadQuoteProductionHandoff(selectedQuoteId)
      }
    }, 0)
    return () => window.clearTimeout(handle)
  }, [activeProjectTab, activeQuoteTab, loadQuoteProductionHandoff, selectedQuoteId])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (currentView === 'project-workspace' && !selectedProjectId) {
        setCurrentView('projects')
      }
    }, 0)
    return () => window.clearTimeout(handle)
  }, [currentView, selectedProjectId])

  function openCreateProjectModal() {
    setProjectEditId(null)
    setModalError(null)
    setProjectDraft(defaultProjectDraft)
    setIsProjectModalOpen(true)
  }

  function openProjectWorkspace(projectId: string) {
    setSelectedProjectId(projectId)
    setCurrentView('project-workspace')
    setActiveProjectTab('quotes')
    setActivePricingTab('overview')
    setActiveQuoteTab('readiness')
  }

  function openProjectPricingTab() {
    setActiveProjectTab('pricing')
    setActiveQuoteTab('pricing')
    if (selectedProjectId) {
      void loadProjectPricing(selectedProjectId)
      void loadProjectPricingSettings(selectedProjectId)
    }
    if (selectedQuoteId) {
      void loadQuotePricingSettings(selectedQuoteId)
    }
  }

  function openQuotePricingTab() {
    setActiveProjectTab('quotes')
    setActiveQuoteTab('pricing')
    if (selectedProjectId) {
      void loadProjectPricing(selectedProjectId)
    }
    if (selectedQuoteId) {
      void loadQuotePricingSettings(selectedQuoteId)
    }
  }

  function openQuoteOutputsTab() {
    setActiveProjectTab('quotes')
    setActiveQuoteTab('outputs')
    if (selectedQuoteId) {
      void loadQuoteOutputReview(selectedQuoteId)
    }
  }

  function openQuoteProductionTab() {
    setActiveProjectTab('quotes')
    setActiveQuoteTab('production')
    if (selectedQuoteId) {
      void loadQuoteProductionHandoff(selectedQuoteId)
    }
  }

  function openQuotePanelsTab() {
    setActiveProjectTab('quotes')
    setActiveQuoteTab('panels')
    if (selectedQuoteId) {
      void loadQuoteCustomPanels(selectedQuoteId)
    }
  }

  function openQuoteCuttingListTab() {
    setActiveProjectTab('quotes')
    setActiveQuoteTab('cutting-lists')
    setActiveCuttingListViewTab('carcass')
    if (selectedQuoteId) {
      void loadQuoteCuttingList(selectedQuoteId)
    }
  }

  function openQuoteWorkspaceTab(target: QuoteWorkspaceTab) {
    if (target === 'pricing') {
      openQuotePricingTab()
      return
    }
    if (target === 'outputs') {
      openQuoteOutputsTab()
      return
    }
    if (target === 'production') {
      openQuoteProductionTab()
      return
    }
    if (target === 'panels') {
      openQuotePanelsTab()
      return
    }
    if (target === 'cutting-lists') {
      openQuoteCuttingListTab()
      return
    }
    if (target === 'extras') {
      setActiveProjectTab('quotes')
      setActiveQuoteTab('extras')
      if (selectedQuoteId) {
        void loadQuoteExtras(selectedQuoteId)
      }
      return
    }
    if (target === 'readiness') {
      setActiveProjectTab('quotes')
      setActiveQuoteTab('readiness')
      if (selectedQuoteId) {
        void loadQuoteReadiness(selectedQuoteId)
      }
      return
    }
    setActiveProjectTab('quotes')
    setActiveQuoteTab('units')
  }

  function handleReadinessAction(check: QuoteReadinessCheck) {
    if (check.action_target === 'project') {
      if (selectedProject) openEditProjectModal(selectedProject)
      return
    }
    if (check.action_target === 'quote') {
      if (selectedQuote) openEditQuoteModal(selectedQuote)
      return
    }
    if (check.action_target === 'units') {
      setActiveProjectTab('quotes')
      setActiveQuoteTab('units')
      return
    }
    if (check.action_target === 'panels') {
      openQuotePanelsTab()
      return
    }
    if (check.action_target === 'cutting-lists') {
      openQuoteCuttingListTab()
      return
    }
    if (check.action_target === 'production') {
      setActiveProjectTab('quotes')
      setActiveQuoteTab('production')
      return
    }
    if (check.action_target === 'pricing') {
      openQuotePricingTab()
      return
    }
    if (check.action_target === 'libraries-pricing') {
      onOpenLibraries('pricing')
      return
    }
    openQuoteOutputsTab()
  }

  function handleOutputReviewAction(action: QuoteOutputAction) {
    if (action.action_target === 'project') {
      if (selectedProject) openEditProjectModal(selectedProject)
      return
    }
    if (action.action_target === 'quote') {
      if (selectedQuote) openEditQuoteModal(selectedQuote)
      return
    }
    if (action.action_target === 'units') {
      setActiveProjectTab('quotes')
      setActiveQuoteTab('units')
      return
    }
    if (action.action_target === 'panels') {
      openQuotePanelsTab()
      return
    }
    if (action.action_target === 'cutting-lists') {
      openQuoteCuttingListTab()
      return
    }
    if (action.action_target === 'production') {
      setActiveProjectTab('quotes')
      setActiveQuoteTab('production')
      return
    }
    if (action.action_target === 'pricing') {
      openQuotePricingTab()
      return
    }
    if (action.action_target === 'libraries-pricing') {
      onOpenLibraries('pricing')
      return
    }
    openQuoteOutputsTab()
  }

  function handleGenerateOutputAction(action: QuoteOutputAction) {
    if (action.id === 'client_quote_pdf' && selectedQuoteId) {
      void downloadCustomerQuotePdf(selectedQuoteId)
      return
    }
    if (action.id === 'workshop_schedule' && selectedQuoteId) {
      void downloadWorkshopSchedulePdf(selectedQuoteId)
      return
    }
    if (action.id === 'production_handoff_csv' && selectedQuoteId) {
      void downloadProductionHandoffExport(selectedQuoteId, 'csv')
      return
    }
    if (action.id === 'production_handoff_xlsx' && selectedQuoteId) {
      void downloadProductionHandoffExport(selectedQuoteId, 'xlsx')
      return
    }
    handleOutputReviewAction(action)
  }

  function openEditProjectModal(project: ProjectRow) {
    setProjectEditId(project.id)
    setModalError(null)
    setProjectDraft({
      name: project.name,
      client: project.client,
      address: project.address,
      description: project.description,
    })
    setIsProjectModalOpen(true)
  }

  function openCreateQuoteModal() {
    setQuoteEditId(null)
    setModalError(null)
    setQuoteDraft(defaultQuoteDraft)
    setIsQuoteModalOpen(true)
  }

  function openEditQuoteModal(quote: QuoteRow) {
    setQuoteEditId(quote.id)
    setModalError(null)
    setQuoteDraft(toQuoteDraft(quote))
    setIsQuoteModalOpen(true)
  }

  async function handleQuoteStatusChange(nextStatus: QuoteStatus) {
    if (!selectedQuoteId) return
    setIsSavingQuoteStatus(true)
    setError(null)
    try {
      const updated = await apiRequest<QuoteRow>(`/api/v1/quotes/${selectedQuoteId}/status`, {
        method: 'PATCH',
        token: authToken,
        body: { status: nextStatus },
      })
      setQuotes((current) => current.map((quote) => (quote.id === updated.id ? updated : quote)))
      if (selectedProjectId && (activeProjectTab === 'pricing' || activeQuoteTab === 'pricing')) {
        await loadProjectPricing(selectedProjectId)
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save quote status.')
    } finally {
      setIsSavingQuoteStatus(false)
    }
  }

  async function handleDuplicateQuote(quote: QuoteRow) {
    if (!selectedProjectId) return
    setDuplicatingQuoteId(quote.id)
    setError(null)
    try {
      const copiedQuote = await apiRequest<QuoteRow>(`/api/v1/quotes/${quote.id}/duplicate`, {
        method: 'POST',
        token: authToken,
      })
      setSelectedQuoteId(copiedQuote.id)
      setActiveProjectTab('quotes')
      setActiveQuoteTab('readiness')
      await loadProjects(search)
      await loadQuotes(selectedProjectId)
      await loadUnits(copiedQuote.id)
      await loadQuoteReadiness(copiedQuote.id)
      if (activeProjectTab === 'pricing' || activeQuoteTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not duplicate quote.')
    } finally {
      setDuplicatingQuoteId(null)
    }
  }

  async function handleCreateQuoteRevision(quote: QuoteRow) {
    if (!selectedProjectId) return
    setIsCreatingQuoteRevision(true)
    setError(null)
    try {
      const revisedQuote = await apiRequest<QuoteRow>(`/api/v1/quotes/${quote.id}/revisions`, {
        method: 'POST',
        token: authToken,
      })
      setSelectedQuoteId(revisedQuote.id)
      setActiveProjectTab('quotes')
      setActiveQuoteTab('readiness')
      await loadProjects(search)
      await loadQuotes(selectedProjectId)
      await loadUnits(revisedQuote.id)
      await loadQuoteReadiness(revisedQuote.id)
      if (activeProjectTab === 'pricing' || activeQuoteTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not create quote revision.')
    } finally {
      setIsCreatingQuoteRevision(false)
    }
  }

  function openCreateUnitModal() {
    if (!selectedQuote) return
    setUnitEditId(null)
    setModalError(null)
    const base = defaultUnitDraft
    const preferredType: UnitPresetKey = 'Base Draw'
    const dims = resolveDefaultDims(selectedQuote.unit_defaults, preferredType)
    setUnitDraft(syncDrawerSplitDraft({
      ...base,
      height: String(dims.height),
      depth: String(dims.depth),
      carcass_board_type_id: selectedQuote.default_carcass_board_type_id ?? '',
      door_board_type_id: selectedQuote.default_door_board_type_id ?? '',
      slide_id: '',
      hinge_id: '',
    }, 'type'))
    setIsUnitModalOpen(true)
  }

  function openEditUnitModal(unit: UnitRow) {
    const unitTypeIsPreset = unitPresets.includes(unit.unit_type_key as UnitPresetKey)
    const numDrawers = String(numberFromExtra(unit.extra_params, 'num_drawers', 3))
    setUnitEditId(unit.id)
    setModalError(null)
    setUnitDraft({
      unit_type_key: unitTypeIsPreset ? unit.unit_type_key : customUnitTypeValue,
      custom_unit_type_key: unitTypeIsPreset ? '' : unit.unit_type_key,
      height: String(unit.height),
      width: String(unit.width),
      depth: String(unit.depth),
      carcass_board_type_id: unit.carcass_board_type_id ?? selectedQuote?.default_carcass_board_type_id ?? '',
      door_board_type_id: unit.door_board_type_id ?? selectedQuote?.default_door_board_type_id ?? '',
      slide_id: unit.slide_id ?? idFromExtra(unit.extra_params, 'slide_id'),
      hinge_id: unit.hinge_id ?? idFromExtra(unit.extra_params, 'hinge_id'),
      num_drawers: numDrawers,
      ...drawerSplitDraftFromExtra(unit.extra_params, String(unit.height), numDrawers),
      num_doors: String(numberFromExtra(unit.extra_params, 'num_doors', 2)),
      num_shelves: String(numberFromExtra(unit.extra_params, 'num_shelves', 1)),
      ...profileHandleDraftFromExtra(unit.extra_params),
    })
    setIsUnitModalOpen(true)
  }

  function bulkRowForTemplate(template: BulkUnitTemplate): BulkUnitGridRow {
    const dims = resolveDefaultDims(selectedQuote?.unit_defaults ?? fallbackUnitDefaults, template.unit_type_key)
    return syncDrawerSplitDraft({
      ...defaultUnitDraft,
      id: null,
      rowKey: nextBulkUnitRowKey(),
      unit_type_key: template.unit_type_key,
      custom_unit_type_key: '',
      width: template.width,
      height: String(dims.height),
      depth: String(dims.depth),
      carcass_board_type_id: selectedQuote?.default_carcass_board_type_id ?? '',
      door_board_type_id: selectedQuote?.default_door_board_type_id ?? '',
      slide_id: '',
      hinge_id: '',
      num_drawers: template.unit_type_key === 'Base Draw' ? '3' : defaultUnitDraft.num_drawers,
      num_doors: template.unit_type_key === 'Base Draw' ? defaultUnitDraft.num_doors : '2',
      num_shelves: template.unit_type_key === 'Base Draw' ? defaultUnitDraft.num_shelves : '1',
    }, 'type')
  }

  function bulkRowFromUnit(unit: UnitRow): BulkUnitGridRow {
    const unitTypeIsPreset = unitPresets.includes(unit.unit_type_key as UnitPresetKey)
    const numDrawers = String(numberFromExtra(unit.extra_params, 'num_drawers', 3))
    return {
      id: unit.id,
      rowKey: nextBulkUnitRowKey(),
      unit_type_key: unitTypeIsPreset ? unit.unit_type_key : customUnitTypeValue,
      custom_unit_type_key: unitTypeIsPreset ? '' : unit.unit_type_key,
      height: String(unit.height),
      width: String(unit.width),
      depth: String(unit.depth),
      carcass_board_type_id: unit.carcass_board_type_id ?? selectedQuote?.default_carcass_board_type_id ?? '',
      door_board_type_id: unit.door_board_type_id ?? selectedQuote?.default_door_board_type_id ?? '',
      slide_id: unit.slide_id ?? idFromExtra(unit.extra_params, 'slide_id'),
      hinge_id: unit.hinge_id ?? idFromExtra(unit.extra_params, 'hinge_id'),
      num_drawers: numDrawers,
      ...drawerSplitDraftFromExtra(unit.extra_params, String(unit.height), numDrawers),
      num_doors: String(numberFromExtra(unit.extra_params, 'num_doors', 2)),
      num_shelves: String(numberFromExtra(unit.extra_params, 'num_shelves', 1)),
      ...profileHandleDraftFromExtra(unit.extra_params),
    }
  }

  function openBulkUnitModal() {
    if (!selectedQuote) return
    setModalError(null)
    setBulkUnitErrors({})
    setBulkUnitRows(units.length > 0 ? units.map((unit) => bulkRowFromUnit(unit)) : smithKitchenBulkTemplates.map((template) => bulkRowForTemplate(template)))
    setIsBulkUnitModalOpen(true)
  }

  function addBulkUnitRow() {
    setBulkUnitRows((current) => [...current, bulkRowForTemplate({ unit_type_key: 'Base Door', width: '600' })])
  }

  function toggleUnitSelection(unitId: string, selected: boolean) {
    setSelectedUnitIds((current) => {
      if (selected) {
        return current.includes(unitId) ? current : [...current, unitId]
      }
      return current.filter((id) => id !== unitId)
    })
  }

  function toggleAllUnits(selected: boolean) {
    setSelectedUnitIds(selected ? units.map((unit) => unit.id) : [])
  }

  function openBulkApplyModal() {
    if (!selectedQuote || visibleSelectedUnitIds.length === 0) return
    setModalError(null)
    setBulkApplyDraft({
      ...defaultBulkApplyDraft(),
      carcass_board_type_id: selectedQuote.default_carcass_board_type_id ?? '',
      door_board_type_id: selectedQuote.default_door_board_type_id ?? '',
      height: '',
      depth: '',
    })
    setIsBulkApplyModalOpen(true)
  }

  function updateUnitDraft(patch: Partial<UnitDraft>, reason: 'mode' | 'count' | 'height' | 'type' | 'none' = 'none') {
    setUnitDraft((current) => {
      const next = { ...current, ...patch }
      return isDrawerUnitType(resolvedUnitType(next)) ? syncDrawerSplitDraft(next, reason) : next
    })
  }

  function updateBulkUnitRow(rowKey: string, patch: Partial<BulkUnitGridRow>) {
    setBulkUnitRows((current) =>
      current.map((row) => {
        if (row.rowKey !== rowKey) return row
        const next = { ...row, ...patch }
        const isDrawer = isDrawerUnitType(resolvedUnitType(next))
        if (!isDrawer) return next
        if (patch.unit_type_key || patch.custom_unit_type_key) return syncDrawerSplitDraft(next, 'type')
        if (patch.num_drawers) return syncDrawerSplitDraft(next, 'count')
        if (patch.height) return syncDrawerSplitDraft(next, 'height')
        return syncDrawerSplitDraft(next)
      }),
    )
    setBulkUnitErrors((current) => {
      const next = { ...current }
      delete next[rowKey]
      return next
    })
  }

  function updateBulkApplyDraft(patch: Partial<BulkApplyDraft>) {
    setBulkApplyDraft((current) => ({ ...current, ...patch }))
  }

  function handleBulkUnitTypeChange(row: BulkUnitGridRow, nextValue: string) {
    if (nextValue === customUnitTypeValue) {
      updateBulkUnitRow(row.rowKey, { unit_type_key: customUnitTypeValue })
      return
    }
    const nextType = nextValue as UnitPresetKey
    const dims = resolveDefaultDims(selectedQuote?.unit_defaults ?? fallbackUnitDefaults, nextType)
    updateBulkUnitRow(row.rowKey, {
      unit_type_key: nextType,
      custom_unit_type_key: '',
      height: String(dims.height),
      depth: String(dims.depth),
    })
  }

  async function handleSaveQuoteCustomPanels() {
    if (!selectedQuoteId || !quoteCustomPanels) return
    setIsSavingQuoteCustomPanels(true)
    setError(null)
    try {
      const payload = await apiRequest<QuoteCustomPanelsResponse>(`/api/v1/quotes/${selectedQuoteId}/custom-panels`, {
        method: 'PUT',
        token: authToken,
        body: quoteCustomPanels,
      })
      setQuoteCustomPanels(normalizeQuoteCustomPanelsState(payload.custom_panels, selectedQuote, units))
      setQuoteCustomPanelRows(payload.computed_rows)
      setIsQuoteCustomPanelsDirty(false)
      await loadQuoteReadiness(selectedQuoteId)
      if (activeQuoteTab === 'cutting-lists') {
        await loadQuoteCuttingList(selectedQuoteId)
      }
      if (activeQuoteTab === 'production') {
        await loadQuoteProductionHandoff(selectedQuoteId)
      }
      if (selectedProjectId && activeProjectTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save quote panels.')
    } finally {
      setIsSavingQuoteCustomPanels(false)
    }
  }

  async function handleSaveQuoteExtras() {
    if (!selectedQuoteId) return
    setIsSavingQuoteExtras(true)
    setError(null)
    try {
      const items = Object.entries(quoteExtrasSelection)
        .filter(([, quantity]) => quantity > 0)
        .map(([extraId, quantity]) => ({ extra_id: extraId, quantity }))
      const payload = await apiRequest<QuoteExtrasResponse>(`/api/v1/quotes/${selectedQuoteId}/extras`, {
        method: 'PUT',
        token: authToken,
        body: { items },
      })
      const nextSelection = payload.items.reduce<Record<string, number>>((accumulator, item) => {
        accumulator[item.extra_id] = item.quantity
        return accumulator
      }, {})
      setQuoteExtrasSelection(nextSelection)
      setIsQuoteExtrasDirty(false)
      await loadQuoteReadiness(selectedQuoteId)
      if (activeQuoteTab === 'production') {
        await loadQuoteProductionHandoff(selectedQuoteId)
      }
      if (selectedProjectId && activeProjectTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save selected extras.')
    } finally {
      setIsSavingQuoteExtras(false)
    }
  }

  async function handleSaveProjectPricingSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedProjectId) return
    const payload = pricingSettingsPayloadFromDraft(projectPricingSettingsDraft)
    if (!payload) {
      setError('Project pricing defaults must be valid positive numbers.')
      return
    }

    setIsSavingProjectPricingSettings(true)
    setError(null)
    try {
      const updated = await apiRequest<ProjectPricingSettingsRow>(`/api/v1/projects/${selectedProjectId}/pricing-settings`, {
        method: 'PATCH',
        token: authToken,
        body: payload,
      })
      setProjectPricingSettings(updated)
      setProjectPricingSettingsDraft(pricingSettingsToDraft(updated))
      if (activeProjectTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
      if (selectedQuoteId) {
        await loadQuoteReadiness(selectedQuoteId)
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save project pricing defaults.')
    } finally {
      setIsSavingProjectPricingSettings(false)
    }
  }

  async function handleSaveQuotePricingSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedProjectId || !selectedQuoteId) return
    const payload = pricingSettingsPayloadFromDraft(quotePricingSettingsDraft)
    if (!payload) {
      setError('Quote pricing settings must be valid positive numbers.')
      return
    }

    setIsSavingQuotePricingSettings(true)
    setError(null)
    try {
      const updated = await apiRequest<QuotePricingSettingsRow>(`/api/v1/quotes/${selectedQuoteId}/pricing-settings`, {
        method: 'PATCH',
        token: authToken,
        body: payload,
      })
      setQuotePricingSettings(updated)
      setQuotePricingSettingsDraft(pricingSettingsToDraft(updated))
      await loadQuoteReadiness(selectedQuoteId)
      if (activeProjectTab === 'pricing' || activeQuoteTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save quote pricing settings.')
    } finally {
      setIsSavingQuotePricingSettings(false)
    }
  }

  async function handleProjectSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedName = projectDraft.name.trim()
    if (!trimmedName) {
      setModalError('Project name is required.')
      return
    }
    setIsSaving(true)
    setError(null)
    setModalError(null)
    try {
      const payload = {
        name: trimmedName,
        client: projectDraft.client.trim(),
        address: projectDraft.address.trim(),
        description: projectDraft.description.trim(),
      }
      if (projectEditId) {
        await apiRequest<ProjectRow>(`/api/v1/projects/${projectEditId}`, {
          method: 'PATCH',
          token: authToken,
          body: payload,
        })
      } else {
        await apiRequest<ProjectRow>('/api/v1/projects', {
          method: 'POST',
          token: authToken,
          body: payload,
        })
      }
      setIsProjectModalOpen(false)
      setSearch('')
      await loadProjects('')
      if (selectedQuoteId) {
        await loadQuoteReadiness(selectedQuoteId)
      }
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : 'Could not save project.'
      setError(message)
      setModalError(message)
    } finally {
      setIsSaving(false)
    }
  }

  async function handleQuoteSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedProjectId) return

    setIsSaving(true)
    setError(null)
    setModalError(null)
    try {
      const payload = quotePayloadFromDraft(quoteDraft)
      if (quoteEditId) {
        await apiRequest<QuoteRow>(`/api/v1/quotes/${quoteEditId}`, {
          method: 'PATCH',
          token: authToken,
          body: payload,
        })
      } else {
        await apiRequest<QuoteRow>(`/api/v1/projects/${selectedProjectId}/quotes`, {
          method: 'POST',
          token: authToken,
          body: payload,
        })
      }
      setIsQuoteModalOpen(false)
      await loadProjects(search)
      await loadQuotes(selectedProjectId)
      if (quoteEditId) {
        await loadQuoteReadiness(quoteEditId)
        if (activeQuoteTab === 'production') {
          await loadQuoteProductionHandoff(quoteEditId)
        }
      }
      if (activeQuoteTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : 'Could not save quote.'
      setError(message)
      setModalError(message)
    } finally {
      setIsSaving(false)
    }
  }

  async function refreshAfterUnitMutation(quoteId: string, options: { reloadUnits?: boolean } = {}) {
    if (options.reloadUnits !== false) {
      await loadUnits(quoteId)
    }
    await loadQuoteReadiness(quoteId)
    if (activeQuoteTab === 'cutting-lists') {
      await loadQuoteCuttingList(quoteId)
    }
    if (activeQuoteTab === 'outputs') {
      await loadQuoteOutputReview(quoteId)
    }
    if (activeQuoteTab === 'production') {
      await loadQuoteProductionHandoff(quoteId)
    }
    if (selectedProjectId) {
      await loadQuotes(selectedProjectId)
      if (activeProjectTab === 'pricing' || activeQuoteTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
    }
  }

  async function handleUnitSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedQuoteId) return

    setIsSaving(true)
    setError(null)
    setModalError(null)
    try {
      const payload = unitPayloadFromDraft(unitDraft)
      if (!payload.carcass_board_type_id) {
        setModalError('Carcass board is required.')
        setIsSaving(false)
        return
      }
      const splitError = isDrawerUnitDraft ? drawerSplitValidationMessage(unitDraft) : null
      if (splitError) {
        setModalError(splitError)
        setIsSaving(false)
        return
      }
      if (slideDepthError) {
        setModalError(slideDepthError)
        setIsSaving(false)
        return
      }
      if (unitEditId) {
        await apiRequest<UnitRow>(`/api/v1/quotes/${selectedQuoteId}/units/${unitEditId}`, {
          method: 'PATCH',
          token: authToken,
          body: payload,
        })
      } else {
        await apiRequest<UnitRow>(`/api/v1/quotes/${selectedQuoteId}/units`, {
          method: 'POST',
          token: authToken,
          body: payload,
        })
      }
      setIsUnitModalOpen(false)
      await refreshAfterUnitMutation(selectedQuoteId)
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : 'Could not save unit.'
      setError(message)
      setModalError(message)
    } finally {
      setIsSaving(false)
    }
  }

  function validateBulkUnitRows() {
    const nextErrors: Record<string, string> = {}
    bulkUnitRows.forEach((row) => {
      const unitType = resolvedUnitType(row).trim()
      const width = Number(row.width)
      const height = Number(row.height)
      const depth = Number(row.depth)
      const isDrawer = unitType.toLowerCase().includes('draw')
      const drawers = Number(row.num_drawers)
      const doors = Number(row.num_doors)
      const shelves = Number(row.num_shelves)

      if (!unitType) {
        nextErrors[row.rowKey] = 'Unit type is required.'
      } else if (!Number.isInteger(width) || width <= 0) {
        nextErrors[row.rowKey] = 'Width must be a positive whole number.'
      } else if (!Number.isInteger(height) || height <= 0) {
        nextErrors[row.rowKey] = 'Height must be a positive whole number.'
      } else if (!Number.isInteger(depth) || depth <= 0) {
        nextErrors[row.rowKey] = 'Depth must be a positive whole number.'
      } else if (!row.carcass_board_type_id) {
        nextErrors[row.rowKey] = 'Carcass board is required.'
      } else if (isDrawer && (!Number.isInteger(drawers) || drawers <= 0)) {
        nextErrors[row.rowKey] = 'Drawers must be a positive whole number.'
      } else if (isDrawer) {
        const splitError = drawerSplitValidationMessage(row)
        if (splitError) nextErrors[row.rowKey] = splitError
      } else if (!isDrawer && (!Number.isInteger(doors) || doors <= 0)) {
        nextErrors[row.rowKey] = 'Doors must be a positive whole number.'
      } else if (!isDrawer && (!Number.isInteger(shelves) || shelves < 0)) {
        nextErrors[row.rowKey] = 'Shelves must be zero or a whole number.'
      }
    })
    setBulkUnitErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  async function handleBulkUnitSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedQuoteId) return
    if (!validateBulkUnitRows()) {
      setModalError('Fix the highlighted rows before saving.')
      return
    }

    setIsSavingBulkUnits(true)
    setError(null)
    setModalError(null)
    try {
      const savedRows = await apiRequest<UnitRow[]>(`/api/v1/quotes/${selectedQuoteId}/units/bulk`, {
        method: 'PUT',
        token: authToken,
        body: {
          units: bulkUnitRows.map((row) => ({
            id: row.id,
            ...unitPayloadFromDraft(row),
          })),
        },
      })
      setUnits(savedRows)
      setIsBulkUnitModalOpen(false)
      await refreshAfterUnitMutation(selectedQuoteId, { reloadUnits: false })
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : 'Could not save bulk units.'
      setError(message)
      setModalError(message)
    } finally {
      setIsSavingBulkUnits(false)
    }
  }

  function bulkApplyPayload(): { ok: true; payload: Record<string, unknown> } | { ok: false; error: string } {
    const payload: Record<string, unknown> = { unit_ids: visibleSelectedUnitIds }
    let fieldCount = 0

    if (bulkApplyDraft.apply_carcass_board_type_id) {
      payload.carcass_board_type_id = bulkApplyDraft.carcass_board_type_id || null
      fieldCount += 1
    }
    if (bulkApplyDraft.apply_door_board_type_id) {
      payload.door_board_type_id = bulkApplyDraft.door_board_type_id || null
      fieldCount += 1
    }
    if (bulkApplyDraft.apply_handle_id) {
      payload.handle_id = bulkApplyDraft.handle_id || null
      fieldCount += 1
    }
    if (bulkApplyDraft.apply_slide_id) {
      payload.slide_id = bulkApplyDraft.slide_id || null
      fieldCount += 1
    }
    if (bulkApplyDraft.apply_hinge_id) {
      payload.hinge_id = bulkApplyDraft.hinge_id || null
      fieldCount += 1
    }
    if (bulkApplyDraft.apply_height) {
      const height = Number(bulkApplyDraft.height)
      if (!Number.isInteger(height) || height <= 0) {
        return { ok: false, error: 'Height must be a positive whole number.' }
      }
      payload.height = height
      fieldCount += 1
    }
    if (bulkApplyDraft.apply_depth) {
      const depth = Number(bulkApplyDraft.depth)
      if (!Number.isInteger(depth) || depth <= 0) {
        return { ok: false, error: 'Depth must be a positive whole number.' }
      }
      payload.depth = depth
      fieldCount += 1
    }
    if (fieldCount === 0) {
      return { ok: false, error: 'Choose at least one field to apply.' }
    }
    return { ok: true, payload }
  }

  async function handleBulkApplySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedQuoteId || visibleSelectedUnitIds.length === 0) return
    const nextPayload = bulkApplyPayload()
    if (!nextPayload.ok) {
      setModalError(nextPayload.error)
      return
    }

    setIsSavingBulkApply(true)
    setError(null)
    setModalError(null)
    try {
      const savedRows = await apiRequest<UnitRow[]>(`/api/v1/quotes/${selectedQuoteId}/units/bulk-apply`, {
        method: 'PATCH',
        token: authToken,
        body: nextPayload.payload,
      })
      setUnits(savedRows)
      setSelectedUnitIds([])
      setIsBulkApplyModalOpen(false)
      await refreshAfterUnitMutation(selectedQuoteId, { reloadUnits: false })
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : 'Could not apply unit changes.'
      setError(message)
      setModalError(message)
    } finally {
      setIsSavingBulkApply(false)
    }
  }

  async function handleDuplicateUnit(unitId: string) {
    if (!selectedQuoteId) return
    setDuplicatingUnitId(unitId)
    setError(null)
    try {
      await apiRequest<UnitRow>(`/api/v1/quotes/${selectedQuoteId}/units/${unitId}/duplicate`, {
        method: 'POST',
        token: authToken,
      })
      await refreshAfterUnitMutation(selectedQuoteId)
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not duplicate unit.')
    } finally {
      setDuplicatingUnitId(null)
    }
  }

  async function handleMoveUnit(unitId: string, direction: 'up' | 'down') {
    if (!selectedQuoteId) return
    const currentIndex = units.findIndex((unit) => unit.id === unitId)
    const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
    if (currentIndex < 0 || targetIndex < 0 || targetIndex >= units.length) return

    const nextUnits = [...units]
    const currentUnit = nextUnits[currentIndex]
    const targetUnit = nextUnits[targetIndex]
    if (!currentUnit || !targetUnit) return
    nextUnits[currentIndex] = targetUnit
    nextUnits[targetIndex] = currentUnit

    setIsReorderingUnits(true)
    setError(null)
    try {
      const orderedRows = await apiRequest<UnitRow[]>(`/api/v1/quotes/${selectedQuoteId}/units/reorder`, {
        method: 'PUT',
        token: authToken,
        body: { unit_ids: nextUnits.map((unit) => unit.id) },
      })
      setUnits(orderedRows)
      await refreshAfterUnitMutation(selectedQuoteId, { reloadUnits: false })
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not reorder units.')
    } finally {
      setIsReorderingUnits(false)
    }
  }

  async function handleDeleteProject(projectId: string) {
    setError(null)
    try {
      await apiRequest(`/api/v1/projects/${projectId}`, { method: 'DELETE', token: authToken })
      if (selectedProjectId === projectId) {
        setSelectedProjectId(null)
        setSelectedQuoteId(null)
        setProjectPricing(null)
        setCurrentView('projects')
      }
      await loadProjects(search)
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Could not delete project.')
    }
  }

  async function handleDeleteQuote(quoteId: string) {
    if (!selectedProjectId) return
    setError(null)
    try {
      await apiRequest(`/api/v1/quotes/${quoteId}`, { method: 'DELETE', token: authToken })
      await loadProjects(search)
      await loadQuotes(selectedProjectId)
      if (activeQuoteTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Could not delete quote.')
    }
  }

  async function handleDeleteUnit(unitId: string) {
    if (!selectedQuoteId) return
    setError(null)
    try {
      await apiRequest(`/api/v1/quotes/${selectedQuoteId}/units/${unitId}`, { method: 'DELETE', token: authToken })
      await refreshAfterUnitMutation(selectedQuoteId)
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Could not delete unit.')
    }
  }

  return (
    <div className="grid gap-4">
      {currentView === 'projects' ? (
        <Card>
          <CardHeader className="space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Projects and quotes</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  Open a recent job, search by customer or address, or create a new project for the work you are quoting.
                </p>
              </div>
              <Button onClick={openCreateProjectModal} size="sm" type="button">
                <Plus className="h-4 w-4" aria-hidden="true" />
                New project
              </Button>
            </div>
            <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
              <Input
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search projects, customers, or addresses"
                value={search}
              />
              <Button onClick={() => void loadProjects(search)} type="button" variant="outline">
                Search
              </Button>
            </div>
          </CardHeader>
          <CardContent className="grid gap-2">
            {isLoadingProjects ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                Loading projects
              </div>
            ) : projects.length > 0 ? (
              projects.map((project) => (
                <div
                  className="rounded-[var(--card-radius)] border border-border bg-card p-3 transition hover:border-primary/40"
                  key={project.id}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">{project.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{project.client || 'No client'}</p>
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <Badge variant="outline">{project.quote_count} {project.quote_count === 1 ? 'quote' : 'quotes'}</Badge>
                      <Button onClick={() => openProjectWorkspace(project.id)} size="sm" type="button">
                        Open project
                        <ArrowRight className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                  <p className="mt-2 truncate text-xs text-muted-foreground">{project.address || 'No address'}</p>
                  <div className="mt-3 flex items-center justify-between gap-2 border-t border-border pt-2">
                    <p className="text-xs text-muted-foreground">Project actions</p>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        aria-label="Edit project"
                        className="text-muted-foreground"
                        onClick={() => openEditProjectModal(project)}
                        size="icon"
                        title="Edit project"
                        type="button"
                        variant="ghost"
                      >
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button
                        aria-label="Delete project"
                        className="text-muted-foreground hover:text-destructive"
                        onClick={() => void handleDeleteProject(project.id)}
                        size="icon"
                        title="Delete project"
                        type="button"
                        variant="ghost"
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <Alert className="text-xs">
                Create your first project for the customer or room you are quoting. Projects keep quotes, units, cutting lists, and pricing together.
              </Alert>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          <Card>
            <CardHeader className="space-y-3 pb-0">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex flex-wrap items-start gap-3">
                  <Button onClick={() => setCurrentView('projects')} type="button" variant="outline">
                    <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                    Back to projects
                  </Button>
                  <div>
                    <CardTitle className="truncate">{selectedProject?.name ?? 'Project'}</CardTitle>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {selectedProject
                        ? `${selectedProject.client || 'No client'} · ${selectedProject.address || 'No address'}`
                        : 'No project selected.'}
                    </p>
                  </div>
                </div>
                <Button disabled={!selectedProject} onClick={openCreateQuoteModal} type="button">
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  New quote
                </Button>
              </div>
              <div className="border-t border-border pt-3">
                <div className="grid gap-2">
                  <p className="text-xs font-semibold uppercase text-muted-foreground">Project workflow</p>
                  <ControlGroup className="h-auto flex-wrap justify-start" role="tablist" aria-label="Project workflow">
                    <ControlGroupItem
                      aria-pressed={activeProjectTab === 'quotes'}
                      className="h-8 px-3 text-xs"
                      onClick={() => {
                        setActiveProjectTab('quotes')
                        if (activeQuoteTab === 'pricing') {
                          setActiveQuoteTab('readiness')
                        }
                      }}
                    >
                      Quote workspace
                    </ControlGroupItem>
                    <ControlGroupItem
                      aria-pressed={activeProjectTab === 'pricing'}
                      className="h-8 px-3 text-xs"
                      onClick={openProjectPricingTab}
                    >
                      Project pricing
                    </ControlGroupItem>
                  </ControlGroup>
                </div>
              </div>
            </CardHeader>
          </Card>

          <div className={`grid gap-4 ${activeProjectTab === 'pricing' ? 'xl:grid-cols-[260px_minmax(0,1fr)]' : 'xl:grid-cols-[340px_minmax(0,1fr)]'}`}>
            <Card>
              {activeProjectTab === 'pricing' ? (
                <>
                  <CardHeader>
                    <CardTitle>Project pricing</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-4">
                    <div className="grid gap-1">
                      {[
                        ['overview', 'Project totals'],
                        ['settings', 'Pricing setup'],
                        ['quotes', 'Compare quotes'],
                      ].map(([tab, label]) => (
                        <Button
                          className="justify-start"
                          key={tab}
                          onClick={() => setActivePricingTab(tab as PricingWorkspaceTab)}
                          type="button"
                          variant={activePricingTab === tab ? 'default' : 'ghost'}
                        >
                          {label}
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                </>
              ) : (
                <>
                  <CardHeader>
                    <CardTitle>Project quotes</CardTitle>
                    <p className="text-sm text-muted-foreground">Choose the quote you want to build, check, price, or send to output.</p>
                  </CardHeader>
                  <CardContent className="grid gap-2">
                    {isLoadingQuotes ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                        Loading quotes
                      </div>
                    ) : quotes.length > 0 ? (
                      quotes.map((quote) => {
                        const previousRevision = previousQuoteRevisionLabel(quote)
                        const isSelectedQuote = quote.id === selectedQuoteId
                        return (
                          <div
                            className={`w-full rounded-[var(--card-radius)] border p-3 text-left transition ${isSelectedQuote ? 'border-primary bg-primary/5' : 'border-border bg-card hover:border-primary/40'}`}
                            key={quote.id}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="truncate text-sm font-semibold">{quote.name}</p>
                                <div className="mt-1 flex flex-wrap items-center gap-1.5">
                                  <Badge variant={quoteStatusBadgeVariant(quote.status)}>{quoteStatusLabels[quote.status]}</Badge>
                                  <Badge variant="outline">{quoteRevisionLabel(quote)}</Badge>
                                  <Badge variant="outline">{`${quote.unit_count} ${quote.unit_count === 1 ? 'unit' : 'units'}`}</Badge>
                                </div>
                                {previousRevision ? (
                                  <p className="mt-1 truncate text-xs text-muted-foreground">{previousRevision}</p>
                                ) : null}
                                <p className="mt-1 truncate text-xs text-muted-foreground">{quote.notes || 'No notes'}</p>
                              </div>
                              {isSelectedQuote ? <Badge variant="outline">Open</Badge> : null}
                            </div>
                            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-2">
                              <Button
                                onClick={() => {
                                  setSelectedQuoteId(quote.id)
                                  setActiveQuoteTab('readiness')
                                }}
                                size="sm"
                                type="button"
                                variant={isSelectedQuote ? 'secondary' : 'outline'}
                              >
                                {isSelectedQuote ? 'Current quote' : 'Open quote'}
                                <ArrowRight className="h-4 w-4" aria-hidden="true" />
                              </Button>
                              <div className="flex items-center justify-end gap-1">
                                <Button
                                  aria-label="Create revision"
                                  className="text-muted-foreground"
                                  disabled={isCreatingQuoteRevision}
                                  onClick={() => void handleCreateQuoteRevision(quote)}
                                  size="icon"
                                  title="Create revision"
                                  type="button"
                                  variant="ghost"
                                >
                                  <GitBranch className="h-4 w-4" aria-hidden="true" />
                                </Button>
                                <Button
                                  aria-label="Duplicate quote"
                                  className="text-muted-foreground"
                                  disabled={duplicatingQuoteId === quote.id}
                                  onClick={() => void handleDuplicateQuote(quote)}
                                  size="icon"
                                  title="Duplicate quote"
                                  type="button"
                                  variant="ghost"
                                >
                                  {duplicatingQuoteId === quote.id ? (
                                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                                  ) : (
                                    <Copy className="h-4 w-4" aria-hidden="true" />
                                  )}
                                </Button>
                                <Button
                                  aria-label="Edit quote"
                                  className="text-muted-foreground"
                                  onClick={() => openEditQuoteModal(quote)}
                                  size="icon"
                                  title="Edit quote"
                                  type="button"
                                  variant="ghost"
                                >
                                  <Pencil className="h-4 w-4" aria-hidden="true" />
                                </Button>
                                <Button
                                  aria-label="Delete quote"
                                  className="text-muted-foreground hover:text-destructive"
                                  onClick={() => void handleDeleteQuote(quote.id)}
                                  size="icon"
                                  title="Delete quote"
                                  type="button"
                                  variant="ghost"
                                >
                                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        )
                      })
                    ) : (
                      <Alert className="text-xs">
                        Create the first quote for this project, then choose the default boards and hardware you want new units to use.
                      </Alert>
                    )}
                  </CardContent>
                </>
              )}
            </Card>

            <Card>
              <CardHeader className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <CardTitle>
                      {activeProjectTab === 'pricing'
                        ? activePricingTab === 'overview'
                          ? 'Project totals'
                          : activePricingTab === 'settings'
                            ? 'Pricing setup'
                            : activePricingTab === 'quotes'
                              ? 'Compare quotes'
                              : 'Project totals'
                        : selectedQuote
                          ? quoteWorkspaceTitle(activeQuoteTab)
                          : 'Select a quote'}
                    </CardTitle>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {activeProjectTab === 'pricing'
                        ? activePricingTab === 'overview'
                          ? 'Review project totals and pricing status across every quote.'
                          : activePricingTab === 'settings'
                            ? 'Set the project defaults and selected quote overrides used for pricing.'
                            : activePricingTab === 'quotes'
                              ? 'Compare priced quotes in this project before deciding what to send.'
                              : 'Review project totals and pricing status across every quote.'
                        : selectedQuote
                          ? quoteWorkspaceDescription(activeQuoteTab)
                          : 'Choose a quote from the left pane to begin.'}
                    </p>
                  </div>
                  {activeProjectTab === 'quotes' ? (
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      {selectedQuote ? (
                        <>
                          <Select
                            aria-label="Quote status"
                            className="h-9 w-36 text-xs"
                            disabled={isSavingQuoteStatus}
                            onChange={(event) => void handleQuoteStatusChange(event.target.value as QuoteStatus)}
                            value={selectedQuote.status}
                          >
                            {quoteStatusOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </Select>
                          <Button
                            disabled={isCreatingQuoteRevision}
                            onClick={() => void handleCreateQuoteRevision(selectedQuote)}
                            type="button"
                            variant="outline"
                          >
                            {isCreatingQuoteRevision ? (
                              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                            ) : (
                              <GitBranch className="h-4 w-4" aria-hidden="true" />
                            )}
                            New revision
                          </Button>
                        </>
                      ) : null}
                      <Button disabled={!selectedQuote} onClick={openCreateUnitModal} type="button">
                        <Plus className="h-4 w-4" aria-hidden="true" />
                        Add unit
                      </Button>
                      <Button disabled={!selectedQuote} onClick={openBulkUnitModal} type="button" variant="outline">
                        <ClipboardList className="h-4 w-4" aria-hidden="true" />
                        Bulk entry
                      </Button>
                      <Button disabled={!selectedQuote || selectedUnitCount === 0} onClick={openBulkApplyModal} type="button" variant="outline">
                        <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                        {`Bulk apply (${selectedUnitCount})`}
                      </Button>
                    </div>
                  ) : null}
                </div>
                {activeProjectTab === 'quotes' && selectedQuote ? (
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">{selectedQuote.name}</span>
                    <Badge variant={quoteStatusBadgeVariant(selectedQuote.status)}>{quoteStatusLabels[selectedQuote.status]}</Badge>
                    <Badge variant="outline">{quoteRevisionLabel(selectedQuote)}</Badge>
                    {previousQuoteRevisionLabel(selectedQuote) ? <span>{previousQuoteRevisionLabel(selectedQuote)}</span> : null}
                  </div>
                ) : null}
                {activeProjectTab === 'quotes' ? (
                  <div className="grid gap-3 border-b border-border pb-3">
                    <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5" role="tablist" aria-label="Quote workflow">
                      {quoteWorkflowSteps.map((step) => {
                        const Icon = step.icon
                        const isActive = isQuoteWorkflowStepActive(step.target, activeQuoteTab)
                        return (
                          <Button
                            aria-pressed={isActive}
                            className="h-auto min-h-24 flex-col items-start justify-start gap-1 whitespace-normal p-3 text-left"
                            disabled={!selectedQuote}
                            key={step.target}
                            onClick={() => openQuoteWorkspaceTab(step.target)}
                            title={step.description}
                            type="button"
                            variant={isActive ? 'secondary' : 'outline'}
                          >
                            <span className="flex w-full items-center justify-between gap-2">
                              <span className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                                <Icon className="h-4 w-4" aria-hidden="true" />
                                {`Step ${step.step}`}
                              </span>
                            </span>
                            <span className="text-sm font-semibold text-foreground">{step.label}</span>
                            <span className="text-xs font-normal leading-4 text-muted-foreground">{step.description}</span>
                          </Button>
                        )
                      })}
                    </div>
                    <div className="grid gap-2">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">Build quote details</p>
                      <ControlGroup className="h-auto flex-wrap justify-start" role="tablist" aria-label="Build quote details">
                        {quoteBuildTabs.map((tab) => (
                          <ControlGroupItem
                            aria-pressed={activeQuoteTab === tab.target}
                            className="h-8 px-3 text-xs"
                            disabled={!selectedQuote}
                            key={tab.target}
                            onClick={() => openQuoteWorkspaceTab(tab.target)}
                            title={tab.description}
                          >
                            {tab.label}
                          </ControlGroupItem>
                        ))}
                      </ControlGroup>
                    </div>
                  </div>
                ) : null}
              </CardHeader>
            <CardContent>
              {activeProjectTab === 'quotes' && !selectedQuote ? (
                <Alert className="text-xs">Choose a quote from the left pane or create a new quote for this project.</Alert>
              ) : activeQuoteTab === 'outputs' ? (
                isLoadingQuoteOutputReview ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Reviewing outputs
                  </div>
                ) : !quoteOutputReview ? (
                  <Alert className="text-xs">
                    Output review appears after the quote has enough saved details to check client and workshop outputs.
                  </Alert>
                ) : (
                  <OutputReviewPanel
                    currencyCode={quoteOutputReview.currency_code}
                    generatingActionId={generatingOutputActionId}
                    onGenerateAction={handleGenerateOutputAction}
                    onReviewAction={handleOutputReviewAction}
                    review={quoteOutputReview}
                  />
                )
              ) : activeQuoteTab === 'production' ? (
                isLoadingQuoteProductionHandoff ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Building production handoff
                  </div>
                ) : !quoteProductionHandoff ? (
                  <Alert className="text-xs">
                    Production handoff appears after the quote has cutting-list rows and material selections.
                  </Alert>
                ) : (
                  <ProductionHandoffPanel
                    exportingFormat={
                      generatingOutputActionId === 'production_handoff_csv'
                        ? 'csv'
                        : generatingOutputActionId === 'production_handoff_xlsx'
                          ? 'xlsx'
                          : null
                    }
                    handoff={quoteProductionHandoff}
                    key={`${quoteProductionHandoff.quote_id}:${quoteProductionHandoff.revision}`}
                    onDownloadExport={(format) => {
                      if (selectedQuoteId) void downloadProductionHandoffExport(selectedQuoteId, format)
                    }}
                  />
                )
              ) : activeQuoteTab === 'readiness' ? (
                isLoadingQuoteReadiness ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Checking readiness
                  </div>
                ) : !quoteReadiness ? (
                  <Alert className="text-xs">
                    Readiness will check quote details, board defaults, units, cutlists, and pricing once this quote has been saved.
                  </Alert>
                ) : (
                  <div className="grid gap-4">
                    <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex min-w-0 items-start gap-3">
                          <div className="mt-0.5">
                            <ReadinessIcon severity={quoteReadiness.is_ready ? 'pass' : quoteReadiness.error_count > 0 ? 'error' : 'warning'} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold">{quoteReadiness.summary_title}</p>
                            <p className="mt-1 text-sm text-muted-foreground">{quoteReadiness.summary_message}</p>
                            <div className="mt-3 flex flex-wrap gap-2">
                              <Badge variant={quoteReadiness.is_ready ? 'success' : 'warning'}>
                                {quoteReadiness.is_ready ? 'Ready' : 'Needs attention'}
                              </Badge>
                              <Badge variant="outline">{formatReadinessCount(quoteReadiness.warning_count, 'warning')}</Badge>
                              <Badge variant="outline">{formatReadinessCount(quoteReadiness.error_count, 'error')}</Badge>
                            </div>
                          </div>
                        </div>
                        {quoteReadiness.is_ready ? (
                          <Button
                            disabled={selectedQuote?.status === 'ready' || isSavingQuoteStatus}
                            onClick={() => void handleQuoteStatusChange('ready')}
                            type="button"
                          >
                            {isSavingQuoteStatus ? (
                              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                            ) : (
                              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                            )}
                            {selectedQuote?.status === 'ready' ? 'Marked Ready' : 'Mark Ready'}
                          </Button>
                        ) : null}
                      </div>
                    </div>

                    <div className="grid gap-2">
                      {quoteReadiness.checks.map((check) => (
                        <div
                          className="rounded-[var(--card-radius)] border border-border bg-card p-3"
                          key={check.id}
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div className="flex min-w-0 items-start gap-3">
                              <div className="mt-0.5">
                                <ReadinessIcon severity={check.severity} />
                              </div>
                              <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                  <p className="text-sm font-semibold">{check.title}</p>
                                  <Badge variant={readinessBadgeVariant(check.severity)}>
                                    {readinessLabel(check.severity)}
                                  </Badge>
                                </div>
                                <p className="mt-1 text-sm text-muted-foreground">{check.message}</p>
                              </div>
                            </div>
                            <Button
                              onClick={() => handleReadinessAction(check)}
                              size="sm"
                              type="button"
                              variant={check.severity === 'pass' ? 'outline' : 'default'}
                            >
                              <ArrowRight className="h-4 w-4" aria-hidden="true" />
                              {check.action_label}
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              ) : activeQuoteTab === 'units' ? (
                isLoadingUnits ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Loading units
                  </div>
                ) : (
                  <TableContainer>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-10">
                            <Checkbox
                              aria-label="Select all units"
                              checked={units.length > 0 && visibleSelectedUnitIds.length === units.length}
                              disabled={units.length === 0}
                              onChange={(event) => toggleAllUnits(event.target.checked)}
                            />
                          </TableHead>
                          <TableHead>#</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Dimensions (mm)</TableHead>
                          <TableHead>Boards</TableHead>
                          <TableHead>Hardware</TableHead>
                          <TableHead>Extra Params</TableHead>
                          <TableHead className="w-48" />
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {units.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={8}>
                              <div className="grid gap-1 py-3">
                                <p className="font-medium">Add the cabinets or built-ins for this quote.</p>
                                <p className="text-sm leading-5 text-muted-foreground">
                                  Units use the quote defaults for carcass and door boards. If the board list is empty, add board materials in Libraries first.
                                </p>
                              </div>
                            </TableCell>
                          </TableRow>
                        ) : (
                          units.map((unit, index) => {
                            const carcassBoardId = unit.carcass_board_type_id ?? selectedQuote?.default_carcass_board_type_id ?? null
                            const doorBoardId = unit.door_board_type_id ?? selectedQuote?.default_door_board_type_id ?? null
                            const unitSlideId = unit.slide_id ?? idFromExtra(unit.extra_params, 'slide_id')
                            const unitHingeId = unit.hinge_id ?? idFromExtra(unit.extra_params, 'hinge_id')
                            const effectiveSlideId = unitSlideId || selectedQuote?.default_slide_id || ''
                            const effectiveSlide = effectiveSlideId ? slides.find((slide) => slide.id === effectiveSlideId) ?? null : null
                            const effectiveDrawerHardwareDepth = effectiveSlide ? drawerSystemRequiredDepth(effectiveSlide) : 0
                            const unitSlideDepthWarning = isDrawerUnitType(unit.unit_type_key) && effectiveSlide && unit.depth < effectiveDrawerHardwareDepth
                              ? `Selected drawer hardware requires a carcass depth of at least ${effectiveDrawerHardwareDepth} mm internally.`
                              : null
                            const hardwareLabel = isDrawerUnitType(unit.unit_type_key)
                              ? `Drawer hardware: ${slideLabel(effectiveSlideId || null)}`
                              : isHingedUnitType(unit.unit_type_key)
                                ? `Hinge: ${hingeLabel((unitHingeId || selectedQuote?.default_hinge_id) ?? null)}`
                                : '-'
                            const unitActionsDisabled = isReorderingUnits || duplicatingUnitId !== null
                            return (
                              <TableRow
                                className={unitSlideDepthWarning ? 'bg-[var(--status-warning)] hover:bg-[var(--status-warning)]' : undefined}
                                key={unit.id}
                              >
                                <TableCell>
                                  <Checkbox
                                    aria-label={`Select unit ${unit.unit_number}`}
                                    checked={visibleSelectedUnitIds.includes(unit.id)}
                                    onChange={(event) => toggleUnitSelection(unit.id, event.target.checked)}
                                  />
                                </TableCell>
                                <TableCell>{unit.unit_number}</TableCell>
                                <TableCell>
                                  <div className="grid gap-1">
                                    <span>{unit.unit_type_key}</span>
                                    {unitSlideDepthWarning ? (
                                      <Badge className="w-fit gap-1" title={unitSlideDepthWarning} variant="warning">
                                        <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                                        Slide depth
                                      </Badge>
                                    ) : null}
                                  </div>
                                </TableCell>
                                <TableCell>{`${unit.height} x ${unit.width} x ${unit.depth} · t${unit.thickness}`}</TableCell>
                                <TableCell>{`${boardLabel(carcassBoardId)} / ${boardLabel(doorBoardId)}`}</TableCell>
                                <TableCell className="max-w-64 text-xs text-muted-foreground">
                                  <div className="grid gap-1">
                                    <span>{hardwareLabel}</span>
                                    {unitSlideDepthWarning ? (
                                      <span className="font-medium text-[var(--status-warning-foreground)]">{unitSlideDepthWarning}</span>
                                    ) : null}
                                  </div>
                                </TableCell>
                                <TableCell className="max-w-72 truncate text-xs text-muted-foreground">{formatExtraParams(unit.extra_params)}</TableCell>
                                <TableCell>
                                  <div className="flex justify-end gap-1">
                                    <Button
                                      aria-label={`Move unit ${unit.unit_number} up`}
                                      disabled={index === 0 || unitActionsDisabled}
                                      onClick={() => void handleMoveUnit(unit.id, 'up')}
                                      size="icon"
                                      title="Move up"
                                      type="button"
                                      variant="ghost"
                                    >
                                      <ArrowUp className="h-4 w-4" aria-hidden="true" />
                                    </Button>
                                    <Button
                                      aria-label={`Move unit ${unit.unit_number} down`}
                                      disabled={index === units.length - 1 || unitActionsDisabled}
                                      onClick={() => void handleMoveUnit(unit.id, 'down')}
                                      size="icon"
                                      title="Move down"
                                      type="button"
                                      variant="ghost"
                                    >
                                      <ArrowDown className="h-4 w-4" aria-hidden="true" />
                                    </Button>
                                    <Button
                                      aria-label={`Duplicate unit ${unit.unit_number}`}
                                      disabled={unitActionsDisabled}
                                      onClick={() => void handleDuplicateUnit(unit.id)}
                                      size="icon"
                                      title="Duplicate"
                                      type="button"
                                      variant="ghost"
                                    >
                                      {duplicatingUnitId === unit.id ? (
                                        <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                                      ) : (
                                        <Copy className="h-4 w-4" aria-hidden="true" />
                                      )}
                                    </Button>
                                    <Button
                                      aria-label={`Edit unit ${unit.unit_number}`}
                                      disabled={unitActionsDisabled}
                                      onClick={() => openEditUnitModal(unit)}
                                      size="icon"
                                      title="Edit"
                                      type="button"
                                      variant="ghost"
                                    >
                                      <Pencil className="h-4 w-4" aria-hidden="true" />
                                    </Button>
                                    <Button
                                      aria-label={`Delete unit ${unit.unit_number}`}
                                      disabled={unitActionsDisabled}
                                      onClick={() => void handleDeleteUnit(unit.id)}
                                      size="icon"
                                      title="Delete"
                                      type="button"
                                      variant="ghost"
                                    >
                                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                                    </Button>
                                  </div>
                                </TableCell>
                              </TableRow>
                            )
                          })
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )
              ) : activeQuoteTab === 'panels' ? (
                isLoadingQuoteCustomPanels ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Loading panel configuration
                  </div>
                ) : !quoteCustomPanels ? (
                  <Alert className="text-xs">
                    Panel setup will appear after the quote is selected. Use it for visible panels, fillers, and quote-level board work.
                  </Alert>
                ) : (
                  <QuotePanelsEditor
                    boardLabel={boardLabel}
                    boards={boards}
                    defaultPanelBoardId={selectedQuote!.default_panel_board_type_id}
                    isSaving={isSavingQuoteCustomPanels}
                    isSavedStateDirty={isQuoteCustomPanelsDirty}
                    onChange={(next) => {
                      setQuoteCustomPanels(next)
                      setIsQuoteCustomPanelsDirty(true)
                    }}
                    onSave={() => void handleSaveQuoteCustomPanels()}
                    panelRows={quoteCustomPanelRows}
                    panelState={quoteCustomPanels}
                    presetFamilyCounts={panelFamilyCounts}
                    selectedQuote={selectedQuote!}
                  />
                )
              ) : activeQuoteTab === 'cutting-lists' ? (
                isLoadingCuttingList ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Building cutting list
                  </div>
                ) : cutlistRowCount === 0 ? (
                  <Alert className="text-xs">
                    Add at least one unit with a carcass board to generate cutting-list rows.
                  </Alert>
                ) : (
                  <div className="grid gap-4">
                    <div className="flex flex-wrap items-center gap-2">
                      {quoteCuttingList ? (
                        <Badge variant={quoteCuttingList.readiness.cutlist_valid ? 'outline' : 'warning'}>
                          {quoteCuttingList.readiness.cutlist_valid
                            ? 'Cutlist ready'
                            : `${quoteCuttingList.readiness.warning_count} cutlist warnings`}
                        </Badge>
                      ) : null}
                    </div>

                    {cutlistWarnings.length > 0 ? (
                      <Alert className="text-xs" variant="warning">
                        <div className="grid gap-1">
                          {cutlistWarnings.map((warning, index) => (
                            <p key={`${warning.section}-${warning.unit_number}-${warning.row_desc}-${index}`}>
                              {`${formatCutlistWarningSource(warning)} / ${warning.row_desc}: ${warning.reason}`}
                            </p>
                          ))}
                        </div>
                      </Alert>
                    ) : null}

                    <div className="flex items-center gap-1">
                      <Button
                        className="h-7 px-2 text-xs"
                        onClick={() => setActiveCuttingListViewTab('carcass')}
                        size="sm"
                        type="button"
                        variant={activeCuttingListViewTab === 'carcass' ? 'default' : 'outline'}
                      >
                        {`Carcass (${quoteCuttingList?.carcass.length ?? 0})`}
                      </Button>
                      <Button
                        className="h-7 px-2 text-xs"
                        onClick={() => setActiveCuttingListViewTab('panels')}
                        size="sm"
                        type="button"
                        variant={activeCuttingListViewTab === 'panels' ? 'default' : 'outline'}
                      >
                        {`Panels (${quoteCuttingList?.panels.length ?? 0})`}
                      </Button>
                      <Button
                        className="h-7 px-2 text-xs"
                        onClick={() => setActiveCuttingListViewTab('extras')}
                        size="sm"
                        type="button"
                        variant={activeCuttingListViewTab === 'extras' ? 'default' : 'outline'}
                      >
                        {`Custom (${quoteCuttingList?.extras.length ?? 0})`}
                      </Button>
                    </div>

                    {activeCuttingListViewTab === 'carcass' ? (
                      quoteCuttingList && quoteCuttingList.carcass.length > 0 ? (
                        <CutlistSection
                          rows={quoteCuttingList.carcass}
                          section="carcass"
                          title="Carcass"
                          warnings={cutlistWarnings}
                        />
                      ) : (
                        <Alert className="text-xs">No carcass rows for this quote.</Alert>
                      )
                    ) : (
                      activeCuttingListViewTab === 'panels' ? (
                        quoteCuttingList && quoteCuttingList.panels.length > 0 ? (
                          <CutlistSection
                            rows={quoteCuttingList.panels}
                            section="panel"
                            title="Panels"
                            warnings={cutlistWarnings}
                          />
                        ) : (
                          <Alert className="text-xs">No panel rows for this quote.</Alert>
                        )
                      ) : quoteCuttingList && quoteCuttingList.extras.length > 0 ? (
                        <CutlistSection
                          rows={quoteCuttingList.extras}
                          section="extra_panel"
                          title="Quote Panels & Extras"
                          warnings={cutlistWarnings}
                        />
                      ) : (
                        <Alert className="text-xs">No quote-level panel rows for this quote.</Alert>
                      )
                    )}
                  </div>
                )
              ) : activeQuoteTab === 'extras' ? (
                <div className="grid gap-3">
                  <div className="flex items-center justify-end">
                    <Button
                      disabled={!isQuoteExtrasDirty || isSavingQuoteExtras}
                      onClick={() => void handleSaveQuoteExtras()}
                      size="sm"
                      type="button"
                    >
                      {isSavingQuoteExtras ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                      Save extras
                    </Button>
                  </div>
                  {isLoadingQuoteExtras ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                      Loading selected extras
                    </div>
                  ) : extras.length === 0 ? (
                    <Alert className="text-xs">
                      Add extras in Libraries when you want to include delivery, installation, accessories, or other add-ons on a quote.
                    </Alert>
                  ) : (
                    <TableContainer>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-20">Use</TableHead>
                            <TableHead>Extra</TableHead>
                            <TableHead>Category</TableHead>
                            <TableHead>Supplier / Code</TableHead>
                            <TableHead className="w-32">Qty</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {extras.map((extra) => {
                            const quantity = quoteExtrasSelection[extra.id] ?? 0
                            const isSelected = quantity > 0
                            return (
                              <TableRow key={extra.id}>
                                <TableCell>
                                  <Checkbox
                                    checked={isSelected}
                                    onChange={(event) => {
                                      const checked = event.target.checked
                                      setQuoteExtrasSelection((current) => {
                                        const next = { ...current }
                                        if (checked) {
                                          next[extra.id] = current[extra.id] ?? 1
                                        } else {
                                          delete next[extra.id]
                                        }
                                        return next
                                      })
                                      setIsQuoteExtrasDirty(true)
                                    }}
                                  />
                                </TableCell>
                                <TableCell>{extra.name}</TableCell>
                                <TableCell>{extra.category_name}</TableCell>
                                <TableCell className="text-xs text-muted-foreground">{`${extra.supplier || '-'} / ${extra.code || '-'}`}</TableCell>
                                <TableCell>
                                  <Input
                                    disabled={!isSelected}
                                    min={1}
                                    onChange={(event) => {
                                      const parsed = Number(event.target.value)
                                      setQuoteExtrasSelection((current) => ({
                                        ...current,
                                        [extra.id]: Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : 1,
                                      }))
                                      setIsQuoteExtrasDirty(true)
                                    }}
                                    type="number"
                                    value={isSelected ? String(quantity) : '1'}
                                  />
                                </TableCell>
                              </TableRow>
                            )
                          })}
                        </TableBody>
                      </Table>
                    </TableContainer>
                    )}
                  </div>
                ) : activeProjectTab === 'quotes' && activeQuoteTab === 'pricing' ? (
                  isLoadingProjectPricing ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                      Loading quote pricing
                    </div>
                  ) : !projectPricing ? (
                    <Alert className="text-xs">
                      Pricing appears after the quote has units and the library has prices for the boards, hardware, and extras being used.
                    </Alert>
                  ) : (
                    <div className="grid gap-5">
                      <div className="grid gap-3">
                        <details className="grid gap-3">
                          <summary className="cursor-pointer text-sm font-semibold">
                            <span className="inline-flex flex-wrap items-center gap-2">
                              Quote pricing
                              {quotePricingSettings ? (
                                <Badge variant="outline">{`Markup ${formatPercentFromBps(quotePricingSettings.default_markup_bps)}`}</Badge>
                              ) : null}
                            </span>
                          </summary>
                          <div className="pt-3">
                            {isLoadingQuotePricingSettings ? (
                              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                                Loading quote pricing
                              </div>
                            ) : (
                              <PricingSettingsEditor
                                currencyCode={pricingCurrencyCode}
                                draft={quotePricingSettingsDraft}
                                isSaving={isSavingQuotePricingSettings}
                                onDraftChange={setQuotePricingSettingsDraft}
                                onSubmit={handleSaveQuotePricingSettings}
                              />
                            )}
                          </div>
                        </details>
                      </div>

                      {selectedQuotePricing ? (
                        <div className="grid gap-3 border-t border-border pt-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-xs font-semibold uppercase text-muted-foreground">{`${selectedQuotePricing.quote_name} line items`}</p>
                            <div className="flex flex-wrap gap-2">
                              <Badge variant="outline">{`Cost ${formatCents(selectedQuotePricing.cost_total_cents, pricingCurrencyCode)}`}</Badge>
                              <Badge variant="outline">{`Sell ${formatCents(selectedQuotePricing.sell_before_vat_cents, pricingCurrencyCode)}`}</Badge>
                              <Badge variant="outline">{`Profit ${formatCents(selectedQuotePricing.profit_cents, pricingCurrencyCode)}`}</Badge>
                            </div>
                          </div>
                          <ActivePriceListGuidance
                            activePriceListId={selectedQuotePricing.active_price_list_id}
                            onOpenLibraries={onOpenLibraries}
                          />
                          <MissingPriceGuidance
                            includeQuote={false}
                            missingPrices={selectedQuotePricing.missing_prices}
                            onOpenLibraries={onOpenLibraries}
                          />
                          <MaterialSummaryReview
                            currencyCode={pricingCurrencyCode}
                            summary={selectedQuotePricing.material_summary}
                          />
                          <HardwarePickListReview pickList={selectedQuotePricing.hardware_pick_list} />
                          {selectedQuotePricing.lines.length === 0 ? (
                            <Alert className="text-xs">
                              Add units and library prices to produce the quote line breakdown.
                            </Alert>
                          ) : (
                            selectedQuotePricingGroups.map((group) => {
                              const bucketTotal = selectedQuotePricing.bucket_totals.find((bucket) => bucket.bucket === group.bucket)
                              return (
                                <div className="grid gap-2" key={group.bucket}>
                                  <div className="flex flex-wrap items-center gap-2 text-xs">
                                    <Badge variant="outline">{formatBucketLabel(group.bucket)}</Badge>
                                    {bucketTotal ? (
                                      <span className="text-muted-foreground">
                                        {`${formatCents(bucketTotal.cost_total_cents, pricingCurrencyCode)} cost · ${formatCents(bucketTotal.sell_total_cents, pricingCurrencyCode)} sell`}
                                      </span>
                                    ) : null}
                                  </div>
                                  <TableContainer>
                                    <Table className="min-w-[760px] text-xs">
                                      <TableHeader>
                                        <TableRow>
                                          <TableHead>Item</TableHead>
                                          <TableHead>Component</TableHead>
                                          <TableHead className="text-right">Qty</TableHead>
                                          <TableHead className="text-right">Cost</TableHead>
                                          <TableHead className="text-right">Markup</TableHead>
                                          <TableHead className="text-right">Sell</TableHead>
                                          <TableHead className="text-right">Profit</TableHead>
                                        </TableRow>
                                      </TableHeader>
                                      <TableBody>
                                        {group.lines.map((line) => (
                                          <TableRow key={`${line.item_key}:${line.price_component}:${line.bucket}:${line.description}`}>
                                            <TableCell>
                                              {line.description}
                                              {line.missing ? <Badge className="ml-2" variant="warning">Missing</Badge> : null}
                                            </TableCell>
                                            <TableCell>{line.price_component}</TableCell>
                                            <TableCell className="text-right">{`${formatPricingQty(line.qty)} ${line.uom}`}</TableCell>
                                            <TableCell className="text-right">{formatCents(line.cost_total_cents, pricingCurrencyCode)}</TableCell>
                                            <TableCell className="text-right">{formatPercentFromBps(line.markup_bps)}</TableCell>
                                            <TableCell className="text-right">{formatCents(line.sell_total_cents, pricingCurrencyCode)}</TableCell>
                                            <TableCell className="text-right">{formatCents(line.profit_cents, pricingCurrencyCode)}</TableCell>
                                          </TableRow>
                                        ))}
                                      </TableBody>
                                    </Table>
                                  </TableContainer>
                                </div>
                              )
                            })
                          )}
                        </div>
                      ) : (
                        <Alert className="text-xs">Select a quote with units to review its priced line breakdown.</Alert>
                      )}
                    </div>
                  )
              ) : isLoadingProjectPricing ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Loading pricing summary
                </div>
              ) : !projectPricing ? (
                <Alert className="text-xs">
                  Project pricing appears once quotes have units and matching prices in the library.
                </Alert>
              ) : (
                  <div className="grid gap-5">
                    {activePricingTab === 'overview' ? (
                      <>
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
                    <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
                      <p className="text-xs text-muted-foreground">Base cost</p>
                      <p className="text-base font-semibold">{formatCents(projectPricing.cost_total_cents, pricingCurrencyCode)}</p>
                    </div>
                    <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
                      <p className="text-xs text-muted-foreground">Sell before VAT</p>
                      <p className="text-base font-semibold">{formatCents(projectPricing.sell_before_vat_cents, pricingCurrencyCode)}</p>
                    </div>
                    <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
                      <p className="text-xs text-muted-foreground">Profit</p>
                      <p className="text-base font-semibold">{formatCents(projectPricing.profit_cents, pricingCurrencyCode)}</p>
                    </div>
                    <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
                      <p className="text-xs text-muted-foreground">VAT</p>
                      <p className="text-base font-semibold">{formatCents(projectPricing.vat_cents, pricingCurrencyCode)}</p>
                    </div>
                    <div className="rounded-[var(--card-radius)] border border-border bg-primary/10 p-3">
                      <p className="text-xs text-muted-foreground">Grand total</p>
                      <p className="text-base font-semibold">{formatCents(projectPricing.grand_total_cents, pricingCurrencyCode)}</p>
                    </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant={projectPricing.is_complete ? 'outline' : 'warning'}>
                      {projectPricing.is_complete
                        ? 'Complete pricing'
                        : projectCutlistWarningCount > 0
                          ? 'Cutlist review'
                          : 'Missing prices'}
                    </Badge>
                    {projectCutlistWarningCount > 0 ? (
                      <Badge variant="warning">{`${projectCutlistWarningCount} cutlist warnings`}</Badge>
                    ) : null}
                    <Badge variant="outline">{pricingCurrencyCode}</Badge>
                    <span>{`Default markup ${formatPercentFromBps(projectPricing.markup_bps)} · VAT ${formatPercentFromBps(projectPricing.vat_rate_bps)}`}</span>
                    </div>
                    <ActivePriceListGuidance
                      activePriceListId={projectPricing.active_price_list_id}
                      onOpenLibraries={onOpenLibraries}
                    />
                    <MissingPriceGuidance
                      includeQuote
                      missingPrices={projectPricing.missing_prices}
                      onOpenLibraries={onOpenLibraries}
                    />
                      </>
                    ) : null}

                    {activePricingTab === 'settings' ? (
                    <div className="grid gap-3">
                    <details className="grid gap-3">
                      <summary className="cursor-pointer text-sm font-semibold">
                        <span className="inline-flex flex-wrap items-center gap-2">
                          Project defaults
                          {projectPricingSettings ? (
                            <Badge variant="outline">{`VAT ${formatPercentFromBps(projectPricingSettings.vat_rate_bps)}`}</Badge>
                          ) : null}
                        </span>
                      </summary>
                      <div className="pt-3">
                        {isLoadingProjectPricingSettings ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                            Loading project defaults
                          </div>
                        ) : (
                          <PricingSettingsEditor
                            currencyCode={pricingCurrencyCode}
                            draft={projectPricingSettingsDraft}
                            isSaving={isSavingProjectPricingSettings}
                            onDraftChange={setProjectPricingSettingsDraft}
                            onSubmit={handleSaveProjectPricingSettings}
                          />
                        )}
                      </div>
                    </details>

                      </div>
                      ) : null}

                    {activePricingTab === 'quotes' ? (
                    <TableContainer>
                    <Table className="min-w-[760px]">
                      <TableHeader>
                        <TableRow>
                          <TableHead>Quote</TableHead>
                          <TableHead>Quote status</TableHead>
                          <TableHead>Pricing</TableHead>
                          <TableHead className="text-right">Cost</TableHead>
                          <TableHead className="text-right">Sell</TableHead>
                          <TableHead className="text-right">Profit</TableHead>
                          <TableHead className="text-right">Total</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {projectPricing.quotes.map((quotePricing) => {
                          const quoteWarningCount = quotePricing.cutlist_warnings.length
                          const previousRevision = previousQuoteRevisionLabel(quotePricing)
                          return (
                            <TableRow key={quotePricing.quote_id}>
                              <TableCell>
                                <div className="grid gap-1">
                                  <span>{quotePricing.quote_name}</span>
                                  <span className="text-xs text-muted-foreground">{quoteRevisionLabel(quotePricing)}</span>
                                  {previousRevision ? <span className="text-xs text-muted-foreground">{previousRevision}</span> : null}
                                </div>
                              </TableCell>
                              <TableCell>
                                <Badge variant={quoteStatusBadgeVariant(quotePricing.quote_status)}>
                                  {quoteStatusLabels[quotePricing.quote_status]}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <div className="flex flex-wrap gap-2">
                                  <Badge variant={quotePricing.is_complete ? 'outline' : 'warning'}>
                                    {quotePricing.is_complete
                                      ? 'Complete'
                                      : quoteWarningCount > 0
                                        ? 'Cutlist review'
                                        : 'Missing prices'}
                                  </Badge>
                                  {quoteWarningCount > 0 ? (
                                    <Badge variant="warning">{`${quoteWarningCount} warnings`}</Badge>
                                  ) : null}
                                </div>
                              </TableCell>
                              <TableCell className="text-right">{formatCents(quotePricing.cost_total_cents, pricingCurrencyCode)}</TableCell>
                              <TableCell className="text-right">{formatCents(quotePricing.sell_before_vat_cents, pricingCurrencyCode)}</TableCell>
                              <TableCell className="text-right">{formatCents(quotePricing.profit_cents, pricingCurrencyCode)}</TableCell>
                              <TableCell className="text-right">{formatCents(quotePricing.grand_total_cents, pricingCurrencyCode)}</TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                    </TableContainer>
                    ) : null}

                    {activePricingTab === 'overview' && projectPricing.bucket_totals.length > 0 ? (
                    <div className="grid gap-2">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">Project bucket totals</p>
                      <TableContainer>
                        <Table className="min-w-[720px]">
                          <TableHeader>
                            <TableRow>
                              <TableHead>Bucket</TableHead>
                              <TableHead className="text-right">Cost</TableHead>
                              <TableHead className="text-right">Sell</TableHead>
                              <TableHead className="text-right">Profit</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {projectPricing.bucket_totals.map((bucket) => (
                              <TableRow key={bucket.bucket}>
                                <TableCell>{formatBucketLabel(bucket.bucket)}</TableCell>
                                <TableCell className="text-right">{formatCents(bucket.cost_total_cents, pricingCurrencyCode)}</TableCell>
                                <TableCell className="text-right">{formatCents(bucket.sell_total_cents, pricingCurrencyCode)}</TableCell>
                                <TableCell className="text-right">{formatCents(bucket.profit_cents, pricingCurrencyCode)}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </div>
                  ) : null}

                    </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
        )}

      {error ? <Alert variant="destructive">{error}</Alert> : null}
      {isLoadingLibraries ? (
        <Alert className="text-xs">Loading library defaults for quote setup.</Alert>
      ) : null}

      {isProjectModalOpen ? (
        <ModalCard title={projectEditId ? 'Edit Project' : 'Create Project'} onClose={() => setIsProjectModalOpen(false)}>
          <form className="grid gap-3" onSubmit={handleProjectSubmit}>
            {modalError ? <Alert variant="destructive">{modalError}</Alert> : null}
            <Label className="grid gap-1.5">
              Project name
              <Input
                onChange={(event) => setProjectDraft((current) => ({ ...current, name: event.target.value }))}
                required
                value={projectDraft.name}
              />
            </Label>
            <Label className="grid gap-1.5">
              Client
              <Input
                onChange={(event) => setProjectDraft((current) => ({ ...current, client: event.target.value }))}
                value={projectDraft.client}
              />
            </Label>
            <Label className="grid gap-1.5">
              Address
              <Input
                onChange={(event) => setProjectDraft((current) => ({ ...current, address: event.target.value }))}
                value={projectDraft.address}
              />
            </Label>
            <Label className="grid gap-1.5">
              Description
              <Textarea
                onChange={(event) => setProjectDraft((current) => ({ ...current, description: event.target.value }))}
                rows={4}
                value={projectDraft.description}
              />
            </Label>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setIsProjectModalOpen(false)} type="button" variant="outline">
                Cancel
              </Button>
              <Button disabled={isSaving} type="submit">
                {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                Save project
              </Button>
            </div>
          </form>
        </ModalCard>
      ) : null}

      {isQuoteModalOpen ? (
        <ModalCard title={quoteEditId ? 'Edit Quote' : 'Create Quote'} onClose={() => setIsQuoteModalOpen(false)}>
          <form className="grid gap-3" onSubmit={handleQuoteSubmit}>
            {modalError ? <Alert variant="destructive">{modalError}</Alert> : null}
            <Label className="grid gap-1.5">
              Quote name
              <Input
                onChange={(event) => setQuoteDraft((current) => ({ ...current, name: event.target.value }))}
                required
                value={quoteDraft.name}
              />
            </Label>
            <Label className="grid gap-1.5">
              Notes
              <Textarea
                onChange={(event) => setQuoteDraft((current) => ({ ...current, notes: event.target.value }))}
                rows={3}
                value={quoteDraft.notes}
              />
            </Label>

            {boards.length === 0 ? (
              <Alert className="text-xs">
                Add board materials in Libraries before choosing quote defaults. Boards are required before units can be saved.
              </Alert>
            ) : null}

            <div className="grid gap-3 md:grid-cols-3">
              <LibrarySelect
                label="Carcass board"
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_carcass_board_type_id: value }))}
                value={quoteDraft.default_carcass_board_type_id}
              />
              <LibrarySelect
                label="Door board"
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_door_board_type_id: value }))}
                value={quoteDraft.default_door_board_type_id}
              />
              <LibrarySelect
                label="Panel board"
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_panel_board_type_id: value }))}
                value={quoteDraft.default_panel_board_type_id}
              />
            </div>

            <div className="grid gap-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Production defaults</p>
              <div className="grid gap-3 lg:grid-cols-2">
                <ProductionMetadataControls
                  label="Door and drawer panels"
                  onChange={(next) =>
                    setQuoteDraft((current) => ({
                      ...current,
                      production_metadata: {
                        ...current.production_metadata,
                        door_panel: next,
                      },
                    }))
                  }
                  value={quoteDraft.production_metadata?.door_panel ?? defaultProductionMetadata}
                />
                <ProductionMetadataControls
                  label="Visible quote panels"
                  onChange={(next) =>
                    setQuoteDraft((current) => ({
                      ...current,
                      production_metadata: {
                        ...current.production_metadata,
                        visible_panel: next,
                      },
                    }))
                  }
                  value={quoteDraft.production_metadata?.visible_panel ?? defaultProductionMetadata}
                />
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <LibrarySelect
                label="Default drawer hardware"
                options={slides.map((slide) => ({ value: slide.id, label: slideLabel(slide.id) }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_slide_id: value }))}
                value={quoteDraft.default_slide_id}
              />
              <LibrarySelect
                label="Default hinge"
                options={hinges.map((hinge) => ({ value: hinge.id, label: `${hinge.brand} ${hinge.model} (${hinge.opening_angle_deg}deg)` }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_hinge_id: value }))}
                value={quoteDraft.default_hinge_id}
              />
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <LibrarySelect
                label="Base handle"
                options={doorHandles.map((handle) => ({ value: handle.id, label: handleLabel(handle.id) }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_base_handle_id: value }))}
                value={quoteDraft.default_base_handle_id}
              />
              <LibrarySelect
                label="Wall handle"
                options={doorHandles.map((handle) => ({ value: handle.id, label: handleLabel(handle.id) }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_wall_handle_id: value }))}
                value={quoteDraft.default_wall_handle_id}
              />
              <LibrarySelect
                label="Tall handle"
                options={doorHandles.map((handle) => ({ value: handle.id, label: handleLabel(handle.id) }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_tall_handle_id: value }))}
                value={quoteDraft.default_tall_handle_id}
              />
              <LibrarySelect
                label="Drawer handle"
                options={standardHandles.map((handle) => ({ value: handle.id, label: handleLabel(handle.id) }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_drawer_handle_id: value }))}
                value={quoteDraft.default_drawer_handle_id}
              />
            </div>

            <div className="grid gap-2">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Default unit dimensions</p>
              <QuoteDefaultDimensionGrid draft={quoteDraft} setDraft={setQuoteDraft} />
            </div>

            <div className="flex justify-end gap-2">
              <Button onClick={() => setIsQuoteModalOpen(false)} type="button" variant="outline">
                Cancel
              </Button>
              <Button disabled={isSaving} type="submit">
                {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                Save quote
              </Button>
            </div>
          </form>
        </ModalCard>
      ) : null}

      {isUnitModalOpen ? (
        <ModalCard title={unitEditId ? 'Edit Unit' : 'Add Unit'} onClose={() => setIsUnitModalOpen(false)}>
          <form className="grid gap-3" onSubmit={handleUnitSubmit}>
            {modalError ? <Alert variant="destructive">{modalError}</Alert> : null}
            <Label className="grid gap-1.5">
              Unit type
              <Select
                onChange={(event) => {
                  const nextValue = event.target.value
                  if (nextValue === customUnitTypeValue) {
                    updateUnitDraft({ unit_type_key: customUnitTypeValue }, 'type')
                    return
                  }
                  const nextType = nextValue as UnitPresetKey
                  const dims = resolveDefaultDims(selectedQuote?.unit_defaults ?? fallbackUnitDefaults, nextType)
                  updateUnitDraft({
                    unit_type_key: nextValue,
                    custom_unit_type_key: '',
                    height: String(dims.height),
                    depth: String(dims.depth),
                  }, 'type')
                }}
                value={unitDraft.unit_type_key}
              >
                {unitPresets.map((unitType) => (
                  <option key={unitType} value={unitType}>
                    {unitType}
                  </option>
                ))}
                <option value={customUnitTypeValue}>Custom unit type</option>
              </Select>
            </Label>

            {unitDraft.unit_type_key === customUnitTypeValue ? (
              <Label className="grid gap-1.5">
                Custom unit type key
                <Input
                  onChange={(event) => updateUnitDraft({ custom_unit_type_key: event.target.value }, 'type')}
                  required
                  value={unitDraft.custom_unit_type_key}
                />
              </Label>
            ) : null}

            <div className="grid gap-3 md:grid-cols-3">
              <Label className="grid gap-1.5">
                Width (mm)
                <Input
                  min={1}
                  onChange={(event) => updateUnitDraft({ width: event.target.value })}
                  required
                  type="number"
                  value={unitDraft.width}
                />
              </Label>
              <Label className="grid gap-1.5">
                Height (mm)
                <Input
                  min={1}
                  onChange={(event) => updateUnitDraft({ height: event.target.value }, 'height')}
                  required
                  type="number"
                  value={unitDraft.height}
                />
              </Label>
              <Label className="grid gap-1.5">
                Depth (mm)
                <Input
                  min={1}
                  onChange={(event) => updateUnitDraft({ depth: event.target.value })}
                  required
                  type="number"
                  value={unitDraft.depth}
                />
              </Label>
            </div>

            {boards.length === 0 ? (
              <Alert className="text-xs">
                Add board materials in Libraries before saving units. Every unit needs at least a carcass board for cutlists and pricing.
              </Alert>
            ) : null}

            <div className="grid gap-3 md:grid-cols-2">
              <LibrarySelect
                label="Carcass board"
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                onChange={(value) => updateUnitDraft({ carcass_board_type_id: value })}
                required
                value={unitDraft.carcass_board_type_id}
              />
              <LibrarySelect
                label="Door board"
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                onChange={(value) => updateUnitDraft({ door_board_type_id: value })}
                value={unitDraft.door_board_type_id}
              />
            </div>

            {isDrawerUnitDraft ? (
              <div className="grid gap-2">
                <LibrarySelect
                  label="Drawer hardware"
                  options={slides.map((slide) => ({ value: slide.id, label: slideLabel(slide.id) }))}
                  onChange={(value) => updateUnitDraft({ slide_id: value })}
                  placeholder={selectedQuote?.default_slide_id ? `Quote default: ${slideLabel(selectedQuote.default_slide_id)}` : 'Quote default'}
                  value={unitDraft.slide_id}
                />
                {slideDepthError ? (
                  <Alert className="text-xs" variant="destructive">
                    {slideDepthError}
                  </Alert>
                ) : null}
              </div>
            ) : isHingedUnitDraft ? (
              <LibrarySelect
                label="Hinge"
                options={hinges.map((hinge) => ({ value: hinge.id, label: hingeLabel(hinge.id) }))}
                onChange={(value) => updateUnitDraft({ hinge_id: value })}
                placeholder={selectedQuote?.default_hinge_id ? `Quote default: ${hingeLabel(selectedQuote.default_hinge_id)}` : 'Quote default'}
                value={unitDraft.hinge_id}
              />
            ) : null}

            {isDrawerUnitDraft ? (
              <div className="grid gap-3">
                <Label className="grid gap-1.5">
                  Number of drawers
                  <Input
                    min={1}
                    onChange={(event) => updateUnitDraft({ num_drawers: event.target.value }, 'count')}
                    required
                    type="number"
                    value={unitDraft.num_drawers}
                  />
                </Label>

                <div className="grid gap-3 md:grid-cols-[minmax(130px,180px)_1fr]">
                  <div
                    aria-label="Drawer front split preview"
                    className="grid h-44 max-h-44 overflow-hidden rounded-md border border-border bg-muted/30 p-1"
                    style={{ gridTemplateRows: drawerPreviewHeights.map((height) => `${Math.max(1, height)}fr`).join(' ') }}
                  >
                    {drawerPreviewHeights.map((height, index) => (
                      <div
                        className="flex min-h-0 items-center justify-center overflow-hidden border border-border bg-background text-[10px] font-medium leading-none text-muted-foreground"
                        key={`${index}-${height}`}
                      >
                        {`${height} mm`}
                      </div>
                    ))}
                  </div>
                  <div className="grid gap-3">
                    <div className="flex flex-wrap gap-2">
                      {drawerSplitPresets.map((preset) => (
                        <Button
                          aria-pressed={unitDraft.drawer_split_mode === preset.mode}
                          key={preset.mode}
                          onClick={() => updateUnitDraft({ drawer_split_mode: preset.mode }, 'mode')}
                          size="sm"
                          type="button"
                          variant={unitDraft.drawer_split_mode === preset.mode ? 'default' : 'outline'}
                        >
                          {preset.label}
                        </Button>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">{`${drawerAvailableHeight} mm available`}</Badge>
                      {unitDraft.drawer_split_mode === 'manual' ? (
                        <>
                          <Badge variant={drawerHeightRemaining === 0 ? 'outline' : 'warning'}>
                            {`${drawerHeightRemaining} mm remaining`}
                          </Badge>
                          <Badge variant="outline">{`${drawerHeightTotal} mm total`}</Badge>
                        </>
                      ) : null}
                    </div>
                    {unitDraft.drawer_split_mode === 'manual' ? (
                      <div className="grid gap-2 sm:grid-cols-3">
                        {drawerHeightValues.map((value, index) => (
                          <Label className="grid gap-1.5" key={`drawer-face-height-${index}`}>
                            {`Drawer ${index + 1} face`}
                            <Input
                              min={1}
                              onChange={(event) =>
                                updateUnitDraft({
                                  drawer_face_heights: drawerHeightValues.map((currentValue, currentIndex) =>
                                    currentIndex === index ? event.target.value : currentValue,
                                  ),
                                })
                              }
                              required
                              type="number"
                              value={value}
                            />
                          </Label>
                        ))}
                      </div>
                    ) : null}
                    {unitDraft.drawer_split_mode === 'manual' ? (
                      <Alert
                        aria-hidden={drawerSplitError ? undefined : true}
                        className={drawerSplitError ? 'text-xs' : 'invisible text-xs'}
                        variant="destructive"
                      >
                        {drawerSplitError ?? 'Drawer split validation placeholder.'}
                      </Alert>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                <Label className="grid gap-1.5">
                  Number of doors
                  <Input
                    min={1}
                    onChange={(event) => setUnitDraft((current) => ({ ...current, num_doors: event.target.value }))}
                    required
                    type="number"
                    value={unitDraft.num_doors}
                  />
                </Label>
                <Label className="grid gap-1.5">
                  Number of shelves
                  <Input
                    min={0}
                    onChange={(event) => setUnitDraft((current) => ({ ...current, num_shelves: event.target.value }))}
                    required
                    type="number"
                    value={unitDraft.num_shelves}
                  />
                </Label>
              </div>
            )}

            {isDrawerUnitDraft && [1, 2, 3].includes(unitDraftDrawerCount) ? (
              <div className="grid gap-3 md:grid-cols-2">
                <LibrarySelect
                  label="Top J channel"
                  options={jChannelHandles.map((handle) => ({ value: handle.id, label: handleLabel(handle.id) }))}
                  onChange={(value) => updateUnitDraft({ top_j_channel_handle_id: value })}
                  value={unitDraft.top_j_channel_handle_id}
                />
                {unitDraftDrawerCount === 2 ? (
                  <LibrarySelect
                    label="Middle C channel"
                    options={cChannelHandles.map((handle) => ({ value: handle.id, label: handleLabel(handle.id) }))}
                    onChange={(value) => updateUnitDraft({ middle_c_channel_handle_id: value })}
                    value={unitDraft.middle_c_channel_handle_id}
                  />
                ) : null}
                {unitDraftDrawerCount === 3 ? (
                  <LibrarySelect
                    label="Between lower drawers C channel"
                    options={cChannelHandles.map((handle) => ({ value: handle.id, label: handleLabel(handle.id) }))}
                    onChange={(value) => updateUnitDraft({ between_lower_c_channel_handle_id: value })}
                    value={unitDraft.between_lower_c_channel_handle_id}
                  />
                ) : null}
              </div>
            ) : null}

            {isBaseDoorUnitDraft ? (
              <LibrarySelect
                label="Top J channel"
                options={jChannelHandles.map((handle) => ({ value: handle.id, label: handleLabel(handle.id) }))}
                onChange={(value) => updateUnitDraft({ base_door_top_j_channel_handle_id: value })}
                value={unitDraft.base_door_top_j_channel_handle_id}
              />
            ) : null}

            {isTallUnitDraft ? (
              <LibrarySelect
                label="Vertical channel"
                options={tallChannelHandles.map((handle) => ({ value: handle.id, label: handleLabel(handle.id) }))}
                onChange={(value) => updateUnitDraft({ tall_vertical_channel_handle_id: value })}
                value={unitDraft.tall_vertical_channel_handle_id}
              />
            ) : null}

            {showFullLengthOrientation ? (
              <Label className="grid gap-1.5">
                Full-length handle attachment
                <Select
                  onChange={(event) => updateUnitDraft({ full_length_handle_orientation: event.target.value === 'width' ? 'width' : 'length' })}
                  value={unitDraft.full_length_handle_orientation}
                >
                  <option value="length">Attach to length</option>
                  <option value="width">Attach to width</option>
                </Select>
              </Label>
            ) : null}

            <div className="flex justify-end gap-2">
              <Button onClick={() => setIsUnitModalOpen(false)} type="button" variant="outline">
                Cancel
              </Button>
              <Button disabled={isSaving} type="submit">
                {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                Save unit
              </Button>
            </div>
          </form>
        </ModalCard>
      ) : null}

      {isBulkUnitModalOpen ? (
        <ModalCard title="Bulk Unit Entry" onClose={() => setIsBulkUnitModalOpen(false)}>
          <form className="grid gap-3" onSubmit={handleBulkUnitSubmit}>
            {modalError ? <Alert variant="destructive">{modalError}</Alert> : null}
            {boards.length === 0 ? (
              <Alert className="text-xs">
                Add board materials in Libraries before saving units. Every row needs at least a carcass board for cutlists and pricing.
              </Alert>
            ) : null}

            <TableContainer>
              <Table className="min-w-[1120px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">#</TableHead>
                    <TableHead className="w-40">Type</TableHead>
                    <TableHead className="w-28">Width</TableHead>
                    <TableHead className="w-28">Height</TableHead>
                    <TableHead className="w-28">Depth</TableHead>
                    <TableHead className="w-56">Carcass</TableHead>
                    <TableHead className="w-56">Door</TableHead>
                    <TableHead className="w-32">Count</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bulkUnitRows.map((row, index) => {
                    const unitType = resolvedUnitType(row)
                    const isDrawer = unitType.toLowerCase().includes('draw')
                    return (
                      <Fragment key={row.rowKey}>
                        <TableRow>
                          <TableCell>{index + 1}</TableCell>
                          <TableCell>
                            <Select
                              aria-label={`Row ${index + 1} unit type`}
                              onChange={(event) => handleBulkUnitTypeChange(row, event.target.value)}
                              value={row.unit_type_key}
                            >
                              {unitPresets.map((unitTypeOption) => (
                                <option key={unitTypeOption} value={unitTypeOption}>
                                  {unitTypeOption}
                                </option>
                              ))}
                              <option value={customUnitTypeValue}>Custom</option>
                            </Select>
                            {row.unit_type_key === customUnitTypeValue ? (
                              <Input
                                aria-label={`Row ${index + 1} custom unit type`}
                                className="mt-2"
                                onChange={(event) => updateBulkUnitRow(row.rowKey, { custom_unit_type_key: event.target.value })}
                                value={row.custom_unit_type_key}
                              />
                            ) : null}
                          </TableCell>
                          <TableCell>
                            <Input
                              aria-label={`Row ${index + 1} width`}
                              min={1}
                              onChange={(event) => updateBulkUnitRow(row.rowKey, { width: event.target.value })}
                              required
                              type="number"
                              value={row.width}
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              aria-label={`Row ${index + 1} height`}
                              min={1}
                              onChange={(event) => updateBulkUnitRow(row.rowKey, { height: event.target.value })}
                              required
                              type="number"
                              value={row.height}
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              aria-label={`Row ${index + 1} depth`}
                              min={1}
                              onChange={(event) => updateBulkUnitRow(row.rowKey, { depth: event.target.value })}
                              required
                              type="number"
                              value={row.depth}
                            />
                          </TableCell>
                          <TableCell>
                            <Select
                              aria-label={`Row ${index + 1} carcass board`}
                              onChange={(event) => updateBulkUnitRow(row.rowKey, { carcass_board_type_id: event.target.value })}
                              required
                              value={row.carcass_board_type_id}
                            >
                              <option value="">Carcass board</option>
                              {boards.map((board) => (
                                <option key={board.id} value={board.id}>
                                  {`${board.brand} ${board.material} (${board.thickness}mm)`}
                                </option>
                              ))}
                            </Select>
                          </TableCell>
                          <TableCell>
                            <Select
                              aria-label={`Row ${index + 1} door board`}
                              onChange={(event) => updateBulkUnitRow(row.rowKey, { door_board_type_id: event.target.value })}
                              value={row.door_board_type_id}
                            >
                              <option value="">Door board</option>
                              {boards.map((board) => (
                                <option key={board.id} value={board.id}>
                                  {`${board.brand} ${board.material} (${board.thickness}mm)`}
                                </option>
                              ))}
                            </Select>
                          </TableCell>
                          <TableCell>
                            <Input
                              aria-label={isDrawer ? `Row ${index + 1} drawers` : `Row ${index + 1} doors`}
                              min={1}
                              onChange={(event) =>
                                updateBulkUnitRow(row.rowKey, isDrawer ? { num_drawers: event.target.value } : { num_doors: event.target.value })
                              }
                              required
                              type="number"
                              value={isDrawer ? row.num_drawers : row.num_doors}
                            />
                            {!isDrawer ? (
                              <Input
                                aria-label={`Row ${index + 1} shelves`}
                                className="mt-2"
                                min={0}
                                onChange={(event) => updateBulkUnitRow(row.rowKey, { num_shelves: event.target.value })}
                                required
                                type="number"
                                value={row.num_shelves}
                              />
                            ) : null}
                          </TableCell>
                        </TableRow>
                        {bulkUnitErrors[row.rowKey] ? (
                          <TableRow>
                            <TableCell colSpan={8}>
                              <Alert className="text-xs" variant="destructive">
                                {bulkUnitErrors[row.rowKey]}
                              </Alert>
                            </TableCell>
                          </TableRow>
                        ) : null}
                      </Fragment>
                    )
                  })}
                </TableBody>
              </Table>
            </TableContainer>

            <div className="flex flex-wrap justify-between gap-2">
              <Button onClick={addBulkUnitRow} type="button" variant="outline">
                <Plus className="h-4 w-4" aria-hidden="true" />
                Add row
              </Button>
              <div className="flex justify-end gap-2">
                <Button onClick={() => setIsBulkUnitModalOpen(false)} type="button" variant="outline">
                  Cancel
                </Button>
                <Button disabled={isSavingBulkUnits} type="submit">
                  {isSavingBulkUnits ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                  Save units
                </Button>
              </div>
            </div>
          </form>
        </ModalCard>
      ) : null}

      {isBulkApplyModalOpen ? (
        <ModalCard title="Bulk Apply" onClose={() => setIsBulkApplyModalOpen(false)}>
          <form className="grid gap-4" onSubmit={handleBulkApplySubmit}>
            {modalError ? <Alert variant="destructive">{modalError}</Alert> : null}
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <Badge variant="outline">{`${selectedUnitCount} ${selectedUnitCount === 1 ? 'unit' : 'units'} selected`}</Badge>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="grid gap-2">
                <Label className="flex items-center gap-2">
                  <Checkbox
                    checked={bulkApplyDraft.apply_carcass_board_type_id}
                    onChange={(event) => updateBulkApplyDraft({ apply_carcass_board_type_id: event.target.checked })}
                  />
                  Carcass board
                </Label>
                <Select
                  disabled={!bulkApplyDraft.apply_carcass_board_type_id}
                  onChange={(event) => updateBulkApplyDraft({ carcass_board_type_id: event.target.value })}
                  value={bulkApplyDraft.carcass_board_type_id}
                >
                  <option value="">Use quote default</option>
                  {boards.map((board) => (
                    <option key={board.id} value={board.id}>
                      {`${board.brand} ${board.material} (${board.thickness}mm)`}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="grid gap-2">
                <Label className="flex items-center gap-2">
                  <Checkbox
                    checked={bulkApplyDraft.apply_door_board_type_id}
                    onChange={(event) => updateBulkApplyDraft({ apply_door_board_type_id: event.target.checked })}
                  />
                  Door board
                </Label>
                <Select
                  disabled={!bulkApplyDraft.apply_door_board_type_id}
                  onChange={(event) => updateBulkApplyDraft({ door_board_type_id: event.target.value })}
                  value={bulkApplyDraft.door_board_type_id}
                >
                  <option value="">Use quote default</option>
                  {boards.map((board) => (
                    <option key={board.id} value={board.id}>
                      {`${board.brand} ${board.material} (${board.thickness}mm)`}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="grid gap-2">
                <Label className="flex items-center gap-2">
                  <Checkbox
                    checked={bulkApplyDraft.apply_handle_id}
                    onChange={(event) => updateBulkApplyDraft({ apply_handle_id: event.target.checked })}
                  />
                  Handle
                </Label>
                <Select
                  disabled={!bulkApplyDraft.apply_handle_id}
                  onChange={(event) => updateBulkApplyDraft({ handle_id: event.target.value })}
                  value={bulkApplyDraft.handle_id}
                >
                  <option value="">Use quote default</option>
                  {standardHandles.map((handle) => (
                    <option key={handle.id} value={handle.id}>
                      {handleLabel(handle.id)}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="grid gap-2">
                <Label className="flex items-center gap-2">
                  <Checkbox
                  checked={bulkApplyDraft.apply_slide_id}
                  onChange={(event) => updateBulkApplyDraft({ apply_slide_id: event.target.checked })}
                />
                  Drawer hardware
                </Label>
                <Select
                  disabled={!bulkApplyDraft.apply_slide_id}
                  onChange={(event) => updateBulkApplyDraft({ slide_id: event.target.value })}
                  value={bulkApplyDraft.slide_id}
                >
                  <option value="">Use quote default</option>
                  {slides.map((slide) => (
                    <option key={slide.id} value={slide.id}>
                      {slideLabel(slide.id)}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="grid gap-2">
                <Label className="flex items-center gap-2">
                  <Checkbox
                    checked={bulkApplyDraft.apply_hinge_id}
                    onChange={(event) => updateBulkApplyDraft({ apply_hinge_id: event.target.checked })}
                  />
                  Hinge
                </Label>
                <Select
                  disabled={!bulkApplyDraft.apply_hinge_id}
                  onChange={(event) => updateBulkApplyDraft({ hinge_id: event.target.value })}
                  value={bulkApplyDraft.hinge_id}
                >
                  <option value="">Use quote default</option>
                  {hinges.map((hinge) => (
                    <option key={hinge.id} value={hinge.id}>
                      {`${hinge.brand} ${hinge.model} (${hinge.opening_angle_deg}deg)`}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="grid gap-2">
                <Label className="flex items-center gap-2">
                  <Checkbox
                    checked={bulkApplyDraft.apply_height}
                    onChange={(event) => updateBulkApplyDraft({ apply_height: event.target.checked })}
                  />
                  Height
                </Label>
                <Input
                  disabled={!bulkApplyDraft.apply_height}
                  min={1}
                  onChange={(event) => updateBulkApplyDraft({ height: event.target.value })}
                  type="number"
                  value={bulkApplyDraft.height}
                />
              </div>

              <div className="grid gap-2">
                <Label className="flex items-center gap-2">
                  <Checkbox
                    checked={bulkApplyDraft.apply_depth}
                    onChange={(event) => updateBulkApplyDraft({ apply_depth: event.target.checked })}
                  />
                  Depth
                </Label>
                <Input
                  disabled={!bulkApplyDraft.apply_depth}
                  min={1}
                  onChange={(event) => updateBulkApplyDraft({ depth: event.target.value })}
                  type="number"
                  value={bulkApplyDraft.depth}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button onClick={() => setIsBulkApplyModalOpen(false)} type="button" variant="outline">
                Cancel
              </Button>
              <Button disabled={isSavingBulkApply} type="submit">
                {isSavingBulkApply ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                Apply changes
              </Button>
            </div>
          </form>
        </ModalCard>
      ) : null}
    </div>
  )
}
