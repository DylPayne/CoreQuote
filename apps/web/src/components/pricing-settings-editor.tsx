import { Save } from 'lucide-react'
import type { FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  pricingMarkupFields,
  pricingMinimumFields,
  pricingMoneyFields,
  pricingPercentFields,
  pricingQuantityFields,
  type PricingSettingsDraft,
} from '@/components/pricing-settings'

type PricingSettingsEditorProps = {
  currencyCode: string
  draft: PricingSettingsDraft
  isSaving: boolean
  onDraftChange: (draft: PricingSettingsDraft) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export function PricingSettingsEditor({
  currencyCode,
  draft,
  isSaving,
  onDraftChange,
  onSubmit,
}: PricingSettingsEditorProps) {
  function updateField(key: keyof PricingSettingsDraft, value: string) {
    onDraftChange({ ...draft, [key]: value })
  }

  return (
    <form className="grid gap-5" onSubmit={onSubmit}>
      <section className="grid gap-3">
        <p className="text-sm font-semibold">Tax and defaults</p>
        <div className="grid gap-3 md:grid-cols-3">
          {pricingPercentFields.map((field) => (
            <Label className="grid gap-1.5" key={field.key}>
              {field.label}
              <Input
                inputMode="decimal"
                onChange={(event) => updateField(field.key, event.target.value)}
                step="0.01"
                type="number"
                value={draft[field.key]}
              />
            </Label>
          ))}
        </div>
      </section>

      <section className="grid gap-3 border-t border-border pt-4">
        <p className="text-sm font-semibold">Markup buckets</p>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {pricingMarkupFields.map((field) => (
            <Label className="grid gap-1.5" key={field.key}>
              {field.label}
              <Input
                inputMode="decimal"
                onChange={(event) => updateField(field.key, event.target.value)}
                step="0.01"
                type="number"
                value={draft[field.key]}
              />
            </Label>
          ))}
        </div>
      </section>

      <section className="grid gap-3 border-t border-border pt-4">
        <p className="text-sm font-semibold">Operational rates ({currencyCode})</p>
        <div className="grid gap-3 md:grid-cols-4">
          {pricingMoneyFields.map((field) => (
            <Label className="grid gap-1.5" key={field.key}>
              {field.label}
              <Input
                inputMode="decimal"
                onChange={(event) => updateField(field.key, event.target.value)}
                step="0.01"
                type="number"
                value={draft[field.key]}
              />
            </Label>
          ))}
        </div>
      </section>

      <section className="grid gap-3 border-t border-border pt-4">
        <p className="text-sm font-semibold">Install and delivery</p>
        <div className="grid gap-3 md:grid-cols-4">
          {pricingQuantityFields.map((field) => (
            <Label className="grid gap-1.5" key={field.key}>
              {field.label}
              <Input
                inputMode="numeric"
                min={1}
                onChange={(event) => updateField(field.key, event.target.value)}
                step="1"
                type="number"
                value={draft[field.key]}
              />
            </Label>
          ))}
          {pricingMinimumFields.map((field) => (
            <Label className="grid gap-1.5" key={field.key}>
              {field.label}
              <Input
                inputMode="decimal"
                min={0}
                onChange={(event) => updateField(field.key, event.target.value)}
                step="0.01"
                type="number"
                value={draft[field.key]}
              />
            </Label>
          ))}
        </div>
      </section>

      <div className="flex justify-end border-t border-border pt-4">
        <Button disabled={isSaving} type="submit">
          <Save className="h-4 w-4" aria-hidden="true" />
          Save
        </Button>
      </div>
    </form>
  )
}
