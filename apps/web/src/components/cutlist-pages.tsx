import { CopyPlus, LoaderCircle, Plus, Save, Trash2 } from 'lucide-react'
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from 'react'

import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { FormulaEditor } from '@/components/formula-editor'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { apiRequest } from '@/lib/api'

type UnitConfigCategory = 'base' | 'wall' | 'tall' | 'custom'
type UnitConfigVariantType = 'drawer' | 'door' | 'wall' | 'tall' | 'custom'
type CuttingConfigStatus = 'draft' | 'active' | 'archived'
type CuttingRuleSection = 'carcass' | 'panel' | 'hardware' | 'extra_panel'
type GrainDirection = 'none' | 'length' | 'width'
type FormulaFieldKey = 'length_formula' | 'width_formula' | 'qty_formula' | 'condition_formula'
type UnitType = string

type UnitConfigResponse = {
  id: string
  company_id: string | null
  unit_type_key: string
  label: string
  category: UnitConfigCategory
  variant_type: UnitConfigVariantType
  version: number
  status: CuttingConfigStatus
  is_default: boolean
  variant_config: Record<string, unknown>
  default_height: number
  default_width: number
  default_depth: number
  height_min: number
  height_max: number
  width_min: number
  width_max: number
  depth_min: number
  depth_max: number
  created_at: string
  updated_at: string
}

type UnitConfigRequest = {
  unit_type_key: string
  label: string
  category: UnitConfigCategory
  variant_type: UnitConfigVariantType
  version: number
  status: CuttingConfigStatus
  is_default: boolean
  variant_config: Record<string, unknown>
  default_height: number
  default_width: number
  default_depth: number
  height_min: number
  height_max: number
  width_min: number
  width_max: number
  depth_min: number
  depth_max: number
}

type CuttingRuleRowResponse = {
  id: string
  sort_order: number
  section: CuttingRuleSection
  description: string
  length_formula: string
  width_formula: string
  qty_formula: string
  condition_formula: string
  grain_direction: GrainDirection
  can_rotate: boolean
  edge_long_1: boolean
  edge_long_2: boolean
  edge_short_1: boolean
  edge_short_2: boolean
  meta: Record<string, unknown>
  created_at: string
  updated_at: string
}

type CuttingRulesetSummaryResponse = {
  id: string
  company_id: string | null
  unit_config_id: string | null
  unit_type_key: string
  name: string
  description: string
  status: CuttingConfigStatus
  version: number
  is_default: boolean
  created_at: string
  updated_at: string
}

type CuttingRulesetResponse = CuttingRulesetSummaryResponse & {
  rows: CuttingRuleRowResponse[]
}

type CuttingRuleRowDraft = Omit<CuttingRuleRowResponse, 'created_at' | 'updated_at'>

type CuttingRulesetDraft = {
  id: string
  unit_config_id: string | null
  unit_type_key: string
  name: string
  description: string
  status: CuttingConfigStatus
  version: number
  is_default: boolean
  rows: CuttingRuleRowDraft[]
}

type CuttingRulesetRequest = {
  unit_config_id: string | null
  unit_type_key: string
  name: string
  description: string
  status: CuttingConfigStatus
  version: number
  is_default: boolean
  rows: Array<{
    sort_order: number
    section: CuttingRuleSection
    description: string
    length_formula: string
    width_formula: string
    qty_formula: string
    condition_formula: string
    grain_direction: GrainDirection
    can_rotate: boolean
    edge_long_1: boolean
    edge_long_2: boolean
    edge_short_1: boolean
    edge_short_2: boolean
    meta: Record<string, unknown>
  }>
}

type CutlistPreviewRow = {
  unit_number: number
  desc: string
  length: number
  width: number
  qty: number
}

type CutlistRuntimeRow = CutlistPreviewRow & {
  section: CuttingRuleSection
  edge_long_1: boolean
  edge_long_2: boolean
  edge_short_1: boolean
  edge_short_2: boolean
}

type CutlistUnitSource = {
  unit_number: number
  unit_type_key: string
  source: 'ruleset' | 'legacy'
  ruleset_id: string | null
  unit_config_id: string | null
  note: string | null
}

type CutlistValidationWarning = {
  severity: 'warning'
  source: 'unit' | 'quote_panel'
  unit_number: number
  section: CuttingRuleSection
  row_desc: string
  reason: string
}

type CutlistReadiness = {
  cutlist_valid: boolean
  warning_count: number
}

type CutlistPreviewResponse = {
  carcass: CutlistPreviewRow[]
  panels: CutlistPreviewRow[]
  hardware: CutlistPreviewRow[]
  extras: CutlistPreviewRow[]
  runtime_rows: CutlistRuntimeRow[]
  runtime_mode: 'legacy' | 'ruleset' | 'mixed'
  unit_sources: CutlistUnitSource[]
  validation_warnings: CutlistValidationWarning[]
  readiness: CutlistReadiness
}

type CutlistTesterDraft = {
  unitNumber: string
  unitType: UnitType
  customUnitType: string
  useCustomUnitType: boolean
  boardTypeId: string
  height: string
  width: string
  depth: string
  parameterValues: Record<string, string>
}

type UnitParameterInputType = 'number' | 'slide'
type SlideMeasurementField = 'length' | 'side_length' | 'side_clearance_total' | 'side_height_uplift'

type UnitParameterDefinition = {
  id: string
  key: string
  label: string
  input_type: UnitParameterInputType
  default_value: string
  slide_field: SlideMeasurementField | null
}

type UnitParameterDefinitionsByType = Record<string, UnitParameterDefinition[]>

type SlideLibraryRow = {
  id: string
  brand: string
  model: string
  code: string
  length: number
  side_length: number
  side_clearance_total: number
  side_height_uplift: number
}

type BoardLibraryRow = {
  id: string
  brand: string
  material: string
  thickness: number
  length_mm: number
  width_mm: number
}

type NewUnitTypeDraft = {
  unit_type_key: string
  label: string
  category: UnitConfigCategory
  variant_type: UnitConfigVariantType
  default_height: string
  default_width: string
  default_depth: string
  height_min: string
  height_max: string
  width_min: string
  width_max: string
  depth_min: string
  depth_max: string
}


const initialNewUnitTypeDraft: NewUnitTypeDraft = {
  unit_type_key: '',
  label: '',
  category: 'custom',
  variant_type: 'custom',
  default_height: '780',
  default_width: '600',
  default_depth: '560',
  height_min: '300',
  height_max: '2400',
  width_min: '150',
  width_max: '1200',
  depth_min: '150',
  depth_max: '700',
}


const rulesetStatusOptions: CuttingConfigStatus[] = ['draft', 'active', 'archived']
const ruleSectionOptions: CuttingRuleSection[] = ['carcass', 'panel', 'hardware', 'extra_panel']
const grainDirectionOptions: GrainDirection[] = ['none', 'length', 'width']
const formulaFields: FormulaFieldKey[] = ['length_formula', 'width_formula', 'qty_formula', 'condition_formula']
const customUnitTypeOptionValue = '__custom_unit_type__'
const cutlistPreviewUnitTypeOptions: UnitType[] = [
  'Base Draw',
  'Base Door',
  'Wall Door',
  'Tall Door',
]
const coreFormulaVariables = ['h', 'w', 'd', 't', 'inner_w', 'inner_h']
const drawerDerivedFormulaVariables = [
  'drawer_depth',
  'drawer_width',
  'drawer_front_height',
  'drawer_front_back_height',
  'drawer_side_height',
]
const slideMeasurementFieldOptions: Array<{ label: string; value: SlideMeasurementField }> = [
  { label: 'Slide length', value: 'length' },
  { label: 'Slide side length', value: 'side_length' },
  { label: 'Slide clearance total', value: 'side_clearance_total' },
  { label: 'Slide side height uplift', value: 'side_height_uplift' },
]
const defaultUnitParameterDefinitionsByType: UnitParameterDefinitionsByType = {
  'Base Draw': [
    {
      id: 'builtin-base-draw-num-drawers',
      key: 'num_drawers',
      label: 'Number of drawers',
      input_type: 'number',
      default_value: '3',
      slide_field: null,
    },
    {
      id: 'builtin-base-draw-panel-gap-mm',
      key: 'panel_gap_mm',
      label: 'Panel gap (mm)',
      input_type: 'number',
      default_value: '3',
      slide_field: null,
    },
    {
      id: 'builtin-base-draw-slide-side-length',
      key: 'slide_side_length',
      label: 'Slide side length (mm)',
      input_type: 'slide',
      default_value: '',
      slide_field: 'side_length',
    },
    {
      id: 'builtin-base-draw-slide-clearance-total',
      key: 'slide_side_clearance_total',
      label: 'Slide clearance total (mm)',
      input_type: 'slide',
      default_value: '',
      slide_field: 'side_clearance_total',
    },
    {
      id: 'builtin-base-draw-slide-height-uplift',
      key: 'slide_side_height_uplift',
      label: 'Slide side uplift (mm)',
      input_type: 'slide',
      default_value: '',
      slide_field: 'side_height_uplift',
    },
  ],
  'Base Door': [
    {
      id: 'builtin-base-door-num-doors',
      key: 'num_doors',
      label: 'Number of doors',
      input_type: 'number',
      default_value: '2',
      slide_field: null,
    },
    {
      id: 'builtin-base-door-num-shelves',
      key: 'num_shelves',
      label: 'Number of shelves',
      input_type: 'number',
      default_value: '1',
      slide_field: null,
    },
    {
      id: 'builtin-base-door-panel-gap-mm',
      key: 'panel_gap_mm',
      label: 'Panel gap (mm)',
      input_type: 'number',
      default_value: '3',
      slide_field: null,
    },
    {
      id: 'builtin-base-door-shelf-setback',
      key: 'shelf_setback',
      label: 'Shelf setback (mm)',
      input_type: 'number',
      default_value: '20',
      slide_field: null,
    },
  ],
  'Wall Door': [
    {
      id: 'builtin-wall-door-num-doors',
      key: 'num_doors',
      label: 'Number of doors',
      input_type: 'number',
      default_value: '2',
      slide_field: null,
    },
    {
      id: 'builtin-wall-door-num-shelves',
      key: 'num_shelves',
      label: 'Number of shelves',
      input_type: 'number',
      default_value: '1',
      slide_field: null,
    },
    {
      id: 'builtin-wall-door-panel-gap-mm',
      key: 'panel_gap_mm',
      label: 'Panel gap (mm)',
      input_type: 'number',
      default_value: '3',
      slide_field: null,
    },
    {
      id: 'builtin-wall-door-shelf-setback',
      key: 'shelf_setback',
      label: 'Shelf setback (mm)',
      input_type: 'number',
      default_value: '20',
      slide_field: null,
    },
  ],
  'Tall Door': [
    {
      id: 'builtin-tall-door-num-doors',
      key: 'num_doors',
      label: 'Number of doors',
      input_type: 'number',
      default_value: '2',
      slide_field: null,
    },
    {
      id: 'builtin-tall-door-num-shelves',
      key: 'num_shelves',
      label: 'Number of shelves',
      input_type: 'number',
      default_value: '4',
      slide_field: null,
    },
    {
      id: 'builtin-tall-door-panel-gap-mm',
      key: 'panel_gap_mm',
      label: 'Panel gap (mm)',
      input_type: 'number',
      default_value: '3',
      slide_field: null,
    },
    {
      id: 'builtin-tall-door-shelf-setback',
      key: 'shelf_setback',
      label: 'Shelf setback (mm)',
      input_type: 'number',
      default_value: '20',
      slide_field: null,
    },
  ],
}
const formulaKeywords = new Set([
  'abs',
  'and',
  'ceil',
  'else',
  'false',
  'floor',
  'if',
  'max',
  'min',
  'not',
  'or',
  'round',
  'true',
])

export function CuttingRulesetsPage({ authToken, companyId }: { authToken: string; companyId: string }) {
  const [unitConfigs, setUnitConfigs] = useState<UnitConfigResponse[]>([])
  const [rulesets, setRulesets] = useState<CuttingRulesetSummaryResponse[]>([])
  const [unitParameterDefinitionsByType] = useState<UnitParameterDefinitionsByType>(() =>
    cloneUnitParameterDefinitionsByType(defaultUnitParameterDefinitionsByType),
  )
  const [newUnitTypeDraft, setNewUnitTypeDraft] = useState<NewUnitTypeDraft>(initialNewUnitTypeDraft)
  const [isCreateUnitModalOpen, setIsCreateUnitModalOpen] = useState(false)
  const [selectedUnitTypeKey, setSelectedUnitTypeKey] = useState('')
  const [selectedRulesetId, setSelectedRulesetId] = useState<string | null>(null)
  const [draft, setDraft] = useState<CuttingRulesetDraft | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isCreatingCopy, setIsCreatingCopy] = useState(false)
  const [isCreatingUnitType, setIsCreatingUnitType] = useState(false)
  const [isCreatingRuleset, setIsCreatingRuleset] = useState(false)
  const [isLoadingConfigs, setIsLoadingConfigs] = useState(true)
  const [isLoadingRulesets, setIsLoadingRulesets] = useState(false)
  const [isLoadingRuleset, setIsLoadingRuleset] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const unitTypeKeys = useMemo(
    () => Array.from(new Set(unitConfigs.map((config) => config.unit_type_key))).sort((a, b) => a.localeCompare(b)),
    [unitConfigs],
  )

  const selectedRulesetSummary = useMemo(
    () => rulesets.find((ruleset) => ruleset.id === selectedRulesetId) ?? null,
    [rulesets, selectedRulesetId],
  )
  const selectedRulesetIsCompanyOwned = selectedRulesetSummary?.company_id === companyId
  const availableFormulaVariables = useMemo(
    () => getAvailableFormulaVariables(unitConfigs, selectedUnitTypeKey, unitParameterDefinitionsByType),
    [selectedUnitTypeKey, unitConfigs, unitParameterDefinitionsByType],
  )
  const formulaErrors = useMemo(
    () => (draft ? validateDraftFormulas(draft.rows, availableFormulaVariables) : {}),
    [availableFormulaVariables, draft],
  )
  const formulaErrorCount = useMemo(
    () =>
      Object.values(formulaErrors).reduce(
        (total, rowErrors) =>
          total + formulaFields.reduce((count, field) => count + (rowErrors[field] ? 1 : 0), 0),
        0,
      ),
    [formulaErrors],
  )
  const exampleParameterVariable = useMemo(
    () =>
      availableFormulaVariables.find(
        (variable) =>
          !coreFormulaVariables.includes(variable) && !drawerDerivedFormulaVariables.includes(variable),
      ) ?? 'h',
    [availableFormulaVariables],
  )
  const exampleConditionVariable = exampleParameterVariable === 'h' ? 'w' : exampleParameterVariable

  const selectedUnitConfig = useMemo(
    () => {
      const visibleMatches = unitConfigs.filter(
        (config) =>
          config.unit_type_key === selectedUnitTypeKey && config.status !== 'archived' && (config.company_id === companyId || config.company_id === null),
      )
      return visibleMatches.find((config) => config.company_id === companyId) ?? visibleMatches.find((config) => config.company_id === null) ?? null
    },
    [companyId, selectedUnitTypeKey, unitConfigs],
  )

  const loadRulesets = useCallback(
    async (unitTypeKey: string, preferredRulesetId?: string | null) => {
      setIsLoadingRulesets(true)
      setError(null)

      try {
        const path = `/api/v1/cutting/rulesets?unit_type_key=${encodeURIComponent(unitTypeKey)}`
        const list = await apiRequest<CuttingRulesetSummaryResponse[]>(path, { token: authToken })
        setRulesets(list)

        const selectedId =
          preferredRulesetId && list.some((ruleset) => ruleset.id === preferredRulesetId)
            ? preferredRulesetId
            : list[0]?.id ?? null
        setSelectedRulesetId(selectedId)
        if (!selectedId) {
          setDraft(null)
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load cutting rulesets.')
        setRulesets([])
        setSelectedRulesetId(null)
        setDraft(null)
      } finally {
        setIsLoadingRulesets(false)
      }
    },
    [authToken],
  )

  const loadUnitConfigs = useCallback(
    async (preferredUnitTypeKey?: string) => {
      setIsLoadingConfigs(true)
      setError(null)
      try {
        const configs = await apiRequest<UnitConfigResponse[]>('/api/v1/cutting/unit-configs', { token: authToken })
        setUnitConfigs(configs)
        const defaultUnitType = preferredUnitTypeKey || configs[0]?.unit_type_key || ''
        setSelectedUnitTypeKey((current) => current || defaultUnitType)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Could not load unit configurations.')
      } finally {
        setIsLoadingConfigs(false)
      }
    },
    [authToken],
  )

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadUnitConfigs()
    }, 0)
    return () => window.clearTimeout(handle)
  }, [loadUnitConfigs])

  useEffect(() => {
    if (!selectedUnitTypeKey) {
      return
    }

    const handle = window.setTimeout(() => {
      void loadRulesets(selectedUnitTypeKey)
    }, 0)
    return () => window.clearTimeout(handle)
  }, [loadRulesets, selectedUnitTypeKey])

  useEffect(() => {
    if (!selectedRulesetId) {
      return
    }

    let isCurrent = true

    async function loadRuleset() {
      setIsLoadingRuleset(true)
      setError(null)

      try {
        const ruleset = await apiRequest<CuttingRulesetResponse>(`/api/v1/cutting/rulesets/${selectedRulesetId}`, {
          token: authToken,
        })
        if (!isCurrent) return
        setDraft(mapRulesetToDraft(ruleset))
      } catch (loadError) {
        if (!isCurrent) return
        setDraft(null)
        setError(loadError instanceof Error ? loadError.message : 'Could not load the selected ruleset.')
      } finally {
        if (isCurrent) {
          setIsLoadingRuleset(false)
        }
      }
    }

    loadRuleset()
    return () => {
      isCurrent = false
    }
  }, [authToken, selectedRulesetId])

  async function handleSaveRuleset() {
    if (!draft || !selectedRulesetId || !selectedRulesetIsCompanyOwned) return

    setIsSaving(true)
    setError(null)
    try {
      const updated = await apiRequest<CuttingRulesetResponse>(`/api/v1/cutting/rulesets/${selectedRulesetId}`, {
        body: toRulesetRequest(draft),
        method: 'PATCH',
        token: authToken,
      })
      setDraft(mapRulesetToDraft(updated))
      setRulesets((current) => current.map((ruleset) => (ruleset.id === updated.id ? toRulesetSummary(updated) : ruleset)))
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save this cutting ruleset.')
    } finally {
      setIsSaving(false)
    }
  }

  async function handleCreateCompanyCopy() {
    if (!draft || !selectedRulesetSummary) return

    const fallbackUnitConfig = unitConfigs.find(
      (config) => config.unit_type_key === draft.unit_type_key && (config.company_id === companyId || config.company_id === null),
    )
    if (!draft.unit_config_id && !fallbackUnitConfig?.id) {
      setError('No visible unit config is available for this ruleset.')
      return
    }

    setIsCreatingCopy(true)
    setError(null)
    try {
      const created = await apiRequest<CuttingRulesetResponse>('/api/v1/cutting/rulesets', {
        body: {
          ...toRulesetRequest(draft),
          is_default: false,
          name: `${draft.name} (Company)`,
          status: 'draft',
          unit_config_id: draft.unit_config_id ?? fallbackUnitConfig?.id ?? null,
        },
        method: 'POST',
        token: authToken,
      })
      await loadRulesets(created.unit_type_key, created.id)
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Could not create a company copy.')
    } finally {
      setIsCreatingCopy(false)
    }
  }

  async function handleCreateRulesetDraft() {
    if (!selectedUnitTypeKey) {
      setError('Select a unit type first.')
      return
    }

    const unitConfigForType = selectedUnitConfig
    if (!unitConfigForType) {
      setError('No visible unit config is available for this unit type.')
      return
    }

    setIsCreatingRuleset(true)
    setError(null)
    try {
      const created = await apiRequest<CuttingRulesetResponse>('/api/v1/cutting/rulesets', {
        body: createStarterRulesetRequest(selectedUnitTypeKey, unitConfigForType.id, unitConfigForType.label),
        method: 'POST',
        token: authToken,
      })
      await loadRulesets(created.unit_type_key, created.id)
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Could not create a ruleset draft.')
    } finally {
      setIsCreatingRuleset(false)
    }
  }

  async function handleCreateUnitType() {
    const unitTypeKey = newUnitTypeDraft.unit_type_key.trim()
    const label = newUnitTypeDraft.label.trim() || unitTypeKey
    if (!unitTypeKey) {
      setError('Unit type key is required.')
      return
    }

    const payload: UnitConfigRequest = {
      unit_type_key: unitTypeKey,
      label,
      category: newUnitTypeDraft.category,
      variant_type: newUnitTypeDraft.variant_type,
      version: 1,
      status: 'active',
      is_default: false,
      variant_config: {},
      default_height: parsePositiveInteger(newUnitTypeDraft.default_height, 780),
      default_width: parsePositiveInteger(newUnitTypeDraft.default_width, 600),
      default_depth: parsePositiveInteger(newUnitTypeDraft.default_depth, 560),
      height_min: parsePositiveInteger(newUnitTypeDraft.height_min, 300),
      height_max: parsePositiveInteger(newUnitTypeDraft.height_max, 2400),
      width_min: parsePositiveInteger(newUnitTypeDraft.width_min, 150),
      width_max: parsePositiveInteger(newUnitTypeDraft.width_max, 1200),
      depth_min: parsePositiveInteger(newUnitTypeDraft.depth_min, 150),
      depth_max: parsePositiveInteger(newUnitTypeDraft.depth_max, 700),
    }
    if (payload.height_max < payload.height_min || payload.width_max < payload.width_min || payload.depth_max < payload.depth_min) {
      setError('Max dimensions must be greater than or equal to min dimensions.')
      return
    }

    setIsCreatingUnitType(true)
    setError(null)
    try {
      const createdConfig = await apiRequest<UnitConfigResponse>('/api/v1/cutting/unit-configs', {
        body: payload,
        method: 'POST',
        token: authToken,
      })
      const createdRuleset = await apiRequest<CuttingRulesetResponse>('/api/v1/cutting/rulesets', {
        body: createStarterRulesetRequest(createdConfig.unit_type_key, createdConfig.id, createdConfig.label),
        method: 'POST',
        token: authToken,
      })

      await loadUnitConfigs(createdConfig.unit_type_key)
      setSelectedUnitTypeKey(createdConfig.unit_type_key)
      await loadRulesets(createdConfig.unit_type_key, createdRuleset.id)
      setNewUnitTypeDraft(initialNewUnitTypeDraft)
      setIsCreateUnitModalOpen(false)
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Could not create the new unit type.')
    } finally {
      setIsCreatingUnitType(false)
    }
  }

  function updateDraftRow<T extends keyof CuttingRuleRowDraft>(rowId: string, key: T, value: CuttingRuleRowDraft[T]) {
    setDraft((current) => {
      if (!current) return current
      return {
        ...current,
        rows: current.rows.map((row) => (row.id === rowId ? { ...row, [key]: value } : row)),
      }
    })
  }

  function updateDraftMeta<K extends 'name' | 'description' | 'status' | 'version' | 'is_default'>(
    key: K,
    value: CuttingRulesetDraft[K],
  ) {
    setDraft((current) => (current ? { ...current, [key]: value } : current))
  }

  function addRow() {
    setDraft((current) => {
      if (!current) return current
      const nextSortOrder = current.rows.length === 0 ? 10 : Math.max(...current.rows.map((row) => row.sort_order)) + 10
      return {
        ...current,
        rows: [...current.rows, createDefaultRow(nextSortOrder)],
      }
    })
  }

  function removeRow(rowId: string) {
    setDraft((current) => {
      if (!current || current.rows.length <= 1) return current
      return {
        ...current,
        rows: current.rows.filter((row) => row.id !== rowId),
      }
    })
  }

  const saveDisabled =
    !draft ||
    !selectedRulesetSummary ||
    !selectedRulesetIsCompanyOwned ||
    isSaving ||
    isLoadingRuleset ||
    draft.rows.length === 0 ||
    formulaErrorCount > 0
  const canCreateCopy = Boolean(draft && selectedRulesetSummary && !selectedRulesetIsCompanyOwned)
  const canCreateRuleset = Boolean(selectedUnitTypeKey && selectedUnitConfig)

  return (
    <div className="grid min-w-0 gap-4 overflow-x-hidden">
      <Card className="min-w-0 overflow-x-hidden">
      <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <CardTitle>Cutting rulesets</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            Edit formula rows, side edging toggles, and save complete ruleset drafts through the new API.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button onClick={() => setIsCreateUnitModalOpen(true)} type="button" variant="outline">
            <Plus className="h-4 w-4" aria-hidden="true" />
            New unit type
          </Button>
          <Button disabled={!draft || isLoadingRuleset} onClick={addRow} type="button" variant="outline">
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add row
          </Button>
          <Button disabled={!canCreateRuleset || isCreatingRuleset} onClick={handleCreateRulesetDraft} type="button" variant="outline">
            {isCreatingRuleset ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Plus className="h-4 w-4" aria-hidden="true" />}
            Create ruleset draft
          </Button>
          <Button disabled={!canCreateCopy || isCreatingCopy} onClick={handleCreateCompanyCopy} type="button" variant="outline">
            {isCreatingCopy ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <CopyPlus className="h-4 w-4" aria-hidden="true" />}
            Duplicate to company
          </Button>
          <Button disabled={saveDisabled} onClick={handleSaveRuleset} type="button">
            {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
            Save ruleset
          </Button>
        </div>
      </CardHeader>

      <CardContent className="min-w-0">
        <div className="grid min-w-0 gap-4">
          <div className="grid content-start gap-4 rounded-[var(--card-radius)] border border-border bg-muted/40 p-[var(--card-padding)]">
            <Label className="grid gap-1.5">
              Unit type
              <Select
                disabled={isLoadingConfigs || unitTypeKeys.length === 0}
                onChange={(event) => setSelectedUnitTypeKey(event.target.value)}
                value={selectedUnitTypeKey}
              >
                {unitTypeKeys.length === 0 ? <option value="">No unit configs</option> : null}
                {unitTypeKeys.map((unitTypeKey) => (
                  <option key={unitTypeKey} value={unitTypeKey}>
                    {unitTypeKey}
                  </option>
                ))}
              </Select>
            </Label>

            <div className="space-y-2">
              <p className="text-xs font-medium uppercase text-muted-foreground">Rulesets</p>
              <div className="grid max-h-96 gap-2 overflow-y-auto pr-1">
                {isLoadingRulesets ? (
                  <div className="flex items-center gap-2 rounded-[var(--control-radius)] border border-border bg-card p-3 text-sm text-muted-foreground">
                    <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Loading rulesets
                  </div>
                ) : rulesets.length > 0 ? (
                  rulesets.map((ruleset) => (
                    <Button
                      className="h-auto justify-between gap-3 py-2"
                      key={ruleset.id}
                      onClick={() => setSelectedRulesetId(ruleset.id)}
                      type="button"
                      variant={selectedRulesetId === ruleset.id ? 'secondary' : 'outline'}
                    >
                      <span className="min-w-0 text-left">
                        <span className="block truncate text-sm font-medium">{ruleset.name}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {ruleset.status} · v{ruleset.version}
                        </span>
                      </span>
                      <Badge variant={ruleset.company_id ? 'outline' : 'warning'}>
                        {ruleset.company_id ? 'Company' : 'Global'}
                      </Badge>
                    </Button>
                  ))
                ) : (
                  <Alert className="text-xs text-muted-foreground">No rulesets found for this unit type.</Alert>
                )}
              </div>
            </div>
          </div>

          <div className="min-w-0">
          {isLoadingRuleset ? (
            <Alert className="flex min-h-64 items-center justify-center gap-2 text-muted-foreground">
              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
              Loading ruleset
            </Alert>
          ) : draft ? (
            <div className="grid min-w-0 gap-4">
                <div className="grid gap-3 rounded-[var(--card-radius)] border border-border bg-card p-[var(--card-padding)] md:grid-cols-3">
                  <Label className="grid min-w-0 gap-1.5">
                    Ruleset name
                    <Input
                      disabled={!selectedRulesetIsCompanyOwned}
                      onChange={(event) => updateDraftMeta('name', event.target.value)}
                      value={draft.name}
                    />
                  </Label>
                  <Label className="grid min-w-0 gap-1.5">
                    Status
                    <Select
                      disabled={!selectedRulesetIsCompanyOwned}
                      onChange={(event) => updateDraftMeta('status', event.target.value as CuttingConfigStatus)}
                      value={draft.status}
                    >
                      {rulesetStatusOptions.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </Select>
                  </Label>
                  <Label className="grid min-w-0 gap-1.5">
                    Version
                    <Input
                      disabled={!selectedRulesetIsCompanyOwned}
                      min={1}
                      onChange={(event) => updateDraftMeta('version', parsePositiveInteger(event.target.value, draft.version))}
                      type="number"
                      value={draft.version}
                    />
                  </Label>
                  <Label className="grid min-w-0 gap-1.5 md:col-span-2">
                    Description
                    <Input
                      disabled={!selectedRulesetIsCompanyOwned}
                      onChange={(event) => updateDraftMeta('description', event.target.value)}
                      value={draft.description}
                    />
                  </Label>
                  <Label className="flex items-center gap-2 pt-6 text-sm font-medium">
                    <Checkbox
                      checked={draft.is_default}
                      disabled={!selectedRulesetIsCompanyOwned}
                      onChange={(event) => updateDraftMeta('is_default', event.target.checked)}
                    />
                    Default ruleset
                  </Label>
                </div>

                {!selectedRulesetIsCompanyOwned ? (
                  <Alert>This is a global ruleset. Create a company copy to customize and save changes.</Alert>
                ) : null}

                <div className="rounded-[var(--card-radius)] border border-border bg-muted/30 p-3">
                  <p className="text-sm font-semibold">Formula helper</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    Formulas accept numbers, + - * / %, parentheses, comparisons ({'>'}, {'>='}, ==), logical
                    operators (and, or, not), and helper functions (min, max, abs, round, floor, ceil).
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {availableFormulaVariables.map((variableName) => (
                      <Badge key={variableName} variant="outline">
                        {variableName}
                      </Badge>
                    ))}
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Example length: <span className="font-mono">h - (2 * t)</span> · Example width:{' '}
                    <span className="font-mono">w - (2 * t)</span> · Example qty:{' '}
                    <span className="font-mono">{exampleParameterVariable}</span> · Example condition:{' '}
                    <span className="font-mono">
                      {exampleConditionVariable} {'>'} 0
                    </span>
                  </p>
                </div>

                {formulaErrorCount > 0 ? (
                  <Alert variant="destructive">
                    {formulaErrorCount} formula validation {formulaErrorCount === 1 ? 'issue' : 'issues'} found. Hover a
                    highlighted formula input to see details.
                  </Alert>
                ) : null}

                <TableContainer>
                  <Table className="min-w-[1500px]">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Order</TableHead>
                        <TableHead>Section</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Length formula</TableHead>
                        <TableHead>Width formula</TableHead>
                        <TableHead>Qty formula</TableHead>
                        <TableHead>Condition</TableHead>
                        <TableHead>Grain</TableHead>
                        <TableHead>Rotate</TableHead>
                        <TableHead>L1</TableHead>
                        <TableHead>L2</TableHead>
                        <TableHead>S1</TableHead>
                        <TableHead>S2</TableHead>
                        <TableHead />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {draft.rows.map((row) => (
                        <TableRow key={row.id}>
                          {/*
                            Validation feedback for formula fields is computed centrally so we can keep
                            the rules grid fast while still providing immediate, field-level guidance.
                          */}
                          <TableCell>
                            <Input
                              className="h-8 w-20"
                              disabled={!selectedRulesetIsCompanyOwned}
                              min={1}
                              onChange={(event) =>
                                updateDraftRow(row.id, 'sort_order', parsePositiveInteger(event.target.value, row.sort_order))
                              }
                              type="number"
                              value={row.sort_order}
                            />
                          </TableCell>
                          <TableCell>
                            <Select
                              className="h-8 min-w-[140px]"
                              disabled={!selectedRulesetIsCompanyOwned}
                              onChange={(event) => updateDraftRow(row.id, 'section', event.target.value as CuttingRuleSection)}
                              value={row.section}
                            >
                              {ruleSectionOptions.map((section) => (
                                <option key={section} value={section}>
                                  {section}
                                </option>
                              ))}
                            </Select>
                          </TableCell>
                          <TableCell>
                            <Input
                              className="h-8 min-w-[200px]"
                              disabled={!selectedRulesetIsCompanyOwned}
                              onChange={(event) => updateDraftRow(row.id, 'description', event.target.value)}
                              value={row.description}
                            />
                          </TableCell>
                          <TableCell>
                            <FormulaEditor
                              disabled={!selectedRulesetIsCompanyOwned}
                              error={formulaErrors[row.id]?.length_formula}
                              onBlur={(value) => updateDraftRow(row.id, 'length_formula', value.trim())}
                              onChange={(value) => updateDraftRow(row.id, 'length_formula', value)}
                              placeholder="h - (2 * t)"
                              suggestions={availableFormulaVariables}
                              value={row.length_formula}
                            />
                          </TableCell>
                          <TableCell>
                            <FormulaEditor
                              disabled={!selectedRulesetIsCompanyOwned}
                              error={formulaErrors[row.id]?.width_formula}
                              onBlur={(value) => updateDraftRow(row.id, 'width_formula', value.trim())}
                              onChange={(value) => updateDraftRow(row.id, 'width_formula', value)}
                              placeholder="w - (2 * t)"
                              suggestions={availableFormulaVariables}
                              value={row.width_formula}
                            />
                          </TableCell>
                          <TableCell>
                            <FormulaEditor
                              disabled={!selectedRulesetIsCompanyOwned}
                              error={formulaErrors[row.id]?.qty_formula}
                              onBlur={(value) => updateDraftRow(row.id, 'qty_formula', value.trim())}
                              onChange={(value) => updateDraftRow(row.id, 'qty_formula', value)}
                              placeholder="1"
                              suggestions={availableFormulaVariables}
                              value={row.qty_formula}
                            />
                          </TableCell>
                          <TableCell>
                            <FormulaEditor
                              disabled={!selectedRulesetIsCompanyOwned}
                              error={formulaErrors[row.id]?.condition_formula}
                              onBlur={(value) => updateDraftRow(row.id, 'condition_formula', value.trim())}
                              onChange={(value) => updateDraftRow(row.id, 'condition_formula', value)}
                              placeholder="num_doors > 0"
                              suggestions={availableFormulaVariables}
                              value={row.condition_formula}
                            />
                          </TableCell>
                          <TableCell>
                            <Select
                              className="h-8 min-w-[120px]"
                              disabled={!selectedRulesetIsCompanyOwned}
                              onChange={(event) => updateDraftRow(row.id, 'grain_direction', event.target.value as GrainDirection)}
                              value={row.grain_direction}
                            >
                              {grainDirectionOptions.map((grainDirection) => (
                                <option key={grainDirection} value={grainDirection}>
                                  {grainDirection}
                                </option>
                              ))}
                            </Select>
                          </TableCell>
                          <TableCell className="text-center">
                            <Checkbox
                              checked={row.can_rotate}
                              disabled={!selectedRulesetIsCompanyOwned}
                              onChange={(event) => updateDraftRow(row.id, 'can_rotate', event.target.checked)}
                            />
                          </TableCell>
                          <TableCell className="text-center">
                            <Checkbox
                              checked={row.edge_long_1}
                              disabled={!selectedRulesetIsCompanyOwned}
                              onChange={(event) => updateDraftRow(row.id, 'edge_long_1', event.target.checked)}
                            />
                          </TableCell>
                          <TableCell className="text-center">
                            <Checkbox
                              checked={row.edge_long_2}
                              disabled={!selectedRulesetIsCompanyOwned}
                              onChange={(event) => updateDraftRow(row.id, 'edge_long_2', event.target.checked)}
                            />
                          </TableCell>
                          <TableCell className="text-center">
                            <Checkbox
                              checked={row.edge_short_1}
                              disabled={!selectedRulesetIsCompanyOwned}
                              onChange={(event) => updateDraftRow(row.id, 'edge_short_1', event.target.checked)}
                            />
                          </TableCell>
                          <TableCell className="text-center">
                            <Checkbox
                              checked={row.edge_short_2}
                              disabled={!selectedRulesetIsCompanyOwned}
                              onChange={(event) => updateDraftRow(row.id, 'edge_short_2', event.target.checked)}
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              aria-label="Delete rule row"
                              disabled={!selectedRulesetIsCompanyOwned || draft.rows.length <= 1}
                              onClick={() => removeRow(row.id)}
                              size="icon"
                              type="button"
                              variant="ghost"
                            >
                              <Trash2 className="h-4 w-4" aria-hidden="true" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
            </div>
          ) : (
            <Alert className="flex min-h-64 items-center justify-center border-dashed text-muted-foreground">
              Select a ruleset to begin editing.
            </Alert>
          )}
          </div>
        </div>

        {error ? <Alert className="mt-4" variant="destructive">{error}</Alert> : null}
      </CardContent>
      </Card>
      {isCreateUnitModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-3xl">
            <CardHeader className="flex flex-row items-start justify-between gap-3">
              <div>
                <CardTitle>Create Unit Type</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  Add a new company unit type and starter ruleset.
                </p>
              </div>
              <Button onClick={() => setIsCreateUnitModalOpen(false)} type="button" variant="ghost">
                Close
              </Button>
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="grid gap-3 md:grid-cols-2">
                <Label className="grid gap-1.5">
                  Unit type key
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, unit_type_key: event.target.value }))}
                    placeholder="e.g. Corner Display Unit"
                    value={newUnitTypeDraft.unit_type_key}
                  />
                </Label>
                <Label className="grid gap-1.5">
                  Label
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, label: event.target.value }))}
                    placeholder="Display label"
                    value={newUnitTypeDraft.label}
                  />
                </Label>
                <Label className="grid gap-1.5">
                  Category
                  <Select
                    onChange={(event) =>
                      setNewUnitTypeDraft((current) => ({ ...current, category: event.target.value as UnitConfigCategory }))
                    }
                    value={newUnitTypeDraft.category}
                  >
                    <option value="custom">custom</option>
                    <option value="base">base</option>
                    <option value="wall">wall</option>
                    <option value="tall">tall</option>
                  </Select>
                </Label>
                <Label className="grid gap-1.5">
                  Variant
                  <Select
                    onChange={(event) =>
                      setNewUnitTypeDraft((current) => ({ ...current, variant_type: event.target.value as UnitConfigVariantType }))
                    }
                    value={newUnitTypeDraft.variant_type}
                  >
                    <option value="custom">custom</option>
                    <option value="door">door</option>
                    <option value="drawer">drawer</option>
                    <option value="wall">wall</option>
                    <option value="tall">tall</option>
                  </Select>
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <Label className="grid gap-1.5">
                  Default height (mm)
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, default_height: event.target.value }))}
                    type="number"
                    value={newUnitTypeDraft.default_height}
                  />
                </Label>
                <Label className="grid gap-1.5">
                  Default width (mm)
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, default_width: event.target.value }))}
                    type="number"
                    value={newUnitTypeDraft.default_width}
                  />
                </Label>
                <Label className="grid gap-1.5">
                  Default depth (mm)
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, default_depth: event.target.value }))}
                    type="number"
                    value={newUnitTypeDraft.default_depth}
                  />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <Label className="grid gap-1.5">
                  Min height (mm)
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, height_min: event.target.value }))}
                    type="number"
                    value={newUnitTypeDraft.height_min}
                  />
                </Label>
                <Label className="grid gap-1.5">
                  Min width (mm)
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, width_min: event.target.value }))}
                    type="number"
                    value={newUnitTypeDraft.width_min}
                  />
                </Label>
                <Label className="grid gap-1.5">
                  Min depth (mm)
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, depth_min: event.target.value }))}
                    type="number"
                    value={newUnitTypeDraft.depth_min}
                  />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <Label className="grid gap-1.5">
                  Max height (mm)
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, height_max: event.target.value }))}
                    type="number"
                    value={newUnitTypeDraft.height_max}
                  />
                </Label>
                <Label className="grid gap-1.5">
                  Max width (mm)
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, width_max: event.target.value }))}
                    type="number"
                    value={newUnitTypeDraft.width_max}
                  />
                </Label>
                <Label className="grid gap-1.5">
                  Max depth (mm)
                  <Input
                    onChange={(event) => setNewUnitTypeDraft((current) => ({ ...current, depth_max: event.target.value }))}
                    type="number"
                    value={newUnitTypeDraft.depth_max}
                  />
                </Label>
              </div>
              <div className="flex justify-end gap-2">
                <Button onClick={() => setIsCreateUnitModalOpen(false)} type="button" variant="outline">
                  Cancel
                </Button>
                <Button disabled={isCreatingUnitType} onClick={handleCreateUnitType} type="button">
                  {isCreatingUnitType ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                  Create unit type
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  )
}

export function CutlistTesterPage({ authToken }: { authToken: string }) {
  const [unitConfigs, setUnitConfigs] = useState<UnitConfigResponse[]>([])
  const [selectedUnitTypeKey, setSelectedUnitTypeKey] = useState('')
  const [isLoadingConfigs, setIsLoadingConfigs] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [unitParameterDefinitionsByType, setUnitParameterDefinitionsByType] = useState<UnitParameterDefinitionsByType>(() =>
    cloneUnitParameterDefinitionsByType(defaultUnitParameterDefinitionsByType),
  )

  const unitTypeKeys = useMemo(
    () => Array.from(new Set(unitConfigs.map((config) => config.unit_type_key))).sort((a, b) => a.localeCompare(b)),
    [unitConfigs],
  )

  useEffect(() => {
    let isCurrent = true
    async function load() {
      setIsLoadingConfigs(true)
      setError(null)
      try {
        const configs = await apiRequest<UnitConfigResponse[]>('/api/v1/cutting/unit-configs', { token: authToken })
        if (!isCurrent) return
        setUnitConfigs(configs)
        setSelectedUnitTypeKey((current) => current || configs[0]?.unit_type_key || 'Base Door')
      } catch (loadError) {
        if (!isCurrent) return
        setError(loadError instanceof Error ? loadError.message : 'Could not load unit configurations.')
      } finally {
        if (isCurrent) setIsLoadingConfigs(false)
      }
    }
    load()
    return () => {
      isCurrent = false
    }
  }, [authToken])

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Cutlist generator tester</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">Select a unit type and run runtime generation previews.</p>
        </CardHeader>
        <CardContent className="grid gap-3">
          <Label className="grid gap-1.5 md:max-w-sm">
            Unit type
            <Select
              disabled={isLoadingConfigs || unitTypeKeys.length === 0}
              onChange={(event) => setSelectedUnitTypeKey(event.target.value)}
              value={selectedUnitTypeKey}
            >
              {unitTypeKeys.length === 0 ? <option value="">No unit configs</option> : null}
              {unitTypeKeys.map((unitTypeKey) => (
                <option key={unitTypeKey} value={unitTypeKey}>
                  {unitTypeKey}
                </option>
              ))}
            </Select>
          </Label>
          {error ? <Alert variant="destructive">{error}</Alert> : null}
        </CardContent>
      </Card>
      <CutlistGeneratorTester
        authToken={authToken}
        selectedUnitTypeKey={selectedUnitTypeKey}
        unitConfigs={unitConfigs}
        unitParameterDefinitionsByType={unitParameterDefinitionsByType}
        setUnitParameterDefinitionsByType={setUnitParameterDefinitionsByType}
      />
    </div>
  )
}

function CutlistGeneratorTester({
  authToken,
  selectedUnitTypeKey,
  unitConfigs,
  unitParameterDefinitionsByType,
  setUnitParameterDefinitionsByType,
}: {
  authToken: string
  selectedUnitTypeKey: string
  unitConfigs: UnitConfigResponse[]
  unitParameterDefinitionsByType: UnitParameterDefinitionsByType
  setUnitParameterDefinitionsByType: Dispatch<SetStateAction<UnitParameterDefinitionsByType>>
}) {
  const [draft, setDraft] = useState<CutlistTesterDraft>(() =>
    createCutlistTesterDraft(
      isPreviewUnitType(selectedUnitTypeKey) ? selectedUnitTypeKey : 'Base Door',
      unitConfigs,
      unitParameterDefinitionsByType,
    ),
  )
  const [isGenerating, setIsGenerating] = useState(false)
  const [preview, setPreview] = useState<CutlistPreviewResponse | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [boards, setBoards] = useState<BoardLibraryRow[]>([])
  const [boardsError, setBoardsError] = useState<string | null>(null)
  const [slides, setSlides] = useState<SlideLibraryRow[]>([])
  const [slidesError, setSlidesError] = useState<string | null>(null)

  const activeUnitTypeKey = (draft.useCustomUnitType ? draft.customUnitType : draft.unitType).trim()
  const activeParameterDefinitions = useMemo(
    () =>
      activeUnitTypeKey
        ? resolveUnitParameterDefinitionsForType(activeUnitTypeKey, unitConfigs, unitParameterDefinitionsByType)
        : [],
    [activeUnitTypeKey, unitConfigs, unitParameterDefinitionsByType],
  )

  useEffect(() => {
    let isCurrent = true
    async function loadBoards() {
      setBoardsError(null)
      try {
        const response = await apiRequest<BoardLibraryRow[]>('/api/v1/libraries/boards', { token: authToken })
        if (!isCurrent) return
        setBoards(response)
        setDraft((current) => (current.boardTypeId || !response[0] ? current : { ...current, boardTypeId: response[0].id }))
      } catch (error) {
        if (!isCurrent) return
        setBoardsError(error instanceof Error ? error.message : 'Could not load board types.')
      }
    }
    async function loadSlides() {
      setSlidesError(null)
      try {
        const response = await apiRequest<SlideLibraryRow[]>('/api/v1/libraries/slides', { token: authToken })
        if (!isCurrent) return
        setSlides(response)
      } catch (error) {
        if (!isCurrent) return
        setSlidesError(error instanceof Error ? error.message : 'Could not load slide profiles.')
      }
    }
    loadBoards()
    loadSlides()
    return () => {
      isCurrent = false
    }
  }, [authToken])

  useEffect(() => {
    if (!selectedUnitTypeKey) {
      return
    }
    const handle = window.setTimeout(() => {
      setDraft((current) => {
        const selected = createCutlistTesterDraftFromSelection(
          selectedUnitTypeKey,
          unitConfigs,
          unitParameterDefinitionsByType,
        )
        const resolvedCurrentUnitType = current.useCustomUnitType ? current.customUnitType : current.unitType
        const resolvedSelectedUnitType = selected.useCustomUnitType ? selected.customUnitType : selected.unitType
        return resolvedCurrentUnitType === resolvedSelectedUnitType
          ? current
          : { ...selected, boardTypeId: current.boardTypeId }
      })
    }, 0)
    return () => window.clearTimeout(handle)
  }, [selectedUnitTypeKey, unitConfigs, unitParameterDefinitionsByType])

  function updateDraftField<K extends keyof CutlistTesterDraft>(key: K, value: CutlistTesterDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  function updateParameterValue(parameterKey: string, value: string) {
    setDraft((current) => ({
      ...current,
      parameterValues: { ...current.parameterValues, [parameterKey]: value },
    }))
  }

  function updateDefinitionsForUnitType(unitTypeKey: string, updater: (defs: UnitParameterDefinition[]) => UnitParameterDefinition[]) {
    const resolvedUnitTypeKey = unitTypeKey.trim()
    if (!resolvedUnitTypeKey) return
    setUnitParameterDefinitionsByType((current) => {
      const existing = resolveUnitParameterDefinitionsForType(resolvedUnitTypeKey, unitConfigs, current)
      const updated = normalizeParameterDefinitions(updater(existing))
      return { ...current, [resolvedUnitTypeKey]: updated }
    })
  }

  function updateParameterDefinition(definitionId: string, patch: Partial<UnitParameterDefinition>) {
    updateDefinitionsForUnitType(activeUnitTypeKey, (definitions) =>
      definitions.map((definition) => {
        if (definition.id !== definitionId) {
          return definition
        }
        const inputType = patch.input_type ?? definition.input_type
        const nextSlideField =
          inputType === 'slide'
            ? patch.slide_field ?? definition.slide_field ?? 'side_length'
            : null
        return {
          ...definition,
          ...patch,
          key: patch.key !== undefined ? sanitizeParameterKey(patch.key) : definition.key,
          label: patch.label !== undefined ? patch.label : definition.label,
          default_value: patch.default_value !== undefined ? patch.default_value : definition.default_value,
          input_type: inputType,
          slide_field: nextSlideField,
        }
      }),
    )
  }

  function addParameterDefinition() {
    updateDefinitionsForUnitType(activeUnitTypeKey, (definitions) => [
      ...definitions,
      createEmptyParameterDefinition(definitions.length + 1),
    ])
  }

  function removeParameterDefinition(definitionId: string) {
    updateDefinitionsForUnitType(activeUnitTypeKey, (definitions) => definitions.filter((definition) => definition.id !== definitionId))
  }

  function resetWithUnitDefaults() {
    setDraft((current) => {
      const defaultsForType = (current.useCustomUnitType ? current.customUnitType : current.unitType).trim() || current.unitType
      return {
        ...current,
        ...resolveCutlistTesterDefaults(defaultsForType, unitConfigs, unitParameterDefinitionsByType),
        boardTypeId: current.boardTypeId,
      }
    })
  }

  async function handleGeneratePreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPreviewError(null)
    setIsGenerating(true)
    try {
      const response = await apiRequest<CutlistPreviewResponse>('/api/v1/cutlists/preview', {
        body: buildCutlistPreviewPayload(draft, activeParameterDefinitions, boards, slides),
        method: 'POST',
        token: authToken,
      })
      setPreview(response)
    } catch (error) {
      setPreviewError(error instanceof Error ? error.message : 'Could not generate cutlist preview.')
      setPreview(null)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cutlist generator tester</CardTitle>
        <p className="mt-1 text-sm text-muted-foreground">
          Run the runtime cutlist generator with custom unit inputs and inspect source resolution, runtime mode, and
          generated rows.
        </p>
      </CardHeader>
      <CardContent className="grid gap-4">
        <form className="grid gap-4" onSubmit={handleGeneratePreview}>
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-4">
            <Label className="grid gap-1.5">
              Unit type
              <Select
                onChange={(event) => {
                  const selected = event.target.value
                  if (selected === customUnitTypeOptionValue) {
                    updateDraftField('useCustomUnitType', true)
                    return
                  }
                  updateDraftField('useCustomUnitType', false)
                  updateDraftField('unitType', selected)
                }}
                value={draft.useCustomUnitType ? customUnitTypeOptionValue : draft.unitType}
              >
                {cutlistPreviewUnitTypeOptions.map((unitType) => (
                  <option key={unitType} value={unitType}>
                    {unitType}
                  </option>
                ))}
                <option value={customUnitTypeOptionValue}>Custom unit type</option>
              </Select>
            </Label>
            {draft.useCustomUnitType ? (
              <Label className="grid gap-1.5">
                Custom unit type key
                <Input
                  onChange={(event) => updateDraftField('customUnitType', event.target.value)}
                  placeholder="e.g. Corner Door"
                  value={draft.customUnitType}
                />
              </Label>
            ) : null}
            <Label className="grid gap-1.5">
              Unit #
              <Input
                min={1}
                onChange={(event) => updateDraftField('unitNumber', event.target.value)}
                type="number"
                value={draft.unitNumber}
              />
            </Label>
            <Label className="grid gap-1.5">
              Height (mm)
              <Input
                min={1}
                onChange={(event) => updateDraftField('height', event.target.value)}
                type="number"
                value={draft.height}
              />
            </Label>
            <Label className="grid gap-1.5">
              Width (mm)
              <Input
                min={1}
                onChange={(event) => updateDraftField('width', event.target.value)}
                type="number"
                value={draft.width}
              />
            </Label>
            <Label className="grid gap-1.5">
              Depth (mm)
              <Input
                min={1}
                onChange={(event) => updateDraftField('depth', event.target.value)}
                type="number"
                value={draft.depth}
              />
            </Label>
            <Label className="grid gap-1.5">
              Carcass board
              <Select
                onChange={(event) => updateDraftField('boardTypeId', event.target.value)}
                required
                value={draft.boardTypeId}
              >
                <option value="">Select board type</option>
                {boards.map((board) => (
                  <option key={board.id} value={board.id}>
                    {formatBoardOptionLabel(board)}
                  </option>
                ))}
              </Select>
            </Label>
            {activeParameterDefinitions.map((definition) => (
              <Label className="grid gap-1.5" key={definition.id}>
                {definition.label || definition.key || 'Parameter'}
                {definition.input_type === 'number' ? (
                  <Input
                    min={0}
                    onChange={(event) => updateParameterValue(definition.key, event.target.value)}
                    placeholder={definition.key}
                    type="number"
                    value={draft.parameterValues[definition.key] ?? definition.default_value}
                  />
                ) : (
                  <>
                    <Select
                      onChange={(event) => updateParameterValue(definition.key, event.target.value)}
                      value={draft.parameterValues[definition.key] ?? definition.default_value}
                    >
                      <option value="">Select slide profile</option>
                      {slides.map((slide) => (
                        <option key={slide.id} value={slide.id}>
                          {formatSlideOptionLabel(slide)}
                        </option>
                      ))}
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Uses{' '}
                      <span className="font-mono">
                        {slideMeasurementFieldLabel(definition.slide_field ?? 'side_length')}
                      </span>{' '}
                      as <span className="font-mono">{definition.key}</span>
                    </p>
                  </>
                )}
              </Label>
            ))}
          </div>

          <div className="grid gap-3 rounded-[var(--card-radius)] border border-border bg-muted/20 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold">Unit parameter definitions</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Configure which parameter inputs are available for <span className="font-mono">{activeUnitTypeKey}</span>.
                </p>
              </div>
              <Badge variant="outline">{activeParameterDefinitions.length} parameters</Badge>
            </div>
            {!activeUnitTypeKey.trim() ? (
              <Alert className="text-xs">Enter a custom unit type key before defining parameters.</Alert>
            ) : (
              <>
                <div className="grid gap-2">
                  {activeParameterDefinitions.map((definition) => (
                    <div
                      className="grid gap-2 rounded-[var(--radius)] border border-border bg-card p-2 md:grid-cols-[1.2fr_1.2fr_0.9fr_1fr_auto]"
                      key={definition.id}
                    >
                      <Label className="grid gap-1 text-xs">
                        Parameter key
                        <Input
                          className="h-8"
                          onChange={(event) => updateParameterDefinition(definition.id, { key: event.target.value })}
                          placeholder="param_key"
                          value={definition.key}
                        />
                      </Label>
                      <Label className="grid gap-1 text-xs">
                        Input label
                        <Input
                          className="h-8"
                          onChange={(event) => updateParameterDefinition(definition.id, { label: event.target.value })}
                          placeholder="Label"
                          value={definition.label}
                        />
                      </Label>
                      <Label className="grid gap-1 text-xs">
                        Input type
                        <Select
                          className="h-8"
                          onChange={(event) =>
                            updateParameterDefinition(definition.id, {
                              input_type: event.target.value as UnitParameterInputType,
                            })
                          }
                          value={definition.input_type}
                        >
                          <option value="number">Number</option>
                          <option value="slide">Slide-linked</option>
                        </Select>
                      </Label>
                      {definition.input_type === 'number' ? (
                        <Label className="grid gap-1 text-xs">
                          Default value
                          <Input
                            className="h-8"
                            onChange={(event) => updateParameterDefinition(definition.id, { default_value: event.target.value })}
                            placeholder="Default"
                            type="number"
                            value={definition.default_value}
                          />
                        </Label>
                      ) : (
                        <Label className="grid gap-1 text-xs">
                          Slide measurement
                          <Select
                            className="h-8"
                            onChange={(event) =>
                              updateParameterDefinition(definition.id, {
                                slide_field: event.target.value as SlideMeasurementField,
                              })
                            }
                            value={definition.slide_field ?? 'side_length'}
                          >
                            {slideMeasurementFieldOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </Select>
                        </Label>
                      )}
                      <div className="flex items-end">
                        <Button
                          aria-label="Delete parameter definition"
                          onClick={() => removeParameterDefinition(definition.id)}
                          size="icon"
                          type="button"
                          variant="ghost"
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
                <Button onClick={addParameterDefinition} type="button" variant="outline">
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  Add parameter
                </Button>
              </>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={resetWithUnitDefaults} type="button" variant="outline">
              Load defaults from unit config
            </Button>
            <Button disabled={isGenerating} type="submit">
              {isGenerating ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              Generate preview
            </Button>
          </div>
        </form>

        {boardsError ? <Alert variant="destructive">{boardsError}</Alert> : null}
        {slidesError ? <Alert variant="destructive">{slidesError}</Alert> : null}
        {previewError ? <Alert variant="destructive">{previewError}</Alert> : null}

        {preview ? (
          <div className="grid gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={runtimeModeBadgeVariant(preview.runtime_mode)}>Runtime: {preview.runtime_mode}</Badge>
              <Badge variant="outline">Units: {preview.unit_sources.length}</Badge>
              <Badge variant={preview.readiness.cutlist_valid ? 'outline' : 'warning'}>
                {preview.readiness.cutlist_valid ? 'Cutlist ready' : `${preview.readiness.warning_count} cutlist warnings`}
              </Badge>
              <Badge variant="outline">
                Sources: {Array.from(new Set(preview.unit_sources.map((row) => row.source))).join(', ') || 'n/a'}
              </Badge>
            </div>

            {preview.validation_warnings.length > 0 ? (
              <Alert className="text-xs" variant="warning">
                <div className="grid gap-1">
                  {preview.validation_warnings.map((warning, index) => (
                    <p key={`${warning.section}-${warning.unit_number}-${warning.row_desc}-${index}`}>
                      {`${formatCutlistWarningSource(warning)} / ${warning.row_desc}: ${warning.reason}`}
                    </p>
                  ))}
                </div>
              </Alert>
            ) : null}

            <TableContainer>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Unit #</TableHead>
                    <TableHead>Type key</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Ruleset</TableHead>
                    <TableHead>Unit config</TableHead>
                    <TableHead>Note</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.unit_sources.map((row) => (
                    <TableRow key={`${row.unit_number}-${row.unit_type_key}-${row.source}`}>
                      <TableCell>{row.unit_number}</TableCell>
                      <TableCell>{row.unit_type_key}</TableCell>
                      <TableCell>{row.source}</TableCell>
                      <TableCell>{row.ruleset_id ?? '-'}</TableCell>
                      <TableCell>{row.unit_config_id ?? '-'}</TableCell>
                      <TableCell>{row.note ?? '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <CutlistPreviewRowsTable rows={preview.carcass} title="Carcass rows" />
            <CutlistPreviewRowsTable rows={preview.panels} title="Panel rows" />
            <CutlistPreviewRowsTable rows={preview.hardware} title="Hardware rows" />
            <CutlistPreviewRowsTable rows={preview.extras} title="Extra rows" />

            <TableContainer>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Section</TableHead>
                    <TableHead>Desc</TableHead>
                    <TableHead>L</TableHead>
                    <TableHead>W</TableHead>
                    <TableHead>Qty</TableHead>
                    <TableHead>Edges</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.runtime_rows.length === 0 ? (
                    <TableRow>
                      <TableCell className="text-muted-foreground" colSpan={6}>
                        No runtime rows generated.
                      </TableCell>
                    </TableRow>
                  ) : (
                    preview.runtime_rows.map((row, index) => (
                      <TableRow key={`${row.unit_number}-${row.section}-${row.desc}-${index}`}>
                        <TableCell>{row.section}</TableCell>
                        <TableCell>{row.desc}</TableCell>
                        <TableCell>{row.length}</TableCell>
                        <TableCell>{row.width}</TableCell>
                        <TableCell>{row.qty}</TableCell>
                        <TableCell>{formatRuntimeEdges(row)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function CutlistPreviewRowsTable({ rows, title }: { rows: CutlistPreviewRow[]; title: string }) {
  return (
    <div className="grid gap-2">
      <p className="text-sm font-semibold">{title}</p>
      <TableContainer>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Unit #</TableHead>
              <TableHead>Desc</TableHead>
              <TableHead>L</TableHead>
              <TableHead>W</TableHead>
              <TableHead>Qty</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell className="text-muted-foreground" colSpan={5}>
                  No rows generated.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row, index) => (
                <TableRow key={`${row.unit_number}-${row.desc}-${index}`}>
                  <TableCell>{row.unit_number}</TableCell>
                  <TableCell>{row.desc}</TableCell>
                  <TableCell>{row.length}</TableCell>
                  <TableCell>{row.width}</TableCell>
                  <TableCell>{row.qty}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  )
}

function mapRulesetToDraft(ruleset: CuttingRulesetResponse): CuttingRulesetDraft {
  return {
    description: ruleset.description,
    id: ruleset.id,
    is_default: ruleset.is_default,
    name: ruleset.name,
    rows: ruleset.rows.map((row) => ({
      can_rotate: row.can_rotate,
      condition_formula: row.condition_formula,
      description: row.description,
      edge_long_1: row.edge_long_1,
      edge_long_2: row.edge_long_2,
      edge_short_1: row.edge_short_1,
      edge_short_2: row.edge_short_2,
      grain_direction: row.grain_direction,
      id: row.id,
      length_formula: row.length_formula,
      meta: row.meta ?? {},
      qty_formula: row.qty_formula,
      section: row.section,
      sort_order: row.sort_order,
      width_formula: row.width_formula,
    })),
    status: ruleset.status,
    unit_config_id: ruleset.unit_config_id,
    unit_type_key: ruleset.unit_type_key,
    version: ruleset.version,
  }
}

function toRulesetRequest(draft: CuttingRulesetDraft): CuttingRulesetRequest {
  return {
    description: draft.description,
    is_default: draft.is_default,
    name: draft.name,
    rows: draft.rows.map((row) => ({
      can_rotate: row.can_rotate,
      condition_formula: row.condition_formula,
      description: row.description,
      edge_long_1: row.edge_long_1,
      edge_long_2: row.edge_long_2,
      edge_short_1: row.edge_short_1,
      edge_short_2: row.edge_short_2,
      grain_direction: row.grain_direction,
      length_formula: row.length_formula,
      meta: row.meta ?? {},
      qty_formula: row.qty_formula,
      section: row.section,
      sort_order: row.sort_order,
      width_formula: row.width_formula,
    })),
    status: draft.status,
    unit_config_id: draft.unit_config_id,
    unit_type_key: draft.unit_type_key,
    version: draft.version,
  }
}

function toRulesetSummary(ruleset: CuttingRulesetResponse): CuttingRulesetSummaryResponse {
  return {
    company_id: ruleset.company_id,
    created_at: ruleset.created_at,
    description: ruleset.description,
    id: ruleset.id,
    is_default: ruleset.is_default,
    name: ruleset.name,
    status: ruleset.status,
    unit_config_id: ruleset.unit_config_id,
    unit_type_key: ruleset.unit_type_key,
    updated_at: ruleset.updated_at,
    version: ruleset.version,
  }
}

function createStarterRulesetRequest(
  unitTypeKey: string,
  unitConfigId: string | null,
  label: string,
): CuttingRulesetRequest {
  const starterRow = createDefaultRow(10)
  return {
    unit_config_id: unitConfigId,
    unit_type_key: unitTypeKey,
    name: `Default ${label}`,
    description: 'Starter ruleset for a custom unit type.',
    status: 'draft',
    version: 1,
    is_default: false,
    rows: [
      {
        sort_order: starterRow.sort_order,
        section: starterRow.section,
        description: starterRow.description,
        length_formula: starterRow.length_formula,
        width_formula: starterRow.width_formula,
        qty_formula: starterRow.qty_formula,
        condition_formula: starterRow.condition_formula,
        grain_direction: starterRow.grain_direction,
        can_rotate: starterRow.can_rotate,
        edge_long_1: starterRow.edge_long_1,
        edge_long_2: starterRow.edge_long_2,
        edge_short_1: starterRow.edge_short_1,
        edge_short_2: starterRow.edge_short_2,
        meta: starterRow.meta,
      },
    ],
  }
}

function createDefaultRow(sortOrder: number): CuttingRuleRowDraft {
  return {
    can_rotate: true,
    condition_formula: '',
    description: 'New row',
    edge_long_1: false,
    edge_long_2: false,
    edge_short_1: false,
    edge_short_2: false,
    grain_direction: 'none',
    id: createLocalRowId(),
    length_formula: '',
    meta: {},
    qty_formula: '1',
    section: 'carcass',
    sort_order: sortOrder,
    width_formula: '',
  }
}

function createLocalRowId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `draft-${crypto.randomUUID()}`
  }
  return `draft-${Date.now()}-${Math.round(Math.random() * 100_000)}`
}

function parsePositiveInteger(value: string, fallback: number) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback
  }
  return Math.floor(parsed)
}

function isPreviewUnitType(value: string): value is UnitType {
  return cutlistPreviewUnitTypeOptions.includes(value as UnitType)
}

function createCutlistTesterDraft(
  unitType: UnitType,
  unitConfigs: UnitConfigResponse[],
  unitParameterDefinitionsByType: UnitParameterDefinitionsByType,
): CutlistTesterDraft {
  const defaults = resolveCutlistTesterDefaults(unitType, unitConfigs, unitParameterDefinitionsByType)
  return {
    unitType,
    customUnitType: '',
    useCustomUnitType: false,
    ...defaults,
  }
}

function createCutlistTesterDraftFromSelection(
  selectedUnitTypeKey: string,
  unitConfigs: UnitConfigResponse[],
  unitParameterDefinitionsByType: UnitParameterDefinitionsByType,
): CutlistTesterDraft {
  if (isPreviewUnitType(selectedUnitTypeKey)) {
    return createCutlistTesterDraft(selectedUnitTypeKey, unitConfigs, unitParameterDefinitionsByType)
  }
  const fallbackDefaults = resolveCutlistTesterDefaults(selectedUnitTypeKey, unitConfigs, unitParameterDefinitionsByType)
  return {
    unitType: 'Base Door',
    customUnitType: selectedUnitTypeKey,
    useCustomUnitType: true,
    ...fallbackDefaults,
  }
}

function resolveCutlistTesterDefaults(
  unitType: string,
  unitConfigs: UnitConfigResponse[],
  unitParameterDefinitionsByType: UnitParameterDefinitionsByType,
) {
  const config = findUnitConfigForType(unitType, unitConfigs)
  const variantConfig = config?.variant_config ?? {}
  const parameterDefinitions = resolveUnitParameterDefinitionsForType(unitType, unitConfigs, unitParameterDefinitionsByType)
  const parameterValues: Record<string, string> = {}
  for (const definition of parameterDefinitions) {
    parameterValues[definition.key] = defaultParameterValueForDefinition(definition, variantConfig)
  }

  return {
    unitNumber: '1',
    boardTypeId: '',
    height: String(config?.default_height ?? 780),
    width: String(config?.default_width ?? 600),
    depth: String(config?.default_depth ?? 560),
    parameterValues,
  }
}

function canonicalTesterUnitType(unitType: string): string {
  if (unitType === 'Base Draw' || unitType === 'Base Drawer' || /Base\s+\d+\s+Draw/.test(unitType)) return 'Base Draw'
  if (unitType === 'Base Door' || /Base\s+\d+\s+Door/.test(unitType)) return 'Base Door'
  if (unitType === 'Wall Door' || /Wall\s+\d+\s+Door/.test(unitType)) return 'Wall Door'
  if (unitType === 'Tall Door' || unitType === 'Tall Standard') return 'Tall Door'
  return unitType
}

function unitTypeConfigCandidates(unitType: string): string[] {
  const canonical = canonicalTesterUnitType(unitType)
  if (canonical === 'Base Draw') return ['Base Draw', 'Base Drawer', 'Base 3 Draw', 'Base 2 Draw', 'Base 1 Draw', 'Base 4 Draw']
  if (canonical === 'Base Door') return ['Base Door', 'Base 2 Door', 'Base 1 Door']
  if (canonical === 'Wall Door') return ['Wall Door', 'Wall 2 Door', 'Wall 1 Door']
  if (canonical === 'Tall Door') return ['Tall Door', 'Tall Standard']
  return [unitType]
}

function findUnitConfigForType(unitType: string, unitConfigs: UnitConfigResponse[]) {
  const candidates = new Set(unitTypeConfigCandidates(unitType))
  for (const candidate of candidates) {
    const match = unitConfigs.find((item) => item.unit_type_key === candidate)
    if (match) return match
  }
  return null
}

function buildCutlistPreviewPayload(
  draft: CutlistTesterDraft,
  parameterDefinitions: UnitParameterDefinition[],
  boards: BoardLibraryRow[],
  slides: SlideLibraryRow[],
) {
  const extraParams: Record<string, number | boolean> = {}
  const resolvedUnitType = draft.useCustomUnitType ? (draft.customUnitType.trim() || 'Custom Unit') : draft.unitType
  const selectedBoard = boards.find((board) => board.id === draft.boardTypeId)

  for (const definition of parameterDefinitions) {
    const parameterKey = sanitizeParameterKey(definition.key)
    if (!parameterKey) continue
    const rawValue = (draft.parameterValues[parameterKey] ?? definition.default_value ?? '').trim()
    if (!rawValue) continue

    if (definition.input_type === 'number') {
      const numeric = parseOptionalNonNegativeInteger(rawValue)
      if (numeric !== null) {
        extraParams[parameterKey] = numeric
      }
      continue
    }

    const slide = slides.find((item) => item.id === rawValue)
    if (!slide) continue
    const measurementValue = numberOrNullFromUnknown(slide[definition.slide_field ?? 'side_length'])
    if (measurementValue !== null) {
      extraParams[parameterKey] = measurementValue
    }
  }

  return {
    units: [
      {
        unit_number: parsePositiveInteger(draft.unitNumber, 1),
        unit_type: resolvedUnitType,
        height: parsePositiveInteger(draft.height, 780),
        width: parsePositiveInteger(draft.width, 600),
        depth: parsePositiveInteger(draft.depth, 560),
        board_type_id: selectedBoard?.id ?? '',
        extra_params: extraParams,
      },
    ],
  }
}

function formatBoardOptionLabel(board: BoardLibraryRow): string {
  return `${board.brand} ${board.material} (${board.thickness}mm)`
}

function parseOptionalNonNegativeInteger(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const parsed = Number(trimmed)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.floor(parsed)
}

function numberOrNullFromUnknown(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.floor(value)
  }
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) {
      return Math.floor(parsed)
    }
  }
  return null
}

function createLocalParameterId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `param-${crypto.randomUUID()}`
  }
  return `param-${Date.now()}-${Math.round(Math.random() * 100_000)}`
}

function createEmptyParameterDefinition(sequence: number): UnitParameterDefinition {
  return {
    id: createLocalParameterId(),
    key: `param_${sequence}`,
    label: `Parameter ${sequence}`,
    input_type: 'number',
    default_value: '',
    slide_field: null,
  }
}

function sanitizeParameterKey(value: string): string {
  const trimmed = value.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '_').replace(/_+/g, '_')
  const stripped = trimmed.replace(/^_+/, '')
  if (!stripped) return ''
  const startsWithLetterOrUnderscore = /^[A-Za-z_]/.test(stripped)
  return startsWithLetterOrUnderscore ? stripped : `param_${stripped}`
}

function parameterLabelFromKey(key: string): string {
  return key
    .split('_')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

function defaultParameterValueForDefinition(definition: UnitParameterDefinition, variantConfig: Record<string, unknown>): string {
  if (definition.input_type === 'slide') {
    return definition.default_value?.trim() ?? ''
  }
  const fromVariant = numberOrNullFromUnknown(variantConfig[definition.key])
  if (fromVariant !== null) {
    return String(fromVariant)
  }
  const trimmed = definition.default_value.trim()
  if (!trimmed) return ''
  return parseOptionalNonNegativeInteger(trimmed) === null ? '' : trimmed
}

function normalizeParameterDefinitions(definitions: UnitParameterDefinition[]): UnitParameterDefinition[] {
  const seenKeys = new Set<string>()
  const normalized: UnitParameterDefinition[] = []
  for (const definition of definitions) {
    const key = sanitizeParameterKey(definition.key)
    if (!key || seenKeys.has(key)) continue
    seenKeys.add(key)
    const inputType = definition.input_type === 'slide' ? 'slide' : 'number'
    normalized.push({
      id: definition.id || createLocalParameterId(),
      key,
      label: definition.label.trim() || parameterLabelFromKey(key),
      input_type: inputType,
      default_value: inputType === 'number' ? definition.default_value.trim() : '',
      slide_field: inputType === 'slide' ? definition.slide_field ?? 'side_length' : null,
    })
  }
  return normalized
}

function cloneUnitParameterDefinitions(definitions: UnitParameterDefinition[]): UnitParameterDefinition[] {
  return definitions.map((definition) => ({ ...definition }))
}

function cloneUnitParameterDefinitionsByType(
  definitionsByType: UnitParameterDefinitionsByType,
): UnitParameterDefinitionsByType {
  const next: UnitParameterDefinitionsByType = {}
  for (const [unitType, definitions] of Object.entries(definitionsByType)) {
    next[unitType] = cloneUnitParameterDefinitions(definitions)
  }
  return next
}

function deriveParameterDefinitionsFromUnitConfig(
  unitType: string,
  unitConfigs: UnitConfigResponse[],
): UnitParameterDefinition[] {
  const config = findUnitConfigForType(unitType, unitConfigs)
  if (!config) return []
  const keys = Object.entries(config.variant_config ?? {})
    .filter(([key, value]) => /^[A-Za-z_][A-Za-z0-9_]*$/.test(key) && numberOrNullFromUnknown(value) !== null)
    .map(([key, value]) => ({ key, value: numberOrNullFromUnknown(value) as number }))
    .sort((a, b) => a.key.localeCompare(b.key))
  return keys.map((entry) => ({
    id: `config-${config.id}-${entry.key}`,
    key: entry.key,
    label: parameterLabelFromKey(entry.key),
    input_type: 'number',
    default_value: String(entry.value),
    slide_field: null,
  }))
}

function resolveUnitParameterDefinitionsForType(
  unitType: string,
  unitConfigs: UnitConfigResponse[],
  unitParameterDefinitionsByType: UnitParameterDefinitionsByType,
): UnitParameterDefinition[] {
  const trimmedUnitType = unitType.trim()
  if (!trimmedUnitType) return []
  const directDefinitions = unitParameterDefinitionsByType[trimmedUnitType]
  if (directDefinitions && directDefinitions.length > 0) {
    return normalizeParameterDefinitions(cloneUnitParameterDefinitions(directDefinitions))
  }

  const canonicalType = canonicalTesterUnitType(trimmedUnitType)
  const canonicalDefinitions = unitParameterDefinitionsByType[canonicalType] ?? defaultUnitParameterDefinitionsByType[canonicalType]
  if (canonicalDefinitions && canonicalDefinitions.length > 0) {
    return normalizeParameterDefinitions(cloneUnitParameterDefinitions(canonicalDefinitions))
  }

  return normalizeParameterDefinitions(deriveParameterDefinitionsFromUnitConfig(trimmedUnitType, unitConfigs))
}

function formatSlideOptionLabel(slide: SlideLibraryRow) {
  const code = slide.code ? ` (${slide.code})` : ''
  return `${slide.brand} ${slide.model}${code}`
}

function slideMeasurementFieldLabel(field: SlideMeasurementField) {
  const match = slideMeasurementFieldOptions.find((option) => option.value === field)
  return match?.label ?? field
}

function runtimeModeBadgeVariant(runtimeMode: CutlistPreviewResponse['runtime_mode']) {
  if (runtimeMode === 'ruleset') return 'default'
  if (runtimeMode === 'mixed') return 'warning'
  return 'outline'
}

function formatCutlistWarningSource(warning: CutlistValidationWarning) {
  return warning.source === 'quote_panel' ? 'Quote panel' : `Unit ${warning.unit_number}`
}

function formatRuntimeEdges(row: CutlistRuntimeRow) {
  const edges: string[] = []
  if (row.edge_long_1) edges.push('L1')
  if (row.edge_long_2) edges.push('L2')
  if (row.edge_short_1) edges.push('S1')
  if (row.edge_short_2) edges.push('S2')
  return edges.length > 0 ? edges.join(', ') : '-'
}

function getAvailableFormulaVariables(
  unitConfigs: UnitConfigResponse[],
  unitTypeKey: string,
  unitParameterDefinitionsByType: UnitParameterDefinitionsByType,
) {
  const definitions = resolveUnitParameterDefinitionsForType(unitTypeKey, unitConfigs, unitParameterDefinitionsByType)
  const variables = new Set<string>(coreFormulaVariables)
  for (const definition of definitions) {
    if (definition.key) {
      variables.add(definition.key)
    }
  }
  if (definitions.length === 0) {
    const config = findUnitConfigForType(unitTypeKey, unitConfigs)
    if (config) {
      for (const [key, value] of Object.entries(config.variant_config ?? {})) {
        if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(key) && numberOrNullFromUnknown(value) !== null) {
          variables.add(key)
        }
      }
    }
  }
  if (variables.has('num_drawers') || canonicalTesterUnitType(unitTypeKey) === 'Base Draw') {
    for (const variable of drawerDerivedFormulaVariables) {
      variables.add(variable)
    }
  }
  return Array.from(variables).sort((a, b) => a.localeCompare(b))
}

function validateDraftFormulas(
  rows: CuttingRuleRowDraft[],
  availableVariables: string[],
): Record<string, Partial<Record<FormulaFieldKey, string>>> {
  const errors: Record<string, Partial<Record<FormulaFieldKey, string>>> = {}
  for (const row of rows) {
    const rowErrors: Partial<Record<FormulaFieldKey, string>> = {}

    const lengthError = validateFormulaExpression('length_formula', row.length_formula, availableVariables)
    if (lengthError) rowErrors.length_formula = lengthError

    const widthError = validateFormulaExpression('width_formula', row.width_formula, availableVariables)
    if (widthError) rowErrors.width_formula = widthError

    const qtyError = validateFormulaExpression('qty_formula', row.qty_formula, availableVariables)
    if (qtyError) rowErrors.qty_formula = qtyError

    const conditionError = validateFormulaExpression('condition_formula', row.condition_formula, availableVariables)
    if (conditionError) rowErrors.condition_formula = conditionError

    if (Object.keys(rowErrors).length > 0) {
      errors[row.id] = rowErrors
    }
  }
  return errors
}

function validateFormulaExpression(
  field: FormulaFieldKey,
  expression: string,
  availableVariables: string[],
): string | null {
  const trimmed = expression.trim()
  if (!trimmed) {
    return field === 'qty_formula' ? 'Quantity formula is required.' : null
  }
  if (!/^[0-9A-Za-z_+\-*/().<>=!&|,%\s]*$/.test(trimmed)) {
    return 'Contains unsupported characters.'
  }
  if (!hasBalancedParentheses(trimmed)) {
    return 'Parentheses are not balanced.'
  }

  const validIdentifiers = new Set<string>(availableVariables)
  const unknownTokens = (trimmed.match(/[A-Za-z_][A-Za-z0-9_]*/g) ?? []).filter(
    (token) => !validIdentifiers.has(token) && !formulaKeywords.has(token.toLowerCase()),
  )
  if (unknownTokens.length > 0) {
    return `Unknown token(s): ${Array.from(new Set(unknownTokens)).join(', ')}`
  }
  return null
}

function hasBalancedParentheses(value: string) {
  let depth = 0
  for (const char of value) {
    if (char === '(') depth += 1
    if (char === ')') {
      depth -= 1
      if (depth < 0) return false
    }
  }
  return depth === 0
}
