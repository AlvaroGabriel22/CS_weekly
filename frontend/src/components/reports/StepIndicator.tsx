import { Check } from 'lucide-react'
import { useI18n } from '@/i18n'
import { REPORTS } from '@/i18n/messages/reports'
import { cn } from '@/lib/utils'

export interface StepIndicatorProps {
  /** Rótulos dos passos, na ordem. */
  steps: string[]
  /** Índice (0-based) do passo atual. */
  current: number
  /** Clique em passos JÁ visitados volta para eles (os futuros ficam bloqueados). */
  onStepClick?: (index: number) => void
  className?: string
}

/** Stepper azul do fluxo de geração: círculos numerados + trilha de progresso. */
export function StepIndicator({ steps, current, onStepClick, className }: StepIndicatorProps) {
  const { t } = useI18n()
  return (
    <nav aria-label={t(REPORTS.stepsAria)} className={className}>
      <ol className="flex items-center">
        {steps.map((label, index) => {
          const done = index < current
          const active = index === current
          const clickable = done && Boolean(onStepClick)
          return (
            <li key={label} className={cn('flex items-center', index > 0 && 'flex-1')}>
              {index > 0 && (
                <span
                  aria-hidden="true"
                  className="relative mx-2 h-0.5 flex-1 overflow-hidden rounded-full bg-gray-200 sm:mx-3"
                >
                  <span
                    className={cn(
                      'absolute inset-0 origin-left rounded-full bg-brand transition-transform duration-500 ease-out',
                      index <= current ? 'scale-x-100' : 'scale-x-0'
                    )}
                  />
                </span>
              )}
              <button
                type="button"
                disabled={!clickable}
                onClick={() => clickable && onStepClick?.(index)}
                aria-current={active ? 'step' : undefined}
                aria-label={`${t(REPORTS.stepAria, { n: index + 1, label })}${done ? ` (${t(REPORTS.stepDone)})` : ''}`}
                className={cn(
                  'group flex min-h-[40px] items-center gap-2 rounded-lg px-1 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                  clickable ? 'cursor-pointer' : 'cursor-default'
                )}
              >
                <span
                  className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold transition-all duration-300',
                    active && 'bg-brand text-white shadow-sm ring-4 ring-brand/15',
                    done && 'bg-brand text-white group-hover:bg-brand-600',
                    !active && !done && 'border-2 border-gray-200 bg-white text-gray-400'
                  )}
                >
                  {done ? <Check className="h-4 w-4" aria-hidden="true" /> : index + 1}
                </span>
                <span
                  className={cn(
                    'hidden whitespace-nowrap text-sm sm:inline',
                    active ? 'font-semibold text-brand' : done ? 'font-medium text-gray-700' : 'text-gray-400'
                  )}
                >
                  {label}
                </span>
              </button>
            </li>
          )
        })}
      </ol>
      {/* Em telas pequenas os rótulos ficam ocultos — mostra o passo atual por extenso. */}
      <p className="mt-2 truncate text-sm font-medium text-brand sm:hidden">
        {t(REPORTS.stepOfTotal, { n: current + 1, total: steps.length })} · {steps[current]}
      </p>
    </nav>
  )
}
