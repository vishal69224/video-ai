import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { DurationSelect } from '@/components/DurationSelect'
import { ModelSelect } from '@/components/ModelSelect'
import { ResolutionSelect } from '@/components/ResolutionSelect'
import {
  AI_MODELS,
  DEFAULT_DURATION_SECONDS,
  DEFAULT_MODEL_ID,
  DEFAULT_RESOLUTION_ID,
  estimateCredits,
  getDurationsForModel,
  getModelById,
  getResolutionsForModel,
  type CreditBreakdown,
  type ResolutionId,
} from '@/data/models'
import { useKieCredits } from '@/hooks/useKieCredits'

export interface GenerationSettingsValue {
  modelId: string
  resolutionId: ResolutionId
  durationSeconds: number
  breakdown: CreditBreakdown | null
  availableCredits: number | null
  hasEnoughCredits: boolean
}

interface GenerationSettingsProps {
  disabled?: boolean
  models?: typeof AI_MODELS
  onChange?: (value: GenerationSettingsValue) => void
}

export function GenerationSettings({
  disabled = false,
  models = AI_MODELS,
  onChange,
}: GenerationSettingsProps) {
  const { credits } = useKieCredits()
  const [modelId, setModelId] = useState(DEFAULT_MODEL_ID)
  const [resolutionId, setResolutionId] = useState<ResolutionId>(DEFAULT_RESOLUTION_ID)
  const [durationSeconds, setDurationSeconds] = useState(DEFAULT_DURATION_SECONDS)

  const model = useMemo(() => getModelById(modelId) ?? models[0], [modelId, models])

  const resolutionOptions = useMemo(
    () => (model ? getResolutionsForModel(model) : []),
    [model],
  )

  const durationOptions = useMemo(
    () => (model ? getDurationsForModel(model) : []),
    [model],
  )

  useEffect(() => {
    if (!model) return
    if (!resolutionOptions.some((option) => option.id === resolutionId)) {
      const fallback =
        resolutionOptions.find((option) => option.id === DEFAULT_RESOLUTION_ID) ??
        resolutionOptions[resolutionOptions.length - 1]
      if (fallback) setResolutionId(fallback.id)
    }
    if (!durationOptions.some((option) => option.seconds === durationSeconds)) {
      const fallback =
        durationOptions.find((option) => option.seconds === DEFAULT_DURATION_SECONDS) ??
        durationOptions[0]
      if (fallback) setDurationSeconds(fallback.seconds)
    }
  }, [model, resolutionOptions, durationOptions, resolutionId, durationSeconds])

  const breakdown = useMemo(
    () => estimateCredits(modelId, resolutionId, durationSeconds),
    [modelId, resolutionId, durationSeconds],
  )

  const hasEnoughCredits =
    credits !== null && breakdown !== null && credits >= breakdown.estimatedCredits

  const onChangeRef = useRef(onChange)
  useEffect(() => {
    onChangeRef.current = onChange
  }, [onChange])

  useEffect(() => {
    onChangeRef.current?.({
      modelId,
      resolutionId,
      durationSeconds,
      breakdown,
      availableCredits: credits,
      hasEnoughCredits,
    })
  }, [modelId, resolutionId, durationSeconds, breakdown, credits, hasEnoughCredits])

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-2xl border border-line bg-white/80 p-4 shadow-soft sm:p-5"
    >
      <div className="mb-5">
        <h2 className="font-display text-lg font-semibold tracking-tight text-ink sm:text-xl">
          Video Generation Settings
        </h2>
        <p className="mt-1 text-sm text-mute">
          Choose the AI model and output settings before generating your video.
        </p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2 lg:col-span-1">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-mute">AI Model</p>
          <ModelSelect
            models={models}
            value={model?.id ?? modelId}
            onChange={setModelId}
            disabled={disabled}
          />
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-mute">Resolution</p>
          <ResolutionSelect
            options={resolutionOptions}
            value={resolutionId}
            onChange={(next) => setResolutionId(next as ResolutionId)}
            disabled={disabled}
          />
        </div>

        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-mute">Duration</p>
          <DurationSelect
            options={durationOptions}
            value={durationSeconds}
            onChange={setDurationSeconds}
            disabled={disabled}
          />
        </div>

        <div className="rounded-xl border border-line bg-canvas/60 p-3.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-mute">Estimated Cost</p>
          <p className="mt-2 font-display text-2xl font-semibold tracking-tight text-ink">
            {breakdown?.estimatedCredits ?? 0}
            <span className="ml-1 text-sm font-semibold text-mute">Credits</span>
          </p>
          <p className="mt-1 text-xs text-mute">
            {breakdown
              ? `${breakdown.estimatedCredits} credits · ${breakdown.resolutionLabel} · ${breakdown.durationSeconds}s`
              : 'Select a model to estimate'}
          </p>
        </div>
      </div>
    </motion.section>
  )
}
