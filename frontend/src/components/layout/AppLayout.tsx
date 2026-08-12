import type { ReactNode } from 'react'
import { TopBar } from './TopBar'
import { Toaster } from '@/components/ui/toast'

/**
 * Casca padrão das telas autenticadas: topbar fixa + conteúdo + toasts.
 * A TopBar é sticky (ocupa espaço no fluxo), então o main não precisa de
 * padding-top extra — o conteúdo nunca fica escondido atrás dela.
 */
export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <TopBar />
      <main className="flex-1 animate-fade-in">{children}</main>
      <Toaster />
    </div>
  )
}
