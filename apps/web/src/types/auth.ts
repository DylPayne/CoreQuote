export type AuthMode = 'login' | 'register'
export type AuthStatus = 'checking' | 'signed-in' | 'signed-out'

export type AuthUser = {
  id: string
  company_id: string
  company_name: string
  company_currency_code: string
  name: string
  email: string
  role: 'owner' | 'admin' | 'manager' | 'estimator' | 'production' | 'viewer' | 'member'
}

export type AuthTokenResponse = {
  access_token: string
  token_type: 'bearer'
  expires_at: string
  user: AuthUser
}

export type AuthFormState = {
  companyName: string
  name: string
  email: string
  password: string
}
