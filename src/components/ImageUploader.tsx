import { AnimatePresence, motion } from 'framer-motion'
import { ImagePlus, UploadCloud } from 'lucide-react'
import { ImageCard } from '@/components/ImageCard'
import { UploadCounter } from '@/components/UploadCounter'
import { useImageUpload } from '@/hooks/useImageUpload'
import { cn } from '@/lib/utils'

export function ImageUploader({ disabled = false }: { disabled?: boolean }) {
  const { images, removeImage, getRootProps, getInputProps, isDragActive, maxImages } =
    useImageUpload({ disabled })

  return (
    <div className="space-y-5">
      <div
        {...getRootProps()}
        className={cn(
          'relative cursor-pointer overflow-hidden rounded-2xl border border-dashed bg-white/80 p-8 text-center shadow-soft transition duration-200 sm:p-12',
          isDragActive
            ? 'border-accent bg-accent-soft/40'
            : 'border-line hover:border-accent/40 hover:bg-white',
          (disabled || images.length >= maxImages) && 'cursor-not-allowed opacity-70',
        )}
      >
        <input {...getInputProps()} />
        <motion.div
          animate={isDragActive ? { scale: 1.02 } : { scale: 1 }}
          transition={{ duration: 0.2 }}
          className="mx-auto flex max-w-md flex-col items-center"
        >
          <span className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-soft text-accent">
            {isDragActive ? <UploadCloud className="h-7 w-7" /> : <ImagePlus className="h-7 w-7" />}
          </span>
          <h3 className="font-display text-xl font-semibold tracking-tight text-ink">
            {isDragActive ? 'Drop images to upload' : 'Drag & drop product images'}
          </h3>
          <p className="mt-2 text-sm leading-relaxed text-mute">
            or click to browse. PNG, JPG, JPEG, WEBP · 1–10 images
          </p>
        </motion.div>
      </div>

      <UploadCounter count={images.length} max={maxImages} />

      <AnimatePresence mode="popLayout">
        {images.length > 0 ? (
          <motion.div
            layout
            className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
          >
            {images.map((image, index) => (
              <ImageCard
                key={image.id}
                image={image}
                onRemove={removeImage}
                disableRemove={disabled}
                isPrimary={index === 0}
                index={index}
              />
            ))}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
