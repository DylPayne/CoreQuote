import {
  Building2,
  Calculator,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  CopyPlus,
  HardHat,
  LoaderCircle,
  LogOut,
  Settings,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { AppPage } from '@/types/app'
import type { AuthUser } from '@/types/auth'

export function AppShell({
  children,
  currentPage,
  isLoggingOut,
  onLogout,
  setCurrentPage,
  user,
}: {
  children: ReactNode
  currentPage: AppPage
  isLoggingOut: boolean
  onLogout: () => void
  setCurrentPage: (page: AppPage) => void
  user: AuthUser
}) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const navItems = [
    { label: 'Projects', icon: ClipboardList, page: 'projects' as const },
    { label: 'Libraries', icon: Building2, page: 'libraries' as const },
    { label: 'Cutlist Rules', icon: Calculator, page: 'cutlist' as const },
    { label: 'Rule Tester', icon: CopyPlus, page: 'cutlist-tester' as const },
  ]
  const pageTitle =
    currentPage === 'settings'
      ? 'Settings'
      : currentPage === 'projects'
        ? 'Projects'
      : currentPage === 'libraries'
        ? 'Libraries'
      : currentPage === 'cutlist'
        ? 'Advanced Cutlist Rules'
        : currentPage === 'cutlist-tester'
          ? 'Advanced Rule Tester'
          : 'Projects'
  const pageDescription =
    currentPage === 'settings'
      ? 'Workspace details and appearance controls'
      : currentPage === 'projects'
        ? 'Projects, quotes, and unit layouts'
      : currentPage === 'libraries'
        ? 'Manage catalog libraries and pricing'
      : currentPage === 'cutlist'
        ? 'Power-user setup for how units become cutting rows'
        : currentPage === 'cutlist-tester'
          ? 'Test cutting-rule changes before using them on quotes'
          : user.company_name

  return (
    <div className="min-h-screen">
      <aside
        className={`fixed inset-y-0 left-0 hidden border-r border-border bg-sidebar transition-[width] duration-200 lg:flex lg:flex-col ${isSidebarCollapsed ? 'w-16' : 'w-64'}`}
      >
        <div className={`flex h-14 items-center border-b border-border ${isSidebarCollapsed ? 'justify-center px-2' : 'justify-between gap-3 px-3'}`}>
          {!isSidebarCollapsed ? (
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <HardHat className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">CoreQuote</p>
                <p className="truncate text-xs text-muted-foreground">{user.company_name}</p>
              </div>
            </div>
          ) : null}
          <Button
            aria-label={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={() => setIsSidebarCollapsed((current) => !current)}
            size="icon"
            title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            type="button"
            variant="ghost"
          >
            {isSidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
          {isSidebarCollapsed ? (
            <span className="sr-only">{user.company_name}</span>
          ) : null}
        </div>

        <nav className="flex-1 space-y-1 px-2 py-3">
          {navItems.map((item) => (
            <Button
              aria-label={isSidebarCollapsed ? item.label : undefined}
              aria-pressed={item.page === currentPage}
              className={isSidebarCollapsed ? 'h-10 justify-center px-0' : 'h-9 px-3'}
              key={item.page}
              onClick={() => setCurrentPage(item.page)}
              title={isSidebarCollapsed ? item.label : undefined}
              type="button"
              variant={item.page === currentPage ? 'navActive' : 'nav'}
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              {isSidebarCollapsed ? <span className="sr-only">{item.label}</span> : item.label}
            </Button>
          ))}
        </nav>

        <div className="border-t border-border p-3">
          <Button
            aria-current={currentPage === 'settings' ? 'page' : undefined}
            aria-label="Open settings"
            className={
              isSidebarCollapsed
                ? 'h-10 justify-center px-0'
                : `h-auto flex-col items-start gap-2 whitespace-normal rounded-[var(--card-radius)] border p-3 text-left hover:bg-sidebar-accent ${currentPage === 'settings' ? 'border-primary bg-sidebar-accent' : 'border-border bg-card'}`
            }
            onClick={() => setCurrentPage('settings')}
            title="Open settings"
            type="button"
            variant={currentPage === 'settings' ? 'navActive' : 'nav'}
          >
            {isSidebarCollapsed ? (
              <Settings className="h-4 w-4" aria-hidden="true" />
            ) : (
              <>
                <div className="flex w-full items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">{user.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                  </div>
                  <Settings className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                </div>
                <Badge variant="outline">{user.role}</Badge>
              </>
            )}
          </Button>
        </div>
      </aside>

      <div className={`overflow-x-hidden transition-[padding] duration-200 ${isSidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'}`}>
        <header className="sticky top-0 z-10 flex min-h-14 items-center justify-between gap-3 border-b border-border bg-background/95 px-4 py-2 backdrop-blur md:px-6">
          <div>
            <h1 className="text-lg font-semibold">{pageTitle}</h1>
            <p className="hidden text-sm text-muted-foreground sm:block">{pageDescription}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              aria-label="Open settings"
              className="lg:hidden"
              onClick={() => setCurrentPage('settings')}
              size="icon"
              title="Open settings"
              type="button"
              variant={currentPage === 'settings' ? 'secondary' : 'outline'}
            >
              <Settings className="h-4 w-4" aria-hidden="true" />
            </Button>
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

        <main className="mx-auto grid w-full min-w-0 max-w-[1920px] gap-[var(--section-gap)] overflow-x-hidden p-4 md:p-5">
          {children}
        </main>
      </div>
    </div>
  )
}
