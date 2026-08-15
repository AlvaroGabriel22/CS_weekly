import type { ReactNode } from 'react'
import { TopBar } from './TopBar'
import { Toaster } from '@/components/ui/toast'
import { TourAutoStart, TourProvider } from '@/components/tour/Tour'

/**
 * Casca padrão das telas autenticadas: topbar fixa + conteúdo + toasts.
 * A TopBar é sticky (ocupa espaço no fluxo), então o main não precisa de
 * padding-top extra — o conteúdo nunca fica escondido atrás dela.
 * O TourProvider habilita o guia de primeiro acesso (spotlight) em toda a área
 * autenticada; TourAutoStart dispara o guia obrigatório quando a flag do
 * backend indicar que o usuário nunca o concluiu.
 */
export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <TourProvider>
      <div className="flex min-h-screen flex-col bg-gray-50">
        <TopBar />
        <main className="flex-1 animate-fade-in">{children}</main>
        <Toaster />
      </div>
      <TourAutoStart />
    </TourProvider>
  )
}
