import { motion } from 'framer-motion'
import { Images } from 'lucide-react'
import { cn } from '@/lib/utils'

interface UploadCounterProps {
  count: number
  max: number
  className?: string
}

export function UploadCounter({ count, max, className }: UploadCounterProps) {
  const percent = Math.min(100, (count / max) * 100)

  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-2xl border border-line bg-white/80 p-4 shadow-soft sm:flex-row sm:items-center sm:justify-between',
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
          <Images className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-semibold text-ink">
            {count} / {max} Images Uploaded
          </p>
          <p className="text-xs text-mute">More reference images improve video quality.</p>
        </div>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-line sm:max-w-[12rem]">
        <motion.div
          className="h-full rounded-full bg-accent"
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
    </div>
  )
}
