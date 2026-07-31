import { memo } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { GalleryCard } from '@/components/GalleryCard'
import type { HeroGalleryImage } from '@/data/heroGalleryData'

interface GalleryPreviewProps {
  image: HeroGalleryImage
  title: string
}

const IMAGE_TRANSITION = { duration: 0.45, ease: 'easeInOut' as const }

function GalleryPreviewComponent({ image, title }: GalleryPreviewProps) {
  return (
    <GalleryCard className="h-full w-full rounded-[28px] sm:rounded-[32px]">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-200 via-slate-100 to-teal-50/40" />

      <AnimatePresence initial={false}>
        <motion.img
          key={image.id}
          src={image.src}
          alt={`${title} — ${image.label}`}
          initial={{ opacity: 0, scale: 0.99 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.99 }}
          transition={IMAGE_TRANSITION}
          className="absolute inset-0 h-full w-full object-cover"
          draggable={false}
        />
      </AnimatePresence>

      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink/50 via-ink/10 to-transparent" />

      <div className="pointer-events-none absolute inset-x-0 bottom-0 p-5 sm:p-6 lg:p-7">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/70">
          AI Reference
        </p>
        <p className="mt-1 font-display text-2xl font-semibold tracking-tight text-white sm:text-[1.75rem]">
          {title}
        </p>
        <p className="mt-1 text-sm text-white/85">{image.label}</p>
      </div>
    </GalleryCard>
  )
}

export const GalleryPreview = memo(GalleryPreviewComponent)
