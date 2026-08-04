import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError } from '@/services/api'
import { getVideoStatus, type VideoStatusResponse } from '@/services/video'
import type { GenerationStep } from '@/types'

/** Mirrors backend STAGE_RANGES order for the progress timeline. */
export const GENERATION_STAGES = [
  { id: 'queued', label: 'Queued' },
  { id: 'uploading_images', label: 'Uploading Images' },
  { id: 'analyzing_images', label: 'Analyzing Images' },
  { id: 'generating_prompt', label: 'Generating Prompt' },
  { id: 'uploading_assets', label: 'Uploading Assets to Kie' },
  { id: 'submitting_to_kie', label: 'Submitting Generation Request' },
  { id: 'waiting_queue', label: 'Waiting For Kie Queue' },
  { id: 'rendering', label: 'Rendering' },
  { id: 'finalizing', label: 'Finalizing' },
  { id: 'completed', label: 'Completed' },
] as const

/** Map legacy backend stage ids onto the current timeline. */
const STAGE_ALIASES: Record<string, string> = {
  submitting_to_ai: 'submitting_to_kie',
}

const POLL_INTERVAL_MS = 2500
const MAX_POLL_ATTEMPTS = 240

function normalizeStage(stage: string): string {
  const normalized = stage.trim().toLowerCase()
  return STAGE_ALIASES[normalized] ?? normalized
}

function stageIndex(stage: string): number {
  const normalized = normalizeStage(stage)
  if (normalized === 'failed') return -1
  const index = GENERATION_STAGES.findIndex((item) => item.id === normalized)
  return index >= 0 ? index : 0
}

function buildSteps(stage: string, status: string): GenerationStep[] {
  if (status === 'failed') {
    const active = Math.max(0, stageIndex(stage === 'failed' ? 'rendering' : stage))
    return GENERATION_STAGES.map((item, index) => ({
      id: item.id,
      label: item.label,
      status: index < active ? 'completed' : index === active ? 'active' : 'pending',
    }))
  }

  const current = stageIndex(stage)
  const completedAll = status === 'completed' || normalizeStage(stage) === 'completed'

  return GENERATION_STAGES.map((item, index) => {
    if (completedAll) return { id: item.id, label: item.label, status: 'completed' as const }
    if (index < current) return { id: item.id, label: item.label, status: 'completed' as const }
    if (index === current) return { id: item.id, label: item.label, status: 'active' as const }
    return { id: item.id, label: item.label, status: 'pending' as const }
  })
}

export function useVideoStatus(taskId: string | null, options?: { enabled?: boolean }) {
  const enabled = options?.enabled ?? true
  const [status, setStatus] = useState<VideoStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const attemptsRef = useRef(0)
  const completedRef = useRef(false)
  const highestProgressRef = useRef(0)

  const poll = useCallback(async () => {
    if (!taskId) return
    try {
      const next = await getVideoStatus(taskId)
      // Never let the bar jump backwards if a poll races an older snapshot.
      const progress = Math.max(highestProgressRef.current, next.progress ?? 0)
      highestProgressRef.current = progress
      setStatus({ ...next, progress })
      setError(next.status === 'failed' ? next.error_message || next.message || 'Generation failed' : null)
      if (next.status === 'completed' || next.status === 'failed') {
        completedRef.current = true
        setIsPolling(false)
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'Unable to check generation status. Retrying…'
      setError(message)
      if (err instanceof ApiError && err.status === 404) {
        completedRef.current = true
        setIsPolling(false)
      }
    }
  }, [taskId])

  useEffect(() => {
    completedRef.current = false
    attemptsRef.current = 0
    highestProgressRef.current = 0
    setStatus(null)
    setError(null)

    if (!taskId || !enabled) {
      setIsPolling(false)
      return
    }

    setIsPolling(true)
    void poll()

    const timer = window.setInterval(() => {
      if (completedRef.current) {
        window.clearInterval(timer)
        return
      }
      attemptsRef.current += 1
      if (attemptsRef.current >= MAX_POLL_ATTEMPTS) {
        setError('Polling timed out. Open the library later or start a new generation.')
        setIsPolling(false)
        window.clearInterval(timer)
        return
      }
      void poll()
    }, POLL_INTERVAL_MS)

    return () => window.clearInterval(timer)
  }, [taskId, enabled, poll])

  const steps = useMemo(
    () => buildSteps(status?.stage || 'queued', status?.status || 'processing'),
    [status?.stage, status?.status],
  )

  const progressPercent = Math.max(0, Math.min(100, status?.progress ?? 0))

  return {
    status,
    steps,
    progressPercent,
    error,
    isPolling,
    refresh: poll,
  }
}
