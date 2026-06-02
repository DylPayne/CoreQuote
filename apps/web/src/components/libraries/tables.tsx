import { Save, Trash2 } from 'lucide-react'
import type { FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'

import { formatHingeLabel, formatSlideLabel } from './helpers'
import type { BoardTypeRow, ExtraCategoryRow, ExtraRow, HandleRow, HingeRow, SlideRow } from './types'

export function LibraryBoardsTable({
  boards,
  editingBoard,
  isSaving,
  onDelete,
  onEdit,
  onEditChange,
  onUpdate,
}: {
  boards: BoardTypeRow[]
  editingBoard: BoardTypeRow | null
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: BoardTypeRow | null) => void
  onEditChange: (row: BoardTypeRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
}) {
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
                <TableHead>Brand</TableHead>
                <TableHead>Material</TableHead>
                <TableHead>Thickness</TableHead>
                <TableHead>Length</TableHead>
                <TableHead>Width</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {boards.length === 0 ? (
                <TableRow>
                  <TableCell className="text-muted-foreground" colSpan={7}>
                    No boards in the library yet.
                  </TableCell>
                </TableRow>
              ) : (
                boards.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.brand}</TableCell>
                    <TableCell>{row.material}</TableCell>
                    <TableCell>{row.thickness}</TableCell>
                    <TableCell>{row.length_mm}</TableCell>
                    <TableCell>{row.width_mm}</TableCell>
                    <TableCell>{row.costing_mode}</TableCell>
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
  editingSlide,
  isSaving,
  onDelete,
  onEdit,
  onEditChange,
  onUpdate,
  slides,
}: {
  editingSlide: SlideRow | null
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: SlideRow | null) => void
  onEditChange: (row: SlideRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
  slides: SlideRow[]
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Slides Library</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <TableContainer>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Slide</TableHead>
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
                  <TableCell className="text-muted-foreground" colSpan={6}>
                    No slides in the library yet.
                  </TableCell>
                </TableRow>
              ) : (
                slides.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{formatSlideLabel(row)}</TableCell>
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

        {editingSlide ? (
          <form className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:grid-cols-4" onSubmit={(event) => void onUpdate(event)}>
            <p className="md:col-span-4 text-sm font-medium">Edit slide</p>
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
      </CardContent>
    </Card>
  )
}

export function LibraryHingesTable({
  editingHinge,
  hinges,
  isSaving,
  onDelete,
  onEdit,
  onEditChange,
  onUpdate,
}: {
  editingHinge: HingeRow | null
  hinges: HingeRow[]
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: HingeRow | null) => void
  onEditChange: (row: HingeRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
}) {
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
                <TableHead>Hinge</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Opening</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {hinges.length === 0 ? (
                <TableRow>
                  <TableCell className="text-muted-foreground" colSpan={4}>
                    No hinges in the library yet.
                  </TableCell>
                </TableRow>
              ) : (
                hinges.map((row) => (
                  <TableRow key={row.id}>
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

        {editingHinge ? (
          <form className="grid gap-3 rounded-[var(--card-radius)] border border-border p-3 md:grid-cols-4" onSubmit={(event) => void onUpdate(event)}>
            <p className="md:col-span-4 text-sm font-medium">Edit hinge</p>
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
  onUpdate,
}: {
  editingHandle: HandleRow | null
  handles: HandleRow[]
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: HandleRow | null) => void
  onEditChange: (row: HandleRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
}) {
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
                <TableHead>Handle</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {handles.length === 0 ? (
                <TableRow>
                  <TableCell className="text-muted-foreground" colSpan={4}>
                    No handles in the library yet.
                  </TableCell>
                </TableRow>
              ) : (
                handles.map((row) => (
                  <TableRow key={row.id}>
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
                  <TableCell className="text-muted-foreground" colSpan={2}>
                    No categories yet.
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
  onUpdate,
}: {
  categories: ExtraCategoryRow[]
  editingExtra: ExtraRow | null
  extras: ExtraRow[]
  isSaving: boolean
  onDelete: (itemId: string) => Promise<void>
  onEdit: (row: ExtraRow | null) => void
  onEditChange: (row: ExtraRow | null) => void
  onUpdate: (event: FormEvent<HTMLFormElement>) => Promise<void>
}) {
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
                  <TableCell className="text-muted-foreground" colSpan={5}>
                    No extras in the library yet.
                  </TableCell>
                </TableRow>
              ) : (
                extras.map((row) => (
                  <TableRow key={row.id}>
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
              <Input value={editingExtra.supplier} onChange={(event) => onEditChange({ ...editingExtra, supplier: event.target.value })} />
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
