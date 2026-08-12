import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type PageMaxWidth = '3xl' | '4xl' | '5xl' | '6xl' | '7xl' | 'full'

const maxWidthClasses: Record<PageMaxWidth, string> = {
  '3xl': 'max-w-3xl',
  '4xl': 'max-w-4xl',
  '5xl': 'max-w-5xl',
  '6xl': 'max-w-6xl',
  '7xl': 'max-w-7xl',
  full: 'max-w-none',
}

export interface PageContainerProps {
  title: string
  description?: string
  /** Botões/ações alinhados à direita do título. */
  actions?: ReactNode
  /** Largura máxima do conteúdo (padrão: 6xl). */
  maxWidth?: PageMaxWidth
  className?: string
  children: ReactNode
}

/** Container padrão de página: centralizado, com header (título + ações). */
export function PageContainer({
  title,
  description,
  actions,
  maxWidth = '6xl',
  className,
  children,
}: PageContainerProps) {
  return (
    <div
      className={cn(
        'mx-auto w-full px-4 py-6 sm:px-6 sm:py-8',
        maxWidthClasses[maxWidth],
        className
      )}
    >
      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">{title}</h1>
          {description && <p className="mt-1 text-sm text-gray-600">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
      </header>
      {children}
    </div>
  )
}
