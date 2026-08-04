/**
 * Model catalog facade — rates come only from GET /api/pricing.
 */

export {
  RESOLUTION_LABELS,
  estimateCredits,
  exampleCredits,
  formatCredits,
  getDefaultModelId,
  getDurationsForModel,
  getModelById,
  getResolutionsForModel,
  getVisibleModels,
  refreshPricingCatalog,
  type CreditBreakdown,
  type DurationOption,
  type PricingModel as AiModel,
  type ResolutionId,
  type ResolutionOption,
} from '@/services/pricing'

import { getDefaultModelId, type ResolutionId } from '@/services/pricing'

/** Fallback defaults until catalog loads from the backend. */
export const DEFAULT_MODEL_ID = 'seedance-1-pro'
export const DEFAULT_RESOLUTION_ID: ResolutionId = '720p'
export const DEFAULT_DURATION_SECONDS = 5

export function resolveDefaultModelId(): string {
  return getDefaultModelId()
}
