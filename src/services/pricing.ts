/**
 * Frontend pricing client.
 *
 * Single source of rates: backend seedance_pricing.json via GET /api/pricing.
 * Single formula (same as backend): credits = credits_per_second × duration
 */

import { API_BASE_URL } from '@/services/api'

export type ResolutionId = '480p' | '720p' | '1080p' | '4k'

export interface PricingModel {
  id: string
  model_id: string
  name: string
  payload_family: string
  ui_visible?: boolean
  description: string
  best_for: string
  provider_mark?: string
  resolutions: ResolutionId[]
  durations: number[]
  duration_min?: number
  duration_max?: number
  default_resolution: ResolutionId
  default_duration: number
  credits_per_second?: Partial<Record<ResolutionId, number>>
  example_credits?: number | null
  pricing_available?: boolean
}

export interface CreditBreakdown {
  modelId: string
  modelName: string
  resolutionId: ResolutionId
  resolutionLabel: string
  durationSeconds: number
  creditsPerSecond: number
  estimatedCredits: number
}

export interface ResolutionOption {
  id: ResolutionId
  label: string
  creditDelta: number
  helper: string
}

export interface DurationOption {
  seconds: number
  label: string
  shortLabel: string
  creditDelta: number
}

export const RESOLUTION_LABELS: Record<ResolutionId, string> = {
  '480p': '480P',
  '720p': '720P',
  '1080p': '1080P',
  '4k': '4K',
}

const DURATION_META: DurationOption[] = [
  { seconds: 4, label: '4 seconds', shortLabel: '4s', creditDelta: 0 },
  { seconds: 5, label: '5 seconds', shortLabel: '5s', creditDelta: 0 },
  { seconds: 6, label: '6 seconds', shortLabel: '6s', creditDelta: 0 },
  { seconds: 7, label: '7 seconds', shortLabel: '7s', creditDelta: 0 },
  { seconds: 8, label: '8 seconds', shortLabel: '8s', creditDelta: 0 },
  { seconds: 9, label: '9 seconds', shortLabel: '9s', creditDelta: 0 },
  { seconds: 10, label: '10 seconds', shortLabel: '10s', creditDelta: 0 },
  { seconds: 11, label: '11 seconds', shortLabel: '11s', creditDelta: 0 },
  { seconds: 12, label: '12 seconds', shortLabel: '12s', creditDelta: 0 },
  { seconds: 15, label: '15 seconds', shortLabel: '15s', creditDelta: 0 },
]

let models: PricingModel[] = []

export function formatCredits(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(1)))
}

/** Same formula as backend SeedancePricingEngine.estimateCredits */
export function estimateCredits(
  model: string,
  resolution: ResolutionId | string,
  duration: number,
): CreditBreakdown | null {
  const config = getModelById(model) ?? getModelByApiSlug(model)
  if (!config) return null

  const resolutionId = (resolution || '').toLowerCase() as ResolutionId
  if (!config.resolutions.includes(resolutionId)) return null

  const seconds = Math.floor(Number(duration))
  const dmin = config.duration_min ?? Math.min(...config.durations)
  const dmax = config.duration_max ?? Math.max(...config.durations)
  if (!Number.isFinite(seconds) || seconds < dmin || seconds > dmax) return null

  const rate = config.credits_per_second?.[resolutionId]
  if (typeof rate !== 'number') return null

  return {
    modelId: config.id,
    modelName: config.name,
    resolutionId,
    resolutionLabel: RESOLUTION_LABELS[resolutionId] ?? resolutionId,
    durationSeconds: seconds,
    creditsPerSecond: rate,
    estimatedCredits: Number((rate * seconds).toFixed(4)),
  }
}

export function getVisibleModels(): PricingModel[] {
  return models.filter((model) => model.ui_visible !== false)
}

export function getModelById(modelId: string): PricingModel | undefined {
  return models.find((model) => model.id === modelId)
}

export function getModelByApiSlug(apiModel: string): PricingModel | undefined {
  return models.find((model) => model.model_id === apiModel)
}

export function exampleCredits(model: PricingModel): number | null {
  if (typeof model.example_credits === 'number') return model.example_credits
  return (
    estimateCredits(
      model.id,
      model.default_resolution,
      model.default_duration,
    )?.estimatedCredits ?? null
  )
}

export function getResolutionsForModel(model: PricingModel): ResolutionOption[] {
  return model.resolutions.map((id) => {
    const rate = model.credits_per_second?.[id]
    return {
      id,
      label: RESOLUTION_LABELS[id],
      creditDelta: rate ?? 0,
      helper: typeof rate === 'number' ? `${rate} credits/sec` : 'Pricing unknown',
    }
  })
}

export function getDurationsForModel(model: PricingModel): DurationOption[] {
  const allowed = new Set(model.durations)
  return DURATION_META.filter((option) => allowed.has(option.seconds))
}

export function getDefaultModelId(): string {
  const visible = getVisibleModels()
  return (
    visible.find((model) => model.id === 'seedance-1-pro')?.id ??
    visible.find((model) => model.pricing_available)?.id ??
    visible[0]?.id ??
    'seedance-1-pro'
  )
}

/** Load the single backend pricing catalog. */
export async function refreshPricingCatalog(): Promise<PricingModel[]> {
  const response = await fetch(`${API_BASE_URL}/api/pricing?ui_only=false`)
  if (!response.ok) {
    throw new Error(`Failed to load pricing catalog (${response.status})`)
  }
  const body = (await response.json()) as {
    success?: boolean
    data?: { models?: PricingModel[] }
  }
  models = body.data?.models ?? []
  return getVisibleModels()
}
