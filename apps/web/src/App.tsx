import {
  Building2,
  Calculator,
  ClipboardList,
  CopyPlus,
  HardHat,
  LoaderCircle,
  LogOut,
  Moon,
  Palette,
  Plus,
  Save,
  ShieldCheck,
  Sun,
  Trash2,
  UserRound,
} from 'lucide-react'
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from 'react'

import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { ChoiceCard, ChoiceCardContent } from '@/components/ui/choice-card'
import { ControlGroup, ControlGroupItem } from '@/components/ui/control-group'
import { FormulaEditor } from '@/components/formula-editor'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow } from '@/components/ui/table'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')
const AUTH_TOKEN_KEY = 'corequote.authToken'

type AuthMode = 'login' | 'register'
type AuthStatus = 'checking' | 'signed-in' | 'signed-out'
type AppPage = 'workspace' | 'cutlist' | 'cutlist-tester' | 'appearance'
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
type ThemeMode = 'light' | 'dark'
type UiStyle = 'vega' | 'nova' | 'maia' | 'lyra' | 'mira' | 'luma' | 'sera'
type UnitConfigCategory = 'base' | 'wall' | 'tall' | 'custom'
type UnitConfigVariantType = 'drawer' | 'door' | 'wall' | 'tall' | 'custom'
type CuttingConfigStatus = 'draft' | 'active' | 'archived'
type CuttingRuleSection = 'carcass' | 'panel' | 'hardware' | 'extra_panel'
type GrainDirection = 'none' | 'length' | 'width'
type FormulaFieldKey = 'length_formula' | 'width_formula' | 'qty_formula' | 'condition_formula'
type UnitType = string

type ThemeSpec = {
  chroma: number
  hue: number
  label: string
  value: ColourTheme
}

type ThemeVars = CSSProperties & Record<`--${string}`, string>

type AuthUser = {
  id: string
  company_id: string
  company_name: string
  name: string
  email: string
  role: 'owner' | 'admin' | 'manager' | 'estimator' | 'production' | 'viewer' | 'member'
}

type AuthTokenResponse = {
  access_token: string
  token_type: 'bearer'
  expires_at: string
  user: AuthUser
}

type AuthFormState = {
  companyName: string
  name: string
  email: string
  password: string
}

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

type CutlistPreviewResponse = {
  carcass: CutlistPreviewRow[]
  panels: CutlistPreviewRow[]
  hardware: CutlistPreviewRow[]
  extras: CutlistPreviewRow[]
  runtime_rows: CutlistRuntimeRow[]
  runtime_mode: 'legacy' | 'ruleset' | 'mixed'
  unit_sources: CutlistUnitSource[]
}

type CutlistTesterDraft = {
  unitNumber: string
  unitType: UnitType
  customUnitType: string
  useCustomUnitType: boolean
  height: string
  width: string
  depth: string
  thickness: string
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

const initialAuthForm: AuthFormState = {
  companyName: '',
  email: '',
  name: '',
  password: '',
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

function App() {
  const [authMode, setAuthMode] = useState<AuthMode>('login')
  const [authForm, setAuthForm] = useState<AuthFormState>(initialAuthForm)
  const [authToken, setAuthToken] = useState<string | null>(getStoredAuthToken)
  const [authStatus, setAuthStatus] = useState<AuthStatus>(() => (getStoredAuthToken() ? 'checking' : 'signed-out'))
  const [authError, setAuthError] = useState<string | null>(null)
  const [colourTheme, setColourTheme] = useState<ColourTheme>('neutral')
  const [currentPage, setCurrentPage] = useState<AppPage>('workspace')
  const [isSubmittingAuth, setIsSubmittingAuth] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [themeMode, setThemeMode] = useState<ThemeMode>('light')
  const [uiStyle, setUiStyle] = useState<UiStyle>('lyra')
  const [user, setUser] = useState<AuthUser | null>(null)
  const selectedTheme = colourThemes.find((theme) => theme.value === colourTheme) ?? colourThemes[0]
  const selectedStyle = uiStyles.find((style) => style.value === uiStyle) ?? uiStyles[3]
  const themeVars = useMemo(() => createThemeVars(selectedTheme, themeMode, uiStyle), [selectedTheme, themeMode, uiStyle])

  const clearSession = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    setAuthToken(null)
    setUser(null)
    setAuthStatus('signed-out')
  }, [])

  const storeSession = useCallback((session: AuthTokenResponse) => {
    localStorage.setItem(AUTH_TOKEN_KEY, session.access_token)
    setAuthToken(session.access_token)
    setUser(session.user)
    setAuthStatus('signed-in')
  }, [])

  useEffect(() => {
    if (!authToken) {
      return
    }

    const token = authToken
    let isCurrent = true

    async function restoreSession() {
      try {
        const currentUser = await apiRequest<AuthUser>('/api/v1/auth/me', {
          token,
        })

        if (!isCurrent) return
        setUser(currentUser)
        setAuthStatus('signed-in')
      } catch (error) {
        if (!isCurrent) return
        clearSession()
        setAuthError(error instanceof Error ? error.message : 'Your session expired. Please sign in again.')
      }
    }

    restoreSession()

    return () => {
      isCurrent = false
    }
  }, [authToken, clearSession])

  async function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthError(null)
    setIsSubmittingAuth(true)

    try {
      const endpoint = authMode === 'register' ? '/api/v1/auth/register' : '/api/v1/auth/login'
      const payload =
        authMode === 'register'
          ? {
              company_name: authForm.companyName.trim(),
              email: authForm.email.trim(),
              name: authForm.name.trim(),
              password: authForm.password,
            }
          : {
              email: authForm.email.trim(),
              password: authForm.password,
            }

      const session = await apiRequest<AuthTokenResponse>(endpoint, {
        body: payload,
        method: 'POST',
      })
      storeSession(session)
      setAuthForm(initialAuthForm)
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Authentication failed.')
    } finally {
      setIsSubmittingAuth(false)
    }
  }

  async function handleLogout() {
    if (!authToken) {
      clearSession()
      return
    }

    setIsLoggingOut(true)
    try {
      await apiRequest('/api/v1/auth/logout', {
        method: 'POST',
        token: authToken,
      })
    } catch {
      // A failed logout still leaves the local session unusable from the user's perspective.
    } finally {
      setIsLoggingOut(false)
      clearSession()
    }
  }

  if (authStatus === 'checking') {
    return (
      <AppTheme colourTheme={colourTheme} themeMode={themeMode} themeVars={themeVars} uiStyle={uiStyle}>
        <LoadingScreen />
      </AppTheme>
    )
  }

  if (authStatus === 'signed-out' || !user || !authToken) {
    return (
      <AppTheme colourTheme={colourTheme} themeMode={themeMode} themeVars={themeVars} uiStyle={uiStyle}>
        <AuthScreen
          authError={authError}
          authForm={authForm}
          authMode={authMode}
          isSubmitting={isSubmittingAuth}
          onModeChange={(mode) => {
            setAuthMode(mode)
            setAuthError(null)
          }}
          onSubmit={handleAuthSubmit}
          setAuthForm={setAuthForm}
        />
      </AppTheme>
    )
  }

  return (
    <AppTheme colourTheme={colourTheme} themeMode={themeMode} themeVars={themeVars} uiStyle={uiStyle}>
      <Workspace
        authToken={authToken}
        colourTheme={colourTheme}
        currentPage={currentPage}
        isLoggingOut={isLoggingOut}
        onLogout={handleLogout}
        selectedStyle={selectedStyle}
        setColourTheme={setColourTheme}
        setCurrentPage={setCurrentPage}
        setThemeMode={setThemeMode}
        setUiStyle={setUiStyle}
        themeMode={themeMode}
        uiStyle={uiStyle}
        user={user}
      />
    </AppTheme>
  )
}

function AppTheme({
  children,
  colourTheme,
  themeMode,
  themeVars,
  uiStyle,
}: {
  children: React.ReactNode
  colourTheme: ColourTheme
  themeMode: ThemeMode
  themeVars: ThemeVars
  uiStyle: UiStyle
}) {
  return (
    <div
      className="min-h-screen bg-background text-foreground"
      data-mode={themeMode}
      data-style={uiStyle}
      data-theme={colourTheme}
      style={themeVars}
    >
      {children}
    </div>
  )
}

function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <LoaderCircle className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
        Restoring your CoreQuote session
      </div>
    </div>
  )
}

function AuthScreen({
  authError,
  authForm,
  authMode,
  isSubmitting,
  onModeChange,
  onSubmit,
  setAuthForm,
}: {
  authError: string | null
  authForm: AuthFormState
  authMode: AuthMode
  isSubmitting: boolean
  onModeChange: (mode: AuthMode) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  setAuthForm: React.Dispatch<React.SetStateAction<AuthFormState>>
}) {
  const isRegistering = authMode === 'register'

  return (
    <div className="grid min-h-screen bg-background text-foreground lg:grid-cols-[0.95fr_1.05fr]">
      <section className="flex min-h-[38vh] flex-col justify-between border-b border-border bg-sidebar p-6 lg:min-h-screen lg:border-b-0 lg:border-r lg:p-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <HardHat className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold">CoreQuote</p>
            <p className="text-xs text-muted-foreground">Cabinetry quoting</p>
          </div>
        </div>

        <div className="max-w-xl py-10">
          <Badge className="mb-5" variant="outline">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            API-backed auth
          </Badge>
          <h1 className="text-3xl font-semibold tracking-normal md:text-4xl">Sign in to your quoting workspace.</h1>
          <p className="mt-4 max-w-lg text-sm leading-6 text-muted-foreground">
            Sessions are restored with <span className="font-medium text-foreground">/api/v1/auth/me</span>, and
            every authenticated request uses the bearer token returned by the API.
          </p>
        </div>

        <div className="grid gap-3 text-sm text-muted-foreground sm:grid-cols-3 lg:grid-cols-1">
          <FeatureLine icon={Building2} label="Company tenant context" />
          <FeatureLine icon={UserRound} label="Owner registration flow" />
          <FeatureLine icon={LogOut} label="Revoked logout sessions" />
        </div>
      </section>

      <main className="flex items-center justify-center p-4 md:p-8">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{isRegistering ? 'Create owner account' : 'Welcome back'}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {isRegistering
                ? 'Register the company and first owner user.'
                : 'Log in with an existing CoreQuote account.'}
            </p>
          </CardHeader>
          <CardContent>
            <ControlGroup className="mb-5 w-full gap-0" role="group" aria-label="Select auth mode">
              <ControlGroupItem
                aria-pressed={authMode === 'login'}
                className="flex-1 justify-center rounded-[calc(var(--control-radius)-0.2rem)]"
                onClick={() => onModeChange('login')}
              >
                Log in
              </ControlGroupItem>
              <ControlGroupItem
                aria-pressed={authMode === 'register'}
                className="flex-1 justify-center rounded-[calc(var(--control-radius)-0.2rem)]"
                onClick={() => onModeChange('register')}
              >
                Register
              </ControlGroupItem>
            </ControlGroup>

            <form className="space-y-4" onSubmit={onSubmit}>
              {isRegistering ? (
                <>
                  <Field
                    autoComplete="organization"
                    label="Company name"
                    minLength={2}
                    onChange={(value) => setAuthForm((current) => ({ ...current, companyName: value }))}
                    required
                    value={authForm.companyName}
                  />
                  <Field
                    autoComplete="name"
                    label="Your name"
                    minLength={2}
                    onChange={(value) => setAuthForm((current) => ({ ...current, name: value }))}
                    required
                    value={authForm.name}
                  />
                </>
              ) : null}

              <Field
                autoComplete="email"
                label="Email"
                onChange={(value) => setAuthForm((current) => ({ ...current, email: value }))}
                required
                type="email"
                value={authForm.email}
              />
              <Field
                autoComplete={isRegistering ? 'new-password' : 'current-password'}
                label="Password"
                minLength={isRegistering ? 12 : 1}
                onChange={(value) => setAuthForm((current) => ({ ...current, password: value }))}
                required
                type="password"
                value={authForm.password}
              />

              {authError ? (
                <Alert variant="destructive">{authError}</Alert>
              ) : null}

              <Button className="w-full" disabled={isSubmitting} type="submit">
                {isSubmitting ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                {isRegistering ? 'Create account' : 'Log in'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}

function Workspace({
  authToken,
  colourTheme,
  currentPage,
  isLoggingOut,
  onLogout,
  selectedStyle,
  setColourTheme,
  setCurrentPage,
  setThemeMode,
  setUiStyle,
  themeMode,
  uiStyle,
  user,
}: {
  authToken: string
  colourTheme: ColourTheme
  currentPage: AppPage
  isLoggingOut: boolean
  onLogout: () => void
  selectedStyle: (typeof uiStyles)[number]
  setColourTheme: (theme: ColourTheme) => void
  setCurrentPage: (page: AppPage) => void
  setThemeMode: (mode: ThemeMode) => void
  setUiStyle: (style: UiStyle) => void
  themeMode: ThemeMode
  uiStyle: UiStyle
  user: AuthUser
}) {
  const navItems = [
    { label: 'Workspace', icon: ClipboardList, page: 'workspace' as const },
    { label: 'Cutlist', icon: Calculator, page: 'cutlist' as const },
    { label: 'Tester', icon: CopyPlus, page: 'cutlist-tester' as const },
    { label: 'Appearance', icon: Palette, page: 'appearance' as const },
  ]
  const pageTitle =
    currentPage === 'appearance'
      ? 'Appearance'
      : currentPage === 'cutlist'
        ? 'Cutlist'
        : currentPage === 'cutlist-tester'
          ? 'Cutlist Tester'
          : 'Workspace'
  const pageDescription =
    currentPage === 'appearance'
      ? 'Global style, colour, and mode controls'
      : currentPage === 'cutlist'
        ? 'Manage cutting rulesets and row formulas'
        : currentPage === 'cutlist-tester'
          ? 'Run runtime cutlist generation with custom unit inputs'
        : user.company_name

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-border bg-sidebar lg:flex lg:flex-col">
        <div className="flex h-14 items-center gap-3 border-b border-border px-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <HardHat className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">CoreQuote</p>
            <p className="text-xs text-muted-foreground">{user.company_name}</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-2 py-3">
          {navItems.map((item) => (
            <Button
              aria-pressed={item.page === currentPage}
              className="h-9 px-3"
              key={item.page}
              onClick={() => setCurrentPage(item.page)}
              type="button"
              variant={item.page === currentPage ? 'navActive' : 'nav'}
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </Button>
          ))}
        </nav>

        <div className="border-t border-border p-3">
          <Card className="p-3">
            <p className="truncate text-sm font-medium">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground">{user.email}</p>
            <Badge className="mt-3" variant="outline">
              {user.role}
            </Badge>
          </Card>
        </div>
      </aside>

      <div className="overflow-x-hidden lg:pl-64">
        <header className="sticky top-0 z-10 flex min-h-14 items-center justify-between gap-3 border-b border-border bg-background/95 px-4 py-2 backdrop-blur md:px-6">
          <div>
            <h1 className="text-lg font-semibold">{pageTitle}</h1>
            <p className="hidden text-sm text-muted-foreground sm:block">{pageDescription}</p>
          </div>
          <div className="flex items-center gap-2">
            {currentPage === 'workspace' ? (
              <Button className="hidden sm:inline-flex" onClick={() => setCurrentPage('appearance')} variant="outline">
                <Palette className="h-4 w-4" aria-hidden="true" />
                Theme
              </Button>
            ) : null}
            <Button disabled={isLoggingOut} onClick={onLogout} variant="outline">
              {isLoggingOut ? (
                <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <LogOut className="h-4 w-4" aria-hidden="true" />
              )}
              Sign out
            </Button>
          </div>
        </header>

        <nav className="grid grid-cols-4 gap-2 border-b border-border bg-background px-4 py-2 lg:hidden">
          {navItems.map((item) => (
            <Button
              aria-pressed={item.page === currentPage}
              className="h-9 justify-center gap-1 px-1 text-xs"
              key={item.page}
              onClick={() => setCurrentPage(item.page)}
              size="sm"
              type="button"
              variant={item.page === currentPage ? 'navActive' : 'nav'}
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              <span className="truncate">{item.label}</span>
            </Button>
          ))}
        </nav>

        <main className="mx-auto grid min-w-0 max-w-7xl gap-[var(--section-gap)] overflow-x-hidden p-4 md:p-5">
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
          ) : currentPage === 'cutlist' ? (
            <CuttingRulesetsPage authToken={authToken} companyId={user.company_id} />
          ) : currentPage === 'cutlist-tester' ? (
            <CutlistTesterPage authToken={authToken} />
          ) : (
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
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <CardTitle>Workspace overview</CardTitle>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Authenticated and ready for quote tools as they come online.
                    </p>
                  </div>
                  <Button onClick={() => setCurrentPage('cutlist')}>
                    <Calculator className="h-4 w-4" aria-hidden="true" />
                    Open cutting rulesets
                  </Button>
                </CardHeader>
              </Card>
            </>
          )}
        </main>
      </div>
    </div>
  )
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

function CuttingRulesetsPage({ authToken, companyId }: { authToken: string; companyId: string }) {
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

function CutlistTesterPage({ authToken }: { authToken: string }) {
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
        return resolvedCurrentUnitType === resolvedSelectedUnitType ? current : selected
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
      }
    })
  }

  async function handleGeneratePreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPreviewError(null)
    setIsGenerating(true)
    try {
      const response = await apiRequest<CutlistPreviewResponse>('/api/v1/cutlists/preview', {
        body: buildCutlistPreviewPayload(draft, activeParameterDefinitions, slides),
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
              Thickness (mm)
              <Input
                min={1}
                onChange={(event) => updateDraftField('thickness', event.target.value)}
                type="number"
                value={draft.thickness}
              />
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

        {slidesError ? <Alert variant="destructive">{slidesError}</Alert> : null}
        {previewError ? <Alert variant="destructive">{previewError}</Alert> : null}

        {preview ? (
          <div className="grid gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={runtimeModeBadgeVariant(preview.runtime_mode)}>Runtime: {preview.runtime_mode}</Badge>
              <Badge variant="outline">Units: {preview.unit_sources.length}</Badge>
              <Badge variant="outline">
                Sources: {Array.from(new Set(preview.unit_sources.map((row) => row.source))).join(', ') || 'n/a'}
              </Badge>
            </div>

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
    height: String(config?.default_height ?? 780),
    width: String(config?.default_width ?? 600),
    depth: String(config?.default_depth ?? 560),
    thickness: '16',
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
  slides: SlideLibraryRow[],
) {
  const extraParams: Record<string, number | boolean> = {}
  const resolvedUnitType = draft.useCustomUnitType ? (draft.customUnitType.trim() || 'Custom Unit') : draft.unitType

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
        thickness: parsePositiveInteger(draft.thickness, 16),
        extra_params: extraParams,
      },
    ],
  }
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
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean }>
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

function FeatureLine({
  icon: Icon,
  label,
}: {
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean }>
  label: string
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="h-4 w-4 text-accent" aria-hidden={true} />
      {label}
    </div>
  )
}

function Field({
  label,
  onChange,
  type = 'text',
  value,
  ...props
}: {
  label: string
  onChange: (value: string) => void
  type?: string
  value: string
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'type' | 'value'>) {
  return (
    <Label className="grid gap-1.5">
      {label}
      <Input
        onChange={(event) => onChange(event.target.value)}
        type={type}
        value={value}
        {...props}
      />
    </Label>
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
    <div className="flex items-center justify-between border-b border-border pb-2 text-sm last:border-b-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

function getStoredAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

async function apiRequest<T = unknown>(
  path: string,
  options: {
    body?: unknown
    method?: 'GET' | 'POST' | 'PATCH'
    token?: string
  } = {},
): Promise<T> {
  const headers = new Headers()
  headers.set('Accept', 'application/json')

  if (options.body) {
    headers.set('Content-Type', 'application/json')
  }

  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: options.body ? JSON.stringify(options.body) : undefined,
    headers,
    method: options.method ?? 'GET',
  })

  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

async function getApiErrorMessage(response: Response) {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg ?? String(item)).join(', ')
  } catch {
    return `Request failed with status ${response.status}`
  }

  return `Request failed with status ${response.status}`
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
