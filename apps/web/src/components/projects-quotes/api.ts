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

export async function apiRequestBlob(
  path: string,
  {
    token,
  }: {
    token: string
  },
): Promise<{ blob: Blob; filename: string | null }> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
  } catch (error) {
    throw new Error(getNetworkErrorMessage(error, path), { cause: error })
  }

  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response, path))
  }

  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get('content-disposition')),
  }
}

function filenameFromDisposition(value: string | null) {
  if (!value) return null
  const encoded = value.match(/filename\*=UTF-8''([^;]+)/i)
  if (encoded?.[1]) return decodeURIComponent(encoded[1].replace(/^"|"$/g, ''))
  const plain = value.match(/filename="?([^";]+)"?/i)
  return plain?.[1] ?? null
}
