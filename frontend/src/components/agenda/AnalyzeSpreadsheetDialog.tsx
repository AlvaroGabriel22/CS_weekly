/**
 * "Analisar planilha com IA" — diálogo aberto a partir de um anexo de planilha.
 *
 * O usuário escreve em português o que quer (ou reaproveita uma análise já
 * aprovada, que roda instantânea). A IA só interpreta; a conta é feita no
 * backend. Resultado = tabela + gráfico + resumo; ao aprovar, a receita fica
 * salva para as próximas semanas.
 *
 * Erros SEMPRE via parseApiError. Gráfico em CSS puro (sem biblioteca nova).
 */
import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  BarChart3,
  Check,
  Loader2,
  Sparkles,
  TrendingUp,
  X,
} from 'lucide-react'
import type { Attachment } from '@/types'
import { parseApiError } from '@/lib/errors'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useToast } from '@/components/ui/toast'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { AGENDA } from '@/i18n/messages/agenda'
import {
  recipeColumn,
  recipeOperation,
  useAnalysisPreview,
  useAnalysisRecipes,
  useApproveAnalysis,
  useDeleteAnalysisRecipe,
  type AnalysisChart,
  type AnalysisPreviewInput,
  type AnalysisPreviewOk,
  type AnalysisResult,
  type AnalysisResultItem,
  type ColumnRole,
  type SavedAnalysis,
} from '@/hooks/useAnalysis'

export interface AnalyzeSpreadsheetDialogProps {
  attachment: Attachment
  onClose: () => void
}

const ROLE_LABEL: Record<ColumnRole, Msg> = {
  numerator: AGENDA.analysisNumerator,
  denominator: AGENDA.analysisDenominator,
  value: AGENDA.analysisValue,
  group_by: AGENDA.analysisGroupBy,
}

/** Gráfico de barras horizontais em CSS — proporcional aos valores. */
function MiniChart({ chart }: { chart: AnalysisChart }) {
  const { t, locale } = useI18n()
  const series = chart.series?.[0]
  if (!series || series.values.length === 0) return null
  const max = Math.max(...series.values.map(v => Math.abs(v))) || 1
  const format = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 })

  return (
    <ul className="min-w-0 space-y-1.5" aria-label={t(AGENDA.analysisChart)}>
      {chart.categories.map((category, index) => {
        const value = series.values[index] ?? 0
        const width = Math.max(2, Math.min(100, (Math.abs(value) / max) * 100))
        return (
          <li key={`${category}-${index}`} className="flex min-w-0 items-center gap-2">
            <span className="w-20 shrink-0 truncate text-xs text-gray-600 sm:w-28" title={category}>
              {category}
            </span>
            <span className="h-3 min-w-0 flex-1 rounded-full bg-gray-100">
              <span
                className="block h-3 rounded-full bg-gradient-to-r from-blue-600 to-blue-700 transition-all duration-300 ease-out"
                style={{ width: `${width}%` }}
              />
            </span>
            <span className="w-14 shrink-0 text-right text-xs font-medium tabular-nums text-gray-900">
              {format.format(value)}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

/** Tabela do resultado (cabeçalho + linhas já formatadas pelo backend). */
function ResultTable({ result }: { result: AnalysisResult }) {
  return (
    <div className="min-w-0 overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            {result.columns.map((column, index) => (
              <th
                key={`${column}-${index}`}
                scope="col"
                className={cn(
                  'whitespace-nowrap px-3 py-2 text-xs font-medium text-gray-600',
                  index === 0 ? 'text-left' : 'text-right'
                )}
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {result.rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="bg-white">
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className={cn(
                    'px-3 py-2',
                    cellIndex === 0
                      ? 'text-gray-700'
                      : 'whitespace-nowrap text-right font-medium tabular-nums text-gray-900'
                  )}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Lista de análises da prévia. O backend manda `results` com TODAS; respostas
 * antigas (ou sem o campo) caem no par `recipe` + `result`.
 */
function analysisItems(data: AnalysisPreviewOk): AnalysisResultItem[] {
  const list = Array.isArray(data.results) ? data.results.filter(item => item?.result) : []
  if (list.length > 0) return list
  return data.result ? [{ recipe: data.recipe, result: data.result }] : []
}

export function AnalyzeSpreadsheetDialog({ attachment, onClose }: AnalyzeSpreadsheetDialogProps) {
  const { t } = useI18n()
  const { toast } = useToast()
  const recipes = useAnalysisRecipes(attachment.id)
  const preview = useAnalysisPreview()
  const approve = useApproveAnalysis()
  const removeRecipe = useDeleteAnalysisRecipe()

  const [requestText, setRequestText] = useState('')
  const [askError, setAskError] = useState<string | null>(null)
  const [overrides, setOverrides] = useState<Partial<Record<ColumnRole, string>>>({})
  /** Índices (dentro de `results`) já aprovados nesta prévia. */
  const [approvedIndexes, setApprovedIndexes] = useState<number[]>([])
  const [approvingIndex, setApprovingIndex] = useState<number | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  /** Última chamada feita — usada em "Tentar de novo" e no recálculo. */
  const lastRun = useRef<AnalysisPreviewInput | null>(null)

  const data = preview.data
  const okData = data && data.ok ? data : null
  const needsColumns = data && !data.ok ? data : null
  const saved = (recipes.data ?? []).filter(item => item.matches_current_file)
  const busy = preview.isPending
  const items = okData ? analysisItems(okData) : []
  const partial = (okData?.partial ?? []).filter(Boolean)

  // Colunas sugeridas pela receita só entram no formulário se existirem mesmo.
  useEffect(() => {
    if (!needsColumns) return
    const columns = needsColumns.columns
    const pick = (role: ColumnRole) => {
      const value = recipeColumn(needsColumns.recipe, role)
      return columns.includes(value) ? value : ''
    }
    setOverrides({
      numerator: pick('numerator'),
      denominator: pick('denominator'),
      value: pick('value'),
      group_by: pick('group_by'),
    })
  }, [needsColumns])

  const run = (input: AnalysisPreviewInput) => {
    lastRun.current = input
    setApprovedIndexes([])
    setApprovingIndex(null)
    preview.mutate(input)
  }

  const handleAnalyze = () => {
    const text = requestText.trim()
    if (text.length < 3) {
      setAskError(t(AGENDA.analysisAskRequired))
      textareaRef.current?.focus()
      return
    }
    setAskError(null)
    setOverrides({})
    run({ attachmentId: attachment.id, requestText: text })
  }

  const handleSaved = (item: SavedAnalysis) => {
    setAskError(null)
    setRequestText(item.request_text)
    setOverrides({})
    run({ attachmentId: attachment.id, requestText: item.request_text, recipeId: item.id })
  }

  const handleRecalculate = () => {
    const base = lastRun.current
    if (!base) return
    const cleaned: Partial<Record<ColumnRole, string>> = {}
    for (const [role, value] of Object.entries(overrides)) {
      if (value) cleaned[role as ColumnRole] = value
    }
    run({ ...base, columnOverrides: cleaned })
  }

  const handleRetry = () => {
    if (lastRun.current) run(lastRun.current)
    else handleAnalyze()
  }

  const handleDiscard = () => {
    preview.reset()
    setOverrides({})
    setApprovedIndexes([])
    setApprovingIndex(null)
    textareaRef.current?.focus()
  }

  /** Aprova UMA análise: a receita/rótulo/total são os daquele item. */
  const handleApprove = (index: number, item: AnalysisResultItem) => {
    setApprovingIndex(index)
    approve.mutate(
      {
        attachmentId: attachment.id,
        requestText: lastRun.current?.requestText ?? requestText.trim(),
        recipe: item.recipe,
        label: item.result.label,
        total: item.result.total,
      },
      {
        onSuccess: () => {
          setApprovedIndexes(prev => (prev.includes(index) ? prev : [...prev, index]))
          toast.success(t(AGENDA.analysisApproved))
        },
        onError: err => toast.error(parseApiError(err).message),
        onSettled: () => setApprovingIndex(null),
      }
    )
  }

  const handleDeleteRecipe = (item: SavedAnalysis) => {
    removeRecipe.mutate(item.id, {
      onSuccess: () => toast.success(t(AGENDA.analysisRecipeDeleted)),
      onError: err => toast.error(parseApiError(err).message),
    })
  }

  const roles: ColumnRole[] =
    recipeOperation(needsColumns?.recipe) === 'ratio'
      ? ['numerator', 'denominator', 'group_by']
      : ['value', 'group_by']
  // Radix não aceita item com value "" e chaves repetidas quebram a lista.
  const columnOptions = Array.from(new Set((needsColumns?.columns ?? []).filter(Boolean)))

  return (
    <Dialog open onOpenChange={open => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 pr-6">
            <BarChart3 className="h-5 w-5 shrink-0 text-brand" aria-hidden="true" />
            {t(AGENDA.analysisTitle)}
          </DialogTitle>
          <DialogDescription className="truncate">{attachment.original_filename}</DialogDescription>
        </DialogHeader>

        <div className="max-h-[62vh] min-w-0 space-y-4 overflow-y-auto">
          {/* Lista de análises salvas falhou — aviso discreto, sem travar o resto */}
          {recipes.isError && !okData && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-200 bg-gray-50 p-3">
              <p role="alert" className="min-w-0 text-xs text-gray-600">
                {parseApiError(recipes.error).message}
              </p>
              <Button type="button" variant="outline" size="sm" onClick={() => void recipes.refetch()}>
                {t(COMMON.retry)}
              </Button>
            </div>
          )}

          {/* Análises já aprovadas que combinam com esta planilha */}
          {saved.length > 0 && !okData && (
            <div className="min-w-0">
              <p className="mb-2 text-xs font-medium text-gray-600">{t(AGENDA.analysisSavedIntro)}</p>
              <div className="flex min-w-0 flex-wrap gap-1.5">
                {saved.map(item => (
                  <span
                    key={item.id}
                    className="inline-flex min-w-0 max-w-full items-center rounded-lg border border-brand/20 bg-brand/[0.04] pl-1 pr-0.5"
                  >
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleSaved(item)}
                      className="flex min-h-10 min-w-0 items-center gap-1.5 rounded-md px-2 text-xs font-medium text-brand transition-colors hover:bg-brand/10 disabled:opacity-50"
                    >
                      <Sparkles className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                      <span className="max-w-[180px] truncate">{item.label}</span>
                    </button>
                    <button
                      type="button"
                      disabled={busy || removeRecipe.isPending}
                      onClick={() => handleDeleteRecipe(item)}
                      aria-label={t(AGENDA.analysisDeleteRecipe, { label: item.label })}
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-gray-400 transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                    >
                      <X className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Pedido em português */}
          {!okData && (
            <div className="min-w-0">
              <Label htmlFor="analise-pedido" className="text-sm text-gray-700">
                {t(AGENDA.analysisAsk)}
              </Label>
              <Textarea
                id="analise-pedido"
                ref={textareaRef}
                value={requestText}
                onChange={e => {
                  setRequestText(e.target.value)
                  if (askError) setAskError(null)
                }}
                rows={2}
                maxLength={500}
                disabled={busy}
                placeholder={t(AGENDA.analysisPlaceholder)}
                aria-invalid={Boolean(askError)}
                aria-describedby={askError ? 'analise-pedido-erro' : undefined}
                className={cn(
                  'mt-1.5 min-h-[60px]',
                  askError && 'border-red-500 bg-red-50 focus-visible:ring-red-500'
                )}
              />
              {askError && (
                <p id="analise-pedido-erro" role="alert" className="mt-1.5 text-xs text-red-600">
                  {askError}
                </p>
              )}
              <div className="mt-2 flex justify-end">
                <Button type="button" onClick={handleAnalyze} disabled={busy} className="min-h-10">
                  {busy ? (
                    <Loader2 className="animate-spin" aria-hidden="true" />
                  ) : (
                    <BarChart3 aria-hidden="true" />
                  )}
                  {t(AGENDA.analyze)}
                </Button>
              </div>
            </div>
          )}

          {/* Processando (pode levar minutos) */}
          {busy && (
            <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
              <Loader2 className="h-7 w-7 animate-spin text-brand" aria-hidden="true" />
              <p className="max-w-xs text-sm text-gray-600" aria-live="polite">
                {t(AGENDA.analysisLoading)}
              </p>
            </div>
          )}

          {/* Erro (422, rede, servidor) */}
          {!busy && preview.isError && (
            <div className="flex flex-col items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-center">
              <AlertTriangle className="h-6 w-6 text-red-600" aria-hidden="true" />
              <p role="alert" className="text-sm text-gray-700">
                {parseApiError(preview.error).message}
              </p>
              <Button type="button" variant="outline" size="sm" onClick={handleRetry}>
                {t(AGENDA.analysisRetry)}
              </Button>
            </div>
          )}

          {/* Confirmação de colunas (ok: false) */}
          {!busy && needsColumns && (
            <div className="min-w-0 space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
              <div>
                <p className="text-sm font-medium text-gray-900">{t(AGENDA.analysisColumnsTitle)}</p>
                <p className="mt-0.5 text-sm text-gray-700">{needsColumns.message}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {roles.map(role => (
                  <div key={role} className="min-w-0">
                    <Label htmlFor={`analise-col-${role}`} className="text-xs text-gray-600">
                      {t(ROLE_LABEL[role])}
                    </Label>
                    <Select
                      value={overrides[role] ?? ''}
                      onValueChange={value => setOverrides(prev => ({ ...prev, [role]: value }))}
                    >
                      <SelectTrigger id={`analise-col-${role}`} className="mt-1 bg-white">
                        <SelectValue placeholder={t(AGENDA.analysisPickColumn)} />
                      </SelectTrigger>
                      <SelectContent>
                        {columnOptions.map(column => (
                          <SelectItem key={column} value={column}>
                            {column}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </div>
              <div className="flex justify-end">
                <Button type="button" size="sm" onClick={handleRecalculate} className="min-h-10">
                  {t(AGENDA.analysisRecalc)}
                </Button>
              </div>
            </div>
          )}

          {/* Resultado — uma seção por análise */}
          {!busy && okData && (
            <div className="min-w-0 space-y-3 animate-fade-in">
              {items.length > 1 && (
                <p className="text-xs font-medium text-gray-500">
                  {t(AGENDA.analysisCount, { n: items.length })}
                </p>
              )}

              {items.map((item, index) => {
                const isSaved = okData.source === 'saved' || approvedIndexes.includes(index)
                const pending = approve.isPending && approvingIndex === index
                return (
                  <section
                    key={`${item.result.label}-${index}`}
                    className="min-w-0 space-y-3 rounded-xl border border-gray-200 bg-white p-4 shadow-card"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="min-w-0 flex-1 break-words text-sm font-semibold text-gray-900">
                        {item.result.label}
                      </h4>
                      {isSaved && <Badge>{t(AGENDA.analysisSaved)}</Badge>}
                    </div>

                    <ResultTable result={item.result} />

                    {item.result.chart && (
                      <div className="min-w-0 rounded-lg border border-gray-200 p-4">
                        <MiniChart chart={item.result.chart} />
                      </div>
                    )}

                    {item.result.summary && (
                      <p className="min-w-0 break-words rounded-lg bg-gray-50 p-3 text-sm text-gray-700">
                        {item.result.summary}
                      </p>
                    )}

                    {index === 0 && okData.comparison && (
                      <p className="flex min-w-0 items-start gap-2 rounded-lg border border-brand/20 bg-brand/[0.04] p-3 text-sm text-gray-700">
                        <TrendingUp
                          className="mt-0.5 h-4 w-4 shrink-0 text-brand"
                          aria-hidden="true"
                        />
                        <span className="min-w-0 break-words">{okData.comparison}</span>
                      </p>
                    )}

                    {okData.source !== 'saved' && !approvedIndexes.includes(index) && (
                      <div className="flex justify-end">
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => handleApprove(index, item)}
                          disabled={approve.isPending}
                          className="min-h-10"
                        >
                          {pending ? (
                            <Loader2 className="animate-spin" aria-hidden="true" />
                          ) : (
                            <Check aria-hidden="true" />
                          )}
                          {pending ? t(AGENDA.analysisApproving) : t(AGENDA.analysisApprove)}
                        </Button>
                      </div>
                    )}
                  </section>
                )
              })}

              {/* Análises que não deram certo — aviso discreto */}
              {partial.length > 0 && (
                <div className="min-w-0 rounded-lg border border-amber-200 bg-amber-50 p-3">
                  <p className="flex items-start gap-2 text-xs font-medium text-amber-900">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="min-w-0 break-words">{t(AGENDA.analysisPartial)}</span>
                  </p>
                  <ul className="mt-1.5 min-w-0 list-disc space-y-1 pl-9 text-xs text-amber-900/80">
                    {partial.map((message, index) => (
                      <li key={index} className="min-w-0 break-words">
                        {message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          {okData ? (
            <>
              <Button type="button" variant="outline" onClick={handleDiscard}>
                {t(AGENDA.analysisDiscard)}
              </Button>
              <Button type="button" onClick={onClose}>
                {t(COMMON.close)}
              </Button>
            </>
          ) : (
            <Button type="button" variant="outline" onClick={onClose}>
              {t(COMMON.close)}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
