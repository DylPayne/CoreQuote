import {
  Archive,
  Boxes,
  Calculator,
  ChevronDown,
  CircleDollarSign,
  ClipboardList,
  DoorOpen,
  FileDown,
  FolderKanban,
  Grid2X2,
  Hammer,
  HardHat,
  Library,
  Menu,
  MoreHorizontal,
  Moon,
  PanelTop,
  Palette,
  Plus,
  Search,
  Settings,
  Sheet,
  SlidersHorizontal,
  Sun,
} from 'lucide-react'
import { useMemo, useState, type ComponentType, type CSSProperties } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChoiceCard, ChoiceCardContent } from '@/components/ui/choice-card'
import { ControlGroup, ControlGroupItem } from '@/components/ui/control-group'

type ColourTheme =
  | 'neutral'
  | 'slate'
  | 'gray'
  | 'zinc'
  | 'stone'
  | 'olive'
  | 'red'
  | 'orange'
  | 'amber'
  | 'yellow'
  | 'lime'
  | 'green'
  | 'emerald'
  | 'teal'
  | 'cyan'
  | 'sky'
  | 'blue'
  | 'indigo'
  | 'violet'
  | 'purple'
  | 'mauve'
  | 'fuchsia'
  | 'pink'
  | 'rose'

type ThemeSpec = {
  chroma: number
  hue: number
  label: string
  value: ColourTheme
}

type ThemeVars = CSSProperties & Record<`--${string}`, string>
type ThemeMode = 'light' | 'dark'
type AppPage = 'projects' | 'appearance'
type UiStyle = 'vega' | 'nova' | 'maia' | 'lyra' | 'mira' | 'luma' | 'sera'

const colourThemes: ThemeSpec[] = [
  { label: 'Neutral', value: 'neutral', chroma: 0.004, hue: 247 },
  { label: 'Slate', value: 'slate', chroma: 0.018, hue: 255 },
  { label: 'Gray', value: 'gray', chroma: 0.006, hue: 247 },
  { label: 'Zinc', value: 'zinc', chroma: 0.008, hue: 286 },
  { label: 'Stone', value: 'stone', chroma: 0.014, hue: 70 },
  { label: 'Olive', value: 'olive', chroma: 0.07, hue: 128 },
  { label: 'Red', value: 'red', chroma: 0.18, hue: 28 },
  { label: 'Orange', value: 'orange', chroma: 0.16, hue: 52 },
  { label: 'Amber', value: 'amber', chroma: 0.14, hue: 75 },
  { label: 'Yellow', value: 'yellow', chroma: 0.12, hue: 95 },
  { label: 'Lime', value: 'lime', chroma: 0.13, hue: 128 },
  { label: 'Green', value: 'green', chroma: 0.13, hue: 145 },
  { label: 'Emerald', value: 'emerald', chroma: 0.13, hue: 164 },
  { label: 'Teal', value: 'teal', chroma: 0.12, hue: 180 },
  { label: 'Cyan', value: 'cyan', chroma: 0.12, hue: 205 },
  { label: 'Sky', value: 'sky', chroma: 0.13, hue: 235 },
  { label: 'Blue', value: 'blue', chroma: 0.14, hue: 255 },
  { label: 'Indigo', value: 'indigo', chroma: 0.13, hue: 275 },
  { label: 'Violet', value: 'violet', chroma: 0.14, hue: 295 },
  { label: 'Purple', value: 'purple', chroma: 0.14, hue: 310 },
  { label: 'Mauve', value: 'mauve', chroma: 0.08, hue: 325 },
  { label: 'Fuchsia', value: 'fuchsia', chroma: 0.15, hue: 330 },
  { label: 'Pink', value: 'pink', chroma: 0.15, hue: 350 },
  { label: 'Rose', value: 'rose', chroma: 0.16, hue: 15 },
]

const uiStyles: {
  description: string
  label: string
  radius: 'locked' | 'soft' | 'balanced' | 'compact'
  value: UiStyle
}[] = [
  { label: 'Vega', value: 'vega', description: 'Classic shadcn baseline with balanced spacing.', radius: 'balanced' },
  { label: 'Nova', value: 'nova', description: 'Reduced padding and margins for compact layouts.', radius: 'compact' },
  { label: 'Maia', value: 'maia', description: 'Soft and rounded with generous spacing.', radius: 'soft' },
  { label: 'Lyra', value: 'lyra', description: 'Boxy, sharp, and structured for precise tools.', radius: 'locked' },
  { label: 'Mira', value: 'mira', description: 'Dense and product-focused for operational screens.', radius: 'compact' },
  { label: 'Luma', value: 'luma', description: 'Rounded geometry, soft elevation, and calmer rhythm.', radius: 'soft' },
  { label: 'Sera', value: 'sera', description: 'Structured editorial feel with crisp surfaces.', radius: 'locked' },
]

function App() {
  const [colourTheme, setColourTheme] = useState<ColourTheme>('neutral')
  const [currentPage, setCurrentPage] = useState<AppPage>('projects')
  const [themeMode, setThemeMode] = useState<ThemeMode>('light')
  const [uiStyle, setUiStyle] = useState<UiStyle>('lyra')
  const selectedTheme = colourThemes.find((theme) => theme.value === colourTheme) ?? colourThemes[0]
  const selectedStyle = uiStyles.find((style) => style.value === uiStyle) ?? uiStyles[3]
  const themeVars = useMemo(() => createThemeVars(selectedTheme, themeMode, uiStyle), [selectedTheme, themeMode, uiStyle])

  const navItems = [
    { label: 'Projects', icon: FolderKanban, page: 'projects' as const },
    { label: 'Quotes', icon: ClipboardList },
    { label: 'Cutlists', icon: Calculator },
    { label: 'Boards', icon: Grid2X2 },
    { label: 'Hardware', icon: DoorOpen },
    { label: 'Pricing', icon: CircleDollarSign },
    { label: 'Appearance', icon: Palette, page: 'appearance' as const },
    { label: 'Settings', icon: Settings },
  ]

  const quoteRows = [
    {
      unit: 'U01',
      type: 'Base drawer',
      dims: '780 x 900 x 580',
      board: 'PG Bison Melawood 16mm',
      hardware: 'Tandem 500mm',
      status: 'Ready',
    },
    {
      unit: 'U02',
      type: 'Base door',
      dims: '780 x 600 x 580',
      board: 'PG Bison Melawood 16mm',
      hardware: 'Blum 110 deg',
      status: 'Review',
    },
    {
      unit: 'U03',
      type: 'Wall door',
      dims: '720 x 800 x 330',
      board: 'PG Bison Melawood 16mm',
      hardware: 'Blum 110 deg',
      status: 'Ready',
    },
  ]

  const projectCards = [
    { name: 'Smith Kitchen', client: 'John Smith', quotes: 3, value: 'R 84,250' },
    { name: 'Oak Avenue Built-in', client: 'Nandi Meyer', quotes: 1, value: 'R 31,780' },
    { name: 'Workshop Display', client: 'Internal', quotes: 2, value: 'R 52,410' },
  ]

  return (
    <div
      className="min-h-screen bg-background text-foreground"
      data-mode={themeMode}
      data-style={uiStyle}
      data-theme={colourTheme}
      style={themeVars}
    >
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-border bg-sidebar lg:flex lg:flex-col">
        <div className="flex h-14 items-center gap-3 border-b border-border px-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <HardHat className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">CoreQuote</p>
            <p className="text-xs text-muted-foreground">Cabinetry quoting</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-2 py-3">
          {navItems.map((item) => (
            <button
              className={
                item.page === currentPage
                  ? 'flex h-9 w-full items-center gap-3 rounded-md bg-sidebar-accent px-3 text-left text-sm font-medium text-foreground'
                  : 'flex h-9 w-full items-center gap-3 rounded-md px-3 text-left text-sm font-medium text-muted-foreground hover:bg-sidebar-accent hover:text-foreground'
              }
              key={item.label}
              onClick={() => item.page && setCurrentPage(item.page)}
              type="button"
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="border-t border-border p-3">
          <div className="rounded-md border border-dashed border-border bg-background p-2.5">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Archive className="h-4 w-4 text-accent" aria-hidden="true" />
              Frontend preview
            </div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">API not connected</p>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex min-h-14 items-center justify-between gap-3 border-b border-border bg-background/95 px-4 py-2 backdrop-blur md:px-6">
          <div className="flex items-center gap-3">
            <Button className="lg:hidden" size="icon" variant="ghost" aria-label="Open navigation">
              <Menu className="h-5 w-5" aria-hidden="true" />
            </Button>
            <div>
              <h1 className="text-lg font-semibold">{currentPage === 'appearance' ? 'Appearance' : 'Projects'}</h1>
              <p className="hidden text-sm text-muted-foreground sm:block">
                {currentPage === 'appearance'
                  ? 'Global style, colour, and mode controls'
                  : 'Quote pipeline and production readiness'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {currentPage === 'projects' ? (
              <div className="hidden h-[var(--control-height)] items-center gap-2 rounded-[var(--control-radius)] border border-input bg-background px-[var(--control-padding-x)] text-sm text-muted-foreground lg:flex">
              <Search className="h-4 w-4" aria-hidden="true" />
              Search projects
              </div>
            ) : null}
            <Button onClick={() => setCurrentPage('appearance')} variant="outline">
              <Palette className="h-4 w-4" aria-hidden="true" />
              Theme
            </Button>
            <Button variant="outline">
              <FileDown className="h-4 w-4" aria-hidden="true" />
              Export
            </Button>
            <Button>
              <Plus className="h-4 w-4" aria-hidden="true" />
              New quote
            </Button>
          </div>
        </header>

        <main className="mx-auto flex max-w-7xl flex-col gap-[var(--section-gap)] p-4 md:p-5">
          {currentPage === 'appearance' ? (
            <AppearancePage
              colourTheme={colourTheme}
              selectedStyle={selectedStyle}
              setColourTheme={setColourTheme}
              setThemeMode={setThemeMode}
              setUiStyle={setUiStyle}
              themeMode={themeMode}
              uiStyle={uiStyle}
            />
          ) : (
            <ProjectsPage projectCards={projectCards} quoteRows={quoteRows} />
          )}
        </main>
      </div>
    </div>
  )
}

function ProjectsPage({
  projectCards,
  quoteRows,
}: {
  projectCards: { client: string; name: string; quotes: number; value: string }[]
  quoteRows: { board: string; dims: string; hardware: string; status: string; type: string; unit: string }[]
}) {
  return (
    <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard icon={FolderKanban} label="Active projects" value="12" delta="+3 this month" />
            <MetricCard icon={ClipboardList} label="Open quotes" value="28" delta="7 awaiting review" />
            <MetricCard icon={Sheet} label="Cutlists ready" value="18" delta="64 sheets planned" />
            <MetricCard icon={CircleDollarSign} label="Quoted value" value="R 412k" delta="Ex VAT estimate" />
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Quote workspace</CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">Smith Kitchen / Revision B</p>
                </div>
                <Button variant="outline">
                  <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                  Defaults
                </Button>
              </CardHeader>
              <CardContent>
                <div className="overflow-hidden rounded-md border border-border">
                  <table className="w-full border-collapse text-left text-sm">
                    <thead className="bg-muted text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3 font-medium">Unit</th>
                        <th className="px-4 py-3 font-medium">Type</th>
                        <th className="hidden px-4 py-3 font-medium md:table-cell">Dimensions</th>
                        <th className="hidden px-4 py-3 font-medium lg:table-cell">Board</th>
                        <th className="hidden px-4 py-3 font-medium lg:table-cell">Hardware</th>
                        <th className="px-4 py-3 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {quoteRows.map((row) => (
                        <tr className="border-t border-border" key={row.unit}>
                          <td className="px-4 py-4 font-medium text-foreground">{row.unit}</td>
                          <td className="px-4 py-4">{row.type}</td>
                          <td className="hidden px-4 py-4 text-muted-foreground md:table-cell">{row.dims}</td>
                          <td className="hidden px-4 py-4 text-muted-foreground lg:table-cell">{row.board}</td>
                          <td className="hidden px-4 py-4 text-muted-foreground lg:table-cell">{row.hardware}</td>
                          <td className="px-4 py-4">
                            <Badge variant={row.status === 'Ready' ? 'success' : 'warning'}>{row.status}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-4">
              <Card>
                <CardHeader>
                  <CardTitle>Material summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <InventoryLine icon={Grid2X2} label="Boards" value="14 sheets" tone="blue" />
                  <InventoryLine icon={PanelTop} label="Panels" value="22 pieces" tone="green" />
                  <InventoryLine icon={Boxes} label="Hardware" value="56 items" tone="amber" />
                  <InventoryLine icon={Hammer} label="Extras" value="8 items" tone="slate" />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Pricing status</CardTitle>
                  <Button size="icon" variant="ghost" aria-label="More pricing actions">
                    <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between rounded-md bg-muted px-3 py-3">
                    <span className="text-sm text-muted-foreground">Markup</span>
                    <span className="text-sm font-medium">35%</span>
                  </div>
                  <div className="flex items-center justify-between rounded-md bg-muted px-3 py-3">
                    <span className="text-sm text-muted-foreground">VAT</span>
                    <span className="text-sm font-medium">15%</span>
                  </div>
                  <Button className="w-full" variant="secondary">
                    View pricing run
                    <ChevronDown className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </CardContent>
              </Card>
            </div>
          </section>

          <section className="grid gap-4 lg:grid-cols-3">
            {projectCards.map((project) => (
              <Card key={project.name}>
                <CardHeader className="space-y-1">
                  <CardTitle className="text-base">{project.name}</CardTitle>
                  <p className="text-sm text-muted-foreground">{project.client}</p>
                </CardHeader>
                <CardContent className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    {project.quotes} quote{project.quotes === 1 ? '' : 's'}
                  </div>
                  <div className="font-semibold">{project.value}</div>
                </CardContent>
              </Card>
            ))}
          </section>

          <section className="grid gap-4 md:grid-cols-3">
            <ActionTile icon={Library} label="Library health" value="Boards, slides, hinges, handles" />
            <ActionTile icon={Calculator} label="Cutlist preview" value="Carcass and panel schedules" />
            <ActionTile icon={FileDown} label="PDF output" value="Production-ready downloads" />
          </section>
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
  selectedStyle: (typeof uiStyles)[number]
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
            <ControlShell>
              <Palette className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <span className="h-3 w-3 border border-border bg-primary" aria-hidden="true" />
              <select
                aria-label="Select colour theme"
                className="h-8 bg-transparent text-sm font-medium outline-none"
                onChange={(event) => setColourTheme(event.target.value as ColourTheme)}
                value={colourTheme}
              >
                {colourThemes.map((theme) => (
                  <option key={theme.value} value={theme.value}>
                    {theme.label}
                  </option>
                ))}
              </select>
            </ControlShell>
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
                      <Badge variant={uiStyle === style.value ? 'default' : 'outline'}>
                        {style.radius}
                      </Badge>
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
              <SummaryLine label="Colour" value={colourThemes.find((theme) => theme.value === colourTheme)?.label ?? colourTheme} />
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

type IconType = ComponentType<{ className?: string; 'aria-hidden'?: boolean }>

function MetricCard({
  icon: Icon,
  label,
  value,
  delta,
}: {
  icon: IconType
  label: string
  value: string
  delta: string
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{delta}</p>
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-md bg-muted">
          <Icon className="h-5 w-5 text-accent" aria-hidden={true} />
        </div>
      </CardContent>
    </Card>
  )
}

function InventoryLine({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: IconType
  label: string
  value: string
  tone: 'blue' | 'green' | 'amber' | 'slate'
}) {
  const toneClasses = {
    amber: 'bg-muted text-accent border-border',
    blue: 'bg-muted text-accent border-border',
    green: 'bg-muted text-accent border-border',
    slate: 'bg-muted text-accent border-border',
  }

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className={`flex h-9 w-9 items-center justify-center rounded-md border ${toneClasses[tone]}`}>
          <Icon className="h-4 w-4" aria-hidden={true} />
        </div>
        <span className="text-sm font-medium">{label}</span>
      </div>
      <span className="text-sm text-muted-foreground">{value}</span>
    </div>
  )
}

function ActionTile({ icon: Icon, label, value }: { icon: IconType; label: string; value: string }) {
  return (
    <button
      className="flex min-h-24 items-center gap-4 rounded-md border border-border bg-card p-[var(--card-padding)] text-left shadow-[var(--shadow-card)] transition hover:border-primary hover:bg-muted"
      type="button"
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <Icon className="h-5 w-5" aria-hidden={true} />
      </span>
      <span>
        <span className="block text-sm font-semibold">{label}</span>
        <span className="mt-1 block text-sm text-muted-foreground">{value}</span>
      </span>
    </button>
  )
}

function ControlShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-[var(--control-height)] items-center gap-2 rounded-[var(--control-radius)] border border-input bg-background px-[var(--control-padding-x)] text-sm font-medium">
      {children}
    </div>
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
    <div className={`flex min-h-24 items-end rounded-[var(--card-radius)] p-[var(--card-padding)] text-sm font-medium ${className}`}>
      {label}
    </div>
  )
}

function SummaryLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-2 text-sm last:border-b-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

function createThemeVars(theme: ThemeSpec, mode: ThemeMode, uiStyle: UiStyle): ThemeVars {
  const { chroma, hue, value } = theme
  const neutralTone = value === 'gray' || value === 'neutral' || value === 'zinc' || value === 'slate'
  const warmNeutral = value === 'stone'
  const primaryLightness = value === 'yellow' || value === 'amber' || value === 'lime' ? 0.34 : 0.39
  const primaryChroma = neutralTone ? chroma : chroma * 0.72
  const accentChroma = neutralTone ? chroma * 1.5 : chroma
  const foregroundChroma = warmNeutral ? 0.014 : chroma
  const primary = `oklch(${primaryLightness} ${primaryChroma} ${hue})`
  const darkPrimary = `oklch(${neutralTone ? 0.76 : 0.72} ${neutralTone ? chroma * 2 : primaryChroma} ${hue})`

  const lightTokens = {
    accent: `oklch(0.56 ${accentChroma} ${hue})`,
    'accent-foreground': 'oklch(0.985 0.003 247)',
    background: `oklch(0.985 ${neutralTone ? 0.002 : 0.008} ${hue})`,
    border: `oklch(0.82 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    card: 'oklch(1 0 0)',
    'card-foreground': `oklch(0.18 ${foregroundChroma} ${hue})`,
    destructive: 'oklch(0.56 0.18 28)',
    'destructive-foreground': 'oklch(0.985 0.003 247)',
    foreground: `oklch(0.18 ${foregroundChroma} ${hue})`,
    input: `oklch(0.82 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    muted: `oklch(0.95 ${neutralTone ? chroma : chroma * 0.1} ${hue})`,
    'muted-foreground': `oklch(0.45 ${neutralTone ? chroma : chroma * 0.28} ${hue})`,
    popover: 'oklch(1 0 0)',
    'popover-foreground': `oklch(0.18 ${foregroundChroma} ${hue})`,
    primary,
    'primary-foreground': 'oklch(0.985 0.003 247)',
    ring: `oklch(0.52 ${neutralTone ? chroma : chroma * 0.72} ${hue})`,
    secondary: `oklch(0.935 ${neutralTone ? chroma : chroma * 0.12} ${hue})`,
    'secondary-foreground': `oklch(0.23 ${neutralTone ? chroma : chroma * 0.32} ${hue})`,
    sidebar: `oklch(0.958 ${neutralTone ? chroma : chroma * 0.12} ${hue})`,
    'sidebar-accent': `oklch(0.9 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'status-success': 'oklch(0.965 0.035 158)',
    'status-success-border': 'oklch(0.78 0.12 158)',
    'status-success-foreground': 'oklch(0.38 0.11 158)',
    'status-warning': 'oklch(0.965 0.04 82)',
    'status-warning-border': 'oklch(0.82 0.11 82)',
    'status-warning-foreground': 'oklch(0.43 0.1 72)',
  }

  const darkTokens = {
    accent: darkPrimary,
    'accent-foreground': `oklch(0.16 ${foregroundChroma} ${hue})`,
    background: `oklch(0.15 ${neutralTone ? chroma : chroma * 0.18} ${hue})`,
    border: `oklch(0.32 ${neutralTone ? chroma : chroma * 0.24} ${hue})`,
    card: `oklch(0.19 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'card-foreground': `oklch(0.95 ${neutralTone ? chroma : chroma * 0.08} ${hue})`,
    destructive: 'oklch(0.66 0.16 28)',
    'destructive-foreground': 'oklch(0.985 0.003 247)',
    foreground: `oklch(0.95 ${neutralTone ? chroma : chroma * 0.08} ${hue})`,
    input: `oklch(0.34 ${neutralTone ? chroma : chroma * 0.24} ${hue})`,
    muted: `oklch(0.25 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'muted-foreground': `oklch(0.72 ${neutralTone ? chroma : chroma * 0.14} ${hue})`,
    popover: `oklch(0.2 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'popover-foreground': `oklch(0.95 ${neutralTone ? chroma : chroma * 0.08} ${hue})`,
    primary: darkPrimary,
    'primary-foreground': `oklch(0.15 ${foregroundChroma} ${hue})`,
    ring: darkPrimary,
    secondary: `oklch(0.27 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'secondary-foreground': `oklch(0.94 ${neutralTone ? chroma : chroma * 0.08} ${hue})`,
    sidebar: `oklch(0.13 ${neutralTone ? chroma : chroma * 0.18} ${hue})`,
    'sidebar-accent': `oklch(0.25 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'status-success': 'oklch(0.24 0.055 158)',
    'status-success-border': 'oklch(0.46 0.12 158)',
    'status-success-foreground': 'oklch(0.84 0.12 158)',
    'status-warning': 'oklch(0.25 0.055 82)',
    'status-warning-border': 'oklch(0.5 0.12 82)',
    'status-warning-foreground': 'oklch(0.86 0.13 82)',
  }

  const tokens = {
    ...(mode === 'dark' ? darkTokens : lightTokens),
    ...styleTokens(uiStyle),
  }

  return Object.entries(tokens).reduce<ThemeVars>((vars, [name, color]) => {
    vars[`--${name}`] = color
    vars[`--color-${name}`] = color
    return vars
  }, {})
}

function styleTokens(uiStyle: UiStyle) {
  const styles: Record<UiStyle, Record<string, string>> = {
    luma: {
      'card-padding': '1.375rem',
      'card-radius': '1rem',
      'control-height': '2.5rem',
      'control-padding-x': '0.9rem',
      'control-radius': '0.875rem',
      'radius-lg-global': '1rem',
      'radius-md-global': '0.875rem',
      'radius-sm-global': '0.625rem',
      'section-gap': '1.25rem',
      'shadow-card': '0 14px 30px rgb(0 0 0 / 0.08)',
    },
    lyra: {
      'card-padding': '1rem',
      'card-radius': '0rem',
      'control-height': '2.25rem',
      'control-padding-x': '0.75rem',
      'control-radius': '0rem',
      'radius-lg-global': '0rem',
      'radius-md-global': '0rem',
      'radius-sm-global': '0rem',
      'section-gap': '1rem',
      'shadow-card': 'none',
    },
    maia: {
      'card-padding': '1.5rem',
      'card-radius': '1.25rem',
      'control-height': '2.5rem',
      'control-padding-x': '1rem',
      'control-radius': '999px',
      'radius-lg-global': '1.25rem',
      'radius-md-global': '1rem',
      'radius-sm-global': '0.75rem',
      'section-gap': '1.5rem',
      'shadow-card': '0 10px 28px rgb(0 0 0 / 0.06)',
    },
    mira: {
      'card-padding': '0.875rem',
      'card-radius': '0.25rem',
      'control-height': '2rem',
      'control-padding-x': '0.625rem',
      'control-radius': '0.25rem',
      'radius-lg-global': '0.375rem',
      'radius-md-global': '0.25rem',
      'radius-sm-global': '0.125rem',
      'section-gap': '0.75rem',
      'shadow-card': '0 1px 0 rgb(0 0 0 / 0.05)',
    },
    nova: {
      'card-padding': '0.95rem',
      'card-radius': '0.375rem',
      'control-height': '2.125rem',
      'control-padding-x': '0.7rem',
      'control-radius': '0.375rem',
      'radius-lg-global': '0.5rem',
      'radius-md-global': '0.375rem',
      'radius-sm-global': '0.25rem',
      'section-gap': '0.875rem',
      'shadow-card': '0 1px 0 rgb(0 0 0 / 0.04)',
    },
    sera: {
      'card-padding': '1.125rem',
      'card-radius': '0.125rem',
      'control-height': '2.25rem',
      'control-padding-x': '0.85rem',
      'control-radius': '0.125rem',
      'radius-lg-global': '0.125rem',
      'radius-md-global': '0.125rem',
      'radius-sm-global': '0.0625rem',
      'section-gap': '1.125rem',
      'shadow-card': '0 0 0 1px rgb(0 0 0 / 0.02)',
    },
    vega: {
      'card-padding': '1rem',
      'card-radius': '0.5rem',
      'control-height': '2.25rem',
      'control-padding-x': '0.75rem',
      'control-radius': '0.5rem',
      'radius-lg-global': '0.5rem',
      'radius-md-global': '0.5rem',
      'radius-sm-global': '0.25rem',
      'section-gap': '1rem',
      'shadow-card': '0 1px 2px rgb(0 0 0 / 0.06)',
    },
  }

  return styles[uiStyle]
}

export default App
