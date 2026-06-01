import * as React from 'react'

import { cn } from '@/lib/utils'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      className={cn(
        'h-[var(--control-height)] w-full min-w-0 max-w-full rounded-[var(--control-radius)] border border-input bg-card px-[var(--control-padding-x)] text-sm text-card-foreground shadow-[var(--shadow-card)] outline-none transition-colors placeholder:text-muted-foreground hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      type={type}
      {...props}
    />
  )
}

export { Input }
