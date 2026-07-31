import { motion } from 'framer-motion'
import { Download, Eye, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/lib/utils'
import type { LibraryVideo } from '@/types'

interface VideoCardProps {
  video: LibraryVideo
  index?: number
  onPreview: (video: LibraryVideo) => void
  onDownload: (video: LibraryVideo) => void
  onDelete: (id: string) => void
}

export function VideoCard({
  video,
  index = 0,
  onPreview,
  onDownload,
  onDelete,
}: VideoCardProps) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.4, delay: index * 0.05, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -4 }}
      className="group overflow-hidden rounded-2xl border border-line bg-white shadow-soft"
    >
      <div className="relative aspect-video overflow-hidden bg-canvas">
        <motion.img
          src={video.thumbnail}
          alt={video.title}
          className="h-full w-full object-cover"
          whileHover={{ scale: 1.04 }}
          transition={{ duration: 0.35 }}
        />
        <div className="absolute inset-x-0 bottom-0 flex items-end justify-between bg-gradient-to-t from-ink/55 to-transparent p-3">
          <span className="rounded-lg bg-white/90 px-2 py-1 text-[11px] font-semibold text-ink backdrop-blur">
            {video.duration}
          </span>
          <span className="rounded-lg bg-white/90 px-2 py-1 text-[11px] font-semibold text-ink backdrop-blur">
            {video.resolution}
          </span>
        </div>
      </div>

      <div className="space-y-4 p-4">
        <div>
          <h3 className="font-display text-base font-semibold tracking-tight text-ink">
            {video.title}
          </h3>
          <p className="mt-1 text-xs text-mute">Created {formatDate(video.createdAt)}</p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="w-full"
            onClick={() => onPreview(video)}
          >
            <Eye className="h-3.5 w-3.5" />
            Preview
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="w-full"
            onClick={() => onDownload(video)}
          >
            <Download className="h-3.5 w-3.5" />
            Download
          </Button>
          <Button
            type="button"
            variant="danger"
            size="sm"
            className="w-full"
            onClick={() => onDelete(video.id)}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </Button>
        </div>
      </div>
    </motion.article>
  )
}
