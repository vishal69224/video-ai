import { motion } from 'framer-motion'
import type { ResolutionOption } from '@/data/models'
import { cn } from '@/lib/utils'

interface ResolutionSelectProps {
  options: ResolutionOption[]
  value: string
  onChange: (resolutionId: string) => void
  disabled?: boolean
}

export function ResolutionSelect({
  options,
  value,
  onChange,
  disabled = false,
}: ResolutionSelectProps) {
  return (
    <div
      className="grid gap-1.5 rounded-xl border border-line bg-canvas/70 p-1"
      style={{
        gridTemplateColumns: `repeat(${Math.max(options.length, 1)}, minmax(0, 1fr))`,
      }}
    >
      {options.map((option) => {
        const isActive = option.id === value
        return (
          <motion.button
            key={option.id}
            type="button"
            disabled={disabled}
            whileHover={disabled ? undefined : { y: -1 }}
            whileTap={disabled ? undefined : { scale: 0.98 }}
            transition={{ duration: 0.2 }}
            onClick={() => onChange(option.id)}
            className={cn(
              'rounded-lg px-2 py-2.5 text-center text-xs font-semibold transition duration-200 sm:text-sm',
              isActive
                ? 'bg-accent text-white shadow-soft'
                : 'bg-transparent text-mute hover:bg-white hover:text-ink',
              disabled && 'cursor-not-allowed opacity-60',
            )}
          >
            {option.label}
          </motion.button>
        )
      })}
    </div>
  )
}
