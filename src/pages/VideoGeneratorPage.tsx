import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { AlertTriangle, LoaderCircle } from 'lucide-react'
import {
  GenerationSettings,
  type GenerationSettingsValue,
} from '@/components/GenerationSettings'
import { ImageUploader } from '@/components/ImageUploader'
import { SectionTitle } from '@/components/SectionTitle'
import { useApp } from '@/context/AppContext'
import { formatCredits, getModelById } from '@/data/models'
import { persistActiveTask } from '@/lib/taskStorage'
import { cn } from '@/lib/utils'
import { API_BASE_URL, ApiError } from '@/services/api'
import { uploadImages } from '@/services/upload'
import { generateVideo } from '@/services/video'
import type { GeneratorPhase } from '@/types'

interface GeneratorFormValues {
  projectName: string
}

function phaseLabel(phase: GeneratorPhase): string {
  switch (phase) {
    case 'uploading':
      return 'Uploading'
    case 'generating_prompt':
      return 'Generating Prompt'
    case 'submitting_to_ai':
      return 'Submitting'
    case 'processing':
      return 'Processing'
    default:
      return 'Generate Video'
  }
}

export function VideoGeneratorPage() {
  const navigate = useNavigate()
  const { images, projectName, setProjectName, clearImages, setActiveTaskId } = useApp()
  const [phase, setPhase] = useState<GeneratorPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [devPrompt, setDevPrompt] = useState<string | null>(null)
  const [developmentMode, setDevelopmentMode] = useState(false)
  const [settings, setSettings] = useState<GenerationSettingsValue | null>(null)

  const estimatedCredits = settings?.breakdown?.estimatedCredits
  const pricingKnown = typeof estimatedCredits === 'number'
  const availableCredits = settings?.availableCredits ?? null
  const hasEnoughCredits = settings?.hasEnoughCredits ?? false
  const creditsKnown = availableCredits !== null
  const canGenerate = images.length >= 1
  const isBusy = phase !== 'idle'
  const blockedByCredits =
    !pricingKnown ||
    (!developmentMode && creditsKnown && !hasEnoughCredits)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/health`)
        if (!response.ok) return
        const body = (await response.json()) as {
          data?: { development_mode?: boolean }
        }
        if (!cancelled) {
          setDevelopmentMode(Boolean(body.data?.development_mode))
        }
      } catch {
        // Keep production defaults if health is unavailable.
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<GeneratorFormValues>({
    defaultValues: { projectName },
  })

  const onSubmit = async (values: GeneratorFormValues) => {
    if (!canGenerate || isBusy || blockedByCredits) return

    const trimmedName = values.projectName.trim()
    setProjectName(trimmedName)
    setError(null)
    setDevPrompt(null)

    try {
      setPhase('uploading')
      const uploadResult = await uploadImages(images.map((image) => image.file))
      const imagePaths = uploadResult.files.map((file) => file.url)
      if (imagePaths.length === 0) {
        throw new ApiError('Upload failed: no files returned.', 502, 'upload_failed')
      }

      const model = settings ? getModelById(settings.modelId) : undefined

      setPhase(developmentMode ? 'generating_prompt' : 'processing')
      const generation = await generateVideo({
        image_paths: imagePaths,
        project_name: trimmedName || undefined,
        model_id: settings?.modelId,
        api_model: model?.model_id,
        resolution: settings?.resolutionId,
        duration_seconds: settings?.durationSeconds,
        estimated_credits: settings?.breakdown?.estimatedCredits,
      })

      if (generation.development_mode) {
        setDevPrompt(generation.generated_prompt || generation.prompt || '')
        setPhase('idle')
        return
      }

      if (!generation.task_id) {
        throw new ApiError('Generation did not return a task id.', 502, 'missing_task_id')
      }

      // Production jobs return immediately; progress page polls live stages.
      persistActiveTask(generation.task_id, trimmedName)
      setActiveTaskId(generation.task_id)
      clearImages()
      navigate('/progress', { state: { taskId: generation.task_id } })
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'Something went wrong while starting generation.'
      setError(message)
      setPhase('idle')
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <SectionTitle
        align="left"
        eyebrow="Video Generator"
        title="Upload references. Generate cinema."
        description="Add 1–10 product images. Lumina will analyze them, generate a cinematic prompt, and submit your film to the AI renderer."
        className="mx-0 max-w-2xl"
      />

      <motion.form
        onSubmit={handleSubmit(onSubmit)}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05 }}
        className="mt-10 space-y-6"
      >
        <div className="rounded-2xl border border-line bg-white/80 p-4 shadow-soft sm:p-5">
          <label htmlFor="projectName" className="text-sm font-semibold text-ink">
            Project name
          </label>
          <p className="mt-1 text-xs text-mute">Optional — used as the video title in your library.</p>
          <input
            id="projectName"
            type="text"
            placeholder="Ceramic vase launch film"
            disabled={isBusy}
            className={cn(
              'mt-3 h-11 w-full rounded-xl border bg-white px-3.5 text-sm text-ink outline-none transition duration-200 placeholder:text-mute/70',
              errors.projectName
                ? 'border-danger focus:ring-2 focus:ring-danger/20'
                : 'border-line focus:border-accent/50 focus:ring-2 focus:ring-accent/15',
            )}
            {...register('projectName', {
              maxLength: { value: 60, message: 'Keep the name under 60 characters.' },
            })}
          />
          {errors.projectName ? (
            <p className="mt-2 text-xs text-danger">{errors.projectName.message}</p>
          ) : null}
        </div>

        <ImageUploader disabled={isBusy} />

        <GenerationSettings disabled={isBusy} onChange={setSettings} />

        <div className="space-y-3">
          <motion.button
            type="submit"
            disabled={!canGenerate || isBusy || blockedByCredits}
            whileHover={
              !canGenerate || isBusy || blockedByCredits ? undefined : { y: -2 }
            }
            whileTap={
              !canGenerate || isBusy || blockedByCredits ? undefined : { scale: 0.99 }
            }
            transition={{ duration: 0.2 }}
            className={cn(
              'flex w-full items-center justify-center gap-3 rounded-2xl bg-accent px-6 py-4 text-white shadow-soft transition duration-200',
              'hover:bg-accent-strong hover:shadow-lift',
              'disabled:pointer-events-none disabled:opacity-45',
            )}
          >
            {isBusy ? (
              <>
                <LoaderCircle className="h-5 w-5 animate-spin" />
                <span className="font-display text-lg font-semibold tracking-tight">
                  {phaseLabel(phase)}
                </span>
              </>
            ) : (
              <span className="font-display text-lg font-semibold tracking-tight">
                {pricingKnown
                  ? `Generate Video • ${formatCredits(estimatedCredits)} Credits`
                  : 'Generate Video • Pricing unknown'}
              </span>
            )}
          </motion.button>

          {!canGenerate && !isBusy ? (
            <p className="text-center text-xs text-mute">
              Upload at least one image to enable generation.
            </p>
          ) : null}

          {blockedByCredits && !isBusy ? (
            <p className="flex items-start justify-center gap-1.5 text-center text-xs text-danger">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                {!pricingKnown
                  ? 'Pricing is not configured for this Seedance model yet. Choose a model with credits_per_second rates.'
                  : `You need ${formatCredits(estimatedCredits!)} credits. Current balance ${availableCredits}.`}
              </span>
            </p>
          ) : null}

          {error ? (
            <p className="flex items-start justify-center gap-1.5 text-center text-xs text-danger">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{error}</span>
            </p>
          ) : null}

          {developmentMode && !isBusy ? (
            <p className="text-center text-xs text-mute">
              Development Mode is on — prompts are generated without calling Kie.ai.
            </p>
          ) : null}

          {devPrompt ? (
            <div className="rounded-2xl border border-line bg-white/80 p-4 text-left shadow-soft">
              <p className="text-xs font-semibold uppercase tracking-wide text-mute">
                Development prompt preview
              </p>
              <p className="mt-2 text-sm leading-relaxed text-ink">{devPrompt}</p>
            </div>
          ) : null}
        </div>
      </motion.form>
    </div>
  )
}
