import * as React from 'react'

import { cn } from '@/lib/utils'

function Card({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn('rounded-[var(--card-radius)] border border-border bg-card text-card-foreground shadow-[var(--shadow-card)]', className)}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('space-y-1 p-[var(--card-padding)]', className)} {...props} />
}

function CardTitle({ className, ...props }: React.ComponentProps<'h2'>) {
  return <h2 className={cn('text-base font-semibold leading-none', className)} {...props} />
}

function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('p-[var(--card-padding)] pt-0', className)} {...props} />
}

export { Card, CardContent, CardHeader, CardTitle }
