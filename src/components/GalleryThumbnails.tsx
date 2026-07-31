import { memo, useMemo } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { GalleryCard } from '@/components/GalleryCard'
import type { HeroGalleryImage } from '@/data/heroGalleryData'
import { cn } from '@/lib/utils'

interface GalleryThumbnailsProps {
  images: HeroGalleryImage[]
  activeId: string
  onSelect: (image: HeroGalleryImage) => void
}

const SLOT_COUNT = 4
const IMAGE_TRANSITION = { duration: 0.45, ease: 'easeInOut' as const }
const SLOTS = Array.from({ length: SLOT_COUNT }, (_, index) => index)

function GalleryThumbnailsComponent({ images, activeId, onSelect }: GalleryThumbnailsProps) {
  const slots = useMemo(
    () => SLOTS.map((index) => ({ index, image: images[index] ?? null })),
    [images],
  )

  return (
    <div className="flex h-full w-full flex-col gap-2.5 sm:gap-3">
      {slots.map(({ index, image }) => {
        const isActive = Boolean(image && image.id === activeId)

        return (
          <div key={index} className="min-h-0 flex-1">
            <GalleryCard
              as="button"
              active={isActive}
              disabled={!image}
              onClick={() => {
                if (image) onSelect(image)
              }}
              className={cn(
                'h-full w-full rounded-[18px] bg-white/70 backdrop-blur-md sm:rounded-[20px]',
                image ? 'cursor-pointer hover:shadow-lift' : 'cursor-default opacity-40',
                isActive && 'ring-1 ring-accent/40',
                'transition-transform duration-300 hover:scale-[1.03]',
              )}
              aria-label={image ? `View ${image.label}` : 'Empty reference slot'}
              aria-pressed={isActive}
            >
              <div className="absolute inset-0 bg-slate-200" />

              <AnimatePresence initial={false}>
                {image ? (
                  <motion.img
                    key={image.id}
                    src={image.src}
                    alt={image.label}
                    initial={{ opacity: 0, scale: 0.99 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.99 }}
                    transition={IMAGE_TRANSITION}
                    className="absolute inset-0 h-full w-full object-cover"
                    draggable={false}
                  />
                ) : null}
              </AnimatePresence>

              <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink/40 to-transparent" />

              {image ? (
                <span className="absolute bottom-2 left-2 text-[9px] font-semibold uppercase tracking-[0.12em] text-white sm:bottom-2.5 sm:left-2.5 sm:text-[10px]">
                  {image.shortLabel}
                </span>
              ) : null}
            </GalleryCard>
          </div>
        )
      })}
    </div>
  )
}

export const GalleryThumbnails = memo(GalleryThumbnailsComponent)
