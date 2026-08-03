import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Film, Plus, Search } from 'lucide-react'
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
import { formatDate } from '@/lib/utils'
import { ApiError } from '@/services/api'
import { deleteVideo, fetchVideos } from '@/services/library'
import type { LibraryVideo } from '@/types'

export function VideoLibraryPage() {
  const [videos, setVideos] = useState<LibraryVideo[]>([])
  const [preview, setPreview] = useState<LibraryVideo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')

  const loadVideos = useCallback(async (term?: string) => {
    setLoading(true)
    setError(null)
    try {
      const items = await fetchVideos(term)
      setVideos(items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load videos.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadVideos(query)
  }, [loadVideos, query])

  const handleDownload = async (video: LibraryVideo) => {
    if (!video.videoUrl) {
      setError('This video has no downloadable MP4 yet.')
      return
    }
    try {
      const response = await fetch(video.videoUrl)
      if (!response.ok) {
        throw new Error(`Download failed (${response.status})`)
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${video.title.replace(/\s+/g, '-').toLowerCase() || 'lumina-video'}.mp4`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch {
      // Fall back to opening the remote MP4 directly.
      const anchor = document.createElement('a')
      anchor.href = video.videoUrl
      anchor.download = `${video.title.replace(/\s+/g, '-').toLowerCase() || 'lumina-video'}.mp4`
      anchor.target = '_blank'
      anchor.rel = 'noopener noreferrer'
      anchor.click()
    }
  }

  const handleDelete = async (id: string) => {
    setDeletingId(id)
    setError(null)
    try {
      await deleteVideo(id)
      setVideos((prev) => prev.filter((video) => video.id !== id))
      if (preview?.id === id) setPreview(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to delete video.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <SectionTitle
          align="left"
          eyebrow="Library"
          title="Your generated videos"
          description="Browse, preview, download, or delete your generated videos."
          className="mx-0 max-w-2xl"
        />
        <PrimaryButton asChild variant="accent">
          <Link to="/generate">
            <Plus className="h-4 w-4" />
            New Video
          </Link>
        </PrimaryButton>
      </div>

      {error ? (
        <div className="mt-6 rounded-2xl border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : null}

      <form
        className="mt-8 flex flex-col gap-3 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault()
          setQuery(search.trim())
        }}
      >
        <label className="relative block min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-mute" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by project, prompt, or model"
            className="h-11 w-full rounded-xl border border-line bg-white pl-10 pr-3 text-sm text-ink shadow-soft outline-none transition focus:border-accent/50"
          />
        </label>
        <PrimaryButton type="submit" variant="secondary" className="sm:w-auto">
          Search
        </PrimaryButton>
      </form>

      <div className="mt-10">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <VideoCardSkeleton key={index} />
            ))}
          </div>
        ) : videos.length === 0 ? (
          <EmptyState
            icon={<Film className="h-6 w-6" />}
            title={query ? 'No matching videos' : 'No videos yet'}
            description={
              query
                ? 'Try a different project name, prompt phrase, or model.'
                : 'Generate your first cinematic product video to populate this library.'
            }
            action={
              query ? (
                <PrimaryButton
                  variant="secondary"
                  onClick={() => {
                    setSearch('')
                    setQuery('')
                  }}
                >
                  Clear search
                </PrimaryButton>
              ) : (
                <PrimaryButton asChild variant="accent">
                  <Link to="/generate">Generate Video</Link>
                </PrimaryButton>
              )
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
                  busy={deletingId === video.id}
                  onPreview={setPreview}
                  onDownload={handleDownload}
                  onDelete={handleDelete}
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
              {preview.videoUrl ? (
                <video
                  key={preview.videoUrl}
                  src={preview.videoUrl}
                  poster={preview.thumbnail || undefined}
                  controls
                  playsInline
                  className="aspect-video w-full bg-ink object-contain"
                />
              ) : (
                <img
                  src={preview.thumbnail}
                  alt={preview.title}
                  className="aspect-video w-full object-cover"
                />
              )}
              <div className="space-y-2 p-4">
                <p className="text-sm font-medium text-ink">
                  {preview.status === 'completed' ? 'Video preview' : `Status: ${preview.status}`}
                </p>
                <p className="text-sm leading-relaxed text-mute">
                  {preview.prompt || 'No prompt available for this video.'}
                </p>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
