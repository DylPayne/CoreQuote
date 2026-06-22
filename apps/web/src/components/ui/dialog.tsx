import * as React from 'react'
import { X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type DialogProps = {
  children: React.ReactNode
  description?: string
  onOpenChange: (open: boolean) => void
  open: boolean
  size?: 'default' | 'wide'
  title: string
}

function Dialog({ children, description, onOpenChange, open, size = 'default', title }: DialogProps) {
  const titleId = React.useId()
  const descriptionId = React.useId()

  React.useEffect(() => {
    if (!open) return

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onOpenChange(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onOpenChange, open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-background/80 p-4 backdrop-blur-sm" onMouseDown={() => onOpenChange(false)}>
      <div
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={cn(
          'max-h-[min(88vh,900px)] w-full overflow-hidden rounded-[var(--card-radius)] border border-border bg-card text-card-foreground shadow-xl',
          size === 'wide' ? 'max-w-5xl' : 'max-w-2xl',
        )}
        onMouseDown={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="flex items-start justify-between gap-4 border-b border-border p-[var(--card-padding)]">
          <div className="grid gap-1">
            <h2 id={titleId} className="text-base font-semibold leading-none">
              {title}
            </h2>
            {description ? (
              <p id={descriptionId} className="text-sm text-muted-foreground">
                {description}
              </p>
            ) : null}
          </div>
          <Button type="button" variant="ghost" size="icon" aria-label="Close dialog" onClick={() => onOpenChange(false)}>
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
        <div className="max-h-[calc(min(88vh,900px)-5rem)] overflow-y-auto p-[var(--card-padding)]">{children}</div>
      </div>
    </div>
  )
}

export { Dialog }
