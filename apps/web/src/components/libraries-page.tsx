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
  Percent,
  Plus,
  RefreshCcw,
  Save,
  Upload,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from 'react'

import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { ControlGroup, ControlGroupItem } from '@/components/ui/control-group'
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
import { defaultBoardDraft, defaultExtraCategoryDraft, defaultExtraDraft, defaultHandleDraft, defaultHingeDraft, defaultItemSupplierDraft, defaultPriceListDraft, defaultSlideDraft, defaultSupplierDraft, libraryTabs } from '@/components/libraries/constants'
import { amountStringToCents, bpsToPercentString, buildBoardPayload, buildExtraPayload, buildHandlePayload, buildHingePayload, buildItemSupplierPayload, buildSlidePayload, buildSupplierPayload, calculateDiscountedAmountString, centsToAmountString, formatBoardLabel, formatCurrencyFromCents, formatDateTime, formatExtraLabel, formatHandleLabel, formatHingeLabel, formatSlideLabel, itemTypeDefaultUom, percentStringToBps } from '@/components/libraries/helpers'
import { LibraryBoardsTable, LibraryExtraCategoriesTable, LibraryExtrasTable, LibraryHandlesTable, LibraryHingesTable, LibrarySlidesTable } from '@/components/libraries/tables'
import { PricingSettingsEditor } from '@/components/pricing-settings-editor'
import { defaultPricingSettingsDraft, pricingSettingsPayloadFromDraft, pricingSettingsToDraft, type PricingSettingsDraft } from '@/components/pricing-settings'
import { currencyLabel, normalizeCurrencyCode } from '@/lib/currency'
import type { BoardDraft, BoardTypeRow, ExtraCategoryDraft, ExtraCategoryRow, ExtraDraft, ExtraRow, GeneratePriceListSummary, HandleDraft, HandleRow, HingeDraft, HingeRow, ItemSupplierDraft, ItemSupplierRow, LibraryImportApplyRequest, LibraryImportApplyResult, LibraryImportApplyRowStatus, LibraryImportPreview, LibraryImportPreviewRequest, LibraryImportResource, LibraryImportRowStatus, LibraryImportSourceFormat, LibrarySetupActionTarget, LibrarySetupChecklist, LibrarySetupItemStatus, LibraryTab, PriceItemType, PriceListDraft, PriceListItemRow, PriceListRow, PricingSettingsRow, SlideDraft, SlideRow, SupplierDiscountSummary, SupplierDraft, SupplierRow } from '@/components/libraries/types'

const priceItemTypes: PriceItemType[] = ['slide', 'hinge', 'handle', 'extra', 'board']

const generationTypeOptions: Array<{ label: string; value: PriceItemType }> = [
  { label: 'Slides', value: 'slide' },
  { label: 'Hinges', value: 'hinge' },
  { label: 'Handles', value: 'handle' },
  { label: 'Extras', value: 'extra' },
  { label: 'Boards', value: 'board' },
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

const importExampleByResource: Record<LibraryImportResource, string> = {
  boards: 'Brand,Material,Thickness,Length,Width,Costing Mode\nPG Bison,MelaWood,16,2750,1830,sheet',
  slides: 'Brand,Model,Code,Length\nGrass,Dynapro,DYN-500,500',
  hinges: 'Brand,Model,Code,Opening Angle\nBlum,Clip Top,BL-110,110',
  handles: 'Name,Supplier,Code\nSlim Bar,Hafele,HB-160',
  suppliers: 'Name,Code,Contact,Email,Default Discount\nGrass ZA,GRASS-ZA,Sales,sales@example.com,30%',
  extra_categories: 'Name\nAppliances',
  extras: 'Name,Category,Supplier,Code\nStove,Appliances,Defy,DFY-600',
  supplier_item_costs: 'Item Type,Brand,Model,Code,Supplier,Order UOM,Unit Cost\nslide,Grass,Dynapro,DYN-500,Grass ZA,pairs,479.49',
  price_list_items: 'Item Type,Brand,Model,Code,Price Component,UOM,Price\nslide,Grass,Dynapro,DYN-500,unit,pairs,899.00',
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

function setupStatusLabel(status: LibrarySetupItemStatus) {
  return status.replace('_', ' ')
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
  if (status === 'skipped') return 'skip'
  return status
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

function importResourceLabel(resource: LibraryImportResource) {
  return importResourceOptions.find((option) => option.value === resource)?.label ?? resource
}

function parseColumnMapping(text: string): Record<string, string> {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .reduce<Record<string, string>>((mapping, line, index) => {
      const separatorIndex = line.includes('=') ? line.indexOf('=') : line.indexOf(':')
      if (separatorIndex <= 0) {
        throw new Error(`Column mapping line ${index + 1} needs field=Column.`)
      }
      const field = line.slice(0, separatorIndex).trim()
      const column = line.slice(separatorIndex + 1).trim()
      if (!field || !column) {
        throw new Error(`Column mapping line ${index + 1} needs both a field and column.`)
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
  authToken,
  currencyCode,
  onOpenProjects,
}: {
  authToken: string
  currencyCode: string
  onOpenProjects: () => void
}) {
  const [activeTab, setActiveTab] = useState<LibraryTab>('pricing')

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
  const [selectedPriceListId, setSelectedPriceListId] = useState('')

  const [isLoadingCatalog, setIsLoadingCatalog] = useState(true)
  const [isLoadingPricing, setIsLoadingPricing] = useState(true)
  const [isLoadingChecklist, setIsLoadingChecklist] = useState(true)
  const [isLoadingPriceItems, setIsLoadingPriceItems] = useState(false)
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
  const [slideDraft, setSlideDraft] = useState<SlideDraft>(defaultSlideDraft)
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

  const activePriceRows = useMemo(
    () => priceItems.filter((item) => item.effective_to === null),
    [priceItems],
  )

  const importSummaryItems = useMemo(() => {
    if (!importPreview) return []
    return [
      { label: 'new', status: 'create' as const, value: importPreview.summary.create_count },
      { label: 'updates', status: 'update' as const, value: importPreview.summary.update_count },
      { label: 'skips', status: 'skipped' as const, value: importPreview.summary.skipped_count },
      { label: 'duplicates', status: 'duplicate' as const, value: importPreview.summary.duplicate_count },
      { label: 'blocked', status: 'blocked' as const, value: importPreview.summary.blocked_count },
    ]
  }, [importPreview])

  const visibleImportRows = useMemo(() => importPreview?.rows.slice(0, 50) ?? [], [importPreview])

  const importApplySummaryItems = useMemo(() => {
    if (!importApplyResult) return []
    return [
      { label: 'created', status: 'created' as const, value: importApplyResult.summary.created_count },
      { label: 'updated', status: 'updated' as const, value: importApplyResult.summary.updated_count },
      { label: 'skipped', status: 'skipped' as const, value: importApplyResult.summary.skipped_count },
      { label: 'failed', status: 'failed' as const, value: importApplyResult.summary.failed_count },
    ]
  }, [importApplyResult])

  const visibleImportApplyRows = useMemo(() => importApplyResult?.rows.slice(0, 50) ?? [], [importApplyResult])

  const itemLabelByRef = useMemo(() => {
    const labels = new Map<string, string>()
    for (const row of boards) labels.set(`board:${row.id}`, formatBoardLabel(row))
    for (const row of slides) labels.set(`slide:${row.id}`, formatSlideLabel(row))
    for (const row of hinges) labels.set(`hinge:${row.id}`, formatHingeLabel(row))
    for (const row of handles) labels.set(`handle:${row.id}`, formatHandleLabel(row))
    for (const row of extras) labels.set(`extra:${row.id}`, formatExtraLabel(row))
    return labels
  }, [boards, extras, handles, hinges, slides])

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
        const rows = await apiRequest<PriceListItemRow[]>(`/api/v1/libraries/price-lists/${priceListId}/items`, {
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
        await refreshPriceItems(activeListId)
      } else {
        setPriceItems([])
      }
    } catch (error) {
      setPricingError(error instanceof Error ? error.message : 'Could not load pricing settings.')
      setPriceItems([])
    } finally {
      setIsLoadingPricing(false)
    }
  }, [authToken, refreshPriceItems])

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
      setPricingItemRefId(pricingItemOptions[0]?.id ?? '')
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
        order_uom: current.item_type === 'slide' ? 'pairs' : current.item_type === 'board' ? 'sheet' : 'pcs',
        price_component: current.item_type === 'board' ? 'sheet' : 'unit',
      }))
    }, 0)

    return () => window.clearTimeout(handle)
  }, [supplierItemOptions])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setSupplierDiscountPercent(bpsToPercentString(selectedDiscountSupplier?.default_discount_bps ?? 0))
    }, 0)

    return () => window.clearTimeout(handle)
  }, [selectedDiscountSupplier])

  const lookupPriceCents = useCallback(
    (itemType: PriceItemType, itemRefId: string, priceComponent: string) => {
      const canonicalKey = `${itemType}::${itemRefId}`
      const row = activePriceRows.find(
        (item) =>
          item.item_type === itemType &&
          item.price_component === priceComponent &&
          (item.item_ref_id === itemRefId || item.item_key === canonicalKey),
      )
      return row?.unit_price_cents ?? 0
    },
    [activePriceRows],
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
      await refreshPriceItems(created.id)
    }, 'Price list created.')
  }

  async function handleSelectPriceList(nextPriceListId: string) {
    setSelectedPriceListId(nextPriceListId)
    if (nextPriceListId) {
      await refreshPriceItems(nextPriceListId)
    } else {
      setPriceItems([])
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
            throw new Error('SQM price must be a valid number.')
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

      await refreshPriceItems(selectedPriceListId)
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

  async function createSlide(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildSlidePayload(slideDraft)
    if (!payload) {
      setActionError('Slide values are invalid.')
      return
    }

    await withActionState(async () => {
      await apiRequest('/api/v1/libraries/slides', { body: payload, method: 'POST', token: authToken })
      setSlideDraft(defaultSlideDraft)
      await refreshCatalog()
    }, 'Slide added.')
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
    }, 'Supplier cost saved.')
  }

  async function deleteItemSupplier(itemId: string) {
    await withActionState(async () => {
      await apiRequest(`/api/v1/libraries/item-suppliers/${itemId}`, { method: 'DELETE', token: authToken })
      await refreshCatalog()
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
          },
          method: 'POST',
          token: authToken,
        },
      )
      setLastGenerationSummary(summary)
      await refreshPriceItems(selectedPriceListId)
    }, 'Price list generated from supplier costs.')
  }

  function toggleGenerationItemType(itemType: PriceItemType, checked: boolean) {
    setGenerationItemTypes((current) => {
      if (checked) return current.includes(itemType) ? current : [...current, itemType]
      return current.filter((value) => value !== itemType)
    })
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

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Libraries and Pricing</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Manage inventory libraries and pricing in one place for your whole team.
            </p>
          </div>
          <Button
            disabled={isLoading || isLoadingChecklist || isSaving}
            onClick={() => {
              void refreshSetupChecklist()
              void refreshCatalog()
              void refreshPricing()
            }}
            variant="outline"
          >
            {isLoading || isLoadingChecklist ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RefreshCcw className="h-4 w-4" aria-hidden="true" />}
            Refresh
          </Button>
        </CardHeader>
        <CardContent className="grid gap-3">
          <ControlGroup className="flex-wrap" role="tablist" aria-label="Libraries tabs">
            {libraryTabs.map((tab) => (
              <ControlGroupItem
                aria-pressed={activeTab === tab.value}
                key={tab.value}
                onClick={() => setActiveTab(tab.value)}
              >
                {tab.label}
              </ControlGroupItem>
            ))}
          </ControlGroup>

          {catalogError ? <Alert variant="destructive">{catalogError}</Alert> : null}
          {pricingError ? <Alert variant="destructive">{pricingError}</Alert> : null}
          {checklistError ? <Alert variant="destructive">{checklistError}</Alert> : null}
          {actionError ? <Alert variant="destructive">{actionError}</Alert> : null}
          {actionSuccess ? <Alert>{actionSuccess}</Alert> : null}
        </CardContent>
      </Card>

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
        <CardContent>
          {isLoadingChecklist ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
              Loading setup checklist.
            </div>
          ) : setupChecklist ? (
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
          ) : (
            <Alert variant="warning">The setup checklist is not available right now.</Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />
              Import Preview
            </CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Check library rows before the import is applied.
            </p>
          </div>
          <Badge variant="outline">preview first</Badge>
        </CardHeader>
        <CardContent className="grid gap-4">
          {importError ? <Alert variant="destructive">{importError}</Alert> : null}
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
                disabled={!importPreview || isPreviewingImport || isApplyingImport || (importSourceFormat === 'xlsx' && !importFilename)}
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
                      <TableHead>Identity</TableHead>
                      <TableHead>Preview</TableHead>
                      <TableHead>Messages</TableHead>
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
                            <Badge variant={importStatusBadgeVariant(row.status)}>{importStatusLabel(row.status)}</Badge>
                          </TableCell>
                          <TableCell className="max-w-64 break-all text-xs">{row.identity || '-'}</TableCell>
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
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">Batch {importApplyResult.batch_id}</Badge>
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
                      <TableHead>Target</TableHead>
                      <TableHead>Messages</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleImportApplyRows.map((row) => (
                      <TableRow key={`${row.row_number}-${row.status}-${row.target_id}`}>
                        <TableCell>{row.row_number}</TableCell>
                        <TableCell>
                          <Badge variant={importApplyStatusBadgeVariant(row.status)}>{row.status}</Badge>
                        </TableCell>
                        <TableCell className="max-w-64 break-all text-xs">{row.target_id || row.identity || '-'}</TableCell>
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

          <section className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Price Lists</CardTitle>
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
                        {row.name} ({row.status})
                      </option>
                    ))}
                  </Select>
                </Label>
                {selectedPriceList ? (
                  <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                    <Badge variant={selectedPriceList.status === 'active' ? 'default' : 'outline'}>{selectedPriceList.status}</Badge>
                    <span>{selectedPriceList.name}</span>
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
                  <Label className="grid gap-1.5">
                    Source selection
                    <Select
                      value={generationMode}
                      onChange={(event) => setGenerationMode(event.target.value as GeneratePriceListSummary['selection_mode'])}
                    >
                      <option value="preferred_then_cheapest">preferred, then cheapest</option>
                      <option value="preferred_only">preferred only</option>
                      <option value="cheapest">cheapest active</option>
                    </Select>
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
                    Preserve manual overrides
                  </Label>
                  <Button disabled={isSaving || isLoadingPriceItems || !selectedPriceListId} type="submit" variant="outline">
                    <RefreshCcw className="h-4 w-4" aria-hidden="true" />
                    Generate
                  </Button>
                  {lastGenerationSummary ? (
                    <p className="text-xs text-muted-foreground">
                      Created {lastGenerationSummary.created_count}, updated {lastGenerationSummary.updated_count}, unchanged {lastGenerationSummary.unchanged_count}, skipped {lastGenerationSummary.skipped_override_count}.
                    </p>
                  ) : null}
                </form>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Quick Price Update</CardTitle>
              </CardHeader>
              <CardContent>
                <form className="grid gap-3" onSubmit={handleSaveQuickPrice}>
                  <Label className="grid gap-1.5">
                    Item type
                    <Select
                      value={pricingItemType}
                      onChange={(event) => setPricingItemType(event.target.value as PriceItemType)}
                    >
                      <option value="slide">slide</option>
                      <option value="hinge">hinge</option>
                      <option value="handle">handle</option>
                      <option value="extra">extra</option>
                      <option value="board">board</option>
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
                      SQM price ({displayCurrencyCode})
                      <Input value={sqmPriceAmount} onChange={(event) => setSqmPriceAmount(event.target.value)} />
                    </Label>
                  ) : null}

                  {pricingItemType !== 'board' ? (
                    <Label className="grid gap-1.5">
                      Cost price ({displayCurrencyCode})
                      <Input value={unitPriceAmount} onChange={(event) => setUnitPriceAmount(event.target.value)} />
                    </Label>
                  ) : null}

                  {pricingItemOptions.length === 0 ? (
                    <Alert className="text-xs">
                      Add at least one {pricingItemType} in the library before saving prices for this item type.
                    </Alert>
                  ) : null}

                  <Button disabled={isSaving || isLoadingPriceItems} type="submit">
                    <Save className="h-4 w-4" aria-hidden="true" />
                    Save Price
                  </Button>
                </form>
              </CardContent>
            </Card>
          </section>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Current Active Prices</CardTitle>
            </CardHeader>
            <CardContent>
              <TableContainer>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Type</TableHead>
                      <TableHead>Item</TableHead>
                      <TableHead>Component</TableHead>
                      <TableHead>UOM</TableHead>
                      <TableHead>Source</TableHead>
                      <TableHead>Price</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {activePriceRows.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6}>
                          <div className="grid gap-1 py-3">
                            <p className="font-medium">Build prices for the active list.</p>
                            <p className="text-sm leading-5 text-muted-foreground">
                              Add board, hardware, handle, and extra prices here so quote totals can be trusted.
                            </p>
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : (
                      activePriceRows.map((row) => (
                        <TableRow key={row.id}>
                          <TableCell>{row.item_type}</TableCell>
                          <TableCell>
                            {row.item_ref_id
                              ? itemLabelByRef.get(`${row.item_type}:${row.item_ref_id}`) ?? row.item_key
                              : row.item_key}
                          </TableCell>
                          <TableCell>{row.price_component}</TableCell>
                          <TableCell>{row.uom}</TableCell>
                          <TableCell>
                            <Badge variant={row.cost_source === 'supplier' ? 'default' : 'outline'}>{row.cost_source}</Badge>
                          </TableCell>
                          <TableCell>{formatCurrencyFromCents(row.unit_price_cents, displayCurrencyCode)}</TableCell>
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

      {!isLoading && activeTab === 'boards' ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Add Board</CardTitle>
            </CardHeader>
            <CardContent>
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
                <div className="md:col-span-3">
                  <Button disabled={isSaving} type="submit">
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    Add Board
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <LibraryBoardsTable
            boards={boards}
            editingBoard={editingBoard}
            isSaving={isSaving}
            onDelete={deleteBoard}
            onEdit={setEditingBoard}
            onEditChange={setEditingBoard}
            onUpdate={updateBoard}
          />
        </>
      ) : null}

      {!isLoading && activeTab === 'slides' ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Add Slide</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-4" onSubmit={createSlide}>
                <Label className="grid gap-1.5">
                  Brand
                  <Input value={slideDraft.brand} onChange={(event) => setSlideDraft((current) => ({ ...current, brand: event.target.value }))} />
                </Label>
                <Label className="grid gap-1.5">
                  Model
                  <Input value={slideDraft.model} onChange={(event) => setSlideDraft((current) => ({ ...current, model: event.target.value }))} />
                </Label>
                <Label className="grid gap-1.5">
                  Code
                  <Input value={slideDraft.code} onChange={(event) => setSlideDraft((current) => ({ ...current, code: event.target.value }))} />
                </Label>
                <Label className="grid gap-1.5">
                  Length
                  <Input value={slideDraft.length} onChange={(event) => setSlideDraft((current) => ({ ...current, length: event.target.value }))} />
                </Label>
                <Label className="grid gap-1.5">
                  Side length
                  <Input value={slideDraft.side_length} onChange={(event) => setSlideDraft((current) => ({ ...current, side_length: event.target.value }))} />
                </Label>
                <Label className="grid gap-1.5">
                  Clearance total
                  <Input value={slideDraft.side_clearance_total} onChange={(event) => setSlideDraft((current) => ({ ...current, side_clearance_total: event.target.value }))} />
                </Label>
                <Label className="grid gap-1.5">
                  Side uplift
                  <Input value={slideDraft.side_height_uplift} onChange={(event) => setSlideDraft((current) => ({ ...current, side_height_uplift: event.target.value }))} />
                </Label>
                <div className="md:col-span-4">
                  <Button disabled={isSaving} type="submit">
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    Add Slide
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <LibrarySlidesTable
            editingSlide={editingSlide}
            isSaving={isSaving}
            onDelete={deleteSlide}
            onEdit={setEditingSlide}
            onEditChange={setEditingSlide}
            onUpdate={updateSlide}
            slides={slides}
          />
        </>
      ) : null}

      {!isLoading && activeTab === 'hinges' ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Add Hinge</CardTitle>
            </CardHeader>
            <CardContent>
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
                <div className="md:col-span-4">
                  <Button disabled={isSaving} type="submit">
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    Add Hinge
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <LibraryHingesTable
            editingHinge={editingHinge}
            hinges={hinges}
            isSaving={isSaving}
            onDelete={deleteHinge}
            onEdit={setEditingHinge}
            onEditChange={setEditingHinge}
            onUpdate={updateHinge}
          />
        </>
      ) : null}

      {!isLoading && activeTab === 'suppliers' ? (
        <>
          <section className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Add Supplier</CardTitle>
              </CardHeader>
              <CardContent>
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
                  <div className="md:col-span-2">
                    <Button disabled={isSaving} type="submit">
                      <Plus className="h-4 w-4" aria-hidden="true" />
                      Add Supplier
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

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
                      <Input value={itemSupplierDraft.price_component} onChange={(event) => setItemSupplierDraft((current) => ({ ...current, price_component: event.target.value }))} />
                    </Label>
                    <Label className="grid gap-1.5">
                      Order UOM
                      <Input value={itemSupplierDraft.order_uom} onChange={(event) => setItemSupplierDraft((current) => ({ ...current, order_uom: event.target.value }))} />
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

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Suppliers</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <TableContainer>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Code</TableHead>
                      <TableHead>Contact</TableHead>
                      <TableHead>Discount</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {suppliers.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5}>
                          <div className="grid gap-1 py-3">
                            <p className="font-medium">Add your main board or hardware supplier.</p>
                            <p className="text-sm leading-5 text-muted-foreground">
                              Supplier records keep contact details, default discounts, and cost sources together.
                            </p>
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : (
                      suppliers.map((row) => (
                        <TableRow key={row.id}>
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

              {editingSupplier ? (
                <form className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:grid-cols-3" onSubmit={updateSupplier}>
                  <p className="md:col-span-3 text-sm font-medium">Edit supplier</p>
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
                  <div className="md:col-span-3 flex gap-2">
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
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Supplier Sources</CardTitle>
            </CardHeader>
            <CardContent>
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
                    {itemSuppliers.length === 0 ? (
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
                      itemSuppliers.map((row) => (
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
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Add Handle</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-4" onSubmit={createHandle}>
                <Label className="grid gap-1.5">
                  Name
                  <Input value={handleDraft.name} onChange={(event) => setHandleDraft((current) => ({ ...current, name: event.target.value }))} />
                </Label>
                <Label className="grid gap-1.5">
                  Supplier
                  <Input value={handleDraft.supplier} onChange={(event) => setHandleDraft((current) => ({ ...current, supplier: event.target.value }))} />
                </Label>
                <Label className="grid gap-1.5">
                  Code
                  <Input value={handleDraft.code} onChange={(event) => setHandleDraft((current) => ({ ...current, code: event.target.value }))} />
                </Label>
                <div className="md:col-span-4">
                  <Button disabled={isSaving} type="submit">
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    Add Handle
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <LibraryHandlesTable
            editingHandle={editingHandle}
            handles={handles}
            isSaving={isSaving}
            onDelete={deleteHandle}
            onEdit={setEditingHandle}
            onEditChange={setEditingHandle}
            onUpdate={updateHandle}
          />
        </>
      ) : null}

      {!isLoading && activeTab === 'extra-categories' ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Add Extra Category</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end" onSubmit={createExtraCategory}>
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
              </form>
            </CardContent>
          </Card>

          <LibraryExtraCategoriesTable
            categories={extraCategories}
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
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Add Extra</CardTitle>
            </CardHeader>
            <CardContent>
              {extraCategories.length === 0 ? (
                <Alert variant="destructive">Create at least one extra category before adding extras.</Alert>
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
                    <Input value={extraDraft.supplier} onChange={(event) => setExtraDraft((current) => ({ ...current, supplier: event.target.value }))} />
                  </Label>
                  <Label className="grid gap-1.5">
                    Code
                    <Input value={extraDraft.code} onChange={(event) => setExtraDraft((current) => ({ ...current, code: event.target.value }))} />
                  </Label>
                  <Label className="grid gap-1.5 md:col-span-2">
                    Notes
                    <Textarea value={extraDraft.notes} onChange={(event) => setExtraDraft((current) => ({ ...current, notes: event.target.value }))} />
                  </Label>
                  <div className="md:col-span-2">
                    <Button disabled={isSaving} type="submit">
                      <Plus className="h-4 w-4" aria-hidden="true" />
                      Add Extra
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>

          <LibraryExtrasTable
            categories={extraCategories}
            editingExtra={editingExtra}
            extras={extras}
            isSaving={isSaving}
            onDelete={deleteExtra}
            onEdit={setEditingExtra}
            onEditChange={setEditingExtra}
            onUpdate={updateExtra}
          />
        </>
      ) : null}
    </div>
  )
}
