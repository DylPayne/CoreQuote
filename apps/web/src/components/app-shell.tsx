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
  type LucideIcon,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { AppPage } from '@/types/app'
import type { AuthUser } from '@/types/auth'

type NavItem = {
  description: string
  icon: LucideIcon
  label: string
  page: AppPage
}

type NavGroup = {
  description: string
  items: NavItem[]
  label: string
}

const navigationGroups: NavGroup[] = [
  {
    description: 'Open projects, build quotes, check prices, and create outputs.',
    items: [
      {
        description: 'Projects, quotes, units, checks, pricing, outputs, and production handoff.',
        icon: ClipboardList,
        label: 'Projects and quotes',
        page: 'projects',
      },
    ],
    label: 'Daily work',
  },
  {
    description: 'Set up the materials, hardware, suppliers, and prices used in quotes.',
    items: [
      {
        description: 'Boards, hardware, suppliers, extras, pricing setup, and imports.',
        icon: Building2,
        label: 'Setup libraries',
        page: 'libraries',
      },
    ],
    label: 'Setup',
  },
  {
    description: 'Power-user tools for custom cutting rules.',
    items: [
      {
        description: 'Advanced setup for how cabinet units become cutting rows.',
        icon: Calculator,
        label: 'Cutlist rules',
        page: 'cutlist',
      },
      {
        description: 'Test cutting-rule changes before using them on a quote.',
        icon: CopyPlus,
        label: 'Rule tester',
        page: 'cutlist-tester',
      },
    ],
    label: 'Advanced',
  },
]

const pageDetails: Record<AppPage, { description: string; title: string }> = {
  'cutlist': {
    description: 'Advanced setup for custom cutting rules. Most quotes do not need this page.',
    title: 'Advanced cutlist rules',
  },
  'cutlist-tester': {
    description: 'Test advanced cutting-rule changes before using them on real quotes.',
    title: 'Advanced rule tester',
  },
  'libraries': {
    description: 'Set up boards, hardware, suppliers, prices, imports, and quote defaults.',
    title: 'Setup libraries',
  },
  'projects': {
    description: 'Find jobs, build quotes, check readiness, review pricing, and create outputs.',
    title: 'Projects and quotes',
  },
  'settings': {
    description: 'Workspace details and appearance controls.',
    title: 'Settings',
  },
}

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
  const pageDetail = pageDetails[currentPage] ?? pageDetails.projects

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

        <nav className="flex-1 space-y-4 px-2 py-3" aria-label="Main navigation">
          {navigationGroups.map((group) => (
            <section className="space-y-1" key={group.label} aria-labelledby={`desktop-nav-${group.label.toLowerCase().replaceAll(' ', '-')}`}>
              {!isSidebarCollapsed ? (
                <div className="px-3">
                  <h2 className="text-xs font-semibold uppercase tracking-normal text-muted-foreground" id={`desktop-nav-${group.label.toLowerCase().replaceAll(' ', '-')}`}>
                    {group.label}
                  </h2>
                  <p className="mt-0.5 text-xs leading-4 text-muted-foreground">{group.description}</p>
                </div>
              ) : (
                <h2 className="sr-only" id={`desktop-nav-${group.label.toLowerCase().replaceAll(' ', '-')}`}>{group.label}</h2>
              )}
              <div className="space-y-1">
                {group.items.map((item) => (
                  <Button
                    aria-label={isSidebarCollapsed ? `${group.label}: ${item.label}` : undefined}
                    aria-pressed={item.page === currentPage}
                    className={isSidebarCollapsed ? 'h-10 justify-center px-0' : 'h-auto items-start px-3 py-2 text-left'}
                    key={item.page}
                    onClick={() => setCurrentPage(item.page)}
                    title={isSidebarCollapsed ? `${group.label}: ${item.label}` : item.description}
                    type="button"
                    variant={item.page === currentPage ? 'navActive' : 'nav'}
                  >
                    <item.icon className="mt-0.5 h-4 w-4" aria-hidden="true" />
                    {isSidebarCollapsed ? (
                      <span className="sr-only">{item.label}</span>
                    ) : (
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-foreground">{item.label}</span>
                        <span className="mt-0.5 block whitespace-normal text-xs font-normal leading-4 text-muted-foreground">{item.description}</span>
                      </span>
                    )}
                  </Button>
                ))}
              </div>
            </section>
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
            <h1 className="text-lg font-semibold">{pageDetail.title}</h1>
            <p className="hidden text-sm text-muted-foreground sm:block">{pageDetail.description}</p>
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

        <nav className="grid gap-2 border-b border-border bg-background px-4 py-2 lg:hidden" aria-label="Main navigation">
          {navigationGroups.map((group) => (
            <section className="grid gap-1" key={group.label} aria-labelledby={`mobile-nav-${group.label.toLowerCase().replaceAll(' ', '-')}`}>
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-xs font-semibold uppercase tracking-normal text-muted-foreground" id={`mobile-nav-${group.label.toLowerCase().replaceAll(' ', '-')}`}>
                  {group.label}
                </h2>
                {group.label === 'Advanced' ? <Badge variant="outline">Power users</Badge> : null}
              </div>
              <div className={`grid gap-2 ${group.items.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                {group.items.map((item) => (
                  <Button
                    aria-pressed={item.page === currentPage}
                    className="h-10 justify-start gap-2 px-2 text-xs"
                    key={item.page}
                    onClick={() => setCurrentPage(item.page)}
                    size="sm"
                    title={item.description}
                    type="button"
                    variant={item.page === currentPage ? 'navActive' : 'nav'}
                  >
                    <item.icon className="h-4 w-4" aria-hidden="true" />
                    <span className="truncate">{item.label}</span>
                  </Button>
                ))}
              </div>
            </section>
          ))}
        </nav>

        <main className="mx-auto grid w-full min-w-0 max-w-[1920px] gap-[var(--section-gap)] overflow-x-hidden p-4 md:p-5">
          {children}
        </main>
      </div>
    </div>
  )
}
