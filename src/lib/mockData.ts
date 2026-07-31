import type { LibraryVideo } from '@/types'

export const MOCK_VIDEOS: LibraryVideo[] = [
  {
    id: 'vid-1',
    title: 'Ceramic Vase — Soft Orbit',
    createdAt: '2026-07-28T14:20:00.000Z',
    duration: '0:08',
    resolution: '1080 × 1920',
    thumbnail:
      'data:image/svg+xml;utf8,' +
      encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="640" height="800" viewBox="0 0 640 800" fill="none">
          <defs>
            <linearGradient id="g" x1="80" y1="40" x2="560" y2="760" gradientUnits="userSpaceOnUse">
              <stop stop-color="#D1FAE5"/>
              <stop offset="0.45" stop-color="#99F6E4"/>
              <stop offset="1" stop-color="#CBD5E1"/>
            </linearGradient>
          </defs>
          <rect width="640" height="800" fill="url(#g)"/>
          <ellipse cx="320" cy="470" rx="120" ry="28" fill="#0B1220" opacity="0.08"/>
          <path d="M250 250c0-40 30-70 70-70s70 30 70 70c0 18-6 34-16 48l-18 172h-72l-18-172c-10-14-16-30-16-48z" fill="#F8FAFC" opacity="0.92"/>
          <rect x="278" y="470" width="84" height="18" rx="9" fill="#F8FAFC" opacity="0.7"/>
        </svg>
      `),
  },
  {
    id: 'vid-2',
    title: 'Minimal Watch — Studio Pan',
    createdAt: '2026-07-26T09:05:00.000Z',
    duration: '0:12',
    resolution: '1920 × 1080',
    thumbnail:
      'data:image/svg+xml;utf8,' +
      encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400" fill="none">
          <defs>
            <linearGradient id="g" x1="0" y1="0" x2="640" y2="400" gradientUnits="userSpaceOnUse">
              <stop stop-color="#E2E8F0"/>
              <stop offset="0.5" stop-color="#F1F5F9"/>
              <stop offset="1" stop-color="#99F6E4"/>
            </linearGradient>
          </defs>
          <rect width="640" height="400" fill="url(#g)"/>
          <circle cx="320" cy="200" r="78" fill="#0B1220" opacity="0.88"/>
          <circle cx="320" cy="200" r="62" fill="#F8FAFC"/>
          <circle cx="320" cy="200" r="4" fill="#0B1220"/>
          <rect x="318" y="150" width="4" height="42" rx="2" fill="#0B1220"/>
          <rect x="318" y="196" width="34" height="4" rx="2" fill="#0F766E"/>
        </svg>
      `),
  },
  {
    id: 'vid-3',
    title: 'Leather Bag — Hero Reveal',
    createdAt: '2026-07-22T18:40:00.000Z',
    duration: '0:10',
    resolution: '1080 × 1080',
    thumbnail:
      'data:image/svg+xml;utf8,' +
      encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640" fill="none">
          <defs>
            <linearGradient id="g" x1="80" y1="40" x2="600" y2="600" gradientUnits="userSpaceOnUse">
              <stop stop-color="#CBD5E1"/>
              <stop offset="0.55" stop-color="#94A3B8"/>
              <stop offset="1" stop-color="#134E4A"/>
            </linearGradient>
          </defs>
          <rect width="640" height="640" fill="url(#g)"/>
          <rect x="190" y="230" width="260" height="190" rx="28" fill="#0B1220" opacity="0.78"/>
          <rect x="250" y="200" width="140" height="50" rx="18" fill="#0B1220" opacity="0.55"/>
          <rect x="220" y="280" width="200" height="16" rx="8" fill="#F8FAFC" opacity="0.2"/>
        </svg>
      `),
  },
  {
    id: 'vid-4',
    title: 'Skincare Set — Clean Motion',
    createdAt: '2026-07-18T11:15:00.000Z',
    duration: '0:09',
    resolution: '1080 × 1920',
    thumbnail:
      'data:image/svg+xml;utf8,' +
      encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="640" height="800" viewBox="0 0 640 800" fill="none">
          <defs>
            <linearGradient id="g" x1="100" y1="0" x2="540" y2="800" gradientUnits="userSpaceOnUse">
              <stop stop-color="#ECFEFF"/>
              <stop offset="0.4" stop-color="#CCFBF1"/>
              <stop offset="1" stop-color="#E2E8F0"/>
            </linearGradient>
          </defs>
          <rect width="640" height="800" fill="url(#g)"/>
          <rect x="250" y="220" width="140" height="280" rx="36" fill="#F8FAFC" opacity="0.95"/>
          <rect x="270" y="250" width="100" height="40" rx="12" fill="#0F766E" opacity="0.15"/>
          <circle cx="320" cy="420" r="18" fill="#0F766E" opacity="0.35"/>
          <ellipse cx="320" cy="540" rx="90" ry="18" fill="#0B1220" opacity="0.06"/>
        </svg>
      `),
  },
  {
    id: 'vid-5',
    title: 'Sneaker Drop — Dynamic Orbit',
    createdAt: '2026-07-12T16:50:00.000Z',
    duration: '0:11',
    resolution: '1920 × 1080',
    thumbnail:
      'data:image/svg+xml;utf8,' +
      encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400" fill="none">
          <defs>
            <linearGradient id="g" x1="0" y1="40" x2="640" y2="360" gradientUnits="userSpaceOnUse">
              <stop stop-color="#0F766E"/>
              <stop offset="0.45" stop-color="#334155"/>
              <stop offset="1" stop-color="#0B1220"/>
            </linearGradient>
          </defs>
          <rect width="640" height="400" fill="url(#g)"/>
          <path d="M160 250c40-60 100-90 180-90s140 30 180 90c-28 20-80 40-180 40s-152-20-180-40z" fill="#F8FAFC" opacity="0.9"/>
          <path d="M220 250h240" stroke="#0B1220" stroke-opacity="0.2" stroke-width="6" stroke-linecap="round"/>
        </svg>
      `),
  },
  {
    id: 'vid-6',
    title: 'Perfume Bottle — Light Sweep',
    createdAt: '2026-07-08T08:30:00.000Z',
    duration: '0:07',
    resolution: '1080 × 1920',
    thumbnail:
      'data:image/svg+xml;utf8,' +
      encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="640" height="800" viewBox="0 0 640 800" fill="none">
          <defs>
            <linearGradient id="g" x1="120" y1="0" x2="520" y2="800" gradientUnits="userSpaceOnUse">
              <stop stop-color="#F8FAFC"/>
              <stop offset="0.5" stop-color="#E2E8F0"/>
              <stop offset="1" stop-color="#99F6E4"/>
            </linearGradient>
          </defs>
          <rect width="640" height="800" fill="url(#g)"/>
          <rect x="270" y="180" width="100" height="40" rx="10" fill="#0B1220" opacity="0.75"/>
          <rect x="245" y="220" width="150" height="280" rx="24" fill="#F8FAFC" opacity="0.85"/>
          <rect x="265" y="250" width="110" height="180" rx="16" fill="#0F766E" opacity="0.12"/>
          <ellipse cx="320" cy="560" rx="80" ry="16" fill="#0B1220" opacity="0.06"/>
        </svg>
      `),
  },
]

export const GENERATION_STEP_LABELS = [
  'Uploading Images',
  'Analyzing Images',
  'Understanding Object',
  'Generating AI Prompt',
  'Sending Request',
  'Rendering Video',
  'Finalizing',
  'Completed',
] as const

export const STEP_DURATIONS_MS = [1200, 1600, 1400, 1800, 1200, 2400, 1400, 900]
