import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  History,
  Loader2,
  Paperclip,
  Sparkles,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { REPORTS } from '@/i18n/messages/reports'
import { currentWeekRef, parseIsoDate, weekLabel, weekRangeLabel, type WeekRef } from '@/lib/dates'
import { parseApiError } from '@/lib/errors'
import { EmptyState, ErrorState } from '@/components/feedback'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { downloadWeeklyPptx, useGenerateWeekly, useWeekActivities } from '@/hooks/useWeekly'
import { useSaveSlideLayoutPrefs, useSlideLayoutPrefs } from '@/hooks/useSlideEditor'
import { useDeckDraft } from '@/hooks/useAi'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { SlideEditor } from './SlideEditor'
import { StepIndicator } from './StepIndicator'
import { WeekPicker } from './WeekPicker'
import { buildCoverDeck, pinnedElements, type DeckLabels, type DeckLayout } from './slideLayout'
import type { Activity, WeeklyReport } from '@/types'

export interface GenerateWeeklyWizardProps {
  /** Semana pré-selecionada (ex.: "Gerar nova versão" vindo do histórico). */
  initialWeek?: WeekRef
  /** Navega para a aba Histórico. */
  onViewHistory: () => void
}

/** Passos: escolher semana → montar no editor WYSIWYG → gerar. */
export function GenerateWeeklyWizard({ initialWeek, onViewHistory }: GenerateWeeklyWizardProps) {
  const { user } = useAuth()
  const { t, locale } = useI18n()
  const { toast } = useToast()

  const [week, setWeek] = useState<WeekRef>(() => initialWeek ?? currentWeekRef())
  const [step, setStep] = useState(0)
  const [selectedOrder, setSelectedOrder] = useState<string[] | null>(null)
  const [deck, setDeck] = useState<DeckLayout | null>(null)
  // Idioma do registro do relatório (a UI de template/idioma saiu do MVP —
  // o conteúdo é 100% montado pelo usuário e traduzível pelo botão Traduzir).
  const language: 'pt' | 'en' = user?.writing_profile?.default_language === 'en' ? 'en' : 'pt'
  const [successReport, setSuccessReport] = useState<WeeklyReport | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [messageIndex, setMessageIndex] = useState(0)

  const activitiesQuery = useWeekActivities(week)
  const generateMutation = useGenerateWeekly()
  const prefsQuery = useSlideLayoutPrefs()
  const savePrefs = useSaveSlideLayoutPrefs()

  const generationMessages = [t(REPORTS.generating1), t(REPORTS.generating2), t(REPORTS.generating3)]

  const sortedActivities = useMemo(
    () =>
      [...(activitiesQuery.data ?? [])].sort((a, b) =>
        a.activity_date.localeCompare(b.activity_date)
      ),
    [activitiesQuery.data]
  )

  // Primeira carga da semana: pré-seleciona as atividades marcadas para o weekly.
  useEffect(() => {
    if (selectedOrder === null && activitiesQuery.data) {
      setSelectedOrder(
        [...activitiesQuery.data]
          .sort((a, b) => a.activity_date.localeCompare(b.activity_date))
          .filter((activity) => activity.include_in_weekly)
          .map((activity) => activity.id)
      )
    }
  }, [activitiesQuery.data, selectedOrder])

  useEffect(() => {
    if (!generateMutation.isPending) return
    setMessageIndex(0)
    const timer = window.setInterval(
      () => setMessageIndex((index) => (index + 1) % generationMessages.length),
      2000
    )
    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generateMutation.isPending])

  const byId = useMemo(() => {
    const map = new Map<string, Activity>()
    for (const activity of sortedActivities) map.set(activity.id, activity)
    return map
  }, [sortedActivities])

  const selectedSet = useMemo(() => new Set(selectedOrder ?? []), [selectedOrder])
  const includedActivities = useMemo(
    () =>
      (selectedOrder ?? []).flatMap((id) => {
        const activity = byId.get(id)
        return activity ? [activity] : []
      }),
    [selectedOrder, byId]
  )

  const deckLabels: DeckLabels = useMemo(
    () => ({
      coverTitle: `Weekly ${weekLabel(week)}`,
      coverSubtitle: `${weekRangeLabel(week)} · ${user?.name ?? ''}`,
    }),
    [week, user?.name]
  )

  const changeWeek = (ref: WeekRef) => {
    setWeek(ref)
    setSelectedOrder(null)
    setDeck(null) // nova semana → novo deck
  }

  const toggleActivity = (id: string) => {
    setSelectedOrder((prev) => {
      const current = prev ?? []
      return current.includes(id) ? current.filter((x) => x !== id) : [...current, id]
    })
  }

  /** Entra na Montagem: o deck nasce SÓ com a capa (+ fixados); o conteúdo
   *  entra pelos bloquinhos. Voltar e mudar a seleção NÃO apaga o trabalho. */
  const goToAssemble = () => {
    setDeck((current) =>
      current === null ? buildCoverDeck(deckLabels, prefsQuery.data?.pinned ?? []) : current
    )
    setStep(1)
  }

  const handlePinnedChange = (next: DeckLayout) => {
    savePrefs.mutate(pinnedElements(next), {
      onSuccess: () => toast.success(t(REPORTS.layoutSaved)),
    })
  }

  // ── Deck em um clique (IA) — opcional, nunca bloqueia o fluxo manual ─────
  const deckDraft = useDeckDraft()
  const [confirmAiDeck, setConfirmAiDeck] = useState(false)

  const runAiDeck = () => {
    setConfirmAiDeck(false)
    deckDraft.mutate(
      { ref: week, activityIds: selectedOrder ?? [] },
      {
        onSuccess: (result) => {
          setDeck(result.layout)
          setStep(1)
          if (result.source === 'ai') toast.success(t(REPORTS.aiDeckDone))
          else toast.info(t(REPORTS.aiDeckFallback))
        },
        onError: (err) => toast.error(parseApiError(err).message),
      }
    )
  }

  /** Deck "não trivial" = usuário já mexeu (mais de 1 slide ou capa editada). */
  const deckHasWork =
    deck !== null && (deck.slides.length > 1 || deck.slides[0]?.elements.length > 2)

  const requestAiDeck = () => {
    if (deckHasWork) setConfirmAiDeck(true)
    else runAiDeck()
  }

  const generate = () => {
    generateMutation.mutate(
      {
        activity_ids: selectedOrder ?? [],
        week_number: week.week,
        year: week.year,
        language,
        layout: deck ?? undefined,
      },
      { onSuccess: (report) => setSuccessReport(report) }
    )
  }

  const handleDownload = async () => {
    if (!successReport) return
    setDownloading(true)
    try {
      await downloadWeeklyPptx(successReport)
      toast.success(t(REPORTS.downloadStarted))
    } catch (err) {
      toast.error(parseApiError(err).message)
    } finally {
      setDownloading(false)
    }
  }

  const resetWizard = () => {
    generateMutation.reset()
    setSuccessReport(null)
    setDeck(null)
    setStep(0)
  }

  const totalSlides = deck?.slides.length ?? 0
  const busy = generateMutation.isPending || successReport !== null
  const steps = [t(REPORTS.stepWeek), t(REPORTS.stepAssemble), t(REPORTS.stepGenerate)]

  return (
    <div className="space-y-5">
      <StepIndicator
        steps={steps}
        current={step}
        onStepClick={busy ? undefined : (index) => {
          if (index === 1 && step === 0) goToAssemble()
          else setStep(index)
        }}
      />

      {/* ── Passo 1 · Semana ─────────────────────────────────────────────── */}
      {step === 0 && (
        <div key="step-week" className="animate-slide-up space-y-4">
          <WeekPicker value={week} onChange={changeWeek} />

          <div className="rounded-xl border border-border/60 bg-white shadow-card">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-gray-900">{t(REPORTS.weekActivities)}</p>
                <p className="text-xs text-gray-500">
                  {t(REPORTS.selectedCount, { n: selectedSet.size })}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={sortedActivities.length === 0}
                  onClick={() => setSelectedOrder(sortedActivities.map((a) => a.id))}
                >
                  {t(REPORTS.selectAll)}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={selectedSet.size === 0}
                  onClick={() => setSelectedOrder([])}
                >
                  {t(REPORTS.clear)}
                </Button>
              </div>
            </div>

            {activitiesQuery.isLoading ? (
              <div className="space-y-2 p-4" role="status" aria-label={t(COMMON.loading)}>
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-3 rounded-lg border border-border/40 p-3">
                    <Skeleton className="h-4 w-4 rounded" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-2/3" />
                      <Skeleton className="h-3 w-1/3" />
                    </div>
                  </div>
                ))}
              </div>
            ) : activitiesQuery.isError ? (
              <ErrorState error={activitiesQuery.error} onRetry={() => activitiesQuery.refetch()} />
            ) : sortedActivities.length === 0 ? (
              <EmptyState
                icon={CalendarDays}
                title={t(REPORTS.noActivities)}
                action={
                  <Button asChild>
                    <Link to="/agenda">{t(REPORTS.goToAgenda)}</Link>
                  </Button>
                }
              />
            ) : (
              <ul className="max-h-[26rem] space-y-1 overflow-y-auto p-2">
                {sortedActivities.map((activity) => {
                  const checked = selectedSet.has(activity.id)
                  const date = parseIsoDate(activity.activity_date)
                  return (
                    <li key={activity.id}>
                      <label
                        className={
                          checked
                            ? 'flex cursor-pointer items-start gap-3 rounded-lg border border-brand/20 bg-brand/[0.04] px-3 py-3 transition-colors duration-200'
                            : 'flex cursor-pointer items-start gap-3 rounded-lg border border-transparent px-3 py-3 transition-colors duration-200 hover:bg-gray-50'
                        }
                      >
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 rounded border-border text-brand focus:ring-brand"
                          checked={checked}
                          onChange={() => toggleActivity(activity.id)}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                            <span className="break-words text-sm font-medium text-gray-900">{activity.title}</span>
                            <span className="text-xs text-gray-500">
                              {date.toLocaleDateString(locale, { weekday: 'short', day: '2-digit', month: '2-digit' })}
                            </span>
                          </div>
                          {activity.description && (
                            <p className="mt-1 line-clamp-2 break-words text-sm text-gray-600">
                              {activity.description}
                            </p>
                          )}
                          {activity.attachments.length > 0 && (
                            <p className="mt-1 flex items-center gap-1 text-xs text-gray-500">
                              <Paperclip className="h-3 w-3" aria-hidden="true" />
                              {t(REPORTS.attachments, { n: activity.attachments.length })}
                            </p>
                          )}
                        </div>
                      </label>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          <div className="flex flex-col-reverse items-stretch gap-2 sm:flex-row sm:items-center sm:justify-end">
            {/* IA opcional: monta o rascunho do deck — o usuário sempre pode ajustar */}
            <Button
              size="lg"
              variant="outline"
              disabled={selectedSet.size === 0 || deckDraft.isPending}
              onClick={requestAiDeck}
              data-tour="ai-deck-btn"
              title={t(REPORTS.aiDeckHint)}
            >
              {deckDraft.isPending ? (
                <>
                  <Loader2 className="animate-spin" aria-hidden="true" />
                  {t(REPORTS.aiDeckBuilding)}
                </>
              ) : (
                <>
                  <Sparkles aria-hidden="true" />
                  {t(REPORTS.aiDeck)}
                </>
              )}
            </Button>
            <Button size="lg" data-tour="assemble-btn" disabled={selectedSet.size === 0 || deckDraft.isPending} onClick={goToAssemble}>
              {t(REPORTS.continueBtn)}
              <ChevronRight aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}

      {/* ── Passo 2 · Montagem (editor WYSIWYG) ──────────────────────────── */}
      {step === 1 && deck && (
        <div key="step-deck" className="animate-slide-up space-y-4">
          <SlideEditor
            deck={deck}
            onChange={setDeck}
            activities={includedActivities}
            onPinnedChange={handlePinnedChange}
          />

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between">
            <div className="flex flex-col-reverse gap-2 sm:flex-row">
              <Button variant="outline" onClick={() => setStep(0)}>
                <ChevronLeft aria-hidden="true" />
                {t(COMMON.back)}
              </Button>
              <Button
                variant="ghost"
                disabled={deckDraft.isPending}
                onClick={requestAiDeck}
                title={t(REPORTS.aiDeckHint)}
              >
                {deckDraft.isPending ? (
                  <>
                    <Loader2 className="animate-spin" aria-hidden="true" />
                    {t(REPORTS.aiDeckBuilding)}
                  </>
                ) : (
                  <>
                    <Sparkles aria-hidden="true" />
                    {t(REPORTS.aiDeck)}
                  </>
                )}
              </Button>
            </div>
            <Button size="lg" disabled={totalSlides === 0} onClick={() => setStep(2)}>
              {t(REPORTS.reviewAndGenerate)}
              <ChevronRight aria-hidden="true" />
            </Button>
          </div>

        </div>
      )}

      {/* ── Passo 3 · Gerar ──────────────────────────────────────────────── */}
      {step === 2 && (
        <div key="step-generate" className="animate-slide-up">
          {successReport ? (
            <div className="animate-slide-up rounded-2xl border border-green-200 bg-green-50/60 p-6 text-center sm:p-10">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-card">
                <CheckCircle2 className="h-9 w-9 text-green-600" aria-hidden="true" />
              </div>
              <h3 className="mt-4 text-xl font-bold text-gray-900">{t(REPORTS.generated)}</h3>
              <p className="mt-1 text-sm text-gray-600">
                {t(REPORTS.generatedDetail, {
                  week: weekLabel(week),
                  version: successReport.version,
                  slides: totalSlides,
                })}
              </p>
              <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
                <Button
                  size="lg"
                  className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800"
                  disabled={downloading}
                  onClick={handleDownload}
                >
                  <Download aria-hidden="true" />
                  {downloading ? t(REPORTS.downloading) : t(REPORTS.downloadPptx)}
                </Button>
                <Button size="lg" variant="outline" onClick={onViewHistory}>
                  <History aria-hidden="true" />
                  {t(REPORTS.viewHistory)}
                </Button>
              </div>
              <button
                type="button"
                onClick={resetWizard}
                className="mt-4 text-sm font-medium text-brand underline-offset-4 hover:underline"
              >
                {t(REPORTS.buildAnother)}
              </button>
            </div>
          ) : generateMutation.isPending ? (
            <div className="rounded-2xl border border-brand/20 bg-brand/[0.03] p-6 sm:p-10">
              <style>{`@keyframes qwi-sweep { 0% { transform: translateX(-110%); } 60% { transform: translateX(260%); } 100% { transform: translateX(260%); } }`}</style>
              <div className="mx-auto max-w-md text-center">
                <div className="h-2 overflow-hidden rounded-full bg-brand/10" role="progressbar" aria-label={t(REPORTS.stepGenerate)}>
                  <div
                    className="h-full w-2/5 rounded-full bg-gradient-to-r from-blue-500 to-blue-700"
                    style={{ animation: 'qwi-sweep 1.4s ease-in-out infinite' }}
                  />
                </div>
                <p
                  key={messageIndex}
                  className="mt-5 animate-fade-in text-base font-semibold text-brand"
                  aria-live="polite"
                >
                  {generationMessages[messageIndex]}
                </p>
                <p className="mt-2 text-sm text-gray-600">{t(REPORTS.keepTabOpen)}</p>
              </div>
            </div>
          ) : generateMutation.isError ? (
            <div className="rounded-2xl border border-border/60 bg-white shadow-card">
              <ErrorState
                title={t(REPORTS.generationFailed)}
                error={generateMutation.error}
                onRetry={generate}
              />
              <div className="flex justify-center pb-6">
                <Button variant="ghost" onClick={() => setStep(1)}>
                  <ChevronLeft aria-hidden="true" />
                  {t(REPORTS.backToAssemble)}
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-xl border border-border/60 bg-white p-5 shadow-card sm:p-6">
                <h3 className="text-sm font-semibold text-gray-900">{t(REPORTS.summaryTitle)}</h3>
                <dl className="mt-4 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                  <div className="flex justify-between gap-3 sm:block">
                    <dt className="text-gray-500">{t(COMMON.week)}</dt>
                    <dd className="font-medium text-gray-900 sm:mt-0.5">
                      {weekLabel(week)} · {weekRangeLabel(week)}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-3 sm:block">
                    <dt className="text-gray-500">{t(REPORTS.summarySlides)}</dt>
                    <dd className="font-medium text-gray-900 sm:mt-0.5">{totalSlides}</dd>
                  </div>
                </dl>
              </div>

              <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
                <Button variant="outline" onClick={() => setStep(1)}>
                  <ChevronLeft aria-hidden="true" />
                  {t(COMMON.back)}
                </Button>
                <Button
                  size="lg"
                  className="h-12 bg-gradient-to-r from-blue-600 to-blue-700 px-8 text-base hover:from-blue-700 hover:to-blue-800"
                  onClick={generate}
                >
                  <Sparkles aria-hidden="true" />
                  {t(REPORTS.generateBtn)}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Confirmação antes de substituir trabalho manual pelo rascunho da IA */}
      <Dialog open={confirmAiDeck} onOpenChange={setConfirmAiDeck}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t(REPORTS.aiDeckReplace)}</DialogTitle>
            <DialogDescription>{t(REPORTS.aiDeckReplaceHint)}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmAiDeck(false)}>
              {t(COMMON.cancel)}
            </Button>
            <Button onClick={runAiDeck}>
              <Sparkles aria-hidden="true" />
              {t(REPORTS.aiDeck)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
