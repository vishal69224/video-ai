import { apiRequest, resolveMediaUrl } from '@/services/api'
import type { LibraryVideo } from '@/types'

export interface LibraryVideoItem {
  id: string
  title: string
  created_at: string
  duration: string
  resolution: string
  thumbnail?: string | null
  thumbnail_url?: string | null
  video_url?: string | null
  prompt: string
  status: string
  task_id: string
  model?: string | null
  credits_used?: number | null
}

export interface LibraryListResponse {
  success: boolean
  videos: LibraryVideoItem[]
}

export interface DeleteVideoResponse {
  success: boolean
  message: string
}

export function mapLibraryVideo(item: LibraryVideoItem): LibraryVideo {
  return {
    id: item.id,
    title: item.title,
    createdAt: item.created_at,
    duration: item.duration,
    resolution: item.resolution,
    thumbnail:
      resolveMediaUrl(item.thumbnail_url) ||
      resolveMediaUrl(item.thumbnail) ||
      resolveMediaUrl(item.video_url),
    videoUrl: resolveMediaUrl(item.video_url),
    prompt: item.prompt,
    status: item.status,
    taskId: item.task_id,
  }
}

export async function fetchVideos(search?: string): Promise<LibraryVideo[]> {
  const query = search?.trim()
    ? `?q=${encodeURIComponent(search.trim())}`
    : ''
  const response = await apiRequest<LibraryListResponse>(`/api/videos${query}`)
  return response.videos.map(mapLibraryVideo)
}

export async function fetchVideo(videoId: string): Promise<LibraryVideo> {
  const item = await apiRequest<LibraryVideoItem>(
    `/api/videos/${encodeURIComponent(videoId)}`,
  )
  return mapLibraryVideo(item)
}

export async function deleteVideo(videoId: string): Promise<DeleteVideoResponse> {
  return apiRequest<DeleteVideoResponse>(`/api/videos/${encodeURIComponent(videoId)}`, {
    method: 'DELETE',
  })
}
