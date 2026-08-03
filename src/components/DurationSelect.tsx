import { motion } from 'framer-motion'
import type { DurationOption } from '@/data/models'
import { cn } from '@/lib/utils'

interface DurationSelectProps {
  options: DurationOption[]
  value: number
  onChange: (seconds: number) => void
  disabled?: boolean
}

export function DurationSelect({
  options,
  value,
  onChange,
  disabled = false,
}: DurationSelectProps) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {options.map((option) => {
          const isActive = option.seconds === value
          return (
            <motion.button
              key={option.seconds}
              type="button"
              disabled={disabled}
              whileHover={disabled ? undefined : { y: -1 }}
              whileTap={disabled ? undefined : { scale: 0.98 }}
              transition={{ duration: 0.2 }}
              onClick={() => onChange(option.seconds)}
              className={cn(
                'min-w-[3.25rem] rounded-full px-3 py-2 text-xs font-semibold transition duration-200',
                isActive
                  ? 'border border-accent bg-accent text-white shadow-soft'
                  : 'border border-line bg-white text-mute hover:border-accent/40 hover:text-ink',
                disabled && 'cursor-not-allowed opacity-60',
              )}
            >
              {option.shortLabel}
            </motion.button>
          )
        })}
      </div>
      <p className="text-xs text-mute">Longer videos require more credits.</p>
    </div>
  )
}
