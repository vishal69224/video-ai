import { useCallback, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Ban, CheckCircle2 } from 'lucide-react'
import { ProgressTimeline } from '@/components/ProgressTimeline'
import { PrimaryButton } from '@/components/PrimaryButton'
import { SectionTitle } from '@/components/SectionTitle'
import { useApp } from '@/context/AppContext'
import { useGenerationProgress } from '@/hooks/useGenerationProgress'

const FALLBACK_THUMBNAIL =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="640" height="800" viewBox="0 0 640 800">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="640" y2="800">
          <stop stop-color="#CCFBF1"/>
          <stop offset="1" stop-color="#CBD5E1"/>
        </linearGradient>
      </defs>
      <rect width="640" height="800" fill="url(#g)"/>
    </svg>
  `)

export function GenerationProgressPage() {
  const navigate = useNavigate()
  const {
    images,
    projectName,
    setProjectName,
    isGenerating,
    setIsGenerating,
    generationCancelled,
    setGenerationCancelled,
    addVideo,
    clearImages,
  } = useApp()
  const imagesRef = useRef(images)
  const projectNameRef = useRef(projectName)
  const hadActiveGeneration = useRef(isGenerating)

  useEffect(() => {
    imagesRef.current = images
  }, [images])

  useEffect(() => {
    projectNameRef.current = projectName
  }, [projectName])

  useEffect(() => {
    if (!hadActiveGeneration.current) {
      navigate('/generate', { replace: true })
    }
  }, [navigate])

  const handleComplete = useCallback(() => {
    const currentImages = imagesRef.current
    const first = currentImages[0]
    const titleBase =
      projectNameRef.current.trim() ||
      first?.name.replace(/\.[^.]+$/, '') ||
      'Product Film'
    const thumbnail = first ? URL.createObjectURL(first.file) : FALLBACK_THUMBNAIL

    addVideo({
      id: crypto.randomUUID(),
      title: `${titleBase} — AI Motion`,
      createdAt: new Date().toISOString(),
      duration: '0:10',
      resolution: '1080 × 1920',
      thumbnail,
    })
    clearImages()
    setProjectName('')
    setIsGenerating(false)
    navigate('/library')
  }, [addVideo, clearImages, navigate, setIsGenerating, setProjectName])

  const { steps, progressPercent, remainingMs } = useGenerationProgress({
    active: isGenerating && !generationCancelled,
    cancelled: generationCancelled,
    onComplete: handleComplete,
  })

  const handleCancel = () => {
    setGenerationCancelled(true)
    setIsGenerating(false)
    navigate('/generate')
  }

  if (!isGenerating) {
    return null
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <SectionTitle
        eyebrow="Generation"
        title="Creating your cinematic video"
        description="Follow each stage as Lumina uploads, analyzes, prompts, and renders your film."
      />

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.08 }}
        className="mt-10"
      >
        <ProgressTimeline
          steps={steps}
          progressPercent={progressPercent}
          remainingMs={remainingMs}
        />

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm text-mute">
            <CheckCircle2 className="h-4 w-4 text-accent" />
            Estimated time updates live as each step completes.
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <PrimaryButton variant="secondary" onClick={handleCancel}>
              <Ban className="h-4 w-4" />
              Cancel
            </PrimaryButton>
            <PrimaryButton asChild variant="ghost">
              <Link to="/library">View Library</Link>
            </PrimaryButton>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
