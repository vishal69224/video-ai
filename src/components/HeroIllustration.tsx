import { motion } from 'framer-motion'

export function HeroIllustration() {
  return (
    <div className="relative mx-auto aspect-[4/3] w-full max-w-xl">
      <motion.div
        className="absolute inset-0 rounded-[2rem] bg-gradient-to-br from-white via-accent-soft/60 to-slate-200/80 shadow-lift"
        animate={{ rotate: [0, 1.2, 0], y: [0, -6, 0] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
      />

      <motion.div
        className="absolute left-[8%] top-[12%] h-[58%] w-[42%] overflow-hidden rounded-2xl border border-white/80 bg-white shadow-soft"
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut' }}
      >
        <div className="h-full bg-gradient-to-br from-slate-100 via-teal-50 to-slate-200" />
        <div className="absolute inset-x-4 bottom-4 rounded-xl bg-white/80 p-3 backdrop-blur">
          <div className="h-2 w-16 rounded-full bg-ink/10" />
          <div className="mt-2 h-2 w-24 rounded-full bg-accent/30" />
        </div>
      </motion.div>

      <motion.div
        className="absolute right-[6%] top-[18%] h-[62%] w-[46%] overflow-hidden rounded-2xl border border-white/80 bg-ink shadow-lift"
        animate={{ y: [0, 12, 0] }}
        transition={{ duration: 6.2, repeat: Infinity, ease: 'easeInOut', delay: 0.4 }}
      >
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(153,246,228,0.35),transparent_45%),linear-gradient(160deg,#0B1220,#134E4A)]" />
        <motion.div
          className="absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/30"
          animate={{ scale: [1, 1.15, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <div className="absolute bottom-5 left-5 right-5">
          <div className="mb-2 flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.16em] text-white/70">
            <span>Rendering</span>
            <span>84%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/15">
            <motion.div
              className="h-full rounded-full bg-teal-300"
              animate={{ width: ['28%', '84%', '54%', '92%'] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            />
          </div>
        </div>
      </motion.div>

      <motion.div
        className="absolute bottom-[8%] left-[28%] rounded-2xl border border-white/80 bg-white/90 px-4 py-3 shadow-soft backdrop-blur"
        animate={{ y: [0, -8, 0], opacity: [0.9, 1, 0.9] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut', delay: 0.2 }}
      >
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">
          AI Prompt Ready
        </p>
        <p className="mt-1 text-sm font-medium text-ink">Cinematic product orbit</p>
      </motion.div>
    </div>
  )
}
