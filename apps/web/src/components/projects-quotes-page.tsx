import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Copy,
  GitBranch,
  LoaderCircle,
  Pencil,
  Plus,
  Trash2,
  XCircle,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'

import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { apiRequest } from '@/components/projects-quotes/api'
import { customUnitTypeValue, defaultProjectDraft, defaultQuoteDraft, defaultUnitDraft, fallbackUnitDefaults, quoteStatusLabels, quoteStatusOptions, unitPresets } from '@/components/projects-quotes/constants'
import { QuotePanelsEditor } from '@/components/projects-quotes/quote-panels-editor'
import { CutlistSection, LibrarySelect, ModalCard, QuoteDefaultDimensionGrid } from '@/components/projects-quotes/shared-ui'
import { countPanelFamilies, formatCents, formatExtraParams, formatPercentFromBps, normalizeQuoteCustomPanelsState, numberFromExtra, previousQuoteRevisionLabel, quotePayloadFromDraft, quoteRevisionLabel, quoteStatusBadgeVariant, resolveDefaultDims, resolvedUnitType, toQuoteDraft, unitPayloadFromDraft } from '@/components/projects-quotes/helpers'
import { PricingSettingsEditor } from '@/components/pricing-settings-editor'
import { defaultPricingSettingsDraft, pricingSettingsPayloadFromDraft, pricingSettingsToDraft, type PricingSettingsDraft, type ProjectPricingSettingsRow, type QuotePricingSettingsRow } from '@/components/pricing-settings'
import type { BoardRow, CuttingListViewTab, ExtraRow, HandleRow, HingeRow, PricingWorkspaceTab, ProjectDraft, ProjectPricingSummary, ProjectRow, ProjectWorkspaceTab, QuoteCuttingList, QuoteCustomPanelComputedRow, QuoteCustomPanelsState, QuoteCustomPanelsResponse, QuoteDraft, QuoteExtrasResponse, QuoteReadiness, QuoteReadinessCheck, QuoteReadinessSeverity, QuoteRow, QuoteStatus, QuoteWorkspaceTab, SlideRow, UnitDraft, UnitPresetKey, UnitRow } from '@/components/projects-quotes/types'

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

export function ProjectsQuotesPage({ authToken, currencyCode }: { authToken: string; currencyCode: string }) {
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

  const [projectDraft, setProjectDraft] = useState<ProjectDraft>(defaultProjectDraft)
  const [quoteDraft, setQuoteDraft] = useState<QuoteDraft>(defaultQuoteDraft)
  const [unitDraft, setUnitDraft] = useState<UnitDraft>(defaultUnitDraft)
  const [projectPricingSettingsDraft, setProjectPricingSettingsDraft] = useState<PricingSettingsDraft>(defaultPricingSettingsDraft)
  const [quotePricingSettingsDraft, setQuotePricingSettingsDraft] = useState<PricingSettingsDraft>(defaultPricingSettingsDraft)

  const [projectEditId, setProjectEditId] = useState<string | null>(null)
  const [quoteEditId, setQuoteEditId] = useState<string | null>(null)
  const [unitEditId, setUnitEditId] = useState<string | null>(null)

  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false)
  const [isQuoteModalOpen, setIsQuoteModalOpen] = useState(false)
  const [isUnitModalOpen, setIsUnitModalOpen] = useState(false)

  const [isLoadingProjects, setIsLoadingProjects] = useState(true)
  const [isLoadingQuotes, setIsLoadingQuotes] = useState(false)
  const [isLoadingUnits, setIsLoadingUnits] = useState(false)
  const [isLoadingCuttingList, setIsLoadingCuttingList] = useState(false)
  const [isLoadingQuoteReadiness, setIsLoadingQuoteReadiness] = useState(false)
  const [isLoadingQuoteExtras, setIsLoadingQuoteExtras] = useState(false)
  const [isLoadingQuoteCustomPanels, setIsLoadingQuoteCustomPanels] = useState(false)
  const [isLoadingProjectPricing, setIsLoadingProjectPricing] = useState(false)
  const [isLoadingProjectPricingSettings, setIsLoadingProjectPricingSettings] = useState(false)
  const [isLoadingQuotePricingSettings, setIsLoadingQuotePricingSettings] = useState(false)
  const [isLoadingLibraries, setIsLoadingLibraries] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isSavingQuoteStatus, setIsSavingQuoteStatus] = useState(false)
  const [isCreatingQuoteRevision, setIsCreatingQuoteRevision] = useState(false)
  const [isSavingQuoteExtras, setIsSavingQuoteExtras] = useState(false)
  const [isSavingQuoteCustomPanels, setIsSavingQuoteCustomPanels] = useState(false)
  const [isSavingProjectPricingSettings, setIsSavingProjectPricingSettings] = useState(false)
  const [isSavingQuotePricingSettings, setIsSavingQuotePricingSettings] = useState(false)
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

  const isDrawerUnitDraft = resolvedUnitType(unitDraft).toLowerCase().includes('draw')
  const cutlistRowCount = quoteCuttingList
    ? quoteCuttingList.carcass.length +
      quoteCuttingList.panels.length +
      quoteCuttingList.hardware.length +
      quoteCuttingList.extras.length
    : 0
  const panelFamilyCounts = useMemo(() => countPanelFamilies(units), [units])

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
    if (check.action_target === 'pricing') {
      openQuotePricingTab()
      return
    }
    openQuoteCuttingListTab()
    if (selectedProjectId) {
      void loadProjectPricing(selectedProjectId)
    }
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

  function openCopyQuoteModal(quote: QuoteRow) {
    setQuoteEditId(null)
    setModalError(null)
    const sourceDraft = toQuoteDraft(quote)
    const hasCopyLabel = /\bcopy\b/i.test(sourceDraft.name)
    setQuoteDraft({
      ...sourceDraft,
      name: hasCopyLabel ? sourceDraft.name : `${sourceDraft.name} (Copy)`,
    })
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
    setUnitDraft({
      ...base,
      height: String(dims.height),
      depth: String(dims.depth),
      carcass_board_type_id: selectedQuote.default_carcass_board_type_id ?? '',
      door_board_type_id: selectedQuote.default_door_board_type_id ?? '',
    })
    setIsUnitModalOpen(true)
  }

  function openEditUnitModal(unit: UnitRow) {
    const unitTypeIsPreset = unitPresets.includes(unit.unit_type_key as UnitPresetKey)
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
      num_drawers: String(numberFromExtra(unit.extra_params, 'num_drawers', 3)),
      num_doors: String(numberFromExtra(unit.extra_params, 'num_doors', 2)),
      num_shelves: String(numberFromExtra(unit.extra_params, 'num_shelves', 1)),
    })
    setIsUnitModalOpen(true)
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
      await loadUnits(selectedQuoteId)
      await loadQuoteReadiness(selectedQuoteId)
      if (activeQuoteTab === 'cutting-lists') {
        await loadQuoteCuttingList(selectedQuoteId)
      }
      if (selectedProjectId) {
        await loadQuotes(selectedProjectId)
        if (activeQuoteTab === 'pricing') {
          await loadProjectPricing(selectedProjectId)
        }
      }
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : 'Could not save unit.'
      setError(message)
      setModalError(message)
    } finally {
      setIsSaving(false)
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
      await loadUnits(selectedQuoteId)
      await loadQuoteReadiness(selectedQuoteId)
      if (activeQuoteTab === 'cutting-lists') {
        await loadQuoteCuttingList(selectedQuoteId)
      }
      if (selectedProjectId) {
        await loadQuotes(selectedProjectId)
        if (activeQuoteTab === 'pricing') {
          await loadProjectPricing(selectedProjectId)
        }
      }
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Could not delete unit.')
    }
  }

  return (
    <div className="grid gap-4">
      {currentView === 'projects' ? (
        <Card>
          <CardHeader className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <CardTitle>Projects</CardTitle>
              <Button onClick={openCreateProjectModal} size="sm" type="button">
                <Plus className="h-4 w-4" aria-hidden="true" />
                New
              </Button>
            </div>
            <div className="flex gap-2">
              <Input
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search projects"
                value={search}
              />
              <Button onClick={() => void loadProjects(search)} type="button" variant="outline">
                Find
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
                  className="rounded-[var(--card-radius)] border border-border bg-card p-3 transition hover:border-primary/50"
                  key={project.id}
                  onClick={() => openProjectWorkspace(project.id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      openProjectWorkspace(project.id)
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">{project.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{project.client || 'No client'}</p>
                    </div>
                    <Badge variant="outline">{project.quote_count} quotes</Badge>
                  </div>
                  <p className="mt-2 truncate text-xs text-muted-foreground">{project.address || 'No address'}</p>
                  <div className="mt-3 flex items-center justify-end gap-2">
                    <Button
                      aria-label="Edit project"
                      onClick={(event) => {
                        event.stopPropagation()
                        openEditProjectModal(project)
                      }}
                      size="icon"
                      title="Edit project"
                      type="button"
                      variant="ghost"
                    >
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                    </Button>
                    <Button
                      aria-label="Delete project"
                      onClick={(event) => {
                        event.stopPropagation()
                        void handleDeleteProject(project.id)
                      }}
                      size="icon"
                      title="Delete project"
                      type="button"
                      variant="ghost"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <Alert className="text-xs">No projects yet. Create one to start quoting.</Alert>
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
                    Projects
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
                <div className="flex flex-wrap items-center gap-1">
                  <button
                    aria-pressed={activeProjectTab === 'quotes'}
                    className={`border-b-2 px-2 py-2 text-xs font-semibold transition-colors ${activeProjectTab === 'quotes' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                    onClick={() => {
                      setActiveProjectTab('quotes')
                      if (activeQuoteTab === 'pricing') {
                        setActiveQuoteTab('readiness')
                      }
                    }}
                    type="button"
                  >
                    Quotes
                  </button>
                  <button
                    aria-pressed={activeProjectTab === 'pricing'}
                    className={`border-b-2 px-2 py-2 text-xs font-semibold transition-colors ${activeProjectTab === 'pricing' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                    onClick={openProjectPricingTab}
                    type="button"
                  >
                    Pricing
                  </button>
                </div>
              </div>
            </CardHeader>
          </Card>

          <div className={`grid gap-4 ${activeProjectTab === 'pricing' ? 'xl:grid-cols-[260px_minmax(0,1fr)]' : 'xl:grid-cols-[340px_minmax(0,1fr)]'}`}>
            <Card>
              {activeProjectTab === 'pricing' ? (
                <>
                  <CardHeader>
                    <CardTitle>Pricing</CardTitle>
                  </CardHeader>
                  <CardContent className="grid gap-4">
                    <div className="grid gap-1">
                      {[
                        ['overview', 'Overview'],
                        ['settings', 'Settings'],
                        ['quotes', 'Quotes'],
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
                    <CardTitle>Quotes</CardTitle>
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
                        return (
                          <div
                            className={`w-full rounded-[var(--card-radius)] border p-3 text-left transition ${quote.id === selectedQuoteId ? 'border-primary bg-primary/5' : 'border-border bg-card hover:border-primary/50'}`}
                            key={quote.id}
                            onClick={() => {
                              setSelectedQuoteId(quote.id)
                              setActiveQuoteTab('readiness')
                            }}
                            onKeyDown={(event) => {
                              if (event.key === 'Enter' || event.key === ' ') {
                                event.preventDefault()
                                setSelectedQuoteId(quote.id)
                                setActiveQuoteTab('readiness')
                              }
                            }}
                            role="button"
                            tabIndex={0}
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
                            </div>
                            <div className="mt-2 flex items-center justify-end gap-1">
                              <Button
                                aria-label="Create revision"
                                disabled={isCreatingQuoteRevision}
                                onClick={(event) => {
                                  event.stopPropagation()
                                  void handleCreateQuoteRevision(quote)
                                }}
                                size="icon"
                                title="Create revision"
                                type="button"
                                variant="ghost"
                              >
                                <GitBranch className="h-4 w-4" aria-hidden="true" />
                              </Button>
                              <Button
                                aria-label="Copy quote setup"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  openCopyQuoteModal(quote)
                                }}
                                size="icon"
                                title="Copy quote setup"
                                type="button"
                                variant="ghost"
                              >
                                <Copy className="h-4 w-4" aria-hidden="true" />
                              </Button>
                              <Button
                                aria-label="Edit quote"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  openEditQuoteModal(quote)
                                }}
                                size="icon"
                                title="Edit quote"
                                type="button"
                                variant="ghost"
                              >
                                <Pencil className="h-4 w-4" aria-hidden="true" />
                              </Button>
                              <Button
                                aria-label="Delete quote"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  void handleDeleteQuote(quote.id)
                                }}
                                size="icon"
                                title="Delete quote"
                                type="button"
                                variant="ghost"
                              >
                                <Trash2 className="h-4 w-4" aria-hidden="true" />
                              </Button>
                            </div>
                          </div>
                        )
                      })
                    ) : (
                      <Alert className="text-xs">No quotes in this project yet.</Alert>
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
                          ? 'Pricing overview'
                          : activePricingTab === 'settings'
                            ? 'Pricing settings'
                            : activePricingTab === 'quotes'
                              ? 'Quote comparison'
                              : 'Pricing overview'
                        : selectedQuote
                          ? selectedQuote.name
                          : 'Select a quote'}
                    </CardTitle>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {activeProjectTab === 'pricing'
                        ? activePricingTab === 'overview'
                          ? 'Project totals and pricing status.'
                          : activePricingTab === 'settings'
                            ? 'Project defaults and selected quote overrides.'
                            : activePricingTab === 'quotes'
                              ? 'Compare priced quotes in this project.'
                              : 'Project totals and pricing status.'
                        : selectedQuote
                          ? activeQuoteTab === 'pricing'
                            ? 'Review this quote pricing override and priced line breakdown.'
                            : activeQuoteTab === 'readiness'
                              ? 'Check whether this quote is complete enough to trust.'
                            : 'Build this quote using units, panels, cutting lists, and extras.'
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
                    </div>
                  ) : null}
                </div>
                {activeProjectTab === 'quotes' && selectedQuote ? (
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant={quoteStatusBadgeVariant(selectedQuote.status)}>{quoteStatusLabels[selectedQuote.status]}</Badge>
                    <Badge variant="outline">{quoteRevisionLabel(selectedQuote)}</Badge>
                    {previousQuoteRevisionLabel(selectedQuote) ? <span>{previousQuoteRevisionLabel(selectedQuote)}</span> : null}
                  </div>
                ) : null}
                {activeProjectTab === 'quotes' ? (
                  <div className="border-b border-border">
                    <div className="flex flex-wrap items-center gap-1">
                      <button
                        aria-pressed={activeQuoteTab === 'readiness'}
                        className={`border-b-2 px-2 py-1 text-xs font-semibold transition-colors ${activeQuoteTab === 'readiness' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                        onClick={() => {
                          setActiveQuoteTab('readiness')
                          if (selectedQuoteId) {
                            void loadQuoteReadiness(selectedQuoteId)
                          }
                        }}
                        type="button"
                      >
                        Readiness
                      </button>
                      <button
                        aria-pressed={activeQuoteTab === 'units'}
                        className={`border-b-2 px-2 py-1 text-xs font-semibold transition-colors ${activeQuoteTab === 'units' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                        onClick={() => setActiveQuoteTab('units')}
                        type="button"
                      >
                        Units
                      </button>
                      <button
                        aria-pressed={activeQuoteTab === 'panels'}
                        className={`border-b-2 px-2 py-1 text-xs font-semibold transition-colors ${activeQuoteTab === 'panels' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                        onClick={openQuotePanelsTab}
                        type="button"
                      >
                        Panels
                      </button>
                      <button
                        aria-pressed={activeQuoteTab === 'cutting-lists'}
                        className={`border-b-2 px-2 py-1 text-xs font-semibold transition-colors ${activeQuoteTab === 'cutting-lists' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                        onClick={openQuoteCuttingListTab}
                        type="button"
                      >
                        Cutting Lists
                      </button>
                      <button
                        aria-pressed={activeQuoteTab === 'extras'}
                        className={`border-b-2 px-2 py-1 text-xs font-semibold transition-colors ${activeQuoteTab === 'extras' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                        onClick={() => {
                          setActiveQuoteTab('extras')
                          if (selectedQuoteId) {
                            void loadQuoteExtras(selectedQuoteId)
                          }
                        }}
                        type="button"
                      >
                        Extras
                      </button>
                      <button
                        aria-pressed={activeQuoteTab === 'pricing'}
                        className={`border-b-2 px-2 py-1 text-xs font-semibold transition-colors ${activeQuoteTab === 'pricing' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                        onClick={openQuotePricingTab}
                        type="button"
                      >
                        Pricing
                      </button>
                    </div>
                  </div>
                ) : null}
              </CardHeader>
            <CardContent>
              {activeProjectTab === 'quotes' && !selectedQuote ? (
                <Alert className="text-xs">No quote selected.</Alert>
              ) : activeQuoteTab === 'readiness' ? (
                isLoadingQuoteReadiness ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Checking readiness
                  </div>
                ) : !quoteReadiness ? (
                  <Alert className="text-xs">No readiness check is available for this quote yet.</Alert>
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
                          <TableHead>#</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Dimensions (mm)</TableHead>
                          <TableHead>Boards</TableHead>
                          <TableHead>Extra Params</TableHead>
                          <TableHead className="w-24" />
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {units.length === 0 ? (
                          <TableRow>
                            <TableCell className="text-muted-foreground" colSpan={6}>
                              No units yet.
                            </TableCell>
                          </TableRow>
                        ) : (
                          units.map((unit) => {
                            const carcassBoardId = unit.carcass_board_type_id ?? selectedQuote?.default_carcass_board_type_id ?? null
                            const doorBoardId = unit.door_board_type_id ?? selectedQuote?.default_door_board_type_id ?? null
                            return (
                              <TableRow key={unit.id}>
                                <TableCell>{unit.unit_number}</TableCell>
                                <TableCell>{unit.unit_type_key}</TableCell>
                                <TableCell>{`${unit.height} x ${unit.width} x ${unit.depth} · t${unit.thickness}`}</TableCell>
                                <TableCell>{`${boardLabel(carcassBoardId)} / ${boardLabel(doorBoardId)}`}</TableCell>
                                <TableCell className="max-w-72 truncate text-xs text-muted-foreground">{formatExtraParams(unit.extra_params)}</TableCell>
                                <TableCell>
                                  <div className="flex justify-end gap-1">
                                    <Button onClick={() => openEditUnitModal(unit)} size="icon" type="button" variant="ghost">
                                      <Pencil className="h-4 w-4" aria-hidden="true" />
                                    </Button>
                                    <Button onClick={() => void handleDeleteUnit(unit.id)} size="icon" type="button" variant="ghost">
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
                  <Alert className="text-xs">No panel configuration loaded for this quote yet.</Alert>
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
                  <Alert className="text-xs">No cutting-list rows yet. Add units to generate results.</Alert>
                ) : (
                  <div className="grid gap-4">
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
                        <CutlistSection rows={quoteCuttingList.carcass} title="Carcass" />
                      ) : (
                        <Alert className="text-xs">No carcass rows for this quote.</Alert>
                      )
                    ) : (
                      activeCuttingListViewTab === 'panels' ? (
                        quoteCuttingList && quoteCuttingList.panels.length > 0 ? (
                          <CutlistSection rows={quoteCuttingList.panels} title="Panels" />
                        ) : (
                          <Alert className="text-xs">No panel rows for this quote.</Alert>
                        )
                      ) : quoteCuttingList && quoteCuttingList.extras.length > 0 ? (
                        <CutlistSection rows={quoteCuttingList.extras} title="Quote Panels & Extras" />
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
                    <Alert className="text-xs">No extras in your library yet. Add extras in Libraries first.</Alert>
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
	                  <Alert className="text-xs">No pricing summary available yet.</Alert>
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
	                        {selectedQuotePricing.lines.length === 0 ? (
	                          <Alert className="text-xs">No priced lines yet.</Alert>
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
	                                        <TableRow key={`${line.item_key}:${line.price_component}:${line.bucket}`}>
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
	                      <Alert className="text-xs">No priced lines yet.</Alert>
	                    )}
	                  </div>
	                )
              ) : isLoadingProjectPricing ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Loading pricing summary
                </div>
              ) : !projectPricing ? (
                <Alert className="text-xs">No pricing summary available yet.</Alert>
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
                      {projectPricing.is_complete ? 'Complete pricing' : 'Missing prices'}
                    </Badge>
                    <Badge variant="outline">{pricingCurrencyCode}</Badge>
                    <span>{`Default markup ${formatPercentFromBps(projectPricing.markup_bps)} · VAT ${formatPercentFromBps(projectPricing.vat_rate_bps)}`}</span>
	                  </div>
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
                                <Badge variant={quotePricing.is_complete ? 'outline' : 'warning'}>
                                  {quotePricing.is_complete ? 'Complete' : 'Missing prices'}
                                </Badge>
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

            <div className="grid gap-3 md:grid-cols-2">
              <LibrarySelect
                label="Default slide"
                options={slides.map((slide) => ({ value: slide.id, label: `${slide.brand} ${slide.model}${slide.code ? ` (${slide.code})` : ''}` }))}
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
                options={handles.map((handle) => ({ value: handle.id, label: `${handle.name}${handle.supplier ? ` · ${handle.supplier}` : ''}` }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_base_handle_id: value }))}
                value={quoteDraft.default_base_handle_id}
              />
              <LibrarySelect
                label="Wall handle"
                options={handles.map((handle) => ({ value: handle.id, label: `${handle.name}${handle.supplier ? ` · ${handle.supplier}` : ''}` }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_wall_handle_id: value }))}
                value={quoteDraft.default_wall_handle_id}
              />
              <LibrarySelect
                label="Tall handle"
                options={handles.map((handle) => ({ value: handle.id, label: `${handle.name}${handle.supplier ? ` · ${handle.supplier}` : ''}` }))}
                onChange={(value) => setQuoteDraft((current) => ({ ...current, default_tall_handle_id: value }))}
                value={quoteDraft.default_tall_handle_id}
              />
              <LibrarySelect
                label="Drawer handle"
                options={handles.map((handle) => ({ value: handle.id, label: `${handle.name}${handle.supplier ? ` · ${handle.supplier}` : ''}` }))}
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
                    setUnitDraft((current) => ({ ...current, unit_type_key: customUnitTypeValue }))
                    return
                  }
                  const nextType = nextValue as UnitPresetKey
                  const dims = resolveDefaultDims(selectedQuote?.unit_defaults ?? fallbackUnitDefaults, nextType)
                  setUnitDraft((current) => ({
                    ...current,
                    unit_type_key: nextValue,
                    height: String(dims.height),
                    depth: String(dims.depth),
                  }))
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
                  onChange={(event) =>
                    setUnitDraft((current) => ({
                      ...current,
                      custom_unit_type_key: event.target.value,
                    }))
                  }
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
                  onChange={(event) => setUnitDraft((current) => ({ ...current, width: event.target.value }))}
                  required
                  type="number"
                  value={unitDraft.width}
                />
              </Label>
              <Label className="grid gap-1.5">
                Height (mm)
                <Input
                  min={1}
                  onChange={(event) => setUnitDraft((current) => ({ ...current, height: event.target.value }))}
                  required
                  type="number"
                  value={unitDraft.height}
                />
              </Label>
              <Label className="grid gap-1.5">
                Depth (mm)
                <Input
                  min={1}
                  onChange={(event) => setUnitDraft((current) => ({ ...current, depth: event.target.value }))}
                  required
                  type="number"
                  value={unitDraft.depth}
                />
              </Label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <LibrarySelect
                label="Carcass board"
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                onChange={(value) => setUnitDraft((current) => ({ ...current, carcass_board_type_id: value }))}
                required
                value={unitDraft.carcass_board_type_id}
              />
              <LibrarySelect
                label="Door board"
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                onChange={(value) => setUnitDraft((current) => ({ ...current, door_board_type_id: value }))}
                value={unitDraft.door_board_type_id}
              />
            </div>

            {isDrawerUnitDraft ? (
              <Label className="grid gap-1.5">
                Number of drawers
                <Input
                  min={1}
                  onChange={(event) => setUnitDraft((current) => ({ ...current, num_drawers: event.target.value }))}
                  required
                  type="number"
                  value={unitDraft.num_drawers}
                />
              </Label>
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
    </div>
  )
}
