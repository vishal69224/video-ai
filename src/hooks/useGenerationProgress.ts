import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { GENERATION_STEP_LABELS, STEP_DURATIONS_MS } from '@/lib/mockData'
import type { GenerationStep } from '@/types'

function buildInitialSteps(): GenerationStep[] {
  return GENERATION_STEP_LABELS.map((label, index) => ({
    id: `step-${index}`,
    label,
    status: index === 0 ? 'active' : 'pending',
  }))
}

export function useGenerationProgress(options: {
  active: boolean
  cancelled: boolean
  onComplete: () => void
}) {
  const { active, cancelled, onComplete } = options
  const [steps, setSteps] = useState<GenerationStep[]>(buildInitialSteps)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [elapsedMs, setElapsedMs] = useState(0)
  const completedRef = useRef(false)
  const onCompleteRef = useRef(onComplete)

  useEffect(() => {
    onCompleteRef.current = onComplete
  }, [onComplete])

  const totalDuration = useMemo(
    () => STEP_DURATIONS_MS.reduce((sum, value) => sum + value, 0),
    [],
  )

  const remainingMs = Math.max(0, totalDuration - elapsedMs)

  const reset = useCallback(() => {
    completedRef.current = false
    setSteps(buildInitialSteps())
    setCurrentIndex(0)
    setElapsedMs(0)
  }, [])

  useEffect(() => {
    if (!active || cancelled) return

    reset()

    let stepIndex = 0
    let elapsed = 0
    let timeoutId: ReturnType<typeof setTimeout>
    let rafId: number
    let start = performance.now()
    let stepStart = start

    const tick = (now: number) => {
      const stepElapsed = now - stepStart
      const globalElapsed = elapsed + stepElapsed
      setElapsedMs(Math.min(globalElapsed, totalDuration))
      rafId = requestAnimationFrame(tick)
    }

    const advance = () => {
      const duration = STEP_DURATIONS_MS[stepIndex]
      timeoutId = setTimeout(() => {
        elapsed += duration
        setSteps((prev) =>
          prev.map((step, index) => {
            if (index < stepIndex + 1) return { ...step, status: 'completed' }
            if (index === stepIndex + 1) return { ...step, status: 'active' }
            return step
          }),
        )

        if (stepIndex >= GENERATION_STEP_LABELS.length - 1) {
          setCurrentIndex(GENERATION_STEP_LABELS.length - 1)
          setElapsedMs(totalDuration)
          if (!completedRef.current) {
            completedRef.current = true
            onCompleteRef.current()
          }
          return
        }

        stepIndex += 1
        setCurrentIndex(stepIndex)
        stepStart = performance.now()
        advance()
      }, duration)
    }

    rafId = requestAnimationFrame(tick)
    advance()

    return () => {
      clearTimeout(timeoutId)
      cancelAnimationFrame(rafId)
    }
  }, [active, cancelled, reset, totalDuration])

  const progressPercent = Math.round((elapsedMs / totalDuration) * 100)

  return {
    steps,
    currentIndex,
    remainingMs,
    progressPercent,
    reset,
  }
}
