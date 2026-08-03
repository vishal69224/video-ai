const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_BASE_URL
).replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number
  readonly code?: string
  readonly detail?: unknown

  constructor(message: string, status: number, code?: string, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = detail
  }
}

type ErrorBody = {
  success?: boolean
  message?: string
  detail?: unknown
}

function extractErrorMessage(body: ErrorBody | null, fallback: string): string {
  if (!body) return fallback
  if (typeof body.message === 'string' && body.message.trim()) return body.message
  if (typeof body.detail === 'string' && body.detail.trim()) return body.detail
  if (body.detail && typeof body.detail === 'object' && !Array.isArray(body.detail)) {
    const detail = body.detail as { code?: string; message?: string }
    if (typeof detail.message === 'string' && detail.message.trim()) return detail.message
  }
  return fallback
}

function extractErrorCode(body: ErrorBody | null): string | undefined {
  if (!body?.detail || typeof body.detail !== 'object' || Array.isArray(body.detail)) {
    return undefined
  }
  const code = (body.detail as { code?: unknown }).code
  return typeof code === 'string' ? code : undefined
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
    })
  } catch {
    throw new ApiError(
      'Network disconnected. Check that the backend is running and try again.',
      0,
      'network_error',
    )
  }

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')
  const body = (isJson ? await response.json().catch(() => null) : null) as ErrorBody | null

  if (!response.ok) {
    throw new ApiError(
      extractErrorMessage(body, `Request failed (${response.status})`),
      response.status,
      extractErrorCode(body),
      body?.detail,
    )
  }

  return body as T
}

export function resolveMediaUrl(path: string | null | undefined): string {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
    return path
  }
  if (path.startsWith('/')) return `${API_BASE_URL}${path}`
  return `${API_BASE_URL}/${path}`
}
