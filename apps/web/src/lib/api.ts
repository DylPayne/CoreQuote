export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')
export const AUTH_TOKEN_KEY = 'corequote.authToken'

export function getStoredAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

export async function apiRequest<T = unknown>(
  path: string,
  options: {
    body?: unknown
    method?: 'GET' | 'POST' | 'PATCH'
    token?: string
  } = {},
): Promise<T> {
  const requestUrl = `${API_BASE_URL}${path}`
  const headers = new Headers()
  headers.set('Accept', 'application/json')

  if (options.body) {
    headers.set('Content-Type', 'application/json')
  }

  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`)
  }

  let response: Response
  try {
    response = await fetch(requestUrl, {
      body: options.body ? JSON.stringify(options.body) : undefined,
      headers,
      method: options.method ?? 'GET',
    })
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    throw new Error(`Network error while calling ${requestUrl}: ${detail}`, { cause: error })
  }

  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response, requestUrl))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

async function getApiErrorMessage(response: Response, requestUrl: string) {
  const statusPrefix = `${response.status} ${response.statusText || ''}`.trim()
  try {
    const body = (await response.json()) as { detail?: unknown } | Record<string, unknown>
    if (typeof (body as { detail?: unknown }).detail === 'string') {
      return `${statusPrefix}: ${(body as { detail: string }).detail} (url: ${requestUrl})`
    }
    if (Array.isArray((body as { detail?: unknown }).detail)) {
      const detailRows = (body as { detail: Array<Record<string, unknown>> }).detail
      const joined = detailRows.map((item) => String(item.msg ?? JSON.stringify(item))).join(', ')
      return `${statusPrefix}: ${joined} (url: ${requestUrl})`
    }
    if ((body as { detail?: unknown }).detail && typeof (body as { detail?: unknown }).detail === 'object') {
      return `${statusPrefix}: ${JSON.stringify((body as { detail: unknown }).detail)} (url: ${requestUrl})`
    }
    if (body && typeof body === 'object') {
      return `${statusPrefix}: ${JSON.stringify(body)} (url: ${requestUrl})`
    }
  } catch {
    try {
      const raw = await response.text()
      if (raw.trim()) return `${statusPrefix}: ${raw.trim()} (url: ${requestUrl})`
    } catch {
      // ignore and use fallback
    }
    return `Request failed: ${statusPrefix} (url: ${requestUrl})`
  }

  return `Request failed: ${statusPrefix} (url: ${requestUrl})`
}
