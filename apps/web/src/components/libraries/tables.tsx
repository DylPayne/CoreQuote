import { Eye, Plus, Save, Trash2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'

import { emptyAccessoryRule, formatBoardGrainPolicy, formatDrawerSystemKind, formatHingeLabel, formatSlideLabel } from './helpers'
import type { BoardGrainPolicy, BoardTypeRow, DrawerSystemConfig, DrawerSystemKind, ExtraCategoryRow, ExtraRow, HandleRow, HardwareAccessoryConditionField, HardwareAccessoryConditionOperator, HardwareAccessoryConfig, HardwareAccessoryQuantityRule, HardwareAccessoryRule, HingeRow, PriceItemType, SlideRow, SupplierRow } from './types'

const boardGrainPolicyOptions: Array<{ label: string; value: BoardGrainPolicy }> = [
  { label: 'Grain required', value: 'required' },
  { label: 'Optional grain', value: 'optional' },
  { label: 'No grain', value: 'none' },
]

type RowSelectionProps = {
  onSelectionChange?: (itemId: string, checked: boolean) => void
  selectedIds?: string[]
}

function isSelected(selectedIds: string[] | undefined, itemId: string) {
  return selectedIds?.includes(itemId) ?? false
}

function EmptyTableMessage({ detail, title }: { detail: string; title: string }) {
  return (
    <div className="grid gap-1 py-3">
      <p className="font-medium text-foreground">{title}</p>
      <p className="text-sm leading-5 text-muted-foreground">{detail}</p>
    </div>
  )
}

export type HardwareAccessoryOptions = Record<Exclude<PriceItemType, 'board'>, Array<{ label: string; value: string }>>

const accessoryQuantityRules: Array<{ label: string; value: HardwareAccessoryQuantityRule }> = [
  { label: 'Fixed quantity', value: 'fixed' },
  { label: 'Per unit', value: 'per_unit' },
  { label: 'Per drawer', value: 'per_drawer' },
  { label: 'Per slide pair', value: 'per_slide_pair' },
  { label: 'Per hinge', value: 'per_hinge' },
  { label: 'Per door', value: 'per_door' },
]

const accessoryConditionFields: Array<{ label: string; value: HardwareAccessoryConditionField }> = [
  { label: 'Always', value: 'always' },
  { label: 'Drawer front height', value: 'drawer_front_height' },
  { label: 'Drawer side height', value: 'drawer_side_height' },
  { label: 'Unit width', value: 'unit_width' },
  { label: 'Unit height', value: 'unit_height' },
  { label: 'Unit depth', value: 'unit_depth' },
  { label: 'Drawer count', value: 'num_drawers' },
  { label: 'Door count', value: 'door_count' },
  { label: 'Hinge count', value: 'hinge_count' },
  { label: 'Hardware variant', value: 'hardware_variant' },
  { label: 'Load class', value: 'load_class' },
]

const accessoryConditionOperators: Array<{ label: string; value: HardwareAccessoryConditionOperator }> = [
  { label: 'Always', value: 'always' },
  { label: 'Greater than', value: 'greater_than' },
  { label: 'At least', value: 'greater_than_or_equal' },
  { label: 'Less than', value: 'less_than' },
  { label: 'At most', value: 'less_than_or_equal' },
  { label: 'Equals', value: 'equals' },
  { label: 'Does not equal', value: 'not_equals' },
]

function accessoryItemTypeLabel(itemType: Exclude<PriceItemType, 'board'>) {
  if (itemType === 'extra') return 'Extra'
  if (itemType === 'handle') return 'Handle'
  if (itemType === 'hinge') return 'Hinge'
  return 'Slide'
}

function accessoryOptionLabel(rule: HardwareAccessoryRule, options: HardwareAccessoryOptions) {
  const itemOptions = options[rule.item_type] ?? []
  return itemOptions.find((option) => option.value === rule.item_ref_id)?.label ?? rule.name.trim()
}

function accessoryDisplayLabel(rule: HardwareAccessoryRule, options: HardwareAccessoryOptions) {
  const label = accessoryOptionLabel(rule, options)
  if (label) return label
  if (rule.item_ref_id) return 'Selected catalog item'
  return 'Custom accessory'
}

function accessoryQuantityLabel(rule: HardwareAccessoryRule) {
  return accessoryQuantityRules.find((option) => option.value === rule.quantity_rule)?.label ?? rule.quantity_rule
}

function accessoryConditionSummary(rule: HardwareAccessoryRule) {
  const condition = rule.condition ?? emptyAccessoryRule().condition
  if (condition.field === 'always' || condition.operator === 'always') return 'Always'
  const field = accessoryConditionFields.find((option) => option.value === condition.field)?.label ?? condition.field
  const operator = accessoryConditionOperators.find((option) => option.value === condition.operator)?.label ?? condition.operator
  const value = condition.value_text?.trim() || (condition.value_number !== null && condition.value_number !== undefined ? String(condition.value_number) : '')
  return value ? `${field} ${operator.toLowerCase()} ${value}` : `${field} ${operator.toLowerCase()}`
}

function isAccessoryRuleComplete(rule: HardwareAccessoryRule | null | undefined) {
  return Boolean(rule?.item_ref_id || rule?.name.trim())
}

export function HardwareAccessoryConfigEditor({
  config,
  onChange,
  options,
}: {
  config: HardwareAccessoryConfig
  onChange: (config: HardwareAccessoryConfig) => void
  options: HardwareAccessoryOptions
}) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const accessories = Array.isArray(config.accessories) ? config.accessories : []
  const editingRule = editingIndex === null ? null : accessories[editingIndex] ?? null
  const editingItemOptions = editingRule ? options[editingRule.item_type] ?? [] : []
  const editingCondition = editingRule?.condition ?? emptyAccessoryRule().condition

  function updateRule(index: number, patch: Partial<HardwareAccessoryRule>) {
    onChange({
      ...config,
      accessories: accessories.map((rule, ruleIndex) => (ruleIndex === index ? { ...rule, ...patch } : rule)),
    })
  }

  function updateCondition(index: number, patch: Partial<HardwareAccessoryRule['condition']>) {
    const current = accessories[index] ?? emptyAccessoryRule()
    updateRule(index, { condition: { ...current.condition, ...patch } })
  }

  function addRule() {
    const nextIndex = accessories.length
    onChange({ ...config, accessories: [...accessories, emptyAccessoryRule()] })
    setEditingIndex(nextIndex)
  }

  function removeRule(index: number) {
    onChange({ ...config, accessories: accessories.filter((_, ruleIndex) => ruleIndex !== index) })
    setEditingIndex((current) => {
      if (current === null) return null
      if (current === index) return null
      return current > index ? current - 1 : current
    })
  }

  function closeEditor(discardEmpty = true) {
    if (discardEmpty && editingIndex !== null) {
      const current = accessories[editingIndex]
      if (current && !isAccessoryRuleComplete(current)) {
        removeRule(editingIndex)
        return
      }
    }
    setEditingIndex(null)
  }

  return (
    <div className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:col-span-4">
      <Dialog
        open={Boolean(editingRule)}
        onOpenChange={(open) => {
          if (!open) closeEditor()
        }}
        title="Accessory Details"
        description={editingRule ? accessoryDisplayLabel(editingRule, options) : undefined}
        size="wide"
      >
        {editingRule && editingIndex !== null ? (
          <div className="grid gap-3 md:grid-cols-4">
            <Label className="grid gap-1.5">
              Accessory type
              <Select
                value={editingRule.item_type}
                onChange={(event) => updateRule(editingIndex, {
                  code: '',
                  item_ref_id: '',
                  item_type: event.target.value as Exclude<PriceItemType, 'board'>,
                  name: '',
                  supplier: '',
                })}
              >
                <option value="extra">Extra</option>
                <option value="handle">Handle</option>
                <option value="hinge">Hinge</option>
                <option value="slide">Slide</option>
              </Select>
            </Label>
            <Label className="grid gap-1.5 md:col-span-2">
              Catalog item
              <Select
                value={editingRule.item_ref_id}
                onChange={(event) => {
                  const selected = editingItemOptions.find((option) => option.value === event.target.value)
                  updateRule(editingIndex, {
                    code: '',
                    item_ref_id: event.target.value,
                    name: selected?.label ?? '',
                    supplier: '',
                  })
                }}
              >
                <option value="">Custom item</option>
                {editingItemOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </Label>
            {!editingRule.item_ref_id ? (
              <Label className="grid gap-1.5 md:col-span-4">
                Custom accessory
                <Input value={editingRule.name} onChange={(event) => updateRule(editingIndex, { name: event.target.value })} />
              </Label>
            ) : null}
            <Label className="grid gap-1.5">
              Quantity
              <Input value={String(editingRule.quantity)} onChange={(event) => updateRule(editingIndex, { quantity: Number(event.target.value) || 0 })} />
            </Label>
            <Label className="grid gap-1.5">
              Applies per
              <Select value={editingRule.quantity_rule} onChange={(event) => updateRule(editingIndex, { quantity_rule: event.target.value as HardwareAccessoryQuantityRule })}>
                {accessoryQuantityRules.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </Label>
            <Label className="grid gap-1.5">
              Unit
              <Input value={editingRule.uom} onChange={(event) => updateRule(editingIndex, { uom: event.target.value })} />
            </Label>
            <Label className="flex items-center gap-2 pt-6 text-sm">
              <Checkbox checked={editingRule.required} onChange={(event) => updateRule(editingIndex, { required: event.target.checked })} />
              Required
            </Label>
            {!editingRule.required ? (
              <Label className="flex items-center gap-2 text-sm md:col-span-4">
                <Checkbox checked={editingRule.enabled} onChange={(event) => updateRule(editingIndex, { enabled: event.target.checked })} />
                Include this optional accessory by default
              </Label>
            ) : null}
            <details className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:col-span-4">
              <summary className="cursor-pointer text-sm font-medium">Advanced conditions</summary>
              <div className="mt-3 grid gap-3 md:grid-cols-4">
                <Label className="grid gap-1.5">
                  Condition field
                  <Select value={editingCondition.field} onChange={(event) => updateCondition(editingIndex, { field: event.target.value as HardwareAccessoryConditionField })}>
                    {accessoryConditionFields.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </Label>
                <Label className="grid gap-1.5">
                  Condition
                  <Select value={editingCondition.operator} onChange={(event) => updateCondition(editingIndex, { operator: event.target.value as HardwareAccessoryConditionOperator })}>
                    {accessoryConditionOperators.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </Label>
                <Label className="grid gap-1.5">
                  Number value
                  <Input value={editingCondition.value_number ?? ''} onChange={(event) => updateCondition(editingIndex, { value_number: event.target.value === '' ? null : Number(event.target.value) })} />
                </Label>
                <Label className="grid gap-1.5">
                  Text value
                  <Input value={editingCondition.value_text ?? ''} onChange={(event) => updateCondition(editingIndex, { value_text: event.target.value })} />
                </Label>
              </div>
            </details>
            <div className="flex flex-wrap gap-2 md:col-span-4">
              <Button disabled={!isAccessoryRuleComplete(editingRule)} type="button" onClick={() => closeEditor(false)}>
                <Save className="h-4 w-4" aria-hidden="true" />
                Save Accessory
              </Button>
              <Button type="button" variant="outline" onClick={() => closeEditor()}>
                Cancel
              </Button>
            </div>
          </div>
        ) : null}
      </Dialog>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium">Accessory bundle</p>
        <Button type="button" size="sm" variant="outline" onClick={addRule}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add accessory
        </Button>
      </div>
      {accessories.length === 0 ? (
        <p className="text-sm text-muted-foreground">No accessory rules configured.</p>
      ) : (
        <TableContainer>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Accessory</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Required</TableHead>
                <TableHead>Condition</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accessories.map((rule, index) => (
                <TableRow key={`${rule.item_type}-${rule.item_ref_id || rule.name || index}`}>
                  <TableCell className="font-medium">{accessoryDisplayLabel(rule, options)}</TableCell>
                  <TableCell>{accessoryItemTypeLabel(rule.item_type)}</TableCell>
                  <TableCell>{rule.quantity} x {accessoryQuantityLabel(rule)}</TableCell>
                  <TableCell>{rule.required ? 'Required' : rule.enabled ? 'Optional default' : 'Optional'}</TableCell>
                  <TableCell>{accessoryConditionSummary(rule)}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" size="sm" variant="outline" onClick={() => setEditingIndex(index)}>
                        <Eye className="h-4 w-4" aria-hidden="true" />
                        Details
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => removeRule(index)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        Remove
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </div>
  )
}

export function DrawerSystemConfigEditor({
  config,
  drawerSystemKind,
  onChange,
}: {
  config: DrawerSystemConfig
  drawerSystemKind: DrawerSystemKind
  onChange: (config: DrawerSystemConfig) => void
}) {
  if (drawerSystemKind !== 'metal') return null

  function updateConfig(patch: Partial<DrawerSystemConfig>) {
    onChange({ ...config, ...patch })
  }

  return (
    <div className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:col-span-4 md:grid-cols-4">
      <p className="text-sm font-medium md:col-span-4">Drawer-system cutting</p>
      <Label className="grid gap-1.5">
        Product family
        <Input value={String(config.product_family ?? '')} onChange={(event) => updateConfig({ product_family: event.target.value })} />
      </Label>
      <Label className="grid gap-1.5">
        Manufacturer
        <Input value={String(config.manufacturer ?? '')} onChange={(event) => updateConfig({ manufacturer: event.target.value })} />
      </Label>
      <Label className="grid gap-1.5">
        Finish
        <Input value={String(config.finish ?? '')} onChange={(event) => updateConfig({ finish: event.target.value })} />
      </Label>
      <Label className="grid gap-1.5">
        Load class
        <Input value={String(config.load_class ?? '')} onChange={(event) => updateConfig({ load_class: event.target.value })} />
      </Label>
      <Label className="grid gap-1.5">
        Side height
        <Input value={config.side_height_mm ?? ''} onChange={(event) => updateConfig({ side_height_mm: numberOrNull(event.target.value) })} />
      </Label>
      <Label className="grid gap-1.5">
        Installation width
        <Input value={config.installation_width_mm ?? ''} onChange={(event) => updateConfig({ installation_width_mm: numberOrNull(event.target.value) })} />
      </Label>
      <Label className="grid gap-1.5">
        Min depth
        <Input value={config.min_depth_mm ?? ''} onChange={(event) => updateConfig({ min_depth_mm: numberOrNull(event.target.value) })} />
      </Label>
      <Label className="grid gap-1.5">
        Min front height
        <Input value={config.min_front_height_mm ?? ''} onChange={(event) => updateConfig({ min_front_height_mm: numberOrNull(event.target.value) })} />
      </Label>
      <Label className="flex items-center gap-2 text-sm">
        <Checkbox checked={Boolean(config.supplied_metal_sides ?? true)} onChange={(event) => updateConfig({ supplied_metal_sides: event.target.checked })} />
        Supplied metal sides
      </Label>
      <Label className="flex items-center gap-2 text-sm">
        <Checkbox checked={Boolean(config.cut_bottom_panel ?? true)} onChange={(event) => updateConfig({ cut_bottom_panel: event.target.checked })} />
        Cut bottom panel
      </Label>
      <Label className="flex items-center gap-2 text-sm">
        <Checkbox checked={Boolean(config.cut_board_back ?? false)} onChange={(event) => updateConfig({ cut_board_back: event.target.checked })} />
        Cut board back
      </Label>
      <Label className="flex items-center gap-2 text-sm">
        <Checkbox checked={Boolean(config.cut_inset_panel ?? false)} onChange={(event) => updateConfig({ cut_inset_panel: event.target.checked })} />
        Cut inset panel
      </Label>
    </div>
  )
}

function numberOrNull(value: string) {
  if (value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? Math.floor(parsed) : null
}

export function LibraryBoardsTable({
  boards,
  editingBoard,
  isSaving,
  onDelete,
  onEdit,
  onEditChange,
  onSelectionChange,
  onUpdate,
  selectedIds,
}: {
  boards: BoardTypeRow[]
  editingBoard: BoardTypeRow | null
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: BoardTypeRow | null) => void
  onEditChange: (row: BoardTypeRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
} & RowSelectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Board Library</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <TableContainer>
          <Table>
            <TableHeader>
              <TableRow>
                {onSelectionChange ? <TableHead className="w-10">Select</TableHead> : null}
                <TableHead>Brand</TableHead>
                <TableHead>Material</TableHead>
                <TableHead>Thickness</TableHead>
                <TableHead>Length</TableHead>
                <TableHead>Width</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Grain</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {boards.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={onSelectionChange ? 9 : 8}>
                    <EmptyTableMessage
                      title="Add the boards you cut most often."
                      detail="Board sheets drive material takeoffs, quote defaults, and cutlist pricing. Start with your everyday carcass board, then add door and panel boards."
                    />
                  </TableCell>
                </TableRow>
              ) : (
                boards.map((row) => (
                  <TableRow key={row.id}>
                    {onSelectionChange ? (
                      <TableCell>
                        <Checkbox
                          checked={isSelected(selectedIds, row.id)}
                          onChange={(event) => onSelectionChange(row.id, event.target.checked)}
                        />
                      </TableCell>
                    ) : null}
                    <TableCell>{row.brand}</TableCell>
                    <TableCell>{row.material}</TableCell>
                    <TableCell>{row.thickness}</TableCell>
                    <TableCell>{row.length_mm}</TableCell>
                    <TableCell>{row.width_mm}</TableCell>
                    <TableCell>{row.costing_mode}</TableCell>
                    <TableCell>{formatBoardGrainPolicy(row.grain_policy)}</TableCell>
                    <TableCell className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => onEdit({ ...row })}>
                        Edit
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void onDelete(row.id)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {editingBoard ? (
          <form className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:grid-cols-3" onSubmit={(event) => void onUpdate(event)}>
            <p className="md:col-span-3 text-sm font-medium">Edit board</p>
            <Label className="grid gap-1.5">
              Brand
              <Input value={editingBoard.brand} onChange={(event) => onEditChange({ ...editingBoard, brand: event.target.value })} />
            </Label>
            <Label className="grid gap-1.5">
              Material
              <Input value={editingBoard.material} onChange={(event) => onEditChange({ ...editingBoard, material: event.target.value })} />
            </Label>
            <Label className="grid gap-1.5">
              Costing mode
              <Select value={editingBoard.costing_mode} onChange={(event) => onEditChange({ ...editingBoard, costing_mode: event.target.value as 'sheet' | 'sqm' })}>
                <option value="sheet">sheet</option>
                <option value="sqm">sqm</option>
              </Select>
            </Label>
            <Label className="grid gap-1.5">
              Grain
              <Select value={editingBoard.grain_policy} onChange={(event) => onEditChange({ ...editingBoard, grain_policy: event.target.value as BoardGrainPolicy })}>
                {boardGrainPolicyOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </Label>
            <Label className="grid gap-1.5">
              Thickness
              <Input value={String(editingBoard.thickness)} onChange={(event) => onEditChange({ ...editingBoard, thickness: Number(event.target.value) || 0 })} />
            </Label>
            <Label className="grid gap-1.5">
              Length
              <Input value={String(editingBoard.length_mm)} onChange={(event) => onEditChange({ ...editingBoard, length_mm: Number(event.target.value) || 0 })} />
            </Label>
            <Label className="grid gap-1.5">
              Width
              <Input value={String(editingBoard.width_mm)} onChange={(event) => onEditChange({ ...editingBoard, width_mm: Number(event.target.value) || 0 })} />
            </Label>
            <div className="md:col-span-3 flex gap-2">
              <Button disabled={isSaving} type="submit">
                <Save className="h-4 w-4" aria-hidden="true" />
                Save Changes
              </Button>
              <Button type="button" variant="outline" onClick={() => onEdit(null)}>
                Cancel
              </Button>
            </div>
          </form>
        ) : null}
      </CardContent>
    </Card>
  )
}

export function LibrarySlidesTable({
  accessoryOptions,
  editingSlide,
  isSaving,
  onDelete,
  onEdit,
  onEditChange,
  onSelectionChange,
  onUpdate,
  selectedIds,
  slides,
}: {
  accessoryOptions: HardwareAccessoryOptions
  editingSlide: SlideRow | null
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: SlideRow | null) => void
  onEditChange: (row: SlideRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
  slides: SlideRow[]
} & RowSelectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Drawer Hardware Library</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <TableContainer>
          <Table>
            <TableHeader>
              <TableRow>
                {onSelectionChange ? <TableHead className="w-10">Select</TableHead> : null}
                <TableHead>Slide</TableHead>
                <TableHead>System</TableHead>
                <TableHead>Length</TableHead>
                <TableHead>Side length</TableHead>
                <TableHead>Clearance</TableHead>
                <TableHead>Uplift</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {slides.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={onSelectionChange ? 8 : 7}>
                    <EmptyTableMessage
                      title="Add drawer hardware before quoting drawer units."
                      detail="Drawer hardware provides drawer clearances, system planning, and hardware pricing. Start with the range you fit most often."
                    />
                  </TableCell>
                </TableRow>
              ) : (
                slides.map((row) => (
                  <TableRow key={row.id}>
                    {onSelectionChange ? (
                      <TableCell>
                        <Checkbox
                          checked={isSelected(selectedIds, row.id)}
                          onChange={(event) => onSelectionChange(row.id, event.target.checked)}
                        />
                      </TableCell>
                    ) : null}
                    <TableCell>{formatSlideLabel(row)}</TableCell>
                    <TableCell>{formatDrawerSystemKind(row.drawer_system_kind)}</TableCell>
                    <TableCell>{row.length}</TableCell>
                    <TableCell>{row.side_length}</TableCell>
                    <TableCell>{row.side_clearance_total}</TableCell>
                    <TableCell>{row.side_height_uplift}</TableCell>
                    <TableCell className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => onEdit({ ...row })}>
                        Edit
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void onDelete(row.id)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
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
          open={Boolean(editingSlide)}
          onOpenChange={(open) => {
            if (!open) onEdit(null)
          }}
          title="Edit Slide"
          description={editingSlide ? formatSlideLabel(editingSlide) : undefined}
          size="wide"
        >
          {editingSlide ? (
            <form className="grid gap-3 md:grid-cols-4" onSubmit={(event) => void onUpdate(event)}>
              <Label className="grid gap-1.5">
                Brand
                <Input value={editingSlide.brand} onChange={(event) => onEditChange({ ...editingSlide, brand: event.target.value })} />
              </Label>
              <Label className="grid gap-1.5">
                Model
                <Input value={editingSlide.model} onChange={(event) => onEditChange({ ...editingSlide, model: event.target.value })} />
              </Label>
              <Label className="grid gap-1.5">
                Code
                <Input value={editingSlide.code} onChange={(event) => onEditChange({ ...editingSlide, code: event.target.value })} />
              </Label>
              <Label className="grid gap-1.5">
                Length
                <Input value={String(editingSlide.length)} onChange={(event) => onEditChange({ ...editingSlide, length: Number(event.target.value) || 0 })} />
              </Label>
              <Label className="grid gap-1.5">
                Side length
                <Input value={String(editingSlide.side_length)} onChange={(event) => onEditChange({ ...editingSlide, side_length: Number(event.target.value) || 0 })} />
              </Label>
              <Label className="grid gap-1.5">
                Clearance total
                <Input value={String(editingSlide.side_clearance_total)} onChange={(event) => onEditChange({ ...editingSlide, side_clearance_total: Number(event.target.value) || 0 })} />
              </Label>
              <Label className="grid gap-1.5">
                Side uplift
                <Input value={String(editingSlide.side_height_uplift)} onChange={(event) => onEditChange({ ...editingSlide, side_height_uplift: Number(event.target.value) || 0 })} />
              </Label>
              <Label className="grid gap-1.5">
                Drawer system
                <Select value={editingSlide.drawer_system_kind ?? 'conventional'} onChange={(event) => onEditChange({ ...editingSlide, drawer_system_kind: event.target.value as DrawerSystemKind })}>
                  <option value="conventional">Conventional slide</option>
                  <option value="metal">Metal system</option>
                </Select>
              </Label>
              <DrawerSystemConfigEditor
                config={editingSlide.drawer_system_config ?? {}}
                drawerSystemKind={editingSlide.drawer_system_kind ?? 'conventional'}
                onChange={(drawer_system_config) => onEditChange({ ...editingSlide, drawer_system_config })}
              />
              <HardwareAccessoryConfigEditor
                config={editingSlide.accessory_config ?? { accessories: [] }}
                onChange={(accessory_config) => onEditChange({ ...editingSlide, accessory_config })}
                options={accessoryOptions}
              />
              <div className="md:col-span-4 flex gap-2">
                <Button disabled={isSaving} type="submit">
                  <Save className="h-4 w-4" aria-hidden="true" />
                  Save Changes
                </Button>
                <Button type="button" variant="outline" onClick={() => onEdit(null)}>
                  Cancel
                </Button>
              </div>
            </form>
          ) : null}
        </Dialog>
      </CardContent>
    </Card>
  )
}

export function LibraryHingesTable({
  accessoryOptions,
  editingHinge,
  hinges,
  isSaving,
  onDelete,
  onEdit,
  onEditChange,
  onSelectionChange,
  onUpdate,
  selectedIds,
}: {
  accessoryOptions: HardwareAccessoryOptions
  editingHinge: HingeRow | null
  hinges: HingeRow[]
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: HingeRow | null) => void
  onEditChange: (row: HingeRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
} & RowSelectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Hinges Library</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <TableContainer>
          <Table>
            <TableHeader>
              <TableRow>
                {onSelectionChange ? <TableHead className="w-10">Select</TableHead> : null}
                <TableHead>Hinge</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Opening</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {hinges.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={onSelectionChange ? 5 : 4}>
                    <EmptyTableMessage
                      title="Add your standard hinge."
                      detail="Hinges complete door-unit defaults and hardware costing. Add the everyday hinge before building door quotes."
                    />
                  </TableCell>
                </TableRow>
              ) : (
                hinges.map((row) => (
                  <TableRow key={row.id}>
                    {onSelectionChange ? (
                      <TableCell>
                        <Checkbox
                          checked={isSelected(selectedIds, row.id)}
                          onChange={(event) => onSelectionChange(row.id, event.target.checked)}
                        />
                      </TableCell>
                    ) : null}
                    <TableCell>{formatHingeLabel(row)}</TableCell>
                    <TableCell>{row.code || '-'}</TableCell>
                    <TableCell>{row.opening_angle_deg}°</TableCell>
                    <TableCell className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => onEdit({ ...row })}>
                        Edit
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void onDelete(row.id)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
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
          open={Boolean(editingHinge)}
          onOpenChange={(open) => {
            if (!open) onEdit(null)
          }}
          title="Edit Hinge"
          description={editingHinge ? formatHingeLabel(editingHinge) : undefined}
          size="wide"
        >
          {editingHinge ? (
            <form className="grid gap-3 md:grid-cols-4" onSubmit={(event) => void onUpdate(event)}>
              <Label className="grid gap-1.5">
                Brand
                <Input value={editingHinge.brand} onChange={(event) => onEditChange({ ...editingHinge, brand: event.target.value })} />
              </Label>
              <Label className="grid gap-1.5">
                Model
                <Input value={editingHinge.model} onChange={(event) => onEditChange({ ...editingHinge, model: event.target.value })} />
              </Label>
              <Label className="grid gap-1.5">
                Code
                <Input value={editingHinge.code} onChange={(event) => onEditChange({ ...editingHinge, code: event.target.value })} />
              </Label>
              <Label className="grid gap-1.5">
                Opening angle
                <Input value={String(editingHinge.opening_angle_deg)} onChange={(event) => onEditChange({ ...editingHinge, opening_angle_deg: Number(event.target.value) || 0 })} />
              </Label>
              <HardwareAccessoryConfigEditor
                config={editingHinge.accessory_config ?? { accessories: [] }}
                onChange={(accessory_config) => onEditChange({ ...editingHinge, accessory_config })}
                options={accessoryOptions}
              />
              <div className="md:col-span-4 flex gap-2">
                <Button disabled={isSaving} type="submit">
                  <Save className="h-4 w-4" aria-hidden="true" />
                  Save Changes
                </Button>
                <Button type="button" variant="outline" onClick={() => onEdit(null)}>
                  Cancel
                </Button>
              </div>
            </form>
          ) : null}
        </Dialog>
      </CardContent>
    </Card>
  )
}

export function LibraryHandlesTable({
  editingHandle,
  handles,
  isSaving,
  onDelete,
  onEdit,
  onEditChange,
  onSelectionChange,
  onUpdate,
  selectedIds,
}: {
  editingHandle: HandleRow | null
  handles: HandleRow[]
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: HandleRow | null) => void
  onEditChange: (row: HandleRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
} & RowSelectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Handles Library</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <TableContainer>
          <Table>
            <TableHeader>
              <TableRow>
                {onSelectionChange ? <TableHead className="w-10">Select</TableHead> : null}
                <TableHead>Handle</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {handles.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={onSelectionChange ? 5 : 4}>
                    <EmptyTableMessage
                      title="Add handles when you want handle defaults."
                      detail="Handles can be selected on quote defaults and priced with the rest of the job. Add common ranges or leave this blank until handle costing matters."
                    />
                  </TableCell>
                </TableRow>
              ) : (
                handles.map((row) => (
                  <TableRow key={row.id}>
                    {onSelectionChange ? (
                      <TableCell>
                        <Checkbox
                          checked={isSelected(selectedIds, row.id)}
                          onChange={(event) => onSelectionChange(row.id, event.target.checked)}
                        />
                      </TableCell>
                    ) : null}
                    <TableCell>{row.name}</TableCell>
                    <TableCell>{row.supplier || '-'}</TableCell>
                    <TableCell>{row.code || '-'}</TableCell>
                    <TableCell className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => onEdit({ ...row })}>
                        Edit
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void onDelete(row.id)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {editingHandle ? (
          <form className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:grid-cols-3" onSubmit={(event) => void onUpdate(event)}>
            <p className="md:col-span-3 text-sm font-medium">Edit handle</p>
            <Label className="grid gap-1.5">
              Name
              <Input value={editingHandle.name} onChange={(event) => onEditChange({ ...editingHandle, name: event.target.value })} />
            </Label>
            <Label className="grid gap-1.5">
              Supplier
              <Input value={editingHandle.supplier} onChange={(event) => onEditChange({ ...editingHandle, supplier: event.target.value })} />
            </Label>
            <Label className="grid gap-1.5">
              Code
              <Input value={editingHandle.code} onChange={(event) => onEditChange({ ...editingHandle, code: event.target.value })} />
            </Label>
            <div className="md:col-span-3 flex gap-2">
              <Button disabled={isSaving} type="submit">
                <Save className="h-4 w-4" aria-hidden="true" />
                Save Changes
              </Button>
              <Button type="button" variant="outline" onClick={() => onEdit(null)}>
                Cancel
              </Button>
            </div>
          </form>
        ) : null}
      </CardContent>
    </Card>
  )
}

export function LibraryExtraCategoriesTable({
  categories,
  editingCategory,
  isSaving,
  onDelete,
  onEdit,
  onEditChange,
  onUpdate,
}: {
  categories: ExtraCategoryRow[]
  editingCategory: ExtraCategoryRow | null
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: ExtraCategoryRow | null) => void
  onEditChange: (row: ExtraCategoryRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Extra Categories</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <TableContainer>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {categories.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={2}>
                    <EmptyTableMessage
                      title="Create an extras category first."
                      detail="Categories keep chargeable items like installation, delivery, accessories, and finishing grouped for faster quote setup."
                    />
                  </TableCell>
                </TableRow>
              ) : (
                categories.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.name}</TableCell>
                    <TableCell className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => onEdit({ ...row })}>
                        Edit
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void onDelete(row.id)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {editingCategory ? (
          <form className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:grid-cols-[1fr_auto_auto] md:items-end" onSubmit={(event) => void onUpdate(event)}>
            <Label className="grid gap-1.5">
              Category name
              <Input value={editingCategory.name} onChange={(event) => onEditChange({ ...editingCategory, name: event.target.value })} />
            </Label>
            <Button disabled={isSaving} type="submit">
              <Save className="h-4 w-4" aria-hidden="true" />
              Save
            </Button>
            <Button type="button" variant="outline" onClick={() => onEdit(null)}>
              Cancel
            </Button>
          </form>
        ) : null}
      </CardContent>
    </Card>
  )
}

export function LibraryExtrasTable({
  categories,
  editingExtra,
  extras,
  isSaving,
  onDelete,
  onEdit,
  onEditChange,
  onSelectionChange,
  onUpdate,
  selectedIds,
  suppliers,
}: {
  categories: ExtraCategoryRow[]
  editingExtra: ExtraRow | null
  extras: ExtraRow[]
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: ExtraRow | null) => void
  onEditChange: (row: ExtraRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
  suppliers: SupplierRow[]
} & RowSelectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Extras Library</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <TableContainer>
          <Table>
            <TableHeader>
              <TableRow>
                {onSelectionChange ? <TableHead className="w-10">Select</TableHead> : null}
                <TableHead>Extra</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {extras.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={onSelectionChange ? 6 : 5}>
                    <EmptyTableMessage
                      title="Add optional charges and accessories."
                      detail="Extras cover items such as delivery, installation, lighting, bins, and other add-ons that should appear in quote pricing."
                    />
                  </TableCell>
                </TableRow>
              ) : (
                extras.map((row) => (
                  <TableRow key={row.id}>
                    {onSelectionChange ? (
                      <TableCell>
                        <Checkbox
                          checked={isSelected(selectedIds, row.id)}
                          onChange={(event) => onSelectionChange(row.id, event.target.checked)}
                        />
                      </TableCell>
                    ) : null}
                    <TableCell>{row.name}</TableCell>
                    <TableCell>{row.category_name}</TableCell>
                    <TableCell>{row.supplier || '-'}</TableCell>
                    <TableCell>{row.code || '-'}</TableCell>
                    <TableCell className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => onEdit({ ...row })}>
                        Edit
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void onDelete(row.id)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {editingExtra ? (
          <form className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:grid-cols-2" onSubmit={(event) => void onUpdate(event)}>
            <p className="md:col-span-2 text-sm font-medium">Edit extra</p>
            <Label className="grid gap-1.5">
              Name
              <Input value={editingExtra.name} onChange={(event) => onEditChange({ ...editingExtra, name: event.target.value })} />
            </Label>
            <Label className="grid gap-1.5">
              Category
              <Select
                value={editingExtra.category_id}
                onChange={(event) => onEditChange({ ...editingExtra, category_id: event.target.value })}
              >
                <option value="">Select a category</option>
                {categories.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </Select>
            </Label>
            <Label className="grid gap-1.5">
              Supplier
              <Select value={editingExtra.supplier_id ?? ''} onChange={(event) => onEditChange({ ...editingExtra, supplier_id: event.target.value || null })}>
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
              <Input value={editingExtra.code} onChange={(event) => onEditChange({ ...editingExtra, code: event.target.value })} />
            </Label>
            <Label className="md:col-span-2 grid gap-1.5">
              Notes
              <Textarea value={editingExtra.notes} onChange={(event) => onEditChange({ ...editingExtra, notes: event.target.value })} />
            </Label>
            <div className="md:col-span-2 flex gap-2">
              <Button disabled={isSaving} type="submit">
                <Save className="h-4 w-4" aria-hidden="true" />
                Save Changes
              </Button>
              <Button type="button" variant="outline" onClick={() => onEdit(null)}>
                Cancel
              </Button>
            </div>
          </form>
        ) : null}
      </CardContent>
    </Card>
  )
}
