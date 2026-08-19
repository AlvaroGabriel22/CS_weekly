/**
 * Card "O que a IA já aprendeu sobre você" — tom pessoal, não formulário.
 * Mostra os KPIs e padrões (entidades) que a IA extraiu do histórico do
 * usuário; cada item é um chip removível que, ao ser descartado, ensina a IA
 * que aquilo não é acompanhado. Vazio = estado de onboarding gentil.
 */
import { Loader2, Sparkles, X } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/feedback'
import { useToast } from '@/components/ui/toast'
import { parseApiError } from '@/lib/errors'
import { useI18n, type Msg } from '@/i18n'
import { PROFILE as M } from '@/i18n/messages/profile'
import {
  useIgnoreKnowledge,
  useKnowledge,
  type IgnoreKnowledgePayload,
} from '@/hooks/useKnowledge'

/** Rótulo traduzido para cada campo de entidade conhecido. */
const ENTITY_LABEL: Record<string, Msg> = {
  line: M.entityLine,
  supplier: M.entitySupplier,
  process: M.entityProcess,
  product: M.entityProduct,
  defect_type: M.entityDefectType,
}

/** Chip removível com "x". */
function KnowledgeChip({
  label,
  ariaLabel,
  busy,
  disabled,
  onDismiss,
}: {
  label: string
  ariaLabel: string
  busy: boolean
  disabled: boolean
  onDismiss: () => void
}) {
  return (
    <span className="inline-flex max-w-full items-center gap-1 rounded-full bg-brand-50 py-0.5 pl-2.5 pr-1 text-xs font-medium text-brand-700 transition-colors duration-200">
      <span className="min-w-0 truncate">{label}</span>
      <button
        type="button"
        onClick={onDismiss}
        disabled={disabled}
        aria-label={ariaLabel}
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-brand-500 transition-colors duration-200 hover:bg-brand-100 hover:text-brand-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand disabled:opacity-50"
      >
        {busy ? (
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
        ) : (
          <X className="h-3 w-3" aria-hidden="true" />
        )}
      </button>
    </span>
  )
}

export function KnowledgeCard() {
  const { t } = useI18n()
  const { toast } = useToast()
  const { data, isLoading, isError, error, refetch } = useKnowledge()
  const ignore = useIgnoreKnowledge()

  const busyFor = (payload: IgnoreKnowledgePayload) =>
    ignore.isPending &&
    ignore.variables?.kind === payload.kind &&
    ignore.variables?.value === payload.value &&
    ignore.variables?.entity_field === payload.entity_field

  const handleDismiss = (payload: IgnoreKnowledgePayload) => {
    ignore.mutate(payload, {
      onError: (err) => toast.error(parseApiError(err).message),
    })
  }

  const renderBody = () => {
    if (isError) return <ErrorState error={error} onRetry={() => refetch()} />
    if (isLoading || !data) {
      return (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-4 w-32" />
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-6 w-20 rounded-full" />
            ))}
          </div>
        </div>
      )
    }

    const kpis = data.learned.kpis ?? []
    const entityGroups = Object.entries(data.learned.entities ?? {}).filter(
      ([, values]) => Array.isArray(values) && values.length > 0
    )
    const hasLearned = kpis.length > 0 || entityGroups.length > 0

    if (!hasLearned) {
      return (
        <p className="rounded-lg border border-blue-100 bg-blue-50/60 p-4 text-sm text-blue-800">
          {t(M.knowledgeEmpty)}
        </p>
      )
    }

    return (
      <div className="space-y-5">
        {kpis.length > 0 && (
          <section className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              {t(M.knowledgeKpis)}
            </h4>
            <div className="flex flex-wrap gap-2">
              {kpis.map((value) => {
                const payload: IgnoreKnowledgePayload = { kind: 'kpi', value }
                return (
                  <KnowledgeChip
                    key={`kpi-${value}`}
                    label={value}
                    ariaLabel={t(M.knowledgeDismiss, { value })}
                    busy={busyFor(payload)}
                    disabled={ignore.isPending}
                    onDismiss={() => handleDismiss(payload)}
                  />
                )
              })}
            </div>
          </section>
        )}

        {entityGroups.length > 0 && (
          <section className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              {t(M.knowledgeEntities)}
            </h4>
            <div className="space-y-3">
              {entityGroups.map(([field, values]) => (
                <div key={field} className="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:gap-3">
                  <span className="shrink-0 pt-0.5 text-xs font-medium text-gray-600 sm:w-28">
                    {ENTITY_LABEL[field] ? t(ENTITY_LABEL[field]) : field}
                  </span>
                  <div className="flex min-w-0 flex-wrap gap-2">
                    {values.map((value) => {
                      const payload: IgnoreKnowledgePayload = {
                        kind: 'entity',
                        value,
                        entity_field: field,
                      }
                      return (
                        <KnowledgeChip
                          key={`${field}-${value}`}
                          label={value}
                          ariaLabel={t(M.knowledgeDismiss, { value })}
                          busy={busyFor(payload)}
                          disabled={ignore.isPending}
                          onDismiss={() => handleDismiss(payload)}
                        />
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <p className="text-xs text-gray-400">{t(M.knowledgeDismissHint)}</p>
      </div>
    )
  }

  const sampleCount = data?.sample_count ?? 0

  return (
    <Card className="animate-fade-in border-brand-100">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <CardTitle className="inline-flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-brand" aria-hidden="true" />
            {t(M.knowledgeTitle)}
          </CardTitle>
          {!isLoading && !isError && (
            <span className="text-xs text-gray-400">
              {t(M.knowledgeSubtitle, { count: sampleCount })}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>{renderBody()}</CardContent>
    </Card>
  )
}
