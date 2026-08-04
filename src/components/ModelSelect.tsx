import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, ChevronsUpDown, Search } from 'lucide-react'
import { exampleCredits, formatCredits, type AiModel } from '@/data/models'
import { cn } from '@/lib/utils'

interface ModelSelectProps {
  models: AiModel[]
  value: string
  onChange: (modelId: string) => void
  disabled?: boolean
}

function displayName(name: string): string {
  return name.replace(/^ByteDance\s+/i, '')
}

export function ModelSelect({ models, value, onChange, disabled = false }: ModelSelectProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const rootRef = useRef<HTMLDivElement>(null)
  const selected = models.find((model) => model.id === value) ?? models[0]

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return models
    return models.filter((model) =>
      [model.name, model.best_for, model.description]
        .join(' ')
        .toLowerCase()
        .includes(needle),
    )
  }, [models, query])

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('mousedown', onPointerDown)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('mousedown', onPointerDown)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          'flex w-full items-center justify-between gap-3 rounded-xl border border-line bg-white px-3.5 py-3 text-left transition duration-200',
          'hover:border-accent/40 focus:outline-none focus:ring-2 focus:ring-accent/15',
          open && 'border-accent/40 ring-2 ring-accent/15',
          disabled && 'cursor-not-allowed opacity-60',
        )}
      >
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">
            {selected ? displayName(selected.name) : 'Select model'}
          </p>
          <p className="mt-1 truncate text-xs text-mute">
            {selected?.description}
            {selected
              ? exampleCredits(selected) != null
                ? ` · ${formatCredits(exampleCredits(selected)!)} Credits`
                : ' · Pricing unknown'
              : ''}
          </p>
        </div>
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-mute" />
      </button>

      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="absolute left-0 right-0 z-30 mt-2 overflow-hidden rounded-2xl border border-line bg-white shadow-lift"
          >
            <div className="border-b border-line p-2">
              <label className="flex items-center gap-2 rounded-xl bg-canvas px-3 py-2">
                <Search className="h-3.5 w-3.5 text-mute" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search models…"
                  className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-mute/70"
                  autoFocus
                />
              </label>
            </div>

            <ul className="max-h-72 overflow-y-auto py-1">
              {filtered.length === 0 ? (
                <li className="px-3 py-4 text-center text-sm text-mute">No models found</li>
              ) : (
                filtered.map((model) => {
                  const isActive = model.id === selected?.id
                  return (
                    <li key={model.id}>
                      <button
                        type="button"
                        onClick={() => {
                          onChange(model.id)
                          setOpen(false)
                          setQuery('')
                        }}
                        className={cn(
                          'flex w-full items-start gap-3 px-3 py-2.5 text-left transition duration-200',
                          isActive ? 'bg-accent-soft/50' : 'hover:bg-canvas',
                        )}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-ink">{displayName(model.name)}</p>
                            {isActive ? <Check className="h-3.5 w-3.5 shrink-0 text-accent" /> : null}
                          </div>
                          <p className="mt-0.5 text-xs text-mute">{model.description}</p>
                          <p className="mt-1 text-[11px] font-medium text-mute">
                            {model.provider}
                            <span className="mx-1.5 text-line">·</span>
                            <span className="text-accent">
                              {exampleCredits(model) != null
                                ? `${formatCredits(exampleCredits(model)!)} Credits example`
                                : 'Official pricing unknown'}
                            </span>
                          </p>
                        </div>
                      </button>
                    </li>
                  )
                })
              )}
            </ul>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
