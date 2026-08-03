import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Coins, Menu, Sparkles, X } from 'lucide-react'
import { PrimaryButton } from '@/components/PrimaryButton'
import { useKieCredits } from '@/hooks/useKieCredits'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/', label: 'Home' },
  { to: '/generate', label: 'Generator' },
  { to: '/library', label: 'Library' },
]

function formatCredits(value: number): string {
  return new Intl.NumberFormat('en-US').format(value)
}

export function Header() {
  const [open, setOpen] = useState(false)
  const { credits, loading, error, refresh } = useKieCredits()

  const creditsLabel = loading
    ? 'Credits…'
    : error
      ? 'Credits —'
      : `Credits ${formatCredits(credits ?? 0)}`

  return (
    <header className="sticky top-0 z-40 border-b border-line/70">
      <div className="glass">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/" className="group flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink text-white shadow-soft transition group-hover:scale-105">
              <Sparkles className="h-4 w-4" />
            </span>
            <span className="font-display text-lg font-semibold tracking-tight text-ink">
              Lumina
            </span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  cn(
                    'rounded-xl px-3.5 py-2 text-sm font-medium transition',
                    isActive ? 'bg-white text-ink shadow-soft' : 'text-mute hover:text-ink',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden items-center gap-2 md:flex">
            <button
              type="button"
              onClick={() => void refresh(true)}
              title={
                error
                  ? `${error} Click to retry.`
                  : 'Kie.ai credits'
              }
              className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-line bg-white px-3 text-sm font-medium text-ink shadow-soft transition hover:border-accent/40"
            >
              <Coins className="h-3.5 w-3.5 text-accent" />
              {creditsLabel}
            </button>
            <PrimaryButton asChild size="sm" variant="accent">
              <Link to="/generate">Generate Video</Link>
            </PrimaryButton>
          </div>

          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-white text-ink md:hidden"
            onClick={() => setOpen((value) => !value)}
            aria-label="Toggle menu"
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-b border-line bg-white md:hidden"
          >
            <div className="flex flex-col gap-1 px-4 py-3">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      'rounded-xl px-3 py-3 text-sm font-medium',
                      isActive ? 'bg-canvas text-ink' : 'text-mute',
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
              <button
                type="button"
                onClick={() => void refresh(true)}
                className="mt-1 inline-flex h-11 items-center justify-center gap-1.5 rounded-xl border border-line bg-white px-3 text-sm font-medium text-ink"
              >
                <Coins className="h-3.5 w-3.5 text-accent" />
                {creditsLabel}
              </button>
              <PrimaryButton asChild className="mt-2 w-full" variant="accent">
                <Link to="/generate" onClick={() => setOpen(false)}>
                  Generate Video
                </Link>
              </PrimaryButton>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </header>
  )
}
