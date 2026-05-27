import {
  Building2,
  Calculator,
  CheckCircle2,
  ClipboardList,
  HardHat,
  LoaderCircle,
  LogOut,
  Moon,
  Palette,
  Play,
  ShieldCheck,
  Sun,
  UserRound,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, type CSSProperties, type FormEvent } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChoiceCard, ChoiceCardContent } from '@/components/ui/choice-card'
import { ControlGroup, ControlGroupItem } from '@/components/ui/control-group'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')
const AUTH_TOKEN_KEY = 'corequote.authToken'

type AuthMode = 'login' | 'register'
type AuthStatus = 'checking' | 'signed-in' | 'signed-out'
type AppPage = 'workspace' | 'cutlist' | 'appearance'
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
type UnitType = 'Base Drawer' | 'Base Door' | 'Wall Door' | 'Tall Standard'

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
  role: 'owner' | 'admin' | 'member'
}

type AuthTokenResponse = {
  access_token: string
  token_type: 'bearer'
  expires_at: string
  user: AuthUser
}

type CutlistRow = {
  unit_number: number
  desc: string
  length: number
  width: number
  qty: number
}

type CutlistPreviewResponse = {
  carcass: CutlistRow[]
  panels: CutlistRow[]
}

type AuthFormState = {
  companyName: string
  name: string
  email: string
  password: string
}

type CutlistFormState = {
  unitType: UnitType
  height: number
  width: number
  depth: number
  thickness: number
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

const initialCutlistForm: CutlistFormState = {
  depth: 580,
  height: 780,
  thickness: 16,
  unitType: 'Base Drawer',
  width: 900,
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
            <div className="mb-5 grid grid-cols-2 rounded-[var(--control-radius)] border border-input bg-muted p-1">
              <button
                aria-pressed={authMode === 'login'}
                className={modeButtonClass(authMode === 'login')}
                onClick={() => onModeChange('login')}
                type="button"
              >
                Log in
              </button>
              <button
                aria-pressed={authMode === 'register'}
                className={modeButtonClass(authMode === 'register')}
                onClick={() => onModeChange('register')}
                type="button"
              >
                Register
              </button>
            </div>

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
                <div className="rounded-[var(--control-radius)] border border-destructive bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {authError}
                </div>
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
    { label: 'Appearance', icon: Palette, page: 'appearance' as const },
  ]
  const pageTitle = currentPage === 'appearance' ? 'Appearance' : currentPage === 'cutlist' ? 'Cutlist' : 'Workspace'
  const pageDescription =
    currentPage === 'appearance'
      ? 'Global style, colour, and mode controls'
      : currentPage === 'cutlist'
        ? 'Preview carcass and panel rows from the API'
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
            <button
              className={
                item.page === currentPage
                  ? 'flex h-9 w-full items-center gap-3 rounded-md bg-sidebar-accent px-3 text-left text-sm font-medium text-foreground'
                  : 'flex h-9 w-full items-center gap-3 rounded-md px-3 text-left text-sm font-medium text-muted-foreground hover:bg-sidebar-accent hover:text-foreground'
              }
              key={item.page}
              onClick={() => setCurrentPage(item.page)}
              type="button"
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="border-t border-border p-3">
          <div className="rounded-md border border-border bg-background p-3">
            <p className="truncate text-sm font-medium">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground">{user.email}</p>
            <Badge className="mt-3" variant="outline">
              {user.role}
            </Badge>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
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

        <nav className="grid grid-cols-3 gap-2 border-b border-border bg-background px-4 py-2 lg:hidden">
          {navItems.map((item) => (
            <button
              aria-pressed={item.page === currentPage}
              className={
                item.page === currentPage
                  ? 'flex h-9 items-center justify-center gap-2 rounded-[var(--control-radius)] bg-sidebar-accent px-2 text-sm font-medium text-foreground'
                  : 'flex h-9 items-center justify-center gap-2 rounded-[var(--control-radius)] px-2 text-sm font-medium text-muted-foreground hover:bg-sidebar-accent hover:text-foreground'
              }
              key={item.page}
              onClick={() => setCurrentPage(item.page)}
              type="button"
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              <span className="truncate">{item.label}</span>
            </button>
          ))}
        </nav>

        <main className="mx-auto grid max-w-7xl gap-[var(--section-gap)] p-4 md:p-5">
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
            <CutlistPreview authToken={authToken} />
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
                    Open cutlist preview
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

function CutlistPreview({ authToken }: { authToken: string }) {
  const [form, setForm] = useState<CutlistFormState>(initialCutlistForm)
  const [preview, setPreview] = useState<CutlistPreviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const totalPieces = useMemo(() => {
    if (!preview) return 0
    return [...preview.carcass, ...preview.panels].reduce((sum, row) => sum + row.qty, 0)
  }, [preview])

  async function handlePreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      const result = await apiRequest<CutlistPreviewResponse>('/api/v1/cutlists/preview', {
        body: {
          units: [
            {
              depth: form.depth,
              height: form.height,
              thickness: form.thickness,
              unit_number: 1,
              unit_type: form.unitType,
              width: form.width,
            },
          ],
        },
        method: 'POST',
        token: authToken,
      })
      setPreview(result)
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : 'Could not generate the cutlist preview.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <CardTitle>Cutlist preview</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            A working API-backed calculator for one cabinet unit.
          </p>
        </div>
        {preview ? (
          <Badge variant="success">
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
            {totalPieces} pieces
          </Badge>
        ) : null}
      </CardHeader>
      <CardContent>
        <div className="grid gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
          <form
            className="grid content-start gap-4 rounded-[var(--card-radius)] border border-border bg-muted/40 p-[var(--card-padding)]"
            onSubmit={handlePreview}
          >
            <div>
              <p className="text-sm font-semibold">Unit inputs</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">Dimensions are in millimetres.</p>
            </div>

            <label className="grid min-w-0 gap-1.5 text-sm font-medium">
              Unit type
              <select
                className="h-[var(--control-height)] min-w-0 rounded-[var(--control-radius)] border border-input bg-background px-[var(--control-padding-x)] text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onChange={(event) => setForm((current) => ({ ...current, unitType: event.target.value as UnitType }))}
                value={form.unitType}
              >
                <option>Base Drawer</option>
                <option>Base Door</option>
                <option>Wall Door</option>
                <option>Tall Standard</option>
              </select>
            </label>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <NumberField label="Height" onChange={(height) => setForm((current) => ({ ...current, height }))} value={form.height} />
              <NumberField label="Width" onChange={(width) => setForm((current) => ({ ...current, width }))} value={form.width} />
              <NumberField label="Depth" onChange={(depth) => setForm((current) => ({ ...current, depth }))} value={form.depth} />
              <NumberField
                label="Thickness"
                onChange={(thickness) => setForm((current) => ({ ...current, thickness }))}
                value={form.thickness}
              />
            </div>

            {error ? (
              <div className="rounded-[var(--control-radius)] border border-destructive bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            <Button className="w-full" disabled={isLoading} type="submit">
              {isLoading ? (
                <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Play className="h-4 w-4" aria-hidden="true" />
              )}
              Run preview
            </Button>
          </form>

          <div className="min-w-0">
            <CutlistTable preview={preview} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function CutlistTable({ preview }: { preview: CutlistPreviewResponse | null }) {
  if (!preview) {
    return (
      <div className="flex min-h-72 items-center justify-center rounded-md border border-dashed border-border bg-muted p-6 text-center text-sm text-muted-foreground">
        Run a preview to see carcass and panel rows from the API.
      </div>
    )
  }

  const rows = [
    ...preview.carcass.map((row) => ({ ...row, section: 'Carcass' })),
    ...preview.panels.map((row) => ({ ...row, section: 'Panels' })),
  ]

  return (
    <div className="min-w-0 overflow-x-auto rounded-md border border-border">
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">
        <thead className="bg-muted text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">Section</th>
            <th className="px-4 py-3 font-medium">Description</th>
            <th className="px-4 py-3 font-medium">Length</th>
            <th className="px-4 py-3 font-medium">Width</th>
            <th className="px-4 py-3 font-medium">Qty</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr className="border-t border-border" key={`${row.section}-${row.desc}-${index}`}>
              <td className="px-4 py-3 text-muted-foreground">{row.section}</td>
              <td className="px-4 py-3 font-medium">{row.desc}</td>
              <td className="px-4 py-3">{row.length}</td>
              <td className="px-4 py-3">{row.width}</td>
              <td className="px-4 py-3">{row.qty}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
    <label className="grid gap-1.5 text-sm font-medium">
      {label}
      <input
        className="h-[var(--control-height)] rounded-[var(--control-radius)] border border-input bg-background px-[var(--control-padding-x)] text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        onChange={(event) => onChange(event.target.value)}
        type={type}
        value={value}
        {...props}
      />
    </label>
  )
}

function NumberField({ label, onChange, value }: { label: string; onChange: (value: number) => void; value: number }) {
  return (
    <label className="grid min-w-0 gap-1.5 text-sm font-medium">
      {label}
      <input
        className="h-[var(--control-height)] min-w-0 rounded-[var(--control-radius)] border border-input bg-background px-[var(--control-padding-x)] text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        min={1}
        onChange={(event) => onChange(Number(event.target.value))}
        required
        type="number"
        value={value}
      />
    </label>
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

function modeButtonClass(isActive: boolean) {
  return [
    'h-8 rounded-[var(--control-radius)] text-sm font-medium transition-colors',
    isActive ? 'bg-background text-foreground shadow-[var(--shadow-card)]' : 'text-muted-foreground hover:text-foreground',
  ].join(' ')
}

function getStoredAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

async function apiRequest<T = unknown>(
  path: string,
  options: {
    body?: unknown
    method?: 'GET' | 'POST'
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
