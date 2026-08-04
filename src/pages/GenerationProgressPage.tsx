import { useEffect, useMemo } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { AlertTriangle, Ban, CheckCircle2 } from 'lucide-react'
import { ProgressTimeline } from '@/components/ProgressTimeline'
import { PrimaryButton } from '@/components/PrimaryButton'
import { SectionTitle } from '@/components/SectionTitle'
import { useApp } from '@/context/AppContext'
import { useVideoStatus } from '@/hooks/useVideoStatus'
import { clearActiveTask, readActiveTaskId } from '@/lib/taskStorage'

export function GenerationProgressPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { activeTaskId, setActiveTaskId, setProjectName } = useApp()

  const taskId = useMemo(() => {
    const fromState = (location.state as { taskId?: string } | null)?.taskId
    return fromState || activeTaskId || readActiveTaskId()
  }, [location.state, activeTaskId])

  useEffect(() => {
    if (!taskId) {
      navigate('/generate', { replace: true })
      return
    }
    setActiveTaskId(taskId)
  }, [taskId, navigate, setActiveTaskId])

  const { status, steps, progressPercent, error, isPolling } = useVideoStatus(taskId, {
    enabled: Boolean(taskId),
  })

  useEffect(() => {
    if (status?.status !== 'completed') return
    clearActiveTask()
    setActiveTaskId(null)
    setProjectName('')
    const timer = window.setTimeout(() => {
      navigate('/library')
    }, 900)
    return () => window.clearTimeout(timer)
  }, [status?.status, navigate, setActiveTaskId, setProjectName])

  const handleCancel = () => {
    clearActiveTask()
    setActiveTaskId(null)
    navigate('/generate')
  }

  if (!taskId) {
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
          remainingMs={-1}
        />

        {error ? (
          <div className="mt-6 flex items-start gap-3 rounded-2xl border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{error}</p>
          </div>
        ) : null}

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm text-mute">
            <CheckCircle2 className="h-4 w-4 text-accent" />
            {isPolling
              ? status?.message || 'Polling backend status every 2.5 seconds.'
              : status?.status === 'completed'
                ? 'Generation complete. Opening library…'
                : 'Status updates paused.'}
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
