import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex h-6 items-center rounded-md border px-2 text-xs font-medium',
  {
    defaultVariants: {
      variant: 'default',
    },
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        outline: 'border-border text-foreground',
        success:
          'border-[var(--status-success-border)] bg-[var(--status-success)] text-[var(--status-success-foreground)]',
        warning:
          'border-[var(--status-warning-border)] bg-[var(--status-warning)] text-[var(--status-warning-foreground)]',
      },
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ className, variant }))} {...props} />
}

export { Badge }
