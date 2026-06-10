import type { ApiMethod } from './types'

import { API_BASE_URL, getApiErrorMessage, getNetworkErrorMessage } from '@/lib/api'

export async function apiRequest<T = unknown>(
  path: string,
  {
    token,
    method = 'GET',
    body,
  }: {
    token: string
    method?: ApiMethod
    body?: unknown
  },
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
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

  return (await response.json()) as T
}
