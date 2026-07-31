import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { GalleryPreview } from '@/components/GalleryPreview'
import { GalleryThumbnails } from '@/components/GalleryThumbnails'
import {
  fashionReferenceAngles,
  preloadHeroGalleryImages,
  type HeroGalleryImage,
} from '@/data/heroGalleryData'

const ROTATE_MS = 4000

export function HeroGallery() {
  const angles = useMemo(() => fashionReferenceAngles, [])
  const [activeIndex, setActiveIndex] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const indexRef = useRef(0)

  const activeImage = angles[activeIndex] ?? angles[0]

  const clearRotation = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const startRotation = useCallback(() => {
    clearRotation()
    intervalRef.current = setInterval(() => {
      indexRef.current = (indexRef.current + 1) % angles.length
      setActiveIndex(indexRef.current)
    }, ROTATE_MS)
  }, [angles.length, clearRotation])

  useEffect(() => {
    preloadHeroGalleryImages()
  }, [])

  useEffect(() => {
    startRotation()
    return clearRotation
  }, [startRotation, clearRotation])

  const handleSelect = useCallback(
    (image: HeroGalleryImage) => {
      const nextIndex = angles.findIndex((angle) => angle.id === image.id)
      if (nextIndex < 0) return
      indexRef.current = nextIndex
      setActiveIndex(nextIndex)
      startRotation()
    },
    [angles, startRotation],
  )

  if (!activeImage) return null

  return (
    <div className="relative w-full">
      <div className="grid h-[22rem] w-full grid-cols-[minmax(0,1fr)_5.75rem] gap-3 sm:h-[28rem] sm:grid-cols-[minmax(0,1fr)_7rem] sm:gap-3.5 md:h-[32rem] lg:h-[34rem] lg:grid-cols-[minmax(0,1fr)_8rem] xl:h-[36rem]">
        <div className="min-h-0 min-w-0">
          <GalleryPreview image={activeImage} title="Fashion Model" />
        </div>

        <div className="min-h-0 min-w-0">
          <GalleryThumbnails
            images={angles}
            activeId={activeImage.id}
            onSelect={handleSelect}
          />
        </div>
      </div>
    </div>
  )
}
