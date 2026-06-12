import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from 'react'

import { AppShell } from '@/components/app-shell'
import { AppTheme } from '@/components/app-theme'
import { AuthScreen } from '@/components/auth-screen'
import { CuttingRulesetsPage, CutlistTesterPage } from '@/components/cutlist-pages'
import { LibrariesPage } from '@/components/libraries-page'
import { LoadingScreen } from '@/components/loading-screen'
import { ProjectsQuotesPage } from '@/components/projects-quotes-page'
import { SettingsPage } from '@/components/settings-page'
import { apiRequest, AUTH_TOKEN_KEY, getStoredAuthToken } from '@/lib/api'
import { colourThemes, createThemeVars, uiStyles } from '@/lib/theme'
import type { LibraryTab } from '@/components/libraries/types'
import type { AppPage } from '@/types/app'
import type { AuthFormState, AuthMode, AuthStatus, AuthTokenResponse, AuthUser } from '@/types/auth'
import type { ColourTheme, ThemeMode, UiStyle } from '@/types/theme'

const initialAuthForm: AuthFormState = {
  companyName: '',
  email: '',
  name: '',
  password: '',
}

function App() {
  const [authMode, setAuthMode] = useState<AuthMode>('login')
  const [authForm, setAuthForm] = useState<AuthFormState>(initialAuthForm)
  const [authToken, setAuthToken] = useState<string | null>(getStoredAuthToken)
  const [authStatus, setAuthStatus] = useState<AuthStatus>(() => (getStoredAuthToken() ? 'checking' : 'signed-out'))
  const [authError, setAuthError] = useState<string | null>(null)
  const [colourTheme, setColourTheme] = useState<ColourTheme>('neutral')
  const [currentPage, setCurrentPage] = useState<AppPage>('projects')
  const [libraryInitialTab, setLibraryInitialTab] = useState<LibraryTab>('pricing')
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
      <AppShell
        currentPage={currentPage}
        isLoggingOut={isLoggingOut}
        onLogout={handleLogout}
        setCurrentPage={setCurrentPage}
        user={user}
      >
        {currentPage === 'settings' ? (
          <SettingsPage
            authToken={authToken}
            colourTheme={colourTheme}
            onUserChange={(nextUser) => setUser(nextUser)}
            selectedStyle={selectedStyle}
            setColourTheme={setColourTheme}
            setThemeMode={setThemeMode}
            setUiStyle={setUiStyle}
            themeMode={themeMode}
            uiStyle={uiStyle}
            user={user}
          />
        ) : currentPage === 'projects' ? (
          <ProjectsQuotesPage
            authToken={authToken}
            currencyCode={user.company_currency_code}
            onOpenLibraries={(target = 'pricing') => {
              setLibraryInitialTab(target)
              setCurrentPage('libraries')
            }}
          />
        ) : currentPage === 'libraries' ? (
          <LibrariesPage
            authToken={authToken}
            currencyCode={user.company_currency_code}
            initialTab={libraryInitialTab}
            onOpenProjects={() => setCurrentPage('projects')}
          />
        ) : currentPage === 'cutlist' ? (
          <CuttingRulesetsPage authToken={authToken} companyId={user.company_id} />
        ) : currentPage === 'cutlist-tester' ? (
          <CutlistTesterPage authToken={authToken} />
        ) : null}
      </AppShell>
    </AppTheme>
  )
}

export default App
