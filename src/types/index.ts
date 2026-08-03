export interface UploadedImage {
  id: string
  file: File
  previewUrl: string
  name: string
  size: number
}

export type GenerationStepStatus = 'pending' | 'active' | 'completed'

export interface GenerationStep {
  id: string
  label: string
  status: GenerationStepStatus
}

export interface LibraryVideo {
  id: string
  title: string
  createdAt: string
  duration: string
  resolution: string
  thumbnail: string
  videoUrl: string
  prompt: string
  status: string
  taskId: string
}

export type AppPage = 'landing' | 'generator' | 'progress' | 'library'

export type GeneratorPhase =
  | 'idle'
  | 'uploading'
  | 'generating_prompt'
  | 'submitting_to_ai'
  | 'processing'
