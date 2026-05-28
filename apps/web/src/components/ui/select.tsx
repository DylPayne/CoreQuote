import * as React from 'react'
import { ChevronDown } from 'lucide-react'

import { cn } from '@/lib/utils'

function Select({ className, ...props }: React.ComponentProps<'select'>) {
  return (
    <span className="relative block min-w-0">
      <select
        className={cn(
          'h-[var(--control-height)] w-full min-w-0 appearance-none rounded-[var(--control-radius)] border border-input bg-card px-[var(--control-padding-x)] pr-9 text-sm text-card-foreground shadow-[var(--shadow-card)] outline-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        {...props}
      />
      <ChevronDown
        className="pointer-events-none absolute right-[var(--control-padding-x)] top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
    </span>
  )
}

export { Select }
