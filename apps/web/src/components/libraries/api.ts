import type { ApiMethod, PriceItemType } from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export async function upsertPriceItem(
  token: string,
  priceListId: string,
  payload: {
    item_type: PriceItemType
    item_ref_id: string
    price_component: string
    uom: string
    unit_price_cents: number
  },
) {
  await apiRequest(`/api/v1/libraries/price-lists/${priceListId}/items/upsert`, {
    body: payload,
    method: 'POST',
    token,
  })
}

export async function apiRequest<T = unknown>(
  path: string,
  options: {
    body?: unknown
    method?: ApiMethod
    token: string
  },
): Promise<T> {
  const headers = new Headers()
  headers.set('Accept', 'application/json')
  headers.set('Authorization', `Bearer ${options.token}`)
  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    headers,
    method: options.method ?? 'GET',
  })

  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export async function getApiErrorMessage(response: Response) {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg ?? String(item)).join(', ')
  } catch {
    return `Request failed with status ${response.status}`
  }

  return `Request failed with status ${response.status}`
}
