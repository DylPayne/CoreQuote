import {
  ArrowLeft,
  Copy,
  LoaderCircle,
  Pencil,
  Plus,
  Trash2,
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
import { customUnitTypeValue, defaultProjectDraft, defaultQuoteDraft, defaultUnitDraft, fallbackUnitDefaults, unitPresets } from '@/components/projects-quotes/constants'
import { QuotePanelsEditor } from '@/components/projects-quotes/quote-panels-editor'
import { CutlistSection, LibrarySelect, ModalCard, QuoteDefaultDimensionGrid } from '@/components/projects-quotes/shared-ui'
import { countPanelFamilies, formatCents, formatExtraParams, formatPercentFromBps, normalizeQuoteCustomPanelsState, numberFromExtra, quotePayloadFromDraft, resolveDefaultDims, resolvedUnitType, toQuoteDraft, unitPayloadFromDraft } from '@/components/projects-quotes/helpers'
import type { BoardRow, CuttingListViewTab, ExtraRow, HandleRow, HingeRow, ProjectDraft, ProjectPricingSummary, ProjectRow, QuoteCuttingList, QuoteCustomPanelComputedRow, QuoteCustomPanelsState, QuoteCustomPanelsResponse, QuoteDraft, QuoteExtrasResponse, QuoteRow, QuoteWorkspaceTab, SlideRow, UnitDraft, UnitPresetKey, UnitRow } from '@/components/projects-quotes/types'

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
  const [quoteExtrasSelection, setQuoteExtrasSelection] = useState<Record<string, number>>({})
  const [quoteCustomPanels, setQuoteCustomPanels] = useState<QuoteCustomPanelsState | null>(null)
  const [quoteCustomPanelRows, setQuoteCustomPanelRows] = useState<QuoteCustomPanelComputedRow[]>([])
  const [projectPricing, setProjectPricing] = useState<ProjectPricingSummary | null>(null)

  const [currentView, setCurrentView] = useState<'projects' | 'project-workspace'>('projects')
  const [activeQuoteTab, setActiveQuoteTab] = useState<QuoteWorkspaceTab>('units')
  const [activeCuttingListViewTab, setActiveCuttingListViewTab] = useState<CuttingListViewTab>('carcass')
  const [search, setSearch] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [selectedQuoteId, setSelectedQuoteId] = useState<string | null>(null)

  const [projectDraft, setProjectDraft] = useState<ProjectDraft>(defaultProjectDraft)
  const [quoteDraft, setQuoteDraft] = useState<QuoteDraft>(defaultQuoteDraft)
  const [unitDraft, setUnitDraft] = useState<UnitDraft>(defaultUnitDraft)

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
  const [isLoadingQuoteExtras, setIsLoadingQuoteExtras] = useState(false)
  const [isLoadingQuoteCustomPanels, setIsLoadingQuoteCustomPanels] = useState(false)
  const [isLoadingProjectPricing, setIsLoadingProjectPricing] = useState(false)
  const [isLoadingLibraries, setIsLoadingLibraries] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isSavingQuoteExtras, setIsSavingQuoteExtras] = useState(false)
  const [isSavingQuoteCustomPanels, setIsSavingQuoteCustomPanels] = useState(false)
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
        return
      }
      void loadQuotes(selectedProjectId)
    }, 0)
    return () => window.clearTimeout(handle)
  }, [loadQuotes, selectedProjectId])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      if (!selectedQuoteId) {
        setUnits([])
        setQuoteCuttingList(null)
        setQuoteExtrasSelection({})
        setQuoteCustomPanels(null)
        setQuoteCustomPanelRows([])
        setIsQuoteExtrasDirty(false)
        setIsQuoteCustomPanelsDirty(false)
        return
      }
      void loadUnits(selectedQuoteId)
    }, 0)
    return () => window.clearTimeout(handle)
  }, [loadUnits, selectedQuoteId])

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
    setActiveQuoteTab('units')
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
      thickness: String(unit.thickness),
      carcass_board_type_id: unit.carcass_board_type_id ?? '',
      door_board_type_id: unit.door_board_type_id ?? '',
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
      if (activeQuoteTab === 'cutting-lists') {
        await loadQuoteCuttingList(selectedQuoteId)
      }
      if (selectedProjectId && activeQuoteTab === 'pricing') {
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
      if (selectedProjectId && activeQuoteTab === 'pricing') {
        await loadProjectPricing(selectedProjectId)
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save selected extras.')
    } finally {
      setIsSavingQuoteExtras(false)
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
        <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
          <Card>
            <CardHeader className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <Button onClick={() => setCurrentView('projects')} type="button" variant="outline">
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                  Projects
                </Button>
                <Button disabled={!selectedProject} onClick={openCreateQuoteModal} size="sm" type="button">
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  New quote
                </Button>
              </div>
              <div>
                <CardTitle className="truncate">{selectedProject?.name ?? 'Project'}</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  {selectedProject
                    ? `${selectedProject.client || 'No client'} · ${selectedProject.address || 'No address'}`
                    : 'No project selected.'}
                </p>
              </div>
            </CardHeader>
            <CardContent className="grid gap-2">
              {isLoadingQuotes ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Loading quotes
                </div>
              ) : quotes.length > 0 ? (
                quotes.map((quote) => (
                  <div
                    className={`w-full rounded-[var(--card-radius)] border p-3 text-left transition ${quote.id === selectedQuoteId ? 'border-primary bg-primary/5' : 'border-border bg-card hover:border-primary/50'}`}
                    key={quote.id}
                    onClick={() => {
                      setSelectedQuoteId(quote.id)
                      setActiveQuoteTab('units')
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        setSelectedQuoteId(quote.id)
                        setActiveQuoteTab('units')
                      }
                    }}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold">{quote.name}</p>
                        <p className="truncate text-xs text-muted-foreground">{quote.notes || 'No notes'}</p>
                      </div>
                      <Badge variant="outline">{quote.unit_count}</Badge>
                    </div>
                    <div className="mt-2 flex items-center justify-end gap-1">
                      <Button
                        aria-label="Copy quote"
                        onClick={(event) => {
                          event.stopPropagation()
                          openCopyQuoteModal(quote)
                        }}
                        size="icon"
                        title="Copy quote"
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
                ))
              ) : (
                <Alert className="text-xs">No quotes in this project yet.</Alert>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <CardTitle>{selectedQuote ? selectedQuote.name : 'Select a quote'}</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {selectedQuote
                      ? `Quote tabs provide room for growth as features are added.`
                      : 'Choose a quote from the left pane to begin.'}
                  </p>
                </div>
                <Button disabled={!selectedQuote} onClick={openCreateUnitModal} type="button">
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  Add unit
                </Button>
              </div>

              <div className="border-b border-border">
                <div className="flex flex-wrap items-center gap-1">
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
                    onClick={() => {
                      setActiveQuoteTab('panels')
                      if (selectedQuoteId) {
                        void loadQuoteCustomPanels(selectedQuoteId)
                      }
                    }}
                    type="button"
                  >
                    Panels
                  </button>
                  <button
                    aria-pressed={activeQuoteTab === 'cutting-lists'}
                    className={`border-b-2 px-2 py-1 text-xs font-semibold transition-colors ${activeQuoteTab === 'cutting-lists' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                    onClick={() => {
                      setActiveQuoteTab('cutting-lists')
                      setActiveCuttingListViewTab('carcass')
                      if (selectedQuoteId) {
                        void loadQuoteCuttingList(selectedQuoteId)
                      }
                    }}
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
                    onClick={() => {
                      setActiveQuoteTab('pricing')
                      if (selectedProjectId) {
                        void loadProjectPricing(selectedProjectId)
                      }
                    }}
                    type="button"
                  >
                    Pricing
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {!selectedQuote ? (
                <Alert className="text-xs">No quote selected.</Alert>
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
                          units.map((unit) => (
                            <TableRow key={unit.id}>
                              <TableCell>{unit.unit_number}</TableCell>
                              <TableCell>{unit.unit_type_key}</TableCell>
                              <TableCell>{`${unit.height} x ${unit.width} x ${unit.depth} · t${unit.thickness}`}</TableCell>
                              <TableCell>{`${boardLabel(unit.carcass_board_type_id)} / ${boardLabel(unit.door_board_type_id)}`}</TableCell>
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
                          ))
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
                    defaultPanelBoardId={selectedQuote.default_panel_board_type_id}
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
                    selectedQuote={selectedQuote}
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
              ) : isLoadingProjectPricing ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Loading pricing summary
                </div>
              ) : !projectPricing ? (
                <Alert className="text-xs">No pricing summary available yet.</Alert>
              ) : (
                <div className="grid gap-4">
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                    <Card className="p-3">
                      <p className="text-xs text-muted-foreground">Subtotal</p>
                      <p className="text-sm font-semibold">{formatCents(projectPricing.subtotal_cents, pricingCurrencyCode)}</p>
                    </Card>
                    <Card className="p-3">
                      <p className="text-xs text-muted-foreground">Before VAT</p>
                      <p className="text-sm font-semibold">{formatCents(projectPricing.sell_before_vat_cents, pricingCurrencyCode)}</p>
                    </Card>
                    <Card className="p-3">
                      <p className="text-xs text-muted-foreground">VAT</p>
                      <p className="text-sm font-semibold">{formatCents(projectPricing.vat_cents, pricingCurrencyCode)}</p>
                    </Card>
                    <Card className="p-3">
                      <p className="text-xs text-muted-foreground">Total</p>
                      <p className="text-sm font-semibold">{formatCents(projectPricing.grand_total_cents, pricingCurrencyCode)}</p>
                    </Card>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant={projectPricing.is_complete ? 'outline' : 'warning'}>
                      {projectPricing.is_complete ? 'Complete pricing' : 'Missing prices'}
                    </Badge>
                    <Badge variant="outline">{pricingCurrencyCode}</Badge>
                    <span>{`Markup ${formatPercentFromBps(projectPricing.markup_bps)} · VAT ${formatPercentFromBps(projectPricing.vat_rate_bps)}`}</span>
                  </div>

                  <TableContainer>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Quote</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="text-right">Total</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {projectPricing.quotes.map((quotePricing) => (
                          <TableRow key={quotePricing.quote_id}>
                            <TableCell>{quotePricing.quote_name}</TableCell>
                            <TableCell>
                              <Badge variant={quotePricing.is_complete ? 'outline' : 'warning'}>
                                {quotePricing.is_complete ? 'Complete' : 'Missing prices'}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{formatCents(quotePricing.grand_total_cents, pricingCurrencyCode)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  {selectedQuotePricing ? (
                    <div className="grid gap-2">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">{`${selectedQuotePricing.quote_name} line items`}</p>
                      <TableContainer>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Item</TableHead>
                              <TableHead>Component</TableHead>
                              <TableHead className="text-right">Qty</TableHead>
                              <TableHead className="text-right">Unit</TableHead>
                              <TableHead className="text-right">Line</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {selectedQuotePricing.lines.length === 0 ? (
                              <TableRow>
                                <TableCell className="text-muted-foreground" colSpan={5}>
                                  No priced lines yet.
                                </TableCell>
                              </TableRow>
                            ) : (
                              selectedQuotePricing.lines.map((line) => (
                                <TableRow key={`${line.item_key}:${line.price_component}`}>
                                  <TableCell>
                                    {line.description}
                                    {line.missing ? <Badge className="ml-2" variant="warning">Missing</Badge> : null}
                                  </TableCell>
                                  <TableCell>{line.price_component}</TableCell>
                                  <TableCell className="text-right">{line.qty.toFixed(2)}</TableCell>
                                  <TableCell className="text-right">{formatCents(line.unit_price_cents, pricingCurrencyCode)}</TableCell>
                                  <TableCell className="text-right">{formatCents(line.line_total_cents, pricingCurrencyCode)}</TableCell>
                                </TableRow>
                              ))
                            )}
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

            <div className="grid gap-3 md:grid-cols-2">
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
              <Label className="grid gap-1.5">
                Thickness (mm)
                <Input
                  min={1}
                  onChange={(event) => setUnitDraft((current) => ({ ...current, thickness: event.target.value }))}
                  required
                  type="number"
                  value={unitDraft.thickness}
                />
              </Label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <LibrarySelect
                label="Carcass board"
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                onChange={(value) => setUnitDraft((current) => ({ ...current, carcass_board_type_id: value }))}
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
