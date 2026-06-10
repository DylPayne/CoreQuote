import { Building2, HardHat, LoaderCircle, LogOut, ShieldCheck, UserRound } from 'lucide-react'
import type { ComponentType, Dispatch, FormEvent, InputHTMLAttributes, SetStateAction } from 'react'

import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ControlGroup, ControlGroupItem } from '@/components/ui/control-group'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { AuthFormState, AuthMode } from '@/types/auth'

export function AuthScreen({
  authError,
  authForm,
  authMode,
  isSubmitting,
  onModeChange,
  onSubmit,
  setAuthForm,
}: {
  authError: string | null
  authForm: AuthFormState
  authMode: AuthMode
  isSubmitting: boolean
  onModeChange: (mode: AuthMode) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  setAuthForm: Dispatch<SetStateAction<AuthFormState>>
}) {
  const isRegistering = authMode === 'register'

  return (
    <div className="grid min-h-screen bg-background text-foreground lg:grid-cols-[0.95fr_1.05fr]">
      <section className="flex min-h-[38vh] flex-col justify-between border-b border-border bg-sidebar p-6 lg:min-h-screen lg:border-b-0 lg:border-r lg:p-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <HardHat className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold">CoreQuote</p>
            <p className="text-xs text-muted-foreground">Cabinetry quoting</p>
          </div>
        </div>

        <div className="max-w-xl py-10">
          <Badge className="mb-5" variant="outline">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            Secure sign-in
          </Badge>
          <h1 className="text-3xl font-semibold tracking-normal md:text-4xl">Sign in to your quoting workspace.</h1>
          <p className="mt-4 max-w-lg text-sm leading-6 text-muted-foreground">
            Keep projects, quote defaults, boards, hardware, and pricing together for the team that builds the work.
          </p>
        </div>

        <div className="grid gap-3 text-sm text-muted-foreground sm:grid-cols-3 lg:grid-cols-1">
          <FeatureLine icon={Building2} label="One company workspace" />
          <FeatureLine icon={UserRound} label="Owner account setup" />
          <FeatureLine icon={LogOut} label="Simple sign-out control" />
        </div>
      </section>

      <main className="flex items-center justify-center p-4 md:p-8">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{isRegistering ? 'Create owner account' : 'Welcome back'}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {isRegistering
                ? 'Register the company and first owner user.'
                : 'Log in with an existing CoreQuote account.'}
            </p>
          </CardHeader>
          <CardContent>
            <ControlGroup className="mb-5 w-full gap-0" role="group" aria-label="Select auth mode">
              <ControlGroupItem
                aria-pressed={authMode === 'login'}
                className="flex-1 justify-center rounded-[calc(var(--control-radius)-0.2rem)]"
                onClick={() => onModeChange('login')}
              >
                Log in
              </ControlGroupItem>
              <ControlGroupItem
                aria-pressed={authMode === 'register'}
                className="flex-1 justify-center rounded-[calc(var(--control-radius)-0.2rem)]"
                onClick={() => onModeChange('register')}
              >
                Register
              </ControlGroupItem>
            </ControlGroup>

            <form className="space-y-4" onSubmit={onSubmit}>
              {isRegistering ? (
                <>
                  <Field
                    autoComplete="organization"
                    label="Company name"
                    minLength={2}
                    onChange={(value) => setAuthForm((current) => ({ ...current, companyName: value }))}
                    required
                    value={authForm.companyName}
                  />
                  <Field
                    autoComplete="name"
                    label="Your name"
                    minLength={2}
                    onChange={(value) => setAuthForm((current) => ({ ...current, name: value }))}
                    required
                    value={authForm.name}
                  />
                </>
              ) : null}

              <Field
                autoComplete="email"
                label="Email"
                onChange={(value) => setAuthForm((current) => ({ ...current, email: value }))}
                required
                type="email"
                value={authForm.email}
              />
              <Field
                autoComplete={isRegistering ? 'new-password' : 'current-password'}
                label="Password"
                minLength={isRegistering ? 12 : 1}
                onChange={(value) => setAuthForm((current) => ({ ...current, password: value }))}
                required
                type="password"
                value={authForm.password}
              />

              {authError ? (
                <Alert variant="destructive">{authError}</Alert>
              ) : null}

              <Button className="w-full" disabled={isSubmitting} type="submit">
                {isSubmitting ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                {isRegistering ? 'Create account' : 'Log in'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}

function FeatureLine({
  icon: Icon,
  label,
}: {
  icon: ComponentType<{ className?: string; 'aria-hidden'?: boolean }>
  label: string
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="h-4 w-4 text-accent" aria-hidden={true} />
      {label}
    </div>
  )
}

function Field({
  label,
  onChange,
  type = 'text',
  value,
  ...props
}: {
  label: string
  onChange: (value: string) => void
  type?: string
  value: string
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'type' | 'value'>) {
  return (
    <Label className="grid gap-1.5">
      {label}
      <Input
        onChange={(event) => onChange(event.target.value)}
        type={type}
        value={value}
        {...props}
      />
    </Label>
  )
}
