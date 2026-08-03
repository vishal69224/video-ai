import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { UploadedImage } from '@/types'

interface AppContextValue {
  images: UploadedImage[]
  setImages: (images: UploadedImage[]) => void
  addImages: (images: UploadedImage[]) => void
  removeImage: (id: string) => void
  clearImages: () => void
  projectName: string
  setProjectName: (name: string) => void
  activeTaskId: string | null
  setActiveTaskId: (taskId: string | null) => void
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [images, setImagesState] = useState<UploadedImage[]>([])
  const [projectName, setProjectName] = useState('')
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)

  const setImages = useCallback((next: UploadedImage[]) => {
    setImagesState((prev) => {
      prev.forEach((image) => {
        if (!next.find((item) => item.id === image.id)) {
          URL.revokeObjectURL(image.previewUrl)
        }
      })
      return next
    })
  }, [])

  const addImages = useCallback((incoming: UploadedImage[]) => {
    setImagesState((prev) => {
      const remaining = 10 - prev.length
      if (remaining <= 0) {
        incoming.forEach((image) => URL.revokeObjectURL(image.previewUrl))
        return prev
      }
      const accepted = incoming.slice(0, remaining)
      incoming.slice(remaining).forEach((image) => URL.revokeObjectURL(image.previewUrl))
      return [...prev, ...accepted]
    })
  }, [])

  const removeImage = useCallback((id: string) => {
    setImagesState((prev) => {
      const target = prev.find((image) => image.id === id)
      if (target) URL.revokeObjectURL(target.previewUrl)
      return prev.filter((image) => image.id !== id)
    })
  }, [])

  const clearImages = useCallback(() => {
    setImagesState((prev) => {
      prev.forEach((image) => URL.revokeObjectURL(image.previewUrl))
      return []
    })
  }, [])

  const value = useMemo(
    () => ({
      images,
      setImages,
      addImages,
      removeImage,
      clearImages,
      projectName,
      setProjectName,
      activeTaskId,
      setActiveTaskId,
    }),
    [
      images,
      setImages,
      addImages,
      removeImage,
      clearImages,
      projectName,
      activeTaskId,
    ],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}
