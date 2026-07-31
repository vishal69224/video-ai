import frontView from '@/assets/hero/fashion/front.avif'
import sideView from '@/assets/hero/fashion/side.avif'
import backView from '@/assets/hero/fashion/back.avif'
import threeQuarterView from '@/assets/hero/fashion/three-quarter.avif'

export interface HeroGalleryImage {
  id: string
  src: string
  label: string
  shortLabel: string
}

/** Four reference angles of the same clothing model — Home hero only. */
export const fashionReferenceAngles: HeroGalleryImage[] = [
  {
    id: 'front',
    src: frontView,
    label: 'Front View',
    shortLabel: 'Front',
  },
  {
    id: 'side',
    src: sideView,
    label: 'Side View',
    shortLabel: 'Side',
  },
  {
    id: 'back',
    src: backView,
    label: 'Back View',
    shortLabel: 'Back',
  },
  {
    id: 'three-quarter',
    src: threeQuarterView,
    label: '3/4 View',
    shortLabel: '3/4',
  },
]

export function preloadHeroGalleryImages(): void {
  if (typeof window === 'undefined') return

  for (const angle of fashionReferenceAngles) {
    const img = new Image()
    img.decoding = 'async'
    img.src = angle.src
  }
}
