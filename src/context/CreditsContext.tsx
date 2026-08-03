import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { ApiError } from '@/services/api'
import { fetchCredits } from '@/services/credits'

interface CreditsContextValue {
  credits: number | null
  loading: boolean
  error: string | null
  refresh: (force?: boolean) => Promise<void>
}

const CreditsContext = createContext<CreditsContextValue | null>(null)

export function CreditsProvider({ children }: { children: ReactNode }) {
  const [credits, setCredits] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async (force = false) => {
    setLoading(true)
    try {
      const response = await fetchCredits({ force })
      setCredits(response.credits)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load credits')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh(false)
    const timer = window.setInterval(() => {
      void refresh(false)
    }, 60_000)
    return () => window.clearInterval(timer)
  }, [refresh])

  const value = useMemo(
    () => ({ credits, loading, error, refresh }),
    [credits, loading, error, refresh],
  )

  return <CreditsContext.Provider value={value}>{children}</CreditsContext.Provider>
}

export function useCredits() {
  const context = useContext(CreditsContext)
  if (!context) {
    throw new Error('useCredits must be used within CreditsProvider')
  }
  return context
}
