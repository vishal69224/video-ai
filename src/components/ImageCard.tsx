import { motion } from 'framer-motion'
import { Trash2 } from 'lucide-react'
import { formatBytes } from '@/lib/utils'
import type { UploadedImage } from '@/types'

interface ImageCardProps {
  image: UploadedImage
  onRemove: (id: string) => void
  index?: number
  disableRemove?: boolean
  isPrimary?: boolean
}

export function ImageCard({
  image,
  onRemove,
  index = 0,
  disableRemove = false,
  isPrimary = false,
}: ImageCardProps) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.28, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -4, boxShadow: '0 4px 12px rgb(11 18 32 / 0.08), 0 20px 40px rgb(11 18 32 / 0.08)' }}
      className="group overflow-hidden rounded-2xl border border-line bg-white shadow-soft"
    >
      <div className="relative aspect-square overflow-hidden bg-canvas">
        <motion.img
          src={image.previewUrl}
          alt={image.name}
          className="h-full w-full object-cover"
          whileHover={{ scale: 1.04 }}
          transition={{ duration: 0.28 }}
        />
        {isPrimary ? (
          <span className="absolute left-3 top-3 rounded-lg bg-accent px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-white shadow-soft">
            Primary
          </span>
        ) : null}
        {!disableRemove ? (
          <button
            type="button"
            onClick={() => onRemove(image.id)}
            className="absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white/90 text-danger opacity-100 shadow-soft backdrop-blur transition duration-200 hover:bg-danger hover:text-white sm:opacity-0 sm:group-hover:opacity-100"
            aria-label={`Remove ${image.name}`}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        ) : null}
      </div>
      <div className="space-y-1 p-3.5">
        <p className="truncate text-sm font-semibold text-ink" title={image.name}>
          {image.name}
        </p>
        <p className="text-xs text-mute">{formatBytes(image.size)}</p>
      </div>
    </motion.article>
  )
}
