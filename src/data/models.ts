/**
 * Kie.ai Image-to-Video catalog (Seedance).
 *
 * Model slugs from:
 * - https://docs.kie.ai/market/bytedance/seedance-2
 * - https://docs.kie.ai/market/bytedance/seedance-2-fast
 * - https://docs.kie.ai/market/bytedance/seedance-2-mini
 * - https://kie.ai/market/image-to-video
 *
 * Credits are billed per output second (image/text input, no reference video):
 * Seedance 2.0 / Fast / Mini rate tables used by Kie-compatible pricing.
 */

export type ResolutionId = '480p' | '720p' | '1080p' | '4k'

export interface AiModel {
  id: string
  name: string
  provider: string
  /** Credits charged per output second at each supported resolution. */
  creditsPerSecond: Partial<Record<ResolutionId, number>>
  /** Example cost shown in the dropdown (default res × default duration). */
  credits: number
  maxResolution: ResolutionId
  resolutions: ResolutionId[]
  durations: number[]
  description: string
  bestFor: string
  providerMark?: string
  /** Official Kie Market model slug. */
  apiModel: string
  payloadFamily: 'seedance2' | 'v1ProFast'
  /** Flat credit prices by duration when Market lists "X Credits / Ys". */
  creditsByDuration?: Partial<Record<number, number>>
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

export interface CreditBreakdown {
  modelId: string
  modelName: string
  modelCredits: number
  resolutionId: ResolutionId
  resolutionLabel: string
  resolutionDelta: number
  durationSeconds: number
  durationDelta: number
  creditsPerSecond: number
  estimatedCredits: number
}

export const RESOLUTION_RANK: Record<ResolutionId, number> = {
  '480p': 1,
  '720p': 2,
  '1080p': 3,
  '4k': 4,
}

export const RESOLUTION_LABELS: Record<ResolutionId, string> = {
  '480p': '480P',
  '720p': '720P',
  '1080p': '1080P',
  '4k': '4K',
}

/** Seedance supports 4–15s; keep common UI picks within that range. */
export const DURATIONS: DurationOption[] = [
  { seconds: 5, label: '5 seconds', shortLabel: '5s', creditDelta: 0 },
  { seconds: 8, label: '8 seconds', shortLabel: '8s', creditDelta: 0 },
  { seconds: 10, label: '10 seconds', shortLabel: '10s', creditDelta: 0 },
  { seconds: 12, label: '12 seconds', shortLabel: '12s', creditDelta: 0 },
  { seconds: 15, label: '15 seconds', shortLabel: '15s', creditDelta: 0 },
]

function exampleCredits(
  rates: Partial<Record<ResolutionId, number>>,
  resolution: ResolutionId,
  seconds: number,
): number {
  const rate = rates[resolution]
  if (!rate) return 0
  return rate * seconds
}

export const AI_MODELS: AiModel[] = [
  {
    id: 'seedance-1-pro-fast',
    name: 'ByteDance Seedance 1.0 Pro Fast',
    provider: 'ByteDance',
    // Market card name; API slug from docs.kie.ai/market/bytedance/v1-pro-fast-image-to-video
    apiModel: 'bytedance/v1-pro-fast-image-to-video',
    payloadFamily: 'v1ProFast',
    creditsPerSecond: {
      '720p': 1.6,
      '1080p': 1.6,
    },
    creditsByDuration: {
      5: 8,
      10: 16,
    },
    credits: 16,
    maxResolution: '1080p',
    resolutions: ['720p', '1080p'],
    durations: [5, 10],
    description: '16 Credits / 10s · fast image-to-video',
    bestFor: 'Affordable Pro Motion',
    providerMark: 'BD',
  },
  {
    id: 'seedance-2',
    name: 'ByteDance Seedance 2.0',
    provider: 'ByteDance',
    apiModel: 'bytedance/seedance-2',
    payloadFamily: 'seedance2',
    creditsPerSecond: {
      '480p': 6,
      '720p': 12,
      '1080p': 30,
      '4k': 70,
    },
    credits: exampleCredits({ '480p': 6, '720p': 12, '1080p': 30, '4k': 70 }, '720p', 5),
    maxResolution: '4k',
    resolutions: ['480p', '720p', '1080p', '4k'],
    durations: [5, 8, 10, 12, 15],
    description: 'Highest cinematic quality · 12 credits/sec at 720P',
    bestFor: 'Premium Cinematic Motion',
    providerMark: 'BD',
  },
  {
    id: 'seedance-2-fast',
    name: 'ByteDance Seedance 2.0 Fast',
    provider: 'ByteDance',
    apiModel: 'bytedance/seedance-2-fast',
    payloadFamily: 'seedance2',
    creditsPerSecond: {
      '480p': 5,
      '720p': 10,
    },
    credits: exampleCredits({ '480p': 5, '720p': 10 }, '720p', 5),
    maxResolution: '720p',
    resolutions: ['480p', '720p'],
    durations: [5, 8, 10, 12, 15],
    description: 'Faster generation · 10 credits/sec at 720P',
    bestFor: 'Fast Generation',
    providerMark: 'BD',
  },
  {
    id: 'seedance-2-mini',
    name: 'ByteDance Seedance 2.0 Mini',
    provider: 'ByteDance',
    apiModel: 'bytedance/seedance-2-mini',
    payloadFamily: 'seedance2',
    creditsPerSecond: {
      '480p': 3,
      '720p': 6,
    },
    credits: exampleCredits({ '480p': 3, '720p': 6 }, '480p', 5),
    maxResolution: '720p',
    resolutions: ['480p', '720p'],
    durations: [5, 8, 10, 12, 15],
    description: 'Lowest cost · 3 credits/sec at 480P',
    bestFor: 'Budget Drafts',
    providerMark: 'BD',
  },
]

export const DEFAULT_MODEL_ID = 'seedance-1-pro-fast'
export const DEFAULT_RESOLUTION_ID: ResolutionId = '720p'
export const DEFAULT_DURATION_SECONDS = 5

export function getModelById(modelId: string): AiModel | undefined {
  return AI_MODELS.find((model) => model.id === modelId)
}

export function getResolutionsForModel(model: AiModel): ResolutionOption[] {
  return model.resolutions.map((id) => {
    const rate = model.creditsPerSecond[id] ?? 0
    const helper = model.creditsByDuration
      ? Object.entries(model.creditsByDuration)
          .map(([seconds, credits]) => `${credits} cr / ${seconds}s`)
          .join(' · ')
      : `${rate} credits/sec`
    return {
      id,
      label: RESOLUTION_LABELS[id],
      creditDelta: rate,
      helper,
    }
  })
}

export function getDurationsForModel(model: AiModel): DurationOption[] {
  const allowed = new Set(model.durations)
  return DURATIONS.filter((option) => allowed.has(option.seconds))
}

export function estimateCredits(
  modelId: string,
  resolutionId: ResolutionId,
  durationSeconds: number,
): CreditBreakdown | null {
  const model = getModelById(modelId)
  if (!model) return null

  const resolutions = getResolutionsForModel(model)
  const resolution =
    resolutions.find((item) => item.id === resolutionId) ?? resolutions[0]
  if (!resolution) return null

  const durations = getDurationsForModel(model)
  const duration =
    durations.find((item) => item.seconds === durationSeconds) ?? durations[0]
  if (!duration) return null

  const flatCredits = model.creditsByDuration?.[duration.seconds]
  const creditsPerSecond = model.creditsPerSecond[resolution.id] ?? 0
  const estimatedCredits =
    typeof flatCredits === 'number'
      ? flatCredits
      : Math.round(creditsPerSecond * duration.seconds)

  return {
    modelId: model.id,
    modelName: model.name,
    modelCredits: estimatedCredits,
    resolutionId: resolution.id,
    resolutionLabel: resolution.label,
    resolutionDelta: 0,
    durationSeconds: duration.seconds,
    durationDelta: 0,
    creditsPerSecond:
      typeof flatCredits === 'number'
        ? Number((flatCredits / duration.seconds).toFixed(2))
        : creditsPerSecond,
    estimatedCredits,
  }
}

export function formatCreditDelta(delta: number): string {
  if (delta === 0) return 'Included'
  return `+${delta}`
}
