import * as React from 'react'

import { cn } from '@/lib/utils'

function TableContainer({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'min-w-0 max-w-full overflow-x-auto overscroll-x-contain rounded-[var(--card-radius)] border border-border bg-card text-card-foreground shadow-[var(--shadow-card)]',
        '[contain:layout_paint]',
        className,
      )}
      {...props}
    />
  )
}

function Table({ className, ...props }: React.ComponentProps<'table'>) {
  return <table className={cn('w-full min-w-[640px] border-collapse text-left text-sm', className)} {...props} />
}

function TableHeader({ className, ...props }: React.ComponentProps<'thead'>) {
  return <thead className={cn('bg-secondary text-xs uppercase text-secondary-foreground', className)} {...props} />
}

function TableBody({ className, ...props }: React.ComponentProps<'tbody'>) {
  return <tbody className={className} {...props} />
}

function TableRow({ className, ...props }: React.ComponentProps<'tr'>) {
  return <tr className={cn('border-b border-border transition-colors last:border-b-0 hover:bg-muted/60', className)} {...props} />
}

function TableHead({ className, ...props }: React.ComponentProps<'th'>) {
  return <th className={cn('h-10 px-4 py-3 font-medium', className)} {...props} />
}

function TableCell({ className, ...props }: React.ComponentProps<'td'>) {
  return <td className={cn('px-4 py-3 align-middle', className)} {...props} />
}

export { Table, TableBody, TableCell, TableContainer, TableHead, TableHeader, TableRow }
