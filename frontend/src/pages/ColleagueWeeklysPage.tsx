import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Building2, CalendarX2, Download, FileText, Loader2, Presentation } from 'lucide-react'
import { EmptyState, ErrorState } from '@/components/feedback'
import { Avatar } from '@/components/ui/avatar'
import { Badge, type BadgeProps } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { DeckViewer, SlideViewer } from '@/components/weekly/SlideViewer'
import { downloadWeeklyPptx, useColleagueWeeklys, useOrgUsers, useWeeklyReportFull } from '@/hooks/useOrg'
import { currentWeekRef, getWeekDaysOf, weekLabel, weeksInYear, type WeekRef } from '@/lib/dates'
import { parseApiError } from '@/lib/errors'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { ORG } from '@/i18n/messages/org'
import { cn } from '@/lib/utils'
import type { WeeklySummary } from '@/types'

const STATUS_INFO: Record<string, { label: Msg; variant: BadgeProps['variant'] }> = {
  draft: { label: ORG.statusDraft, variant: 'outline' },
  generating: { label: ORG.statusGenerating, variant: 'info' },
  completed: { label: ORG.statusCompleted, variant: 'success' },
  failed: { label: ORG.statusFailed, variant: 'danger' },
}

/** "10 de ago. – 16 de ago. de 2026" no idioma ativo (seg→dom da semana). */
function weekRange(ref: WeekRef, locale: string): string {
  const days = getWeekDaysOf(ref)
  const start = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short' }).format(days[0])
  const end = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', year: 'numeric' }).format(days[6])
  return `${start} – ${end}`
}

// ── Card de um weekly (usado na semana selecionada e na aba "Tudo") ─────────

interface WeeklyCardProps {
  summary: WeeklySummary
  opening: boolean
  downloading: boolean
  onView: (summary: WeeklySummary) => void
  onDownload: (summary: WeeklySummary) => void
  style?: CSSProperties
}

function WeeklyCard({ summary, opening, downloading, onView, onDownload, style }: WeeklyCardProps) {
  const { t, locale } = useI18n()
  const info = STATUS_INFO[summary.status]
  const statusLabel = info ? t(info.label) : summary.status
  const statusVariant = info?.variant ?? ('outline' as const)
  const ref = { year: summary.year, week: summary.week_number }

  return (
    <div
      style={style}
      className="rounded-xl border border-border/60 bg-white p-5 shadow-card transition-shadow duration-200 animate-slide-up hover:shadow-elevated"
    >
      <div className="flex items-start gap-3.5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50">
          <FileText className="h-5 w-5 text-brand" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="min-w-0 flex-1 truncate text-sm font-semibold text-gray-900 sm:text-base">
              {summary.title ?? `Weekly ${weekLabel(ref)} · ${summary.year}`}
            </h3>
            <Badge variant={statusVariant}>{statusLabel}</Badge>
          </div>
          <p className="mt-1 text-xs text-gray-500 sm:text-sm">
            {weekLabel(ref)} · {summary.year} · {t(ORG.version, { n: summary.version })}
            {summary.generated_at &&
              ` · ${new Date(summary.generated_at).toLocaleDateString(locale)}`}
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" disabled={opening} onClick={() => onView(summary)}>
          {opening ? (
            <Loader2 className="animate-spin" aria-hidden="true" />
          ) : (
            <Presentation aria-hidden="true" />
          )}
          {t(COMMON.view)}
        </Button>
        {summary.has_pptx && (
          <Button size="sm" variant="outline" disabled={downloading} onClick={() => onDownload(summary)}>
            {downloading ? (
              <Loader2 className="animate-spin" aria-hidden="true" />
            ) : (
              <Download aria-hidden="true" />
            )}
            {t(COMMON.download)}
          </Button>
        )}
      </div>
    </div>
  )
}

function ListSkeleton() {
  const { t } = useI18n()
  return (
    <div role="status" aria-label={t(COMMON.loading)} className="space-y-3 animate-fade-in">
      {[0, 1].map(i => (
        <div key={i} className="rounded-xl border border-border/60 bg-white p-5 shadow-card">
          <div className="flex items-start gap-3.5">
            <Skeleton className="h-10 w-10 shrink-0 rounded-lg" />
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-8 w-28" />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Página ──────────────────────────────────────────────────────────────────

/** Weeklys de um colega: header com perfil + seletor de semanas + relatórios. */
export function ColleagueWeeklysPage() {
  const { userId } = useParams<{ userId: string }>()
  const navigate = useNavigate()
  const { t, locale } = useI18n()
  const { toast } = useToast()

  const current = currentWeekRef()
  const yearOptions = [current.year, current.year - 1, current.year - 2]

  const [year, setYear] = useState(current.year)
  const [view, setView] = useState<number | 'all'>(current.week)
  const [viewReportId, setViewReportId] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const chipsRef = useRef<HTMLDivElement>(null)

  const orgQuery = useOrgUsers()
  const colleague = useMemo(
    () => (orgQuery.data ?? []).find(u => u.id === userId),
    [orgQuery.data, userId]
  )

  const weeklysQuery = useColleagueWeeklys(userId, view === 'all' ? undefined : year)
  const reportQuery = useWeeklyReportFull(viewReportId)

  // Falha ao abrir a apresentação → toast com a mensagem normalizada.
  useEffect(() => {
    if (viewReportId && reportQuery.isError) {
      toast.error(parseApiError(reportQuery.error).message)
      setViewReportId(null)
    }
  }, [viewReportId, reportQuery.isError, reportQuery.error, toast])

  // Mantém o chip da semana selecionada visível na faixa rolável.
  useEffect(() => {
    if (view === 'all') return
    const chip = chipsRef.current?.querySelector<HTMLElement>(`[data-week="${view}"]`)
    chip?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
  }, [view, year])

  const handleYearChange = (value: string) => {
    const nextYear = Number(value)
    setYear(nextYear)
    if (typeof view === 'number' && view > weeksInYear(nextYear)) {
      setView(weeksInYear(nextYear))
    }
  }

  const handleDownload = async (summary: WeeklySummary) => {
    setDownloadingId(summary.id)
    try {
      await downloadWeeklyPptx(summary)
      toast.success(t(ORG.downloadStarted))
    } catch (err) {
      toast.error(parseApiError(err).message)
    } finally {
      setDownloadingId(null)
    }
  }

  const weeks = Array.from({ length: weeksInYear(year) }, (_, i) => i + 1)
  const list = weeklysQuery.data ?? []
  const selectedSummary =
    typeof view === 'number'
      ? list.find(w => w.week_number === view && w.year === year)
      : undefined

  const groupedByYear = useMemo(() => {
    const map = new Map<number, WeeklySummary[]>()
    for (const summary of list) {
      const bucket = map.get(summary.year)
      if (bucket) bucket.push(summary)
      else map.set(summary.year, [summary])
    }
    return [...map.entries()] // já em ordem decrescente (lista vem ordenada)
  }, [list])

  // ── Estados de página (organograma ainda carregando / erro / não achou) ──

  if (orgQuery.isLoading) {
    return (
      <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
        <div className="mb-6 rounded-xl border border-border/60 bg-white p-5 shadow-card sm:p-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-14 w-14 shrink-0 rounded-full sm:h-24 sm:w-24" />
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-6 w-56 max-w-full" />
              <Skeleton className="h-4 w-40 max-w-full" />
              <Skeleton className="h-4 w-32 max-w-full" />
            </div>
          </div>
        </div>
        <ListSkeleton />
      </div>
    )
  }

  if (orgQuery.isError) {
    return (
      <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
        <ErrorState error={orgQuery.error} onRetry={() => orgQuery.refetch()} />
      </div>
    )
  }

  if (!userId || !colleague) {
    return (
      <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
        <EmptyState
          title={t(ORG.colleagueNotFound)}
          action={<Button onClick={() => navigate('/departamentos')}>{t(ORG.seeDepartments)}</Button>}
        />
      </div>
    )
  }

  const fullReport =
    viewReportId && reportQuery.data && reportQuery.data.id === viewReportId
      ? reportQuery.data
      : null
  const deckLayout = fullReport?.content?.layout ?? null

  const chipBase =
    'h-9 shrink-0 rounded-full border px-3.5 text-xs font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
      {/* Header do colega */}
      <section className="mb-6 rounded-xl border border-border/60 bg-white p-5 shadow-card animate-fade-in sm:p-6">
        <div className="flex items-center gap-4 sm:gap-5">
          <Avatar src={colleague.photo_url} name={colleague.name} size="lg" className="sm:hidden" />
          <Avatar
            src={colleague.photo_url}
            name={colleague.name}
            size="xl"
            className="hidden sm:inline-flex"
          />
          <div className="min-w-0">
            <h1 className="truncate text-xl font-bold tracking-tight text-gray-900 sm:text-2xl">
              {colleague.name}
            </h1>
            <p className="mt-0.5 truncate text-sm text-gray-600">{colleague.role}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge>{colleague.sector}</Badge>
              <span className="inline-flex min-w-0 items-center gap-1 text-xs text-gray-500">
                <Building2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span className="truncate">{colleague.department}</span>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Seletor: ano + chips de semanas */}
      <section className="mb-6 animate-fade-in">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Select value={String(year)} onValueChange={handleYearChange}>
            <SelectTrigger className="w-28 shrink-0 bg-white" aria-label={t(ORG.year)}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {yearOptions.map(y => (
                <SelectItem key={y} value={String(y)}>
                  {y}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div
            ref={chipsRef}
            role="tablist"
            aria-label={t(ORG.weeksOfYear)}
            className="flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto pb-1"
          >
            <button
              type="button"
              role="tab"
              aria-selected={view === 'all'}
              onClick={() => setView('all')}
              className={cn(
                chipBase,
                view === 'all'
                  ? 'border-brand bg-brand text-white shadow-sm'
                  : 'border-border bg-white text-gray-600 hover:border-brand-200 hover:text-brand-700'
              )}
            >
              {t(COMMON.all)}
            </button>
            <div className="h-5 w-px shrink-0 bg-border" aria-hidden="true" />
            {weeks.map(week => {
              const selected = view === week
              const isCurrent = year === current.year && week === current.week
              const isFuture = year === current.year && week > current.week
              return (
                <button
                  key={week}
                  type="button"
                  role="tab"
                  data-week={week}
                  aria-selected={selected}
                  onClick={() => setView(week)}
                  className={cn(
                    chipBase,
                    selected
                      ? 'border-brand bg-brand text-white shadow-sm'
                      : isCurrent
                        ? 'border-brand-300 bg-brand-50 text-brand-700 hover:border-brand-400'
                        : 'border-border bg-white text-gray-600 hover:border-brand-200 hover:text-brand-700',
                    !selected && isFuture && 'opacity-40'
                  )}
                >
                  W{week}
                </button>
              )
            })}
          </div>
        </div>
      </section>

      {/* Conteúdo */}
      {weeklysQuery.isLoading ? (
        <ListSkeleton />
      ) : weeklysQuery.isError ? (
        <ErrorState error={weeklysQuery.error} onRetry={() => weeklysQuery.refetch()} />
      ) : view === 'all' ? (
        list.length === 0 ? (
          <EmptyState icon={CalendarX2} title={t(ORG.noWeeklys)} />
        ) : (
          <div className="space-y-6">
            {groupedByYear.map(([groupYear, summaries]) => (
              <section key={groupYear}>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                  {groupYear}
                </h2>
                <div className="space-y-3">
                  {summaries.map((summary, idx) => (
                    <WeeklyCard
                      key={summary.id}
                      summary={summary}
                      opening={viewReportId === summary.id && reportQuery.isLoading}
                      downloading={downloadingId === summary.id}
                      onView={s => setViewReportId(s.id)}
                      onDownload={handleDownload}
                      style={{ animationDelay: `${idx * 60}ms`, animationFillMode: 'backwards' }}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )
      ) : (
        <div>
          <p className="mb-3 text-sm text-gray-500">
            {weekLabel({ year, week: view })} · {weekRange({ year, week: view }, locale)}
          </p>
          {selectedSummary ? (
            <WeeklyCard
              summary={selectedSummary}
              opening={viewReportId === selectedSummary.id && reportQuery.isLoading}
              downloading={downloadingId === selectedSummary.id}
              onView={s => setViewReportId(s.id)}
              onDownload={handleDownload}
            />
          ) : (
            <EmptyState
              icon={CalendarX2}
              title={t(ORG.noWeeklyThisWeek, { week: `W${view}` })}
              description={
                year === current.year && view > current.week
                  ? t(ORG.futureWeek)
                  : t(ORG.nothingPublished)
              }
            />
          )}
        </div>
      )}

      {/* Apresentação em tela cheia: layout do PPT quando existir; senão, fallback */}
      {fullReport &&
        (deckLayout && deckLayout.slides.length > 0 ? (
          <DeckViewer
            report={fullReport}
            layout={deckLayout}
            open
            onClose={() => setViewReportId(null)}
          />
        ) : (
          <SlideViewer report={fullReport} open onClose={() => setViewReportId(null)} />
        ))}
    </div>
  )
}
