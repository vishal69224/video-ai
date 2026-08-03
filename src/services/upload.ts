import { apiRequest } from '@/services/api'

export interface UploadedFileInfo {
  filename: string
  url: string
  original_filename?: string | null
  size?: number | null
  content_type?: string | null
}

export interface UploadResponse {
  success: boolean
  message: string
  files: UploadedFileInfo[]
}

export async function uploadImages(files: File[]): Promise<UploadResponse> {
  const formData = new FormData()
  files.forEach((file) => {
    formData.append('files', file)
  })

  return apiRequest<UploadResponse>('/api/upload', {
    method: 'POST',
    body: formData,
  })
}
