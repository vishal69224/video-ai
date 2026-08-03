import { Link } from 'react-router-dom'
import { Sparkles } from 'lucide-react'

const FOOTER_LINKS = [
  { label: 'Generator', to: '/generate' },
  { label: 'Library', to: '/library' },
  { label: 'How it works', to: '/#how-it-works' },
  { label: 'FAQ', to: '/#faq' },
]

export function Footer() {
  return (
    <footer className="mt-auto border-t border-line bg-white/70">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-12 sm:px-6 lg:flex-row lg:items-start lg:justify-between lg:px-8">
        <div className="max-w-sm">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink text-white">
              <Sparkles className="h-4 w-4" />
            </span>
            <span className="font-display text-lg font-semibold tracking-tight">Lumina</span>
          </div>
          <p className="mt-4 text-sm leading-relaxed text-mute">
            A premium AI video studio for product storytelling. Upload images, generate cinematic
            motion, and ship beautiful creative in minutes.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-x-10 gap-y-3 sm:grid-cols-4">
          {FOOTER_LINKS.map((link) => (
            <Link
              key={link.label}
              to={link.to}
              className="text-sm font-medium text-mute transition hover:text-ink"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-5 text-xs text-mute sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <p>© {new Date().getFullYear()} Lumina. Crafted for modern product teams.</p>
          <p>Connected to the Lumina AI video backend.</p>
        </div>
      </div>
    </footer>
  )
}
