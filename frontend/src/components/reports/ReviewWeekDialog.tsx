import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  Loader2,
  RotateCcw,
  Sparkles,
  Star,
  TrendingDown,
  X,
} from 'lucide-react'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { REPORTS } from '@/i18n/messages/reports'
import type { WeekRef } from '@/lib/dates'
import { parseApiError } from '@/lib/errors'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useReviewWeek, type ReviewSuggestionType } from '@/hooks/useAi'
import type { Msg } from '@/i18n'

export interface ReviewWeekDialogProps {
  open: boolean
  onClose: () => void
  week: WeekRef
  activityIds: string[]
}

/** Aparência por tipo de sugestão — cores dentro da paleta azul da marca. */
const TYPE_STYLES: Record<
  ReviewSuggestionType,
  { icon: typeof Star; label: Msg; wrap: string; iconBox: string; iconColor: string }
> = {
  highlight: {
    icon: Star,
    label: REPORTS.reviewTypeHighlight,
    wrap: 'border-brand/20 bg-brand/[0.04]',
    iconBox: 'bg-brand/10',
    iconColor: 'text-brand',
  },
  gap: {
    icon: AlertCircle,
    label: REPORTS.reviewTypeGap,
    wrap: 'border-amber-200 bg-amber-50',
    iconBox: 'bg-amber-100',
    iconColor: 'text-amber-600',
  },
  anomaly: {
    icon: TrendingDown,
    label: REPORTS.reviewTypeAnomaly,
    wrap: 'border-orange-200 bg-orange-50',
    iconBox: 'bg-orange-100',
    iconColor: 'text-orange-600',
  },
  inconsistency: {
    icon: AlertTriangle,
    label: REPORTS.reviewTypeInconsistency,
    wrap: 'border-red-200 bg-red-50',
    iconBox: 'bg-red-100',
    iconColor: 'text-red-600',
  },
}

/** Painel "Revisar com IA": conselho ancorado no padrão do usuário; não altera nada. */
export function ReviewWeekDialog({ open, onClose, week, activityIds }: ReviewWeekDialogProps) {
  const { t } = useI18n()
  const review = useReviewWeek()
  const [dismissed, setDismissed] = useState<Set<number>>(new Set())

  // Ao abrir: dispara a revisão. Reabrir = nova revisão (limpa dispensados).
  useEffect(() => {
    if (!open) return
    setDismissed(new Set())
    review.mutate({ ref: week, activityIds })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const suggestions = review.data?.suggestions ?? []
  const visible = useMemo(
    () => suggestions.map((s, i) => ({ s, i })).filter(({ i }) => !dismissed.has(i)),
    [suggestions, dismissed]
  )

  const retry = () => {
    setDismissed(new Set())
    review.mutate({ ref: week, activityIds })
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-brand" aria-hidden="true" />
            {t(REPORTS.reviewTitle)}
          </DialogTitle>
        </DialogHeader>

        <div className="max-h-[60vh] min-h-[8rem] overflow-y-auto">
          {review.isPending ? (
            <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
              <Loader2 className="h-7 w-7 animate-spin text-brand" aria-hidden="true" />
              <p className="max-w-xs text-sm text-gray-600" aria-live="polite">
                {t(REPORTS.reviewLoading)}
              </p>
            </div>
          ) : review.isError ? (
            <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-red-100">
                <AlertTriangle className="h-6 w-6 text-red-600" aria-hidden="true" />
              </div>
              <p className="max-w-sm text-sm text-gray-700" role="alert">
                {parseApiError(review.error).message}
              </p>
              <Button variant="outline" size="sm" onClick={retry}>
                <RotateCcw aria-hidden="true" />
                {t(REPORTS.reviewRetry)}
              </Button>
            </div>
          ) : visible.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-brand/10">
                <Sparkles className="h-6 w-6 text-brand" aria-hidden="true" />
              </div>
              <p className="max-w-xs text-sm text-gray-600">{t(REPORTS.reviewEmpty)}</p>
            </div>
          ) : (
            <ul className="space-y-2.5 py-1">
              {visible.map(({ s, i }) => {
                const style = TYPE_STYLES[s.type] ?? TYPE_STYLES.gap
                const Icon = style.icon
                return (
                  <li
                    key={i}
                    className={`flex items-start gap-3 rounded-xl border p-3 ${style.wrap}`}
                  >
                    <span
                      className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${style.iconBox}`}
                    >
                      <Icon className={`h-4 w-4 ${style.iconColor}`} aria-hidden="true" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-gray-900">{t(style.label)}</p>
                      <p className="mt-0.5 break-words text-sm text-gray-700">{s.message}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setDismissed((prev) => new Set(prev).add(i))}
                      className="-mr-1 -mt-1 shrink-0 rounded-md p-1 text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-ring"
                      aria-label={t(REPORTS.reviewDismiss)}
                      title={t(REPORTS.reviewDismiss)}
                    >
                      <X className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        <DialogFooter className="sm:items-center sm:justify-between">
          <p className="flex items-center gap-1.5 text-xs text-gray-500">
            <Sparkles className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
            {t(REPORTS.reviewFooter)}
          </p>
          <Button variant="outline" onClick={onClose}>
            {t(COMMON.close)}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
