import { Building2, HardHat, Moon, Palette, ShieldCheck, Sun, UserRound } from 'lucide-react'
import type { ComponentType } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChoiceCard, ChoiceCardContent } from '@/components/ui/choice-card'
import { ControlGroup, ControlGroupItem } from '@/components/ui/control-group'
import { Select } from '@/components/ui/select'
import { colourThemes, uiStyles } from '@/lib/theme'
import type { AuthUser } from '@/types/auth'
import type { ColourTheme, ThemeMode, UiStyle, UiStyleSpec } from '@/types/theme'

export function SettingsPage({
  colourTheme,
  selectedStyle,
  setColourTheme,
  setThemeMode,
  setUiStyle,
  themeMode,
  uiStyle,
  user,
}: {
  colourTheme: ColourTheme
  selectedStyle: UiStyleSpec
  setColourTheme: (theme: ColourTheme) => void
  setThemeMode: (mode: ThemeMode) => void
  setUiStyle: (style: UiStyle) => void
  themeMode: ThemeMode
  uiStyle: UiStyle
  user: AuthUser
}) {
  return (
    <>
      <section className="grid gap-4 lg:grid-cols-3">
        <StatusCard
          icon={ShieldCheck}
          label="Session"
          title="Authenticated"
          value="Bearer token restored through /me"
        />
        <StatusCard icon={Building2} label="Company" title={user.company_name} value={user.company_id} />
        <StatusCard icon={UserRound} label="User" title={user.name} value={user.email} />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Workspace details</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">Company, role, and session details for this account.</p>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <SummaryLine label="Company" value={user.company_name} />
          <SummaryLine label="Company ID" value={user.company_id} />
          <SummaryLine label="User" value={user.name} />
          <SummaryLine label="Email" value={user.email} />
          <SummaryLine label="Role" value={user.role} />
          <SummaryLine label="User ID" value={user.id} />
        </CardContent>
      </Card>

      <AppearancePage
        colourTheme={colourTheme}
        selectedStyle={selectedStyle}
        setColourTheme={setColourTheme}
        setThemeMode={setThemeMode}
        setUiStyle={setUiStyle}
        themeMode={themeMode}
        uiStyle={uiStyle}
      />
    </>
  )
}

function AppearancePage({
  colourTheme,
  selectedStyle,
  setColourTheme,
  setThemeMode,
  setUiStyle,
  themeMode,
  uiStyle,
}: {
  colourTheme: ColourTheme
  selectedStyle: UiStyleSpec
  setColourTheme: (theme: ColourTheme) => void
  setThemeMode: (mode: ThemeMode) => void
  setUiStyle: (style: UiStyle) => void
  themeMode: ThemeMode
  uiStyle: UiStyle
}) {
  return (
    <>
      <Card>
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Theme studio</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              These controls update global variables for the entire app shell.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2">
              <Palette className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <span className="h-3 w-3 shrink-0 border border-border bg-primary" aria-hidden="true" />
              <Select
                aria-label="Select colour theme"
                className="w-36"
                onChange={(event) => setColourTheme(event.target.value as ColourTheme)}
                value={colourTheme}
              >
                {colourThemes.map((theme) => (
                  <option key={theme.value} value={theme.value}>
                    {theme.label}
                  </option>
                ))}
              </Select>
            </div>
            <ModeSwitch setThemeMode={setThemeMode} themeMode={themeMode} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            <PreviewBlock label="Primary" className="bg-primary text-primary-foreground" />
            <PreviewBlock label="Muted" className="bg-muted text-muted-foreground" />
            <PreviewBlock label="Card" className="border border-border bg-card text-card-foreground" />
          </div>
        </CardContent>
      </Card>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>Style</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Styles are global shape, density, radius, and elevation presets.
            </p>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {uiStyles.map((style) => (
              <ChoiceCard
                aria-pressed={uiStyle === style.value}
                key={style.value}
                onClick={() => setUiStyle(style.value)}
              >
                <ChoiceCardContent>
                  <div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-base font-semibold">{style.label}</span>
                      <Badge variant={uiStyle === style.value ? 'default' : 'outline'}>{style.radius}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{style.description}</p>
                  </div>
                  <div className="mt-4 grid grid-cols-3 gap-2">
                    <span className="h-8 rounded-[var(--control-radius)] bg-primary" />
                    <span className="h-8 rounded-[var(--control-radius)] bg-muted" />
                    <span className="h-8 rounded-[var(--control-radius)] border border-border bg-card" />
                  </div>
                </ChoiceCardContent>
              </ChoiceCard>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Current selection</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              <SummaryLine label="Style" value={selectedStyle.label} />
              <SummaryLine label="Mode" value={themeMode === 'dark' ? 'Dark' : 'Light'} />
              <SummaryLine
                label="Colour"
                value={colourThemes.find((theme) => theme.value === colourTheme)?.label ?? colourTheme}
              />
            </div>
            <div className="rounded-[var(--card-radius)] border border-border bg-muted p-[var(--card-padding)]">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-[var(--control-radius)] bg-primary text-primary-foreground">
                  <HardHat className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm font-semibold">Global preview</p>
                  <p className="text-sm text-muted-foreground">One token set, every component follows.</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
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

function ModeSwitch({
  setThemeMode,
  themeMode,
}: {
  setThemeMode: (mode: ThemeMode) => void
  themeMode: ThemeMode
}) {
  return (
    <ControlGroup
      aria-label="Select light or dark mode"
      className="min-w-[calc(var(--control-height)*2)]"
      role="group"
    >
      <ControlGroupItem aria-pressed={themeMode === 'light'} onClick={() => setThemeMode('light')}>
        <Sun className="h-4 w-4" aria-hidden="true" />
        <span className="sr-only">Light mode</span>
      </ControlGroupItem>
      <ControlGroupItem aria-pressed={themeMode === 'dark'} onClick={() => setThemeMode('dark')}>
        <Moon className="h-4 w-4" aria-hidden="true" />
        <span className="sr-only">Dark mode</span>
      </ControlGroupItem>
    </ControlGroup>
  )
}

function PreviewBlock({ className, label }: { className: string; label: string }) {
  return (
    <div
      className={`flex min-h-24 items-end rounded-[var(--card-radius)] p-[var(--card-padding)] text-sm font-medium ${className}`}
    >
      {label}
    </div>
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
