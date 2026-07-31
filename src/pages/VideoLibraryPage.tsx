import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Film, Plus } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { PrimaryButton } from '@/components/PrimaryButton'
import { SectionTitle } from '@/components/SectionTitle'
import { VideoCard } from '@/components/VideoCard'
import { VideoCardSkeleton } from '@/components/LoadingSkeleton'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useApp } from '@/context/AppContext'
import { formatDate } from '@/lib/utils'
import type { LibraryVideo } from '@/types'

export function VideoLibraryPage() {
  const { videos, removeVideo } = useApp()
  const [preview, setPreview] = useState<LibraryVideo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const timer = window.setTimeout(() => setLoading(false), 700)
    return () => window.clearTimeout(timer)
  }, [])

  const handleDownload = (video: LibraryVideo) => {
    const blob = new Blob(
      [
        `Lumina demo placeholder for "${video.title}"\nCreated: ${video.createdAt}\nDuration: ${video.duration}\nResolution: ${video.resolution}\n`,
      ],
      { type: 'text/plain' },
    )
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${video.title.replace(/\s+/g, '-').toLowerCase()}.txt`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <SectionTitle
          align="left"
          eyebrow="Library"
          title="Your generated videos"
          description="Browse, preview, download, or delete videos stored in local React state."
          className="mx-0 max-w-2xl"
        />
        <PrimaryButton asChild variant="accent">
          <Link to="/generate">
            <Plus className="h-4 w-4" />
            New Video
          </Link>
        </PrimaryButton>
      </div>

      <div className="mt-10">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <VideoCardSkeleton key={index} />
            ))}
          </div>
        ) : videos.length === 0 ? (
          <EmptyState
            icon={<Film className="h-6 w-6" />}
            title="No videos yet"
            description="Generate your first cinematic product video to populate this library."
            action={
              <PrimaryButton asChild variant="accent">
                <Link to="/generate">Generate Video</Link>
              </PrimaryButton>
            }
          />
        ) : (
          <motion.div layout className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <AnimatePresence mode="popLayout">
              {videos.map((video, index) => (
                <VideoCard
                  key={video.id}
                  video={video}
                  index={index}
                  onPreview={setPreview}
                  onDownload={handleDownload}
                  onDelete={removeVideo}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>

      <Dialog open={Boolean(preview)} onOpenChange={(open) => !open && setPreview(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{preview?.title}</DialogTitle>
            <DialogDescription>
              Created {preview ? formatDate(preview.createdAt) : ''} · {preview?.duration} ·{' '}
              {preview?.resolution}
            </DialogDescription>
          </DialogHeader>
          {preview ? (
            <div className="overflow-hidden rounded-2xl border border-line bg-canvas">
              <img
                src={preview.thumbnail}
                alt={preview.title}
                className="aspect-video w-full object-cover"
              />
              <div className="space-y-2 p-4">
                <p className="text-sm font-medium text-ink">Preview mode</p>
                <p className="text-sm leading-relaxed text-mute">
                  This frontend demo shows a local thumbnail preview. No remote media is fetched.
                </p>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
