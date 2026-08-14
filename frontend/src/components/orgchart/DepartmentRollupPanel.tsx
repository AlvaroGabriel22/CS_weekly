/**
 * Copiloto do gestor — "weekly do departamento" (IA, opcional).
 *
 * Diálogo com navegação de semanas: mostra o resumo cacheado (se existir) e
 * permite gerar/regenerar. A geração pode levar minutos no modelo local —
 * o progresso fica visível e nada é bloqueado.
 */
import { useState } from 'react'
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ListChecks,
  Loader2,
  RefreshCw,
  Sparkles,
  Star,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { addWeeks, currentWeekRef, weekLabel, weekRangeLabel, type WeekRef } from '@/lib/dates'
import { parseApiError } from '@/lib/errors'
import { useDepartmentRollup, useGenerateRollup, type RollupContent } from '@/hooks/useAi'
import { useI18n } from '@/i18n'
import { ORG } from '@/i18n/messages/org'

function Section({
  icon: Icon,
  title,
  children,
  tone = 'default',
}: {
  icon: typeof Sparkles
  title: string
  children: React.ReactNode
  tone?: 'default' | 'risk'
}) {
  return (
    <section>
      <h3
        className={`flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide ${
          tone === 'risk' ? 'text-amber-600' : 'text-gray-500'
        }`}
      >
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {title}
      </h3>
      <div className="mt-2">{children}</div>
    </section>
  )
}

function RollupBody({ content }: { content: RollupContent }) {
  const { t } = useI18n()
  return (
    <div className="space-y-5">
      {content.summary && (
        <p className="rounded-lg bg-brand-50/60 p-3 text-sm leading-relaxed text-gray-800">
          {content.summary}
        </p>
      )}

      {content.highlights.length > 0 && (
        <Section icon={Star} title={t(ORG.rollupHighlights)}>
          <ul className="space-y-1.5">
            {content.highlights.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {content.kpis.length > 0 && (
        <Section icon={BarChart3} title={t(ORG.rollupKpis)}>
          <div className="flex flex-wrap gap-2">
            {content.kpis.map((kpi, i) => (
              <span
                key={i}
                className="rounded-lg border border-brand-200 bg-white px-2.5 py-1 text-sm font-medium text-brand"
              >
                {kpi}
              </span>
            ))}
          </div>
        </Section>
      )}

      {content.risks.length > 0 && (
        <Section icon={AlertTriangle} title={t(ORG.rollupRisks)} tone="risk">
          <ul className="space-y-1.5">
            {content.risks.map((risk, i) => (
              <li
                key={i}
                className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
              >
                {risk}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {content.by_person.length > 0 && (
        <Section icon={CheckCircle2} title={t(ORG.rollupTeam)}>
          <div className="grid gap-2 sm:grid-cols-2">
            {content.by_person.map(person => (
              <div key={person.name} className="min-w-0 rounded-lg border border-border/60 bg-white p-3">
                <div className="flex flex-wrap items-center justify-between gap-1">
                  <p className="truncate text-sm font-semibold text-gray-900">{person.name}</p>
                  <span
                    className={`shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium ${
                      person.has_weekly
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {person.has_weekly ? t(ORG.rollupHasWeekly) : t(ORG.rollupNoWeekly)}
                  </span>
                </div>
                <p className="text-xs text-gray-500">{person.role}</p>
                <p className="mt-1.5 break-words text-sm text-gray-700">{person.headline}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {content.next_steps.length > 0 && (
        <Section icon={ListChecks} title={t(ORG.rollupNextSteps)}>
          <ol className="space-y-1.5">
            {content.next_steps.map((step, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-50 text-[11px] font-semibold text-brand">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </Section>
      )}
    </div>
  )
}

export interface DepartmentRollupPanelProps {
  sector: string
  open: boolean
  onClose: () => void
}

export function DepartmentRollupPanel({ sector, open, onClose }: DepartmentRollupPanelProps) {
  const { t, locale } = useI18n()
  const { toast } = useToast()
  const [week, setWeek] = useState<WeekRef>(() => currentWeekRef())

  const query = useDepartmentRollup(sector, week, open)
  const generate = useGenerateRollup(sector, week)

  const runGenerate = (force: boolean) => {
    generate.mutate(
      { force },
      { onError: err => toast.error(parseApiError(err).message) }
    )
  }

  const content = query.data?.content ?? null
  const generatedAt = query.data?.generated_at
    ? new Date(query.data.generated_at).toLocaleDateString(locale, {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
      })
    : null

  return (
    <Dialog open={open} onOpenChange={value => !value && onClose()}>
      <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-brand" aria-hidden />
            {t(ORG.rollupTitle)} · {sector}
          </DialogTitle>
        </DialogHeader>

        {/* Navegação de semanas */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setWeek(w => addWeeks(w, -1))}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100"
              aria-label={t(ORG.rollupTitle)}
            >
              <ChevronLeft className="h-4 w-4" aria-hidden />
            </button>
            <span className="min-w-40 text-center text-sm font-semibold text-gray-900">
              {weekLabel(week)} · {weekRangeLabel(week)}
            </span>
            <button
              type="button"
              onClick={() => setWeek(w => addWeeks(w, 1))}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100"
              aria-label={t(ORG.rollupTitle)}
            >
              <ChevronRight className="h-4 w-4" aria-hidden />
            </button>
          </div>

          {content && !generate.isPending && (
            <Button size="sm" variant="outline" onClick={() => runGenerate(true)}>
              <RefreshCw aria-hidden />
              {t(ORG.rollupRegenerate)}
            </Button>
          )}
        </div>

        {/* Corpo */}
        {generate.isPending ? (
          <div className="rounded-xl border border-brand/20 bg-brand/[0.03] p-8 text-center">
            <Loader2 className="mx-auto h-7 w-7 animate-spin text-brand" aria-hidden />
            <p className="mt-3 text-sm font-semibold text-brand" aria-live="polite">
              {t(ORG.rollupGenerating)}
            </p>
            <p className="mt-1 text-xs text-gray-500">{t(ORG.rollupGeneratingHint)}</p>
          </div>
        ) : query.isLoading ? (
          <div className="space-y-3" role="status">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : content ? (
          <>
            <RollupBody content={content} />
            {generatedAt && (
              <p className="text-right text-xs text-gray-400">
                {t(ORG.rollupGeneratedAt, { date: generatedAt })}
              </p>
            )}
          </>
        ) : (
          <div className="rounded-xl border border-dashed border-border p-8 text-center">
            <p className="text-sm font-medium text-gray-600">{t(ORG.rollupEmpty)}</p>
            <Button className="mt-4" onClick={() => runGenerate(false)}>
              <Sparkles aria-hidden />
              {t(ORG.rollupGenerate)}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
