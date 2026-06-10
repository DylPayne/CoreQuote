import type { ApiMethod, PriceItemType } from './types'

import { API_BASE_URL, getApiErrorMessage, getNetworkErrorMessage } from '@/lib/api'

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

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
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
