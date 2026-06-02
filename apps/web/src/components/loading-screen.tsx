import { LoaderCircle } from 'lucide-react'

export function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <LoaderCircle className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
        Restoring your CoreQuote session
      </div>
    </div>
  )
}
