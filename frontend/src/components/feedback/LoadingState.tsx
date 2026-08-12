import { Loader2 } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { cn } from '@/lib/utils'

export interface LoadingStateProps {
  /** Texto opcional abaixo do spinner (ex.: "Gerando…"). */
  text?: string
  className?: string
}

/** Spinner centralizado — para carregamentos pontuais (modais, ações). */
export function LoadingState({ text, className }: LoadingStateProps) {
  const { t } = useI18n()
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn('flex flex-col items-center justify-center gap-3 px-4 py-12', className)}
    >
      <Loader2 className="h-7 w-7 animate-spin text-brand" aria-hidden="true" />
      <p className="text-sm text-gray-600">{text ?? t(COMMON.loading)}</p>
    </div>
  )
}

/** Skeleton de página inteira: header + 3 cartões. Use no loading de queries. */
export function PageSkeleton() {
  const { t } = useI18n()
  return (
    <div role="status" aria-label={t(COMMON.loading)} className="animate-fade-in">
      {/* Header da página */}
      <div className="mb-6 space-y-2">
        <Skeleton className="h-7 w-56 max-w-full" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </div>
      {/* 3 cartões */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className="rounded-xl border border-border/60 bg-white p-6 shadow-card"
          >
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 shrink-0 rounded-full" />
              <div className="min-w-0 flex-1 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            </div>
            <div className="mt-5 space-y-2">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-5/6" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
