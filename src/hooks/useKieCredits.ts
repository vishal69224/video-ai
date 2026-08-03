import { useCredits } from '@/context/CreditsContext'

/** Shared live Kie.ai credits from CreditsProvider. */
export function useKieCredits(_pollMs = 60_000) {
  return useCredits()
}
