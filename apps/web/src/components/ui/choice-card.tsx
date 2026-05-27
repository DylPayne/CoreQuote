import * as React from 'react'

import { cn } from '@/lib/utils'

function ChoiceCard({ className, ...props }: React.ComponentProps<'button'>) {
  return (
    <button
      className={cn(
        'overflow-hidden rounded-[var(--card-radius)] border border-border bg-card text-left text-card-foreground shadow-[var(--shadow-card)] transition-colors hover:border-primary hover:bg-muted aria-pressed:border-primary aria-pressed:bg-muted',
        className,
      )}
      type="button"
      {...props}
    />
  )
}

function ChoiceCardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('flex min-h-36 flex-col justify-between p-[var(--card-padding)]', className)} {...props} />
}

export { ChoiceCard, ChoiceCardContent }
