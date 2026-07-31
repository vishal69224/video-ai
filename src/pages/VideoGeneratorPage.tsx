import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { ArrowRight, Clapperboard } from 'lucide-react'
import { ImageUploader } from '@/components/ImageUploader'
import { PrimaryButton } from '@/components/PrimaryButton'
import { SectionTitle } from '@/components/SectionTitle'
import { useApp } from '@/context/AppContext'
import { cn } from '@/lib/utils'

interface GeneratorFormValues {
  projectName: string
}

export function VideoGeneratorPage() {
  const navigate = useNavigate()
  const { images, projectName, setProjectName, setIsGenerating, setGenerationCancelled } = useApp()
  const canGenerate = images.length >= 1

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<GeneratorFormValues>({
    defaultValues: { projectName },
  })

  const onSubmit = (values: GeneratorFormValues) => {
    if (!canGenerate) return
    setProjectName(values.projectName.trim())
    setGenerationCancelled(false)
    setIsGenerating(true)
    navigate('/progress')
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <SectionTitle
        align="left"
        eyebrow="Video Generator"
        title="Upload references. Generate cinema."
        description="Add 1–10 product images. Lumina will analyze them locally and walk you through a simulated generation pipeline."
        className="mx-0 max-w-2xl"
      />

      <motion.form
        onSubmit={handleSubmit(onSubmit)}
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.1 }}
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
            className={cn(
              'mt-3 h-11 w-full rounded-xl border bg-white px-3.5 text-sm text-ink outline-none transition placeholder:text-mute/70',
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

        <ImageUploader />

        <div className="flex flex-col gap-3 rounded-2xl border border-line bg-white/80 p-4 shadow-soft sm:flex-row sm:items-center sm:justify-between sm:p-5">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-xl bg-ink text-white">
              <Clapperboard className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-ink">Ready when you are</p>
              <p className="text-xs text-mute">
                {canGenerate
                  ? `${images.length} reference${images.length > 1 ? 's' : ''} selected for generation.`
                  : 'Upload at least one image to enable generation.'}
              </p>
            </div>
          </div>

          <PrimaryButton
            type="submit"
            size="lg"
            variant="accent"
            disabled={!canGenerate}
            className="w-full sm:w-auto"
          >
            Generate Video
            <ArrowRight className="h-4 w-4" />
          </PrimaryButton>
        </div>
      </motion.form>
    </div>
  )
}
