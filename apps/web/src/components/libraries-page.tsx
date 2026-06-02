import {
  CircleDollarSign,
  LoaderCircle,
  Plus,
  RefreshCcw,
  Save,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'

import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { defaultBoardDraft, defaultExtraCategoryDraft, defaultExtraDraft, defaultHandleDraft, defaultHingeDraft, defaultPriceListDraft, defaultSlideDraft, libraryTabs } from '@/components/libraries/constants'
import { amountStringToCents, bpsToPercentString, buildBoardPayload, buildExtraPayload, buildHandlePayload, buildHingePayload, buildSlidePayload, centsToAmountString, formatBoardLabel, formatCurrencyFromCents, formatDateTime, formatExtraLabel, formatHandleLabel, formatHingeLabel, formatSlideLabel, itemTypeDefaultUom, percentStringToBps } from '@/components/libraries/helpers'
import { LibraryBoardsTable, LibraryExtraCategoriesTable, LibraryExtrasTable, LibraryHandlesTable, LibraryHingesTable, LibrarySlidesTable } from '@/components/libraries/tables'
import { currencyLabel, normalizeCurrencyCode } from '@/lib/currency'
import type { BoardDraft, BoardTypeRow, ExtraCategoryDraft, ExtraCategoryRow, ExtraDraft, ExtraRow, HandleDraft, HandleRow, HingeDraft, HingeRow, LibraryTab, PriceItemType, PriceListDraft, PriceListItemRow, PriceListRow, PricingSettingsRow, SlideDraft, SlideRow } from '@/components/libraries/types'

export function LibrariesPage({ authToken, currencyCode }: { authToken: string; currencyCode: string }) {
  const [activeTab, setActiveTab] = useState<LibraryTab>('pricing')

  const [boards, setBoards] = useState<BoardTypeRow[]>([])
  const [slides, setSlides] = useState<SlideRow[]>([])
  const [hinges, setHinges] = useState<HingeRow[]>([])
  const [handles, setHandles] = useState<HandleRow[]>([])
  const [extraCategories, setExtraCategories] = useState<ExtraCategoryRow[]>([])
  const [extras, setExtras] = useState<ExtraRow[]>([])

  const [pricingSettings, setPricingSettings] = useState<PricingSettingsRow | null>(null)
  const [priceLists, setPriceLists] = useState<PriceListRow[]>([])
  const [priceItems, setPriceItems] = useState<PriceListItemRow[]>([])
  const [selectedPriceListId, setSelectedPriceListId] = useState('')

  const [isLoadingCatalog, setIsLoadingCatalog] = useState(true)
  const [isLoadingPricing, setIsLoadingPricing] = useState(true)
  const [isLoadingPriceItems, setIsLoadingPriceItems] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [pricingError, setPricingError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  const [boardDraft, setBoardDraft] = useState<BoardDraft>(defaultBoardDraft)
  const [slideDraft, setSlideDraft] = useState<SlideDraft>(defaultSlideDraft)
  const [hingeDraft, setHingeDraft] = useState<HingeDraft>(defaultHingeDraft)
  const [handleDraft, setHandleDraft] = useState<HandleDraft>(defaultHandleDraft)
  const [extraCategoryDraft, setExtraCategoryDraft] = useState<ExtraCategoryDraft>(defaultExtraCategoryDraft)
  const [extraDraft, setExtraDraft] = useState<ExtraDraft>(defaultExtraDraft)

  const [editingBoard, setEditingBoard] = useState<BoardTypeRow | null>(null)
  const [editingSlide, setEditingSlide] = useState<SlideRow | null>(null)
  const [editingHinge, setEditingHinge] = useState<HingeRow | null>(null)
  const [editingHandle, setEditingHandle] = useState<HandleRow | null>(null)
  const [editingExtraCategory, setEditingExtraCategory] = useState<ExtraCategoryRow | null>(null)
  const [editingExtra, setEditingExtra] = useState<ExtraRow | null>(null)

  const [vatPercent, setVatPercent] = useState('15.00')
  const [defaultMarkupPercent, setDefaultMarkupPercent] = useState('25.00')
  const [priceListDraft, setPriceListDraft] = useState<PriceListDraft>(defaultPriceListDraft)

  const [pricingItemType, setPricingItemType] = useState<PriceItemType>('slide')
  const [pricingItemRefId, setPricingItemRefId] = useState('')
  const [unitPriceAmount, setUnitPriceAmount] = useState('0.00')
  const [sheetPriceAmount, setSheetPriceAmount] = useState('0.00')
  const [edgingPriceAmount, setEdgingPriceAmount] = useState('0.00')
  const [labourPriceAmount, setLabourPriceAmount] = useState('0.00')
  const [sqmPriceAmount, setSqmPriceAmount] = useState('0.00')
  const displayCurrencyCode = normalizeCurrencyCode(currencyCode)

  const selectedPriceList = useMemo(
    () => priceLists.find((item) => item.id === selectedPriceListId) ?? null,
    [priceLists, selectedPriceListId],
  )

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

  const activePriceRows = useMemo(
    () => priceItems.filter((item) => item.effective_to === null),
    [priceItems],
  )

  const itemLabelByRef = useMemo(() => {
    const labels = new Map<string, string>()
    for (const row of boards) labels.set(`board:${row.id}`, formatBoardLabel(row))
    for (const row of slides) labels.set(`slide:${row.id}`, formatSlideLabel(row))
    for (const row of hinges) labels.set(`hinge:${row.id}`, formatHingeLabel(row))
    for (const row of handles) labels.set(`handle:${row.id}`, formatHandleLabel(row))
    for (const row of extras) labels.set(`extra:${row.id}`, formatExtraLabel(row))
    return labels
  }, [boards, extras, handles, hinges, slides])

  const refreshCatalog = useCallback(async () => {
    setIsLoadingCatalog(true)
    setCatalogError(null)

    try {
      const [nextBoards, nextSlides, nextHinges, nextHandles, nextCategories, nextExtras] = await Promise.all([
        apiRequest<BoardTypeRow[]>('/api/v1/libraries/boards', { token: authToken }),
        apiRequest<SlideRow[]>('/api/v1/libraries/slides', { token: authToken }),
        apiRequest<HingeRow[]>('/api/v1/libraries/hinges', { token: authToken }),
        apiRequest<HandleRow[]>('/api/v1/libraries/handles', { token: authToken }),
        apiRequest<ExtraCategoryRow[]>('/api/v1/libraries/extra-categories', { token: authToken }),
        apiRequest<ExtraRow[]>('/api/v1/libraries/extras', { token: authToken }),
      ])

      setBoards(nextBoards)
      setSlides(nextSlides)
      setHinges(nextHinges)
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
      setVatPercent(bpsToPercentString(settings.vat_rate_bps))
      setDefaultMarkupPercent(bpsToPercentString(settings.default_markup_bps))
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
      void refreshCatalog()
      void refreshPricing()
    }, 0)

    return () => window.clearTimeout(handle)
  }, [refreshCatalog, refreshPricing])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setPricingItemRefId(pricingItemOptions[0]?.id ?? '')
    }, 0)

    return () => window.clearTimeout(handle)
  }, [pricingItemOptions])

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

  async function withActionState(action: () => Promise<void>, successMessage: string) {
    setIsSaving(true)
    setActionError(null)
    setActionSuccess(null)
    try {
      await action()
      setActionSuccess(successMessage)
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Action failed.')
    } finally {
      setIsSaving(false)
    }
  }

  async function handleSavePricingSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const vatBps = percentStringToBps(vatPercent)
    const markupBps = percentStringToBps(defaultMarkupPercent)
    if (vatBps === null || markupBps === null) {
      setActionError('VAT and markup must be valid positive percentages.')
      return
    }

    await withActionState(async () => {
      const updated = await apiRequest<PricingSettingsRow>('/api/v1/libraries/pricing-settings', {
        body: {
          vat_rate_bps: vatBps,
          default_markup_bps: markupBps,
        },
        method: 'PATCH',
        token: authToken,
      })
      setPricingSettings(updated)
      setVatPercent(bpsToPercentString(updated.vat_rate_bps))
      setDefaultMarkupPercent(bpsToPercentString(updated.default_markup_bps))
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
            disabled={isLoading || isSaving}
            onClick={() => {
              void refreshCatalog()
              void refreshPricing()
            }}
            variant="outline"
          >
            {isLoading ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RefreshCcw className="h-4 w-4" aria-hidden="true" />}
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
          {actionError ? <Alert variant="destructive">{actionError}</Alert> : null}
          {actionSuccess ? <Alert>{actionSuccess}</Alert> : null}
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
              <form className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end" onSubmit={handleSavePricingSettings}>
                <Label className="grid gap-1.5">
                  VAT (%)
                  <Input value={vatPercent} onChange={(event) => setVatPercent(event.target.value)} />
                </Label>
                <Label className="grid gap-1.5">
                  Default markup (%)
                  <Input value={defaultMarkupPercent} onChange={(event) => setDefaultMarkupPercent(event.target.value)} />
                </Label>
                <Button disabled={isSaving} type="submit">
                  <Save className="h-4 w-4" aria-hidden="true" />
                  Save
                </Button>
              </form>
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
                      <TableHead>Price</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {activePriceRows.length === 0 ? (
                      <TableRow>
                        <TableCell className="text-muted-foreground" colSpan={5}>
                          No active prices found for this price list.
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
