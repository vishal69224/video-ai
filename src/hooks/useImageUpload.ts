import { useCallback, useMemo } from 'react'
import { useDropzone, type Accept, type FileRejection } from 'react-dropzone'
import { useApp } from '@/context/AppContext'
import type { UploadedImage } from '@/types'

const ACCEPT: Accept = {
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/webp': ['.webp'],
}

const MAX_IMAGES = 10

function createUploadedImage(file: File): UploadedImage {
  return {
    id: crypto.randomUUID(),
    file,
    previewUrl: URL.createObjectURL(file),
    name: file.name,
    size: file.size,
  }
}

export function useImageUpload(options?: { disabled?: boolean }) {
  const { images, addImages, removeImage } = useApp()
  const disabled = Boolean(options?.disabled)

  const onDrop = useCallback(
    (acceptedFiles: File[], _rejections: FileRejection[]) => {
      if (disabled || !acceptedFiles.length) return
      addImages(acceptedFiles.map(createUploadedImage))
    },
    [addImages, disabled],
  )

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: ACCEPT,
    multiple: true,
    maxFiles: MAX_IMAGES,
    noClick: false,
    noKeyboard: false,
    disabled: disabled || images.length >= MAX_IMAGES,
  })

  const canGenerate = images.length >= 1
  const remainingSlots = Math.max(0, MAX_IMAGES - images.length)

  const counterLabel = useMemo(
    () => `${images.length} / ${MAX_IMAGES} Images Uploaded`,
    [images.length],
  )

  return {
    images,
    removeImage,
    getRootProps,
    getInputProps,
    isDragActive,
    open,
    canGenerate,
    remainingSlots,
    counterLabel,
    maxImages: MAX_IMAGES,
  }
}
