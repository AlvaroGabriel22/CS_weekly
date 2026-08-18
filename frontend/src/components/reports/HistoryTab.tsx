import { useState } from 'react'
import { ChevronDown, Download, Mail, Monitor, MoreVertical, Presentation, RefreshCw, Sparkles, Wand2 } from 'lucide-react'
import type { WeekRef } from '@/lib/dates'
import { parseApiError } from '@/lib/errors'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { REPORTS } from '@/i18n/messages/reports'
import { EmptyState, ErrorState } from '@/components/feedback'
import { Badge, type BadgeProps } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { downloadWeeklyPptx, useWeeklyReports } from '@/hooks/useWeekly'
import { useAiStyle, useSetAiTemplate } from '@/hooks/useAi'
import { DeckViewer, SlideViewer } from '@/components/weekly/SlideViewer'
import { SendEmailDialog } from '@/components/reports/SendEmailDialog'
import type { WeeklyReport } from '@/types'

export interface HistoryTabProps {
  /** Vai para a aba Gerar. */
  onGenerate: () => void
  /** Vai para a aba Gerar com a semana do weekly pré-selecionada. */
  onRegenerate: (ref: WeekRef) => void
}

/** Histórico dos weeklys gerados pelo usuário. */
export function HistoryTab({ onGenerate, onRegenerate }: HistoryTabProps) {
  const { t } = useI18n()
  const query = useWeeklyReports()

  if (query.isLoading) {
    return (
      <div className="space-y-3" role="status" aria-label={t(COMMON.loading)}>
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-xl border border-border/60 bg-white p-5 shadow-card">
            <div className="flex items-center gap-4">
              <Skeleton className="h-12 w-12 rounded-xl" />
              <div className="min-w-0 flex-1 space-y-2">
                <Skeleton className="h-4 w-48 max-w-full" />
                <Skeleton className="h-3 w-64 max-w-full" />
              </div>
              <Skeleton className="hidden h-9 w-28 sm:block" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  }

  const reports = query.data ?? []

  if (reports.length === 0) {
    return (
      <EmptyState
        icon={Presentation}
        title={t(REPORTS.historyEmpty)}
        action={
          <Button onClick={onGenerate}>
            <Sparkles aria-hidden="true" />
            {t(REPORTS.tabGenerate)}
          </Button>
        }
      />
    )
  }

  return (
    <ul className="space-y-3">
      {reports.map((report, index) => (
        <li
          key={report.id}
          className="animate-slide-up"
          style={{ animationDelay: `${Math.min(index, 8) * 50}ms`, animationFillMode: 'backwards' }}
        >
          <ReportCard report={report} onRegenerate={onRegenerate} />
        </li>
      ))}
    </ul>
  )
}

function statusMeta(status: string): { msg: Msg; variant: BadgeProps['variant'] } {
  switch (status) {
    case 'completed':
      return { msg: REPORTS.statusReady, variant: 'success' }
    case 'generating':
    case 'processing':
      return { msg: REPORTS.statusGenerating, variant: 'info' }
    case 'failed':
    case 'error':
      return { msg: REPORTS.statusFailed, variant: 'danger' }
    default:
      return { msg: REPORTS.statusDraft, variant: 'outline' }
  }
}

function formatDateTime(iso: string, locale: string): string {
  const date = new Date(iso)
  const day = date.toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: 'numeric' })
  const time = date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
  return `${day} ${time}`
}

function ReportCard({
  report,
  onRegenerate,
}: {
  report: WeeklyReport
  onRegenerate: (ref: WeekRef) => void
}) {
  const { t, locale } = useI18n()
  const { toast } = useToast()
  const [downloading, setDownloading] = useState(false)
  const [viewing, setViewing] = useState(false)
  const [emailing, setEmailing] = useState(false)
  const aiStyle = useAiStyle()
  const setTemplate = useSetAiTemplate()
  const status = statusMeta(report.status)
  const ready = report.status === 'completed' && Boolean(report.pptx_path)
  // Decks montados no editor têm o layout salvo → preview fiel página a página;
  // weeklys antigos (sem layout) caem no visualizador de conteúdo legado.
  const layout = report.content?.layout
  const hasLayout = Boolean(layout?.slides?.length)
  const canView = report.status === 'completed' && (hasLayout || Boolean(report.content))
  const isAiTemplate = aiStyle.data?.template?.report_id === report.id

  const toggleAiTemplate = () => {
    setTemplate.mutate(
      { reportId: isAiTemplate ? null : report.id },
      {
        onSuccess: () => toast.success(t(REPORTS.aiTemplateSaved)),
        onError: (err) => toast.error(parseApiError(err).message),
      }
    )
  }

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await downloadWeeklyPptx(report)
      toast.success(t(REPORTS.downloadStarted))
    } catch (err) {
      toast.error(parseApiError(err).message)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="rounded-xl border border-border/60 bg-white shadow-card transition-shadow duration-200 hover:shadow-elevated">
      <div className="flex items-center gap-3 p-4 sm:gap-4 sm:p-5">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand/10">
          <Presentation className="h-6 w-6 text-brand" aria-hidden="true" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h3 className="text-sm font-semibold text-gray-900">
              W{report.week_number} · {report.year}
            </h3>
            <Badge variant={status.variant}>{t(status.msg)}</Badge>
            <Badge variant="outline">v{report.version}</Badge>
            <Badge variant="outline" className="uppercase">
              {report.language}
            </Badge>
            {isAiTemplate && (
              <Badge className="border-transparent bg-brand/10 text-brand">
                <Wand2 className="mr-1 h-3 w-3" aria-hidden="true" />
                {t(REPORTS.aiTemplateBadge)}
              </Badge>
            )}
            {report.ai_degraded && (
              <Badge className="border-transparent bg-amber-100 text-amber-700">
                {t(REPORTS.aiDegraded)}
              </Badge>
            )}
          </div>
          <p className="mt-1 truncate text-xs text-gray-500">
            {report.title ?? 'Weekly Report'}
            {report.generated_at && ` · ${formatDateTime(report.generated_at, locale)}`}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <Button
            size="sm"
            className="hidden sm:inline-flex"
            disabled={!canView}
            onClick={() => setViewing(true)}
          >
            <Monitor aria-hidden="true" />
            {t(COMMON.view)}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="hidden sm:inline-flex"
            disabled={!ready || downloading}
            onClick={handleDownload}
          >
            <Download aria-hidden="true" />
            {downloading ? t(REPORTS.downloading) : t(COMMON.download)}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`${t(REPORTS.reportActions)} · W${report.week_number}`}
              >
                <MoreVertical aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem disabled={!canView} onSelect={() => setViewing(true)}>
                <Monitor aria-hidden="true" />
                {t(COMMON.view)}
              </DropdownMenuItem>
              <DropdownMenuItem disabled={!ready || downloading} onSelect={handleDownload}>
                <Download aria-hidden="true" />
                {t(REPORTS.downloadPptx)}
              </DropdownMenuItem>
              <DropdownMenuItem disabled={!ready} onSelect={() => setEmailing(true)}>
                <Mail aria-hidden="true" />
                {t(REPORTS.sendEmail)}
              </DropdownMenuItem>
              <DropdownMenuItem
                disabled={!hasLayout || setTemplate.isPending}
                onSelect={toggleAiTemplate}
              >
                <Wand2 aria-hidden="true" />
                {isAiTemplate ? t(REPORTS.aiTemplateUnset) : t(REPORTS.aiTemplateSet)}
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={() => onRegenerate({ year: report.year, week: report.week_number })}
              >
                <RefreshCw aria-hidden="true" />
                {t(REPORTS.newVersion)}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {report.ai_summary && (
        <details className="group border-t border-border/60 bg-gray-50/60">
          <summary className="flex min-h-[40px] cursor-pointer list-none items-center justify-between gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 sm:px-5">
            <span className="min-w-0 truncate">{t(REPORTS.aiSummary)}</span>
            <ChevronDown
              className="h-4 w-4 shrink-0 text-gray-400 transition-transform duration-200 group-open:rotate-180"
              aria-hidden="true"
            />
          </summary>
          <p className="whitespace-pre-wrap px-4 pb-4 text-sm leading-relaxed text-gray-600 sm:px-5">
            {report.ai_summary}
          </p>
        </details>
      )}

      {/* Pré-visualização página a página (mesmo viewer dos weeklys de colegas) */}
      {hasLayout && layout ? (
        <DeckViewer report={report} layout={layout} open={viewing} onClose={() => setViewing(false)} />
      ) : (
        <SlideViewer report={report} open={viewing} onClose={() => setViewing(false)} />
      )}

      {/* Envio por e-mail com o .pptx anexado (lista pré-cadastrada em Configurações) */}
      {emailing && (
        <SendEmailDialog report={report} open={emailing} onClose={() => setEmailing(false)} />
      )}
    </div>
  )
}
