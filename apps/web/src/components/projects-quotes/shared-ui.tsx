import { Fragment, type Dispatch, type ReactNode, type SetStateAction } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow } from '@/components/ui/table'

import type { CutlistRow, CutlistValidationWarning, QuoteDraft } from './types'

export function CutlistSection({
  title,
  rows,
  section,
  warnings = [],
}: {
  title: string
  rows: CutlistRow[]
  section: CutlistValidationWarning['section']
  warnings?: CutlistValidationWarning[]
}) {
  if (rows.length === 0) return null
  const groupedRows = rows.reduce<Array<{ row: CutlistRow; showDivider: boolean }>>((accumulator, row, index) => {
    const previous = rows[index - 1]
    accumulator.push({
      row,
      showDivider: index > 0 && previous?.unit_number !== row.unit_number,
    })
    return accumulator
  }, [])

  return (
    <div className="grid gap-1">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{title}</p>
      <TableContainer>
        <Table>
          <TableHeader>
            <TableRow className="h-8">
              <TableHead className="px-2 py-1">#</TableHead>
              <TableHead className="px-2 py-1">Description</TableHead>
              <TableHead className="px-2 py-1">L</TableHead>
              <TableHead className="px-2 py-1">W</TableHead>
              <TableHead className="px-2 py-1">Qty</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {groupedRows.map(({ row, showDivider }, index) => (
              <Fragment key={`${title}-group-${index}-${row.unit_number}-${row.desc}`}>
                {showDivider ? (
                  <TableRow className="h-2 border-0">
                    <TableCell className="border-0 p-0" colSpan={5}>
                      <div className="my-1 h-px w-full bg-border" />
                    </TableCell>
                  </TableRow>
                ) : null}
                <TableRow className="h-8">
                  <TableCell className="px-2 py-1 text-xs">{row.unit_number}</TableCell>
                  <TableCell className="px-2 py-1 text-xs">
                    {row.desc}
                    {hasCutlistWarning(row, section, warnings) ? (
                      <Badge className="ml-2 h-5 align-middle" variant="warning">
                        Review
                      </Badge>
                    ) : null}
                  </TableCell>
                  <TableCell className="px-2 py-1 text-xs">{row.length}</TableCell>
                  <TableCell className="px-2 py-1 text-xs">{row.width}</TableCell>
                  <TableCell className="px-2 py-1 text-xs">{row.qty}</TableCell>
                </TableRow>
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  )
}

function hasCutlistWarning(
  row: CutlistRow,
  section: CutlistValidationWarning['section'],
  warnings: CutlistValidationWarning[],
) {
  return warnings.some(
    (warning) =>
      warning.section === section &&
      warning.unit_number === row.unit_number &&
      warning.row_desc === row.desc,
  )
}

export function ModalCard({
  title,
  children,
  onClose,
}: {
  title: string
  children: ReactNode
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <Card className="w-full max-w-4xl">
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>{title}</CardTitle>
          <Button onClick={onClose} type="button" variant="ghost">
            Close
          </Button>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </div>
  )
}

export function LibrarySelect({
  label,
  options,
  onChange,
  value,
}: {
  label: string
  options: Array<{ value: string; label: string }>
  onChange: (value: string) => void
  value: string
}) {
  return (
    <Label className="grid gap-1.5">
      {label}
      <Select onChange={(event) => onChange(event.target.value)} value={value}>
        <option value="">None</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </Label>
  )
}

export function QuoteDefaultDimensionGrid({
  draft,
  setDraft,
}: {
  draft: QuoteDraft
  setDraft: Dispatch<SetStateAction<QuoteDraft>>
}) {
  return (
    <div className="grid gap-2">
      <DimensionRow
        depthKey="base_draw_depth"
        draft={draft}
        heightKey="base_draw_height"
        label="Base Draw"
        setDraft={setDraft}
      />
      <DimensionRow
        depthKey="base_door_depth"
        draft={draft}
        heightKey="base_door_height"
        label="Base Door"
        setDraft={setDraft}
      />
      <DimensionRow
        depthKey="wall_door_depth"
        draft={draft}
        heightKey="wall_door_height"
        label="Wall Door"
        setDraft={setDraft}
      />
      <DimensionRow
        depthKey="tall_door_depth"
        draft={draft}
        heightKey="tall_door_height"
        label="Tall Door"
        setDraft={setDraft}
      />
    </div>
  )
}

export function DimensionRow({
  label,
  draft,
  setDraft,
  heightKey,
  depthKey,
}: {
  label: string
  draft: QuoteDraft
  setDraft: Dispatch<SetStateAction<QuoteDraft>>
  heightKey:
    | 'base_draw_height'
    | 'base_door_height'
    | 'wall_door_height'
    | 'tall_door_height'
  depthKey: 'base_draw_depth' | 'base_door_depth' | 'wall_door_depth' | 'tall_door_depth'
}) {
  return (
    <div className="grid grid-cols-[140px_1fr_1fr] items-center gap-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <Input
        min={1}
        onChange={(event) => setDraft((current) => ({ ...current, [heightKey]: event.target.value }))}
        type="number"
        value={draft[heightKey]}
      />
      <Input
        min={1}
        onChange={(event) => setDraft((current) => ({ ...current, [depthKey]: event.target.value }))}
        type="number"
        value={draft[depthKey]}
      />
    </div>
  )
}
