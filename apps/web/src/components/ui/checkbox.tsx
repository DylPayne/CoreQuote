import * as React from 'react'

import { cn } from '@/lib/utils'

function Checkbox({ className, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      className={cn(
        'h-4 w-4 shrink-0 rounded-[calc(var(--control-radius)-2px)] border border-input bg-card accent-primary outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      type="checkbox"
      {...props}
    />
  )
}

export { Checkbox }
