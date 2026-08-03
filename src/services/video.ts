import { apiRequest } from '@/services/api'

export interface VideoGenerationRequest {
  image_paths: string[]
  project_name?: string | null
  model_id?: string | null
  api_model?: string | null
  resolution?: string | null
  duration_seconds?: number | null
  estimated_credits?: number | null
}

export interface VideoGenerationResponse {
  success: boolean
  status: string
  task_id?: string | null
  prompt?: string | null
  message: string
  development_mode?: boolean
  generated_prompt?: string | null
  estimated_model?: string | null
  estimated_resolution?: string | null
  estimated_duration?: string | null
  estimated_credits?: number | null
}

export interface VideoStatusResponse {
  success: boolean
  task_id: string
  status: string
  stage: string
  progress: number
  prompt?: string | null
  video_url?: string | null
  thumbnail_url?: string | null
  created_at?: string | null
  duration?: string | null
  resolution?: string | null
  title?: string | null
  message?: string | null
  error_message?: string | null
}

export async function generateVideo(
  payload: VideoGenerationRequest,
): Promise<VideoGenerationResponse> {
  return apiRequest<VideoGenerationResponse>('/api/video/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getVideoStatus(taskId: string): Promise<VideoStatusResponse> {
  return apiRequest<VideoStatusResponse>(`/api/video/status/${encodeURIComponent(taskId)}`)
}
