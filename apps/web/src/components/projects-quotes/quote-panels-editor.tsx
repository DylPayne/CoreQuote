import { LoaderCircle, Plus, Trash2 } from 'lucide-react'
import { useCallback } from 'react'

import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow } from '@/components/ui/table'

import { panelPresetFamily, panelPresetKeys, panelPresetLabels } from './constants'
import { optionalId, parseNonNegativeInteger, resolveDefaultDims } from './helpers'
import { LibrarySelect } from './shared-ui'
import type {
  BoardRow,
  PanelPresetKey,
  QuoteCustomPanelComputedRow,
  QuoteCustomPanelPresetConfig,
  QuoteCustomPanelsState,
  QuoteRow,
} from './types'

export function QuotePanelsEditor({
  selectedQuote,
  boards,
  boardLabel,
  panelState,
  panelRows,
  presetFamilyCounts,
  defaultPanelBoardId,
  isSavedStateDirty,
  isSaving,
  onChange,
  onSave,
}: {
  selectedQuote: QuoteRow
  boards: BoardRow[]
  boardLabel: (boardId: string | null) => string
  panelState: QuoteCustomPanelsState
  panelRows: QuoteCustomPanelComputedRow[]
  presetFamilyCounts: Record<'base' | 'wall' | 'tall', number>
  defaultPanelBoardId: string | null
  isSavedStateDirty: boolean
  isSaving: boolean
  onChange: (next: QuoteCustomPanelsState) => void
  onSave: () => void
}) {
  const baseDoor = resolveDefaultDims(selectedQuote.unit_defaults, 'Base Door')
  const wallDoor = resolveDefaultDims(selectedQuote.unit_defaults, 'Wall Door')
  const tallDoor = resolveDefaultDims(selectedQuote.unit_defaults, 'Tall Door')
  const defaultReturnDepth = baseDoor.depth

  const defaultPresetConfig = useCallback(
    (key: PanelPresetKey): QuoteCustomPanelPresetConfig => {
      const family = panelPresetFamily[key]
      const defaultQty = presetFamilyCounts[family] > 0 ? 1 : 0
      return {
        qty: defaultQty,
        board_type_id: defaultPanelBoardId,
      }
    },
    [defaultPanelBoardId, presetFamilyCounts],
  )

  const panelPresetDimensions: Record<PanelPresetKey, { length: number; width: number }> = {
    base_side_panel: { length: baseDoor.height, width: baseDoor.depth },
    base_side_filler: { length: baseDoor.height, width: 100 },
    wall_side_panel: { length: wallDoor.height, width: wallDoor.depth },
    wall_side_filler: { length: wallDoor.height, width: 100 },
    tall_side_panel: { length: tallDoor.height, width: tallDoor.depth },
    tall_side_filler: { length: tallDoor.height, width: 100 },
  }

  const kickerReturnsDepth = panelState.auto.kicker_return_depth_mm > 0
    ? panelState.auto.kicker_return_depth_mm
    : defaultReturnDepth

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          Configure preset side panels/fillers, automatic kickers and pelmets, and custom manual panel rows.
        </p>
        <Button disabled={!isSavedStateDirty || isSaving} onClick={onSave} size="sm" type="button">
          {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
          Save panels
        </Button>
      </div>

      <Alert className="text-xs">
        Kicker length is based on total base-unit width, plus any optional return sections.
      </Alert>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="p-3">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Preset Panels</p>
          <TableContainer className="mt-2">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Panel</TableHead>
                  <TableHead className="w-24">Qty</TableHead>
                  <TableHead className="w-28">Size (mm)</TableHead>
                  <TableHead>Board</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {panelPresetKeys.map((key) => {
                  const current = panelState.presets[key] ?? defaultPresetConfig(key)
                  const dims = panelPresetDimensions[key]
                  return (
                    <TableRow key={key}>
                      <TableCell>{panelPresetLabels[key]}</TableCell>
                      <TableCell>
                        <Input
                          min={0}
                          onChange={(event) => {
                            const nextQty = parseNonNegativeInteger(event.target.value, 0)
                            onChange({
                              ...panelState,
                              presets: {
                                ...panelState.presets,
                                [key]: { ...current, qty: nextQty },
                              },
                            })
                          }}
                          type="number"
                          value={String(current.qty)}
                        />
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{`${dims.length} x ${dims.width}`}</TableCell>
                      <TableCell>
                        <Select
                          onChange={(event) =>
                            onChange({
                              ...panelState,
                              presets: {
                                ...panelState.presets,
                                [key]: {
                                  ...current,
                                  board_type_id: optionalId(event.target.value),
                                },
                              },
                            })
                          }
                          value={current.board_type_id ?? ''}
                        >
                          <option value="">Default panel board</option>
                          {boards.map((board) => (
                            <option key={board.id} value={board.id}>
                              {`${board.brand} ${board.material} (${board.thickness}mm)`}
                            </option>
                          ))}
                        </Select>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>

        <Card className="p-3">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Auto Panels</p>
          <div className="mt-2 grid gap-3">
            <div className="grid gap-3 md:grid-cols-2">
              <LibrarySelect
                label="Kicker board"
                onChange={(value) =>
                  onChange({
                    ...panelState,
                    auto: { ...panelState.auto, kicker_board_type_id: optionalId(value) },
                  })
                }
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                value={panelState.auto.kicker_board_type_id ?? ''}
              />
              <LibrarySelect
                label="Wall pelmet board"
                onChange={(value) =>
                  onChange({
                    ...panelState,
                    auto: { ...panelState.auto, pelmet_board_type_id: optionalId(value) },
                  })
                }
                options={boards.map((board) => ({ value: board.id, label: `${board.brand} ${board.material} (${board.thickness}mm)` }))}
                value={panelState.auto.pelmet_board_type_id ?? ''}
              />
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <Label className="grid gap-1.5">
                Kicker returns (qty)
                <Input
                  min={0}
                  onChange={(event) =>
                    onChange({
                      ...panelState,
                      auto: { ...panelState.auto, kicker_return_count: parseNonNegativeInteger(event.target.value, 0) },
                    })
                  }
                  type="number"
                  value={String(panelState.auto.kicker_return_count)}
                />
              </Label>
              <Label className="grid gap-1.5">
                Return depth (mm)
                <Input
                  min={0}
                  onChange={(event) =>
                    onChange({
                      ...panelState,
                      auto: { ...panelState.auto, kicker_return_depth_mm: parseNonNegativeInteger(event.target.value, defaultReturnDepth) },
                    })
                  }
                  type="number"
                  value={String(kickerReturnsDepth)}
                />
              </Label>
            </div>

            <div className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3">
              <Label className="flex items-center gap-2">
                <Checkbox
                  checked={panelState.auto.kicker_override_on}
                  onChange={(event) =>
                    onChange({
                      ...panelState,
                      auto: { ...panelState.auto, kicker_override_on: event.target.checked },
                    })
                  }
                />
                Kicker override
              </Label>
              {panelState.auto.kicker_override_on ? (
                <div className="grid gap-3 md:grid-cols-3">
                  <Label className="grid gap-1.5">
                    Qty
                    <Input
                      min={0}
                      onChange={(event) =>
                        onChange({
                          ...panelState,
                          auto: { ...panelState.auto, kicker_override_qty: parseNonNegativeInteger(event.target.value, 0) },
                        })
                      }
                      type="number"
                      value={String(panelState.auto.kicker_override_qty)}
                    />
                  </Label>
                  <Label className="grid gap-1.5">
                    Length (mm)
                    <Input
                      min={0}
                      onChange={(event) =>
                        onChange({
                          ...panelState,
                          auto: { ...panelState.auto, kicker_override_length: parseNonNegativeInteger(event.target.value, 0) },
                        })
                      }
                      type="number"
                      value={String(panelState.auto.kicker_override_length)}
                    />
                  </Label>
                  <Label className="grid gap-1.5">
                    Width (mm)
                    <Input
                      min={0}
                      onChange={(event) =>
                        onChange({
                          ...panelState,
                          auto: { ...panelState.auto, kicker_override_width: parseNonNegativeInteger(event.target.value, 100) },
                        })
                      }
                      type="number"
                      value={String(panelState.auto.kicker_override_width)}
                    />
                  </Label>
                </div>
              ) : null}
            </div>

            <div className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3">
              <Label className="flex items-center gap-2">
                <Checkbox
                  checked={panelState.auto.pelmet_override_on}
                  onChange={(event) =>
                    onChange({
                      ...panelState,
                      auto: { ...panelState.auto, pelmet_override_on: event.target.checked },
                    })
                  }
                />
                Wall pelmet override
              </Label>
              {panelState.auto.pelmet_override_on ? (
                <div className="grid gap-3 md:grid-cols-3">
                  <Label className="grid gap-1.5">
                    Qty
                    <Input
                      min={0}
                      onChange={(event) =>
                        onChange({
                          ...panelState,
                          auto: { ...panelState.auto, pelmet_override_qty: parseNonNegativeInteger(event.target.value, 0) },
                        })
                      }
                      type="number"
                      value={String(panelState.auto.pelmet_override_qty)}
                    />
                  </Label>
                  <Label className="grid gap-1.5">
                    Length (mm)
                    <Input
                      min={0}
                      onChange={(event) =>
                        onChange({
                          ...panelState,
                          auto: { ...panelState.auto, pelmet_override_length: parseNonNegativeInteger(event.target.value, 0) },
                        })
                      }
                      type="number"
                      value={String(panelState.auto.pelmet_override_length)}
                    />
                  </Label>
                  <Label className="grid gap-1.5">
                    Width (mm)
                    <Input
                      min={0}
                      onChange={(event) =>
                        onChange({
                          ...panelState,
                          auto: { ...panelState.auto, pelmet_override_width: parseNonNegativeInteger(event.target.value, wallDoor.depth) },
                        })
                      }
                      type="number"
                      value={String(panelState.auto.pelmet_override_width)}
                    />
                  </Label>
                </div>
              ) : null}
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Manual Custom Rows</p>
          <Button
            onClick={() =>
              onChange({
                ...panelState,
                manual: [
                  ...panelState.manual,
                  {
                    name: 'Custom Panel',
                    length: 0,
                    width: 0,
                    qty: 1,
                    board_type_id: defaultPanelBoardId,
                  },
                ],
              })
            }
            size="sm"
            type="button"
            variant="outline"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add row
          </Button>
        </div>

        {panelState.manual.length === 0 ? (
          <Alert className="mt-2 text-xs">
            Add manual rows for one-off panels, fillers, or site-specific pieces that are not created from unit presets.
          </Alert>
        ) : (
          <TableContainer className="mt-2">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead className="w-28">L (mm)</TableHead>
                  <TableHead className="w-28">W (mm)</TableHead>
                  <TableHead className="w-24">Qty</TableHead>
                  <TableHead>Board</TableHead>
                  <TableHead className="w-16" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {panelState.manual.map((row, index) => (
                  <TableRow key={`manual-panel-${index}`}>
                    <TableCell>
                      <Input
                        onChange={(event) =>
                          onChange({
                            ...panelState,
                            manual: panelState.manual.map((current, currentIndex) =>
                              currentIndex === index ? { ...current, name: event.target.value } : current,
                            ),
                          })
                        }
                        value={row.name}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        min={0}
                        onChange={(event) =>
                          onChange({
                            ...panelState,
                            manual: panelState.manual.map((current, currentIndex) =>
                              currentIndex === index ? { ...current, length: parseNonNegativeInteger(event.target.value, 0) } : current,
                            ),
                          })
                        }
                        type="number"
                        value={String(row.length)}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        min={0}
                        onChange={(event) =>
                          onChange({
                            ...panelState,
                            manual: panelState.manual.map((current, currentIndex) =>
                              currentIndex === index ? { ...current, width: parseNonNegativeInteger(event.target.value, 0) } : current,
                            ),
                          })
                        }
                        type="number"
                        value={String(row.width)}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        min={0}
                        onChange={(event) =>
                          onChange({
                            ...panelState,
                            manual: panelState.manual.map((current, currentIndex) =>
                              currentIndex === index ? { ...current, qty: parseNonNegativeInteger(event.target.value, 0) } : current,
                            ),
                          })
                        }
                        type="number"
                        value={String(row.qty)}
                      />
                    </TableCell>
                    <TableCell>
                      <Select
                        onChange={(event) =>
                          onChange({
                            ...panelState,
                            manual: panelState.manual.map((current, currentIndex) =>
                              currentIndex === index ? { ...current, board_type_id: optionalId(event.target.value) } : current,
                            ),
                          })
                        }
                        value={row.board_type_id ?? ''}
                      >
                        <option value="">Default panel board</option>
                        {boards.map((board) => (
                          <option key={board.id} value={board.id}>
                            {`${board.brand} ${board.material} (${board.thickness}mm)`}
                          </option>
                        ))}
                      </Select>
                    </TableCell>
                    <TableCell>
                      <Button
                        onClick={() =>
                          onChange({
                            ...panelState,
                            manual: panelState.manual.filter((_, currentIndex) => currentIndex !== index),
                          })
                        }
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
        )}
      </Card>

      <Card className="p-3">
        <p className="text-xs font-semibold uppercase text-muted-foreground">Computed Rows</p>
        {panelRows.length === 0 ? (
          <Alert className="mt-2 text-xs">
            Save panel changes to refresh the preview of quote-level panel rows.
          </Alert>
        ) : (
          <TableContainer className="mt-2">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Description</TableHead>
                  <TableHead className="w-24">L (mm)</TableHead>
                  <TableHead className="w-24">W (mm)</TableHead>
                  <TableHead className="w-20">Qty</TableHead>
                  <TableHead>Board</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {panelRows.map((row, index) => (
                  <TableRow key={`panel-row-${index}-${row.desc}`}>
                    <TableCell>{row.desc}</TableCell>
                    <TableCell>{row.length}</TableCell>
                    <TableCell>{row.width}</TableCell>
                    <TableCell>{row.qty}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{boardLabel(row.board_type_id)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>
    </div>
  )
}
