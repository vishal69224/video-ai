import { apiRequest } from '@/services/api'

export interface CreditsResponse {
  success: boolean
  credits: number
  message: string
}

const CACHE_TTL_MS = 30_000

let cached: { value: CreditsResponse; at: number } | null = null
let inflight: Promise<CreditsResponse> | null = null

export async function fetchCredits(options?: { force?: boolean }): Promise<CreditsResponse> {
  const force = Boolean(options?.force)
  const now = Date.now()

  if (!force && cached && now - cached.at < CACHE_TTL_MS) {
    return cached.value
  }

  if (!force && inflight) {
    return inflight
  }

  inflight = apiRequest<CreditsResponse>('/api/credits')
    .then((value) => {
      cached = { value, at: Date.now() }
      return value
    })
    .finally(() => {
      inflight = null
    })

  return inflight
}
