import { Building2, CircleDollarSign, Save, ShieldCheck, UserRound } from 'lucide-react'
import { useEffect, useMemo, useState, type ComponentType, type FormEvent } from 'react'

import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { apiRequest } from '@/lib/api'
import { currencyLabel, normalizeCurrencyCode, optionsForCurrency } from '@/lib/currency'
import type { AuthUser } from '@/types/auth'

type CompanyResponse = {
  id: string
  name: string
  slug: string
  currency_code: string
  created_at: string
  updated_at: string
}

export function SettingsPage({
  authToken,
  onUserChange,
  user,
}: {
  authToken: string
  onUserChange: (user: AuthUser) => void
  user: AuthUser
}) {
  const savedCurrencyCode = normalizeCurrencyCode(user.company_currency_code)
  const [currencyCode, setCurrencyCode] = useState(savedCurrencyCode)
  const [currencyError, setCurrencyError] = useState<string | null>(null)
  const [currencyMessage, setCurrencyMessage] = useState<string | null>(null)
  const [isSavingCurrency, setIsSavingCurrency] = useState(false)
  const isOwner = user.role === 'owner'
  const currencyChoices = useMemo(() => optionsForCurrency(savedCurrencyCode), [savedCurrencyCode])
  const hasCurrencyChange = currencyCode !== savedCurrencyCode

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setCurrencyCode(savedCurrencyCode)
    }, 0)

    return () => window.clearTimeout(handle)
  }, [savedCurrencyCode])

  async function handleCurrencySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!isOwner || !hasCurrencyChange) return

    setCurrencyError(null)
    setCurrencyMessage(null)
    setIsSavingCurrency(true)
    try {
      const updatedCompany = await apiRequest<CompanyResponse>(`/api/v1/companies/${user.company_id}`, {
        body: { currency_code: currencyCode },
        method: 'PATCH',
        token: authToken,
      })
      const nextCurrencyCode = normalizeCurrencyCode(updatedCompany.currency_code)
      setCurrencyCode(nextCurrencyCode)
      onUserChange({
        ...user,
        company_currency_code: nextCurrencyCode,
        company_name: updatedCompany.name,
      })
      setCurrencyMessage('Currency saved.')
    } catch (error) {
      setCurrencyError(error instanceof Error ? error.message : 'Could not save company currency.')
    } finally {
      setIsSavingCurrency(false)
    }
  }

  return (
    <>
      <section className="grid gap-4 lg:grid-cols-4">
        <StatusCard
          icon={ShieldCheck}
          label="Access"
          title="Signed in"
          value="Workspace ready"
        />
        <StatusCard icon={Building2} label="Company" title={user.company_name} value="Company profile" />
        <StatusCard icon={CircleDollarSign} label="Currency" title={savedCurrencyCode} value={currencyLabel(savedCurrencyCode)} />
        <StatusCard icon={UserRound} label="User" title={user.name} value={user.email} />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Workspace details</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">Company profile and account details used across quotes.</p>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <SummaryLine label="Company" value={user.company_name} />
          <SummaryLine label="Currency" value={currencyLabel(savedCurrencyCode)} />
          <SummaryLine label="User" value={user.name} />
          <SummaryLine label="Email" value={user.email} />
          <SummaryLine label="Role" value={user.role} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Company currency</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Quote and pricing screens use this currency.</p>
          </div>
          <Badge variant={isOwner ? 'outline' : 'warning'}>{isOwner ? 'Owner' : 'Read only'}</Badge>
        </CardHeader>
        <CardContent className="grid gap-3">
          <form className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end" onSubmit={handleCurrencySubmit}>
            <Label className="grid gap-1.5">
              Local currency
              <Select
                disabled={!isOwner || isSavingCurrency}
                onChange={(event) => {
                  setCurrencyCode(normalizeCurrencyCode(event.target.value))
                  setCurrencyError(null)
                  setCurrencyMessage(null)
                }}
                value={currencyCode}
              >
                {currencyChoices.map((option) => (
                  <option key={option.code} value={option.code}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </Label>
            <Button disabled={!isOwner || isSavingCurrency || !hasCurrencyChange} type="submit">
              <Save className="h-4 w-4" aria-hidden="true" />
              Save
            </Button>
          </form>
          {!isOwner ? <Alert className="text-xs">Only company owners can change company currency.</Alert> : null}
          {currencyError ? <Alert className="text-xs" variant="destructive">{currencyError}</Alert> : null}
          {currencyMessage ? <Alert className="text-xs">{currencyMessage}</Alert> : null}
        </CardContent>
      </Card>
    </>
  )
}

function StatusCard({
  icon: Icon,
  label,
  title,
  value,
}: {
  icon: ComponentType<{ className?: string; 'aria-hidden'?: boolean }>
  label: string
  title: string
  value: string
}) {
  return (
    <Card>
      <CardContent className="flex items-start gap-4 p-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-muted text-accent">
          <Icon className="h-5 w-5" aria-hidden={true} />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-1 truncate font-semibold">{title}</p>
          <p className="mt-1 truncate text-xs text-muted-foreground">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function SummaryLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-3 border-b border-border pb-2 text-sm last:border-b-0 last:pb-0">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate text-right font-medium" title={value}>
        {value}
      </span>
    </div>
  )
}
