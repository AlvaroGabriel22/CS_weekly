import { AlertTriangle, Lock, RefreshCw, WifiOff } from 'lucide-react'
import { parseApiError } from '@/lib/errors'
import { Button } from '@/components/ui/button'
import { defineMessages, useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { cn } from '@/lib/utils'

const M = defineMessages({
  offline: { pt: 'Sem conexão', en: 'No connection', ko: '연결 없음' },
})

export interface ErrorStateProps {
  /** Erro cru (axios ou não) — é normalizado via parseApiError. */
  error: unknown
  /** Quando presente, mostra o botão "Tentar novamente". */
  onRetry?: () => void
  /** Título opcional; há um padrão sensato por tipo de erro. */
  title?: string
  className?: string
}

/**
 * Estado de erro para queries (GET). Use no lugar do conteúdo da tela:
 *   if (isError) return <ErrorState error={error} onRetry={() => refetch()} />
 */
export function ErrorState({ error, onRetry, title, className }: ErrorStateProps) {
  const { t } = useI18n()
  const parsed = parseApiError(error)

  const isForbidden = parsed.kind === 'forbidden'
  const isNetwork = parsed.kind === 'network'

  const Icon = isForbidden ? Lock : isNetwork ? WifiOff : AlertTriangle
  const defaultTitle = isForbidden
    ? t(COMMON.noAccess)
    : isNetwork
      ? t(M.offline)
      : t(COMMON.error)

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-4 py-12 text-center animate-fade-in',
        className
      )}
    >
      <div
        className={cn(
          'mb-4 flex h-14 w-14 items-center justify-center rounded-full',
          isForbidden ? 'bg-amber-50' : 'bg-red-50'
        )}
      >
        <Icon
          className={cn('h-7 w-7', isForbidden ? 'text-amber-500' : 'text-red-500')}
          aria-hidden="true"
        />
      </div>
      <h3 className="text-base font-semibold text-gray-900">{title ?? defaultTitle}</h3>
      <p role="alert" className="mt-1.5 max-w-md text-sm text-gray-600">
        {parsed.message}
      </p>
      {onRetry && (
        <Button variant="outline" className="mt-5" onClick={onRetry}>
          <RefreshCw aria-hidden="true" />
          {t(COMMON.retry)}
        </Button>
      )}
    </div>
  )
}
