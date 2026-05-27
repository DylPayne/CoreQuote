import * as React from 'react'

import { cn } from '@/lib/utils'

function ControlGroup({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'inline-flex h-[var(--control-height)] items-center gap-1 overflow-hidden rounded-[var(--control-radius)] border border-input bg-background p-0.5',
        className,
      )}
      {...props}
    />
  )
}

function ControlGroupItem({ className, ...props }: React.ComponentProps<'button'>) {
  return (
    <button
      className={cn(
        'inline-flex h-full min-w-[calc(var(--control-height)-0.25rem)] items-center justify-center gap-2 rounded-[calc(var(--control-radius)-0.125rem)] px-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground aria-pressed:bg-primary aria-pressed:text-primary-foreground',
        className,
      )}
      type="button"
      {...props}
    />
  )
}

export { ControlGroup, ControlGroupItem }
