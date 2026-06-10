import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const alertVariants = cva('rounded-[var(--control-radius)] border px-3 py-2 text-sm', {
  defaultVariants: {
    variant: 'default',
  },
  variants: {
    variant: {
      default: 'border-border bg-muted text-foreground',
      destructive: 'border-destructive bg-destructive/10 text-destructive',
      warning:
        'border-[var(--status-warning-border)] bg-[var(--status-warning)] text-[var(--status-warning-foreground)]',
    },
  },
})

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {}

function Alert({ className, variant, ...props }: AlertProps) {
  return <div className={cn(alertVariants({ className, variant }))} {...props} />
}

export { Alert }
