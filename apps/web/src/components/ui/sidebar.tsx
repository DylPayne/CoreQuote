import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'

import { cn } from '@/lib/utils'

type SidebarContextValue = {
  open: boolean
  setOpen: (open: boolean) => void
  state: 'expanded' | 'collapsed'
  toggleSidebar: () => void
}

const SidebarContext = React.createContext<SidebarContextValue | null>(null)

function useSidebar() {
  const context = React.useContext(SidebarContext)
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider.')
  }
  return context
}

function SidebarProvider({
  children,
  defaultOpen = true,
  onOpenChange,
  open: controlledOpen,
}: React.PropsWithChildren<{
  defaultOpen?: boolean
  onOpenChange?: (open: boolean) => void
  open?: boolean
}>) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen)
  const open = controlledOpen ?? uncontrolledOpen
  const setOpen = React.useCallback(
    (nextOpen: boolean) => {
      if (controlledOpen === undefined) {
        setUncontrolledOpen(nextOpen)
      }
      onOpenChange?.(nextOpen)
    },
    [controlledOpen, onOpenChange],
  )
  const value = React.useMemo<SidebarContextValue>(
    () => ({
      open,
      setOpen,
      state: open ? 'expanded' : 'collapsed',
      toggleSidebar: () => setOpen(!open),
    }),
    [open, setOpen],
  )

  return <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>
}

function Sidebar({ className, ...props }: React.ComponentProps<'aside'>) {
  const { state } = useSidebar()

  return (
    <aside
      className={cn(
        'group/sidebar fixed inset-y-0 left-0 hidden border-r border-border bg-sidebar text-foreground transition-[width] duration-200 lg:flex lg:flex-col',
        state === 'collapsed' ? 'w-16' : 'w-64',
        className,
      )}
      data-state={state}
      {...props}
    />
  )
}

function SidebarInset({ className, ...props }: React.ComponentProps<'div'>) {
  const { state } = useSidebar()

  return (
    <div
      className={cn('overflow-x-hidden transition-[padding] duration-200', state === 'collapsed' ? 'lg:pl-16' : 'lg:pl-64', className)}
      {...props}
    />
  )
}

function SidebarHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('flex h-14 shrink-0 items-center border-b border-border', className)} {...props} />
}

function SidebarContent({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-2 py-3', className)} {...props} />
}

function SidebarFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('shrink-0 border-t border-border p-3', className)} {...props} />
}

function SidebarGroup({ className, ...props }: React.ComponentProps<'section'>) {
  return <section className={cn('grid gap-1', className)} {...props} />
}

function SidebarGroupLabel({ className, ...props }: React.ComponentProps<'h2'>) {
  return <h2 className={cn('px-3 text-xs font-semibold uppercase tracking-normal text-muted-foreground', className)} {...props} />
}

function SidebarGroupContent({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('grid gap-1', className)} {...props} />
}

function SidebarMenu({ className, ...props }: React.ComponentProps<'ul'>) {
  return <ul className={cn('grid gap-1', className)} {...props} />
}

function SidebarMenuItem({ className, ...props }: React.ComponentProps<'li'>) {
  return <li className={cn('grid gap-1', className)} {...props} />
}

function SidebarMenuButton({
  asChild = false,
  className,
  isActive,
  ...props
}: React.ComponentProps<'button'> & {
  asChild?: boolean
  isActive?: boolean
}) {
  const Comp = asChild ? Slot : 'button'

  return (
    <Comp
      className={cn(
        'inline-flex h-9 w-full items-center gap-2 rounded-[var(--control-radius)] px-3 text-left text-sm font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 data-[active=true]:bg-sidebar-accent data-[active=true]:text-foreground group-data-[state=collapsed]/sidebar:justify-center group-data-[state=collapsed]/sidebar:px-0 [&_svg]:h-4 [&_svg]:w-4 [&_svg]:shrink-0',
        className,
      )}
      data-active={isActive ? 'true' : 'false'}
      type={asChild ? undefined : 'button'}
      {...props}
    />
  )
}

function SidebarMenuSub({ className, ...props }: React.ComponentProps<'ul'>) {
  return (
    <ul
      className={cn(
        'ml-5 grid gap-0.5 border-l border-border pl-2 group-data-[state=collapsed]/sidebar:hidden',
        className,
      )}
      {...props}
    />
  )
}

function SidebarMenuSubItem({ className, ...props }: React.ComponentProps<'li'>) {
  return <li className={cn('grid', className)} {...props} />
}

function SidebarMenuSubButton({
  asChild = false,
  className,
  isActive,
  ...props
}: React.ComponentProps<'button'> & {
  asChild?: boolean
  isActive?: boolean
}) {
  const Comp = asChild ? Slot : 'button'

  return (
    <Comp
      className={cn(
        'inline-flex h-8 w-full items-center gap-2 rounded-[var(--control-radius)] px-2 text-left text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[active=true]:bg-sidebar-accent data-[active=true]:font-medium data-[active=true]:text-foreground',
        className,
      )}
      data-active={isActive ? 'true' : 'false'}
      type={asChild ? undefined : 'button'}
      {...props}
    />
  )
}

function SidebarTrigger({ className, onClick, ...props }: React.ComponentProps<'button'>) {
  const { toggleSidebar } = useSidebar()

  return (
    <button
      className={cn(
        'inline-flex h-[var(--control-height)] w-[var(--control-height)] items-center justify-center rounded-[var(--control-radius)] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className,
      )}
      onClick={(event) => {
        onClick?.(event)
        if (!event.defaultPrevented) {
          toggleSidebar()
        }
      }}
      type="button"
      {...props}
    />
  )
}

export {
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
}
