import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { AppProvider } from '@/context/AppContext'
import { CreditsProvider } from '@/context/CreditsContext'
import { GenerationProgressPage } from '@/pages/GenerationProgressPage'
import { LandingPage } from '@/pages/LandingPage'
import { VideoGeneratorPage } from '@/pages/VideoGeneratorPage'
import { VideoLibraryPage } from '@/pages/VideoLibraryPage'

export default function App() {
  return (
    <AppProvider>
      <CreditsProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<LandingPage />} />
              <Route path="generate" element={<VideoGeneratorPage />} />
              <Route path="progress" element={<GenerationProgressPage />} />
              <Route path="library" element={<VideoLibraryPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </CreditsProvider>
    </AppProvider>
  )
}
