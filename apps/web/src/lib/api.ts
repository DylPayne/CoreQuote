export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')
export const AUTH_TOKEN_KEY = 'corequote.authToken'

type ApiMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
type ApiErrorBody = { detail?: unknown } | Record<string, unknown>

export function getStoredAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

export async function apiRequest<T = unknown>(
  path: string,
  options: {
    body?: unknown
    method?: ApiMethod
    token?: string
  } = {},
): Promise<T> {
  const requestUrl = `${API_BASE_URL}${path}`
  const headers = new Headers()
  headers.set('Accept', 'application/json')

  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }

  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`)
  }

  let response: Response
  try {
    response = await fetch(requestUrl, {
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      headers,
      method: options.method ?? 'GET',
    })
  } catch (error) {
    throw new Error(getNetworkErrorMessage(error, path), { cause: error })
  }

  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response, path))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function getNetworkErrorMessage(error: unknown, path?: string) {
  if (import.meta.env.DEV) {
    console.warn('CoreQuote API connection failed', { error, path })
  }

  return 'CoreQuote could not connect right now. Please try again in a moment.'
}

export async function getApiErrorMessage(response: Response, path?: string) {
  const body = await readApiErrorBody(response)
  const fallback = fallbackMessageForStatus(response.status, path)
  const detail = detailMessageFromBody(body)

  if (import.meta.env.DEV) {
    console.warn('CoreQuote API request failed', { body, path, status: response.status })
  }

  if (!detail) {
    return fallback
  }

  return `${fallback} ${detail}`
}

async function readApiErrorBody(response: Response): Promise<ApiErrorBody | string | null> {
  try {
    return (await response.json()) as ApiErrorBody
  } catch {
    try {
      const raw = await response.text()
      return raw.trim() || null
    } catch {
      return null
    }
  }
}

function fallbackMessageForStatus(status: number, path?: string) {
  if (status === 400) return 'Some details need checking.'
  if (status === 401) {
    if (path?.includes('/auth/login')) return 'Email or password not recognised.'
    return 'Your sign-in has expired. Please sign in again.'
  }
  if (status === 403) return 'This account cannot make that change.'
  if (status === 404) return 'We could not find that item. It may have been removed.'
  if (status === 409) return 'That change conflicts with an existing record.'
  if (status === 422) return 'Some details need checking.'
  if (status >= 500) return 'CoreQuote hit a problem while finishing that request. Please try again.'
  return 'CoreQuote could not finish that request. Please try again.'
}

function detailMessageFromBody(body: ApiErrorBody | string | null) {
  if (!body) return null
  if (typeof body === 'string') return cleanSafeDetail(body)

  const detail = (body as { detail?: unknown }).detail
  if (typeof detail === 'string') return cleanSafeDetail(detail)
  if (Array.isArray(detail)) return validationDetailMessage(detail)
  if (body && typeof body === 'object') return null
  return null
}

function validationDetailMessage(detailRows: unknown[]) {
  const messages = detailRows.map((item) => {
    if (item && typeof item === 'object' && 'msg' in item) {
      return String((item as { msg?: unknown }).msg ?? '')
    }
    return String(item)
  })
  const joined = messages.join(' ')

  if (/required/i.test(joined)) return 'Some required details are missing.'
  if (/valid|number|integer|decimal|greater|less|too short|too long/i.test(joined)) {
    return 'Check the values in the form and try again.'
  }

  return null
}

function cleanSafeDetail(detail: string) {
  const trimmed = detail.trim()
  if (!trimmed || isTechnicalDetail(trimmed)) return null
  return trimmed.endsWith('.') ? trimmed : `${trimmed}.`
}

function isTechnicalDetail(detail: string) {
  return /localhost|https?:\/\/|\/api\/|bearer|token|request failed|network error|traceback|postgres|sql|uuid|\b[A-Z_]+Error\b|[{}[\]]|_id\b/i.test(detail)
}
