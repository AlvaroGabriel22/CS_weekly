import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, Home, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { defineMessages, useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'

const M = defineMessages({
  reloadHint: { pt: 'Recarregue a página.', en: 'Reload the page.', ko: '페이지를 새로고침하세요.' },
  reload: { pt: 'Recarregar', en: 'Reload', ko: '새로고침' },
})

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
}

/** Fallback funcional (a classe não pode usar hooks de i18n). */
function BoundaryFallback() {
  const { t } = useI18n()
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-12 animate-fade-in">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-50">
          <AlertTriangle className="h-7 w-7 text-red-500" aria-hidden="true" />
        </div>
        <h2 className="text-lg font-semibold text-gray-900">{t(COMMON.error)}</h2>
        <p className="mt-2 text-sm text-gray-600">{t(M.reloadHint)}</p>
        <div className="mt-6 flex flex-col-reverse justify-center gap-2 sm:flex-row">
          <Button asChild variant="outline">
            <a href="/">
              <Home aria-hidden="true" />
              {t(COMMON.backToHome)}
            </a>
          </Button>
          <Button onClick={() => window.location.reload()}>
            <RotateCcw aria-hidden="true" />
            {t(M.reload)}
          </Button>
        </div>
      </div>
    </div>
  )
}

/**
 * Captura erros de renderização e mostra um fallback amigável no lugar da
 * tela quebrada. Envolva áreas de página — o App já envolve as rotas.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Log técnico apenas no console — nunca na UI.
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (!this.state.hasError) return this.props.children
    return <BoundaryFallback />
  }
}
