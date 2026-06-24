import {
  Building2,
  Calculator,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  HardHat,
  LoaderCircle,
  LogOut,
  Settings,
  type LucideIcon,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { libraryTabs } from '@/components/libraries/constants'
import type { LibraryTab } from '@/components/libraries/types'
import type { AppPage } from '@/types/app'
import type { AuthUser } from '@/types/auth'

type NavigationItem = {
  label: string
  libraryTab?: LibraryTab
  page: AppPage
}

type NavigationGroup = {
  groupLabel: string
  icon: LucideIcon
  items: NavigationItem[]
  label: string
  page: AppPage
}

const setupLibraryItems: NavigationItem[] = libraryTabs.map((tab) => ({
  label: tab.label,
  libraryTab: tab.value,
  page: 'libraries',
}))

const navigationGroups: NavigationGroup[] = [
  {
    groupLabel: 'Daily work',
    icon: ClipboardList,
    items: [],
    label: 'Projects and quotes',
    page: 'projects',
  },
  {
    groupLabel: 'Setup',
    icon: Building2,
    items: setupLibraryItems,
    label: 'Setup libraries',
    page: 'libraries',
  },
  {
    groupLabel: 'Advanced',
    icon: Calculator,
    items: [
      {
        label: 'Cutlist rules',
        page: 'cutlist',
      },
      {
        label: 'Rule tester',
        page: 'cutlist-tester',
      },
    ],
    label: 'Advanced tools',
    page: 'cutlist',
  },
]

const pageTitles: Record<AppPage, string> = {
  'cutlist': 'Cutlist rules',
  'cutlist-tester': 'Rule tester',
  'libraries': 'Setup libraries',
  'projects': 'Projects and quotes',
  'settings': 'Settings',
}

function libraryTabLabel(tab: LibraryTab) {
  return libraryTabs.find((item) => item.value === tab)?.label ?? 'Setup & Imports'
}

function pageTitle(currentPage: AppPage, currentLibraryTab: LibraryTab) {
  if (currentPage === 'libraries') return libraryTabLabel(currentLibraryTab)
  return pageTitles[currentPage] ?? pageTitles.projects
}

function navItemIsActive(item: NavigationItem, currentPage: AppPage, currentLibraryTab: LibraryTab) {
  if (item.page !== currentPage) return false
  if (item.libraryTab) return item.libraryTab === currentLibraryTab
  return true
}

function navGroupIsActive(group: NavigationGroup, currentPage: AppPage) {
  if (group.page === 'cutlist') return currentPage === 'cutlist' || currentPage === 'cutlist-tester'
  return currentPage === group.page
}

export function AppShell({
  children,
  currentLibraryTab,
  currentPage,
  isLoggingOut,
  onLibraryTabChange,
  onLogout,
  setCurrentPage,
  user,
}: {
  children: ReactNode
  currentLibraryTab: LibraryTab
  currentPage: AppPage
  isLoggingOut: boolean
  onLibraryTabChange: (tab: LibraryTab) => void
  onLogout: () => void
  setCurrentPage: (page: AppPage) => void
  user: AuthUser
}) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [expandedMenuGroups, setExpandedMenuGroups] = useState<Record<string, boolean>>({})
  const title = pageTitle(currentPage, currentLibraryTab)

  function openNavigationItem(item: NavigationItem) {
    if (item.libraryTab) {
      onLibraryTabChange(item.libraryTab)
    }
    setCurrentPage(item.page)
  }

  function openNavigationGroup(group: NavigationGroup) {
    if (group.page === 'libraries') {
      onLibraryTabChange('setup-imports')
    }
    setCurrentPage(group.page)
  }

  function toggleNavigationGroup(group: NavigationGroup, isGroupActive: boolean) {
    if (group.items.length < 1) {
      openNavigationGroup(group)
      return
    }

    if (!isGroupActive) {
      openNavigationGroup(group)
      setExpandedMenuGroups((current) => ({ ...current, [group.label]: true }))
      return
    }

    setExpandedMenuGroups((current) => ({ ...current, [group.label]: !current[group.label] }))
  }

  return (
    <SidebarProvider open={!isSidebarCollapsed} onOpenChange={(open) => setIsSidebarCollapsed(!open)}>
      <div className="min-h-screen">
        <Sidebar aria-label="Main navigation">
          <SidebarHeader className={isSidebarCollapsed ? 'justify-center px-2' : 'justify-between gap-3 px-3'}>
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
            <SidebarTrigger
              aria-label={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isSidebarCollapsed ? (
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
              ) : (
                <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              )}
            </SidebarTrigger>
            {isSidebarCollapsed ? <span className="sr-only">{user.company_name}</span> : null}
          </SidebarHeader>

          <SidebarContent>
            {navigationGroups.map((group) => {
              const GroupIcon = group.icon
              const isGroupActive = navGroupIsActive(group, currentPage)
              const hasSubmenu = group.items.length > 1
              const isGroupExpanded = hasSubmenu && (expandedMenuGroups[group.label] ?? isGroupActive)

              return (
                <SidebarGroup key={group.label}>
                  <SidebarGroupLabel className={isSidebarCollapsed ? 'sr-only' : undefined}>{group.groupLabel}</SidebarGroupLabel>
                  <SidebarGroupContent>
                    <SidebarMenu>
                      <SidebarMenuItem>
                        <SidebarMenuButton
                          aria-label={isSidebarCollapsed ? group.label : undefined}
                          aria-expanded={hasSubmenu && !isSidebarCollapsed ? isGroupExpanded : undefined}
                          isActive={isGroupActive}
                          onClick={() => toggleNavigationGroup(group, isGroupActive)}
                          title={group.label}
                        >
                          <GroupIcon aria-hidden="true" />
                          {isSidebarCollapsed ? <span className="sr-only">{group.label}</span> : <span className="truncate">{group.label}</span>}
                          {!isSidebarCollapsed && hasSubmenu ? (
                            <ChevronDown
                              className={`ml-auto h-4 w-4 transition-transform ${isGroupExpanded ? 'rotate-180' : ''}`}
                              aria-hidden="true"
                            />
                          ) : null}
                        </SidebarMenuButton>
                        {!isSidebarCollapsed && isGroupExpanded ? (
                          <SidebarMenuSub aria-label={`${group.label} sections`}>
                            {group.items.map((item) => {
                              return (
                                <SidebarMenuSubItem key={`${item.page}-${item.libraryTab ?? item.label}`}>
                                  <SidebarMenuSubButton
                                    isActive={navItemIsActive(item, currentPage, currentLibraryTab)}
                                    onClick={() => openNavigationItem(item)}
                                  >
                                    <span className="truncate">{item.label}</span>
                                  </SidebarMenuSubButton>
                                </SidebarMenuSubItem>
                              )
                            })}
                          </SidebarMenuSub>
                        ) : null}
                      </SidebarMenuItem>
                    </SidebarMenu>
                  </SidebarGroupContent>
                </SidebarGroup>
              )
            })}
          </SidebarContent>

          <SidebarFooter>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  aria-current={currentPage === 'settings' ? 'page' : undefined}
                  aria-label="Open settings"
                  className={isSidebarCollapsed ? 'h-10 justify-center px-0' : 'h-auto items-start py-2'}
                  isActive={currentPage === 'settings'}
                  onClick={() => setCurrentPage('settings')}
                  title="Open settings"
                >
                  <Settings className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  {isSidebarCollapsed ? (
                    <span className="sr-only">Settings</span>
                  ) : (
                    <span className="grid min-w-0 gap-1">
                      <span className="truncate text-sm font-medium">{user.name}</span>
                      <span className="truncate text-xs font-normal text-muted-foreground">{user.email}</span>
                      <Badge className="w-fit" variant="outline">{user.role}</Badge>
                    </span>
                  )}
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarFooter>
        </Sidebar>

        <SidebarInset>
          <header className="sticky top-0 z-10 flex min-h-12 items-center justify-between gap-3 border-b border-border bg-background/95 px-4 py-2 backdrop-blur md:px-5">
            <h1 className="truncate text-lg font-semibold">{title}</h1>
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

          <MobileNavigation
            currentLibraryTab={currentLibraryTab}
            currentPage={currentPage}
            onLibraryTabChange={onLibraryTabChange}
            setCurrentPage={setCurrentPage}
          />

          <main className="mx-auto grid w-full min-w-0 max-w-[1920px] gap-[var(--section-gap)] overflow-x-hidden p-4 md:p-5">
            {children}
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  )
}

function MobileNavigation({
  currentLibraryTab,
  currentPage,
  onLibraryTabChange,
  setCurrentPage,
}: {
  currentLibraryTab: LibraryTab
  currentPage: AppPage
  onLibraryTabChange: (tab: LibraryTab) => void
  setCurrentPage: (page: AppPage) => void
}) {
  const isAdvancedPage = currentPage === 'cutlist' || currentPage === 'cutlist-tester'
  const [expandedMobileGroups, setExpandedMobileGroups] = useState<Partial<Record<'advanced' | 'libraries', boolean>>>({})
  const isLibraryMenuExpanded = currentPage === 'libraries' && (expandedMobileGroups.libraries ?? true)
  const isAdvancedMenuExpanded = isAdvancedPage && (expandedMobileGroups.advanced ?? true)

  function openLibraryTab(tab: LibraryTab) {
    onLibraryTabChange(tab)
    setCurrentPage('libraries')
  }

  function toggleLibraryMenu() {
    if (currentPage !== 'libraries') {
      openLibraryTab('setup-imports')
      setExpandedMobileGroups((current) => ({ ...current, libraries: true }))
      return
    }

    setExpandedMobileGroups((current) => ({ ...current, libraries: !current.libraries }))
  }

  function openAdvancedPage(page: Extract<AppPage, 'cutlist' | 'cutlist-tester'>) {
    setCurrentPage(page)
  }

  function toggleAdvancedMenu() {
    if (!isAdvancedPage) {
      openAdvancedPage('cutlist')
      setExpandedMobileGroups((current) => ({ ...current, advanced: true }))
      return
    }

    setExpandedMobileGroups((current) => ({ ...current, advanced: !current.advanced }))
  }

  return (
    <nav className="grid gap-2 border-b border-border bg-background px-4 py-2 lg:hidden" aria-label="Main navigation">
      <div className="grid grid-cols-3 gap-2">
        <Button
          aria-pressed={currentPage === 'projects'}
          className="h-9 justify-start gap-2 px-2 text-xs"
          onClick={() => setCurrentPage('projects')}
          size="sm"
          type="button"
          variant={currentPage === 'projects' ? 'navActive' : 'nav'}
        >
          <ClipboardList className="h-4 w-4" aria-hidden="true" />
          <span className="truncate">Projects</span>
        </Button>
        <Button
          aria-pressed={currentPage === 'libraries'}
          aria-expanded={isLibraryMenuExpanded}
          className="h-9 justify-start gap-2 px-2 text-xs"
          onClick={toggleLibraryMenu}
          size="sm"
          type="button"
          variant={currentPage === 'libraries' ? 'navActive' : 'nav'}
        >
          <Building2 className="h-4 w-4" aria-hidden="true" />
          <span className="truncate">Setup</span>
          <ChevronDown className={`ml-auto h-3.5 w-3.5 transition-transform ${isLibraryMenuExpanded ? 'rotate-180' : ''}`} aria-hidden="true" />
        </Button>
        <Button
          aria-pressed={isAdvancedPage}
          aria-expanded={isAdvancedMenuExpanded}
          className="h-9 justify-start gap-2 px-2 text-xs"
          onClick={toggleAdvancedMenu}
          size="sm"
          type="button"
          variant={isAdvancedPage ? 'navActive' : 'nav'}
        >
          <Calculator className="h-4 w-4" aria-hidden="true" />
          <span className="truncate">Advanced</span>
          <ChevronDown className={`ml-auto h-3.5 w-3.5 transition-transform ${isAdvancedMenuExpanded ? 'rotate-180' : ''}`} aria-hidden="true" />
        </Button>
      </div>

      {isLibraryMenuExpanded ? (
        <div className="grid grid-cols-2 gap-1.5 border-l border-border pl-2 sm:grid-cols-3" aria-label="Setup library sections">
          {libraryTabs.map((tab) => (
            <Button
              aria-pressed={currentLibraryTab === tab.value}
              className="h-8 justify-start px-2 text-xs"
              key={tab.value}
              onClick={() => openLibraryTab(tab.value)}
              size="sm"
              type="button"
              variant={currentLibraryTab === tab.value ? 'secondary' : 'outline'}
            >
              <span className="truncate">{tab.label}</span>
            </Button>
          ))}
        </div>
      ) : null}

      {isAdvancedMenuExpanded ? (
        <div className="grid grid-cols-2 gap-1.5 border-l border-border pl-2" aria-label="Advanced tools">
          <Button
            aria-pressed={currentPage === 'cutlist'}
            className="h-8 justify-start px-2 text-xs"
            onClick={() => openAdvancedPage('cutlist')}
            size="sm"
            type="button"
            variant={currentPage === 'cutlist' ? 'secondary' : 'outline'}
          >
            <span className="truncate">Cutlist rules</span>
          </Button>
          <Button
            aria-pressed={currentPage === 'cutlist-tester'}
            className="h-8 justify-start px-2 text-xs"
            onClick={() => openAdvancedPage('cutlist-tester')}
            size="sm"
            type="button"
            variant={currentPage === 'cutlist-tester' ? 'secondary' : 'outline'}
          >
            <span className="truncate">Rule tester</span>
          </Button>
        </div>
      ) : null}
    </nav>
  )
}
