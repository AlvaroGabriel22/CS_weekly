/**
 * Contexto do guia de primeiro acesso.
 *
 * Separado do Tour.tsx de propósito: o Fast Refresh do Vite exige que módulos
 * de componentes exportem SOMENTE componentes — exportar o hook `useTour` no
 * mesmo arquivo invalidava o módulo a cada edição e derrubava o TopBar (o
 * botão de rever o guia "sumia" até um reload completo).
 */
import { createContext, useContext } from 'react'

export interface TourContextType {
  /** Inicia o tour. mandatory = primeiro acesso (sem fechar/pular). */
  start: (mandatory: boolean) => void
  active: boolean
}

export const TourContext = createContext<TourContextType | null>(null)

export function useTour(): TourContextType {
  const ctx = useContext(TourContext)
  if (!ctx) throw new Error('useTour must be used within TourProvider')
  return ctx
}
