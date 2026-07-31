import { motion } from 'framer-motion'
import { Trash2 } from 'lucide-react'
import { formatBytes } from '@/lib/utils'
import type { UploadedImage } from '@/types'

interface ImageCardProps {
  image: UploadedImage
  onRemove: (id: string) => void
  index?: number
}

export function ImageCard({ image, onRemove, index = 0 }: ImageCardProps) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 18, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.94 }}
      transition={{ duration: 0.35, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -4 }}
      className="group overflow-hidden rounded-2xl border border-line bg-white shadow-soft"
    >
      <div className="relative aspect-square overflow-hidden bg-canvas">
        <motion.img
          src={image.previewUrl}
          alt={image.name}
          className="h-full w-full object-cover"
          whileHover={{ scale: 1.05 }}
          transition={{ duration: 0.35 }}
        />
        <button
          type="button"
          onClick={() => onRemove(image.id)}
          className="absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white/90 text-danger opacity-100 shadow-soft backdrop-blur transition hover:bg-danger hover:text-white sm:opacity-0 sm:group-hover:opacity-100"
          aria-label={`Remove ${image.name}`}
        >
          <Trash2 className="h-4 w-4" />
        </button>
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
