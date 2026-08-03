import { motion } from 'framer-motion'
import {
  Check,
  CircleDashed,
  Clapperboard,
  LoaderCircle,
  ScanSearch,
  Send,
  Sparkles,
  WandSparkles,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import type { GenerationStep } from '@/types'

const STEP_ICONS: LucideIcon[] = [
  CircleDashed,
  ScanSearch,
  WandSparkles,
  Send,
  Clapperboard,
  Sparkles,
  Check,
]

interface ProgressTimelineProps {
  steps: GenerationStep[]
  progressPercent: number
  remainingMs: number
}

function formatRemaining(ms: number): string {
  if (ms < 0) return 'Live status from server · updates every 3s'
  const totalSeconds = Math.ceil(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes <= 0) return `${seconds}s remaining`
  return `${minutes}m ${seconds.toString().padStart(2, '0')}s remaining`
}

export function ProgressTimeline({
  steps,
  progressPercent,
  remainingMs,
}: ProgressTimelineProps) {
  return (
    <div className="space-y-8">
      <div className="rounded-2xl border border-line bg-white/90 p-5 shadow-soft sm:p-6">
        <div className="mb-3 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-ink">Overall progress</p>
            <p className="text-xs text-mute">{formatRemaining(remainingMs)}</p>
          </div>
          <p className="font-display text-2xl font-semibold text-accent">{progressPercent}%</p>
        </div>
        <Progress value={progressPercent} />
      </div>

      <ol className="space-y-3">
        {steps.map((step, index) => {
          const Icon = STEP_ICONS[index] ?? Sparkles
          const isActive = step.status === 'active'
          const isCompleted = step.status === 'completed'

          return (
            <motion.li
              key={step.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.04, duration: 0.35 }}
              className={cn(
                'relative flex items-center gap-4 rounded-2xl border px-4 py-4 transition sm:px-5',
                isActive && 'border-accent/40 bg-accent-soft/50 shadow-soft',
                isCompleted && 'border-line bg-white',
                step.status === 'pending' && 'border-transparent bg-white/50',
              )}
            >
              <div
                className={cn(
                  'relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl',
                  isCompleted && 'bg-accent text-white',
                  isActive && 'bg-white text-accent shadow-soft',
                  step.status === 'pending' && 'bg-canvas text-mute',
                )}
              >
                {isActive ? (
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
                  >
                    <LoaderCircle className="h-5 w-5" />
                  </motion.span>
                ) : isCompleted ? (
                  <motion.span
                    initial={{ scale: 0.6, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ type: 'spring', stiffness: 320, damping: 18 }}
                  >
                    <Check className="h-5 w-5" />
                  </motion.span>
                ) : (
                  <Icon className="h-5 w-5" />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <p
                    className={cn(
                      'truncate text-sm font-semibold sm:text-base',
                      isActive ? 'text-ink' : isCompleted ? 'text-ink' : 'text-mute',
                    )}
                  >
                    {step.label}
                  </p>
                  <span
                    className={cn(
                      'shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide',
                      isCompleted && 'bg-accent-soft text-accent',
                      isActive && 'bg-ink text-white',
                      step.status === 'pending' && 'bg-canvas text-mute',
                    )}
                  >
                    {isCompleted ? 'Done' : isActive ? 'Running' : 'Queued'}
                  </span>
                </div>

                {isActive ? (
                  <motion.div
                    className="mt-3 h-1.5 overflow-hidden rounded-full bg-white"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <motion.div
                      className="h-full rounded-full bg-accent"
                      initial={{ width: '8%' }}
                      animate={{ width: ['12%', '88%', '42%', '96%'] }}
                      transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
                    />
                  </motion.div>
                ) : null}
              </div>
            </motion.li>
          )
        })}
      </ol>
    </div>
  )
}
