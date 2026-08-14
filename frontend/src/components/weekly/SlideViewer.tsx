import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { StaticSlidePage } from '@/components/reports/SlideStatic'
import type { DeckLayout } from '@/components/reports/slideLayout'
import { parseIsoDate, weekLabel } from '@/lib/dates'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { ORG } from '@/i18n/messages/org'
import { cn } from '@/lib/utils'
import type { WeeklyReport } from '@/types'

/**
 * CONTRATO PÚBLICO (charter): visualizador de apresentação inline.
 * Monta slides 16:9 a partir de report.content — todos os campos são
 * opcionais, então a renderização é 100% defensiva.
 */
export interface SlideViewerProps {
  report: WeeklyReport
  open: boolean
  onClose: () => void
}

// ── Leitura defensiva do content ────────────────────────────────────────────

function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : undefined
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined
}

interface ParsedActivity {
  title?: string
  date?: string
  narrative?: string
  impact?: string
  facts: string[]
  actions: string[]
}

type Slide =
  | { kind: 'cover'; title: string; author?: string }
  | { kind: 'summary'; summary?: string; highlights: string[] }
  | { kind: 'activity'; position: number; total: number; activity: ParsedActivity }
  | { kind: 'kpis'; kpis: string[] }
  | { kind: 'closing'; conclusions: string[]; nextSteps: string[] }

function buildSlides(report: WeeklyReport): Slide[] {
  const content = asRecord(report.content) ?? {}
  const slides: Slide[] = []

  slides.push({
    kind: 'cover',
    title: asString(report.title) ?? `Weekly ${weekLabel({ year: report.year, week: report.week_number })}`,
    author: asString(content.author) ?? asString(content.author_name),
  })

  const summary = asString(content.summary)
  const highlights = asStringArray(content.highlights)
  if (summary || highlights.length > 0) {
    slides.push({ kind: 'summary', summary, highlights })
  }

  const rawActivities = Array.isArray(content.activities) ? content.activities : []
  const activities: ParsedActivity[] = rawActivities
    .map(asRecord)
    .filter((a): a is Record<string, unknown> => a !== undefined)
    .map(a => ({
      title: asString(a.title),
      date: asString(a.date),
      narrative: asString(a.narrative),
      impact: asString(a.impact),
      facts: asStringArray(a.facts),
      actions: asStringArray(a.actions),
    }))
  activities.forEach((activity, idx) => {
    slides.push({ kind: 'activity', position: idx + 1, total: activities.length, activity })
  })

  const kpis = asStringArray(content.kpis)
  if (kpis.length > 0) slides.push({ kind: 'kpis', kpis })

  const conclusions = asStringArray(content.conclusions)
  const nextSteps = asStringArray(content.next_steps)
  if (conclusions.length > 0 || nextSteps.length > 0) {
    slides.push({ kind: 'closing', conclusions, nextSteps })
  }

  return slides
}

/** "2026-08-10" → data no idioma ativo; qualquer outro formato é exibido como veio. */
function formatActivityDate(raw: string, locale: string): string {
  return /^\d{4}-\d{2}-\d{2}/.test(raw) ? parseIsoDate(raw).toLocaleDateString(locale) : raw
}

// ── Blocos visuais dos slides ───────────────────────────────────────────────

function BulletList({ items, className }: { items: string[]; className?: string }) {
  return (
    <ul className={cn('space-y-2', className)}>
      {items.map((item, idx) => (
        <li key={idx} className="flex items-start gap-2.5 text-sm text-gray-700 sm:text-base">
          <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-brand" aria-hidden="true" />
          <span className="min-w-0 break-words">{item}</span>
        </li>
      ))}
    </ul>
  )
}

function SlideHeading({ overline, title }: { overline: string; title: string }) {
  return (
    <header className="mb-5 sm:mb-6">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-brand sm:text-xs">
        {overline}
      </p>
      <h3 className="mt-1 text-xl font-bold text-gray-900 sm:text-2xl">{title}</h3>
      <div className="mt-3 h-1 w-14 rounded-full bg-gradient-to-r from-blue-600 to-blue-700" />
    </header>
  )
}

function SlideBody({ slide, report }: { slide: Slide; report: WeeklyReport }) {
  const { t, locale } = useI18n()
  const weekRef = { year: report.year, week: report.week_number }

  if (slide.kind === 'cover') {
    return (
      <div className="flex h-full flex-col items-center justify-center px-2 text-center">
        <Badge className="mb-4 text-sm sm:text-base">
          {weekLabel(weekRef)} · {report.year}
        </Badge>
        <h2 className="max-w-3xl break-words text-2xl font-bold leading-tight text-gray-900 sm:text-4xl">
          {slide.title}
        </h2>
        {slide.author && (
          <p className="mt-3 text-sm text-gray-500 sm:text-base">
            {t(ORG.by, { name: slide.author })}
          </p>
        )}
        <div className="mt-8 h-1.5 w-28 rounded-full bg-gradient-to-r from-blue-600 to-blue-700" />
      </div>
    )
  }

  if (slide.kind === 'summary') {
    return (
      <div>
        <SlideHeading overline={t(ORG.overview)} title={t(ORG.summary)} />
        {slide.summary && (
          <p className="mb-5 whitespace-pre-line text-sm leading-relaxed text-gray-700 sm:text-base">
            {slide.summary}
          </p>
        )}
        {slide.highlights.length > 0 && (
          <>
            <p className="mb-2 text-sm font-semibold text-gray-900">{t(ORG.highlights)}</p>
            <BulletList items={slide.highlights} />
          </>
        )}
      </div>
    )
  }

  if (slide.kind === 'activity') {
    const { activity } = slide
    return (
      <div>
        <SlideHeading
          overline={t(ORG.activityOf, { i: slide.position, n: slide.total })}
          title={activity.title ?? t(ORG.untitled)}
        />
        {activity.date && (
          <p className="-mt-3 mb-4 text-xs text-gray-500 sm:text-sm">
            {formatActivityDate(activity.date, locale)}
          </p>
        )}
        {activity.narrative && (
          <p className="mb-4 whitespace-pre-line text-sm leading-relaxed text-gray-700 sm:text-base">
            {activity.narrative}
          </p>
        )}
        {activity.impact && (
          <div className="mb-4 rounded-lg border border-brand-100 bg-brand-50 p-3 sm:p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              {t(ORG.impact)}
            </p>
            <p className="mt-1 text-sm text-brand-800 sm:text-base">{activity.impact}</p>
          </div>
        )}
        {(activity.facts.length > 0 || activity.actions.length > 0) && (
          <div className="grid gap-4 md:grid-cols-2">
            {activity.facts.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-semibold text-gray-900">{t(ORG.facts)}</p>
                <BulletList items={activity.facts} />
              </div>
            )}
            {activity.actions.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-semibold text-gray-900">{t(ORG.actions)}</p>
                <BulletList items={activity.actions} />
              </div>
            )}
          </div>
        )}
        {!activity.narrative &&
          !activity.impact &&
          activity.facts.length === 0 &&
          activity.actions.length === 0 && (
            <p className="text-sm text-gray-500">{t(ORG.noDetails)}</p>
          )}
      </div>
    )
  }

  if (slide.kind === 'kpis') {
    return (
      <div>
        <SlideHeading overline={t(ORG.indicators)} title={t(ORG.kpis)} />
        <div className="grid gap-3 sm:grid-cols-2">
          {slide.kpis.map((kpi, idx) => (
            <div
              key={idx}
              className="min-w-0 break-words rounded-lg border border-border/60 bg-gray-50 p-3 text-sm text-gray-800 sm:p-4 sm:text-base"
            >
              {kpi}
            </div>
          ))}
        </div>
      </div>
    )
  }

  // closing
  return (
    <div>
      <SlideHeading overline={t(ORG.closing)} title={t(ORG.conclusions)} />
      <div className="grid gap-5 md:grid-cols-2">
        {slide.conclusions.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-semibold text-gray-900">{t(ORG.conclusions)}</p>
            <BulletList items={slide.conclusions} />
          </div>
        )}
        {slide.nextSteps.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-semibold text-gray-900">{t(ORG.nextSteps)}</p>
            <BulletList items={slide.nextSteps} />
          </div>
        )}
      </div>
    </div>
  )
}

// ── Visualizador ────────────────────────────────────────────────────────────

export function SlideViewer({ report, open, onClose }: SlideViewerProps) {
  const { t } = useI18n()
  const slides = useMemo(() => buildSlides(report), [report])
  const [index, setIndex] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const total = slides.length

  const goPrev = useCallback(() => setIndex(i => Math.max(0, i - 1)), [])
  const goNext = useCallback(() => setIndex(i => Math.min(total - 1, i + 1)), [total])

  // Reabrir (ou trocar de relatório) sempre volta ao primeiro slide.
  useEffect(() => {
    if (open) setIndex(0)
  }, [open, report.id])

  // Setas do teclado + Esc; trava o scroll da página enquanto aberto.
  useEffect(() => {
    if (!open) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') goNext()
      else if (e.key === 'ArrowLeft') goPrev()
      else if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    containerRef.current?.focus()
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [open, goNext, goPrev, onClose])

  if (!open || total === 0) return null

  const slide = slides[Math.min(index, total - 1)]

  return (
    <div
      ref={containerRef}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label={`${t(ORG.presentation)} · ${weekLabel({ year: report.year, week: report.week_number })} ${report.year}`}
      className="fixed inset-0 z-[90] flex flex-col bg-gray-950/95 outline-none animate-fade-in"
    >
      {/* Barra superior */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <p className="min-w-0 truncate text-sm font-medium text-white/80">
          {asString(report.title) ?? 'Weekly'} · {weekLabel({ year: report.year, week: report.week_number })}{' '}
          {report.year}
        </p>
        <button
          type="button"
          onClick={onClose}
          aria-label={t(COMMON.close)}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      {/* Palco */}
      <div className="flex min-h-0 flex-1 items-center justify-center gap-2 px-2 sm:gap-4 sm:px-6">
        <button
          type="button"
          onClick={goPrev}
          disabled={index === 0}
          aria-label={t(ORG.prevSlide)}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-white/80 transition-all hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60 disabled:pointer-events-none disabled:opacity-30"
        >
          <ChevronLeft className="h-6 w-6" aria-hidden="true" />
        </button>

        <div className="min-w-0 flex-1">
          {/* key = index remonta o slide → fade curto a cada troca */}
          <div
            key={index}
            className="mx-auto aspect-video w-full max-w-5xl overflow-hidden rounded-xl bg-white shadow-2xl animate-fade-in"
          >
            <div className="h-full overflow-y-auto p-6 sm:p-10">
              <SlideBody slide={slide} report={report} />
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={goNext}
          disabled={index === total - 1}
          aria-label={t(ORG.nextSlide)}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-white/80 transition-all hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60 disabled:pointer-events-none disabled:opacity-30"
        >
          <ChevronRight className="h-6 w-6" aria-hidden="true" />
        </button>
      </div>

      {/* Rodapé: contador + dica */}
      <div className="flex flex-col items-center gap-1 px-4 py-3 sm:py-4">
        <p className="text-sm font-medium tabular-nums text-white/90" aria-live="polite">
          {index + 1} / {total}
        </p>
        <p className="hidden text-xs text-white/40 sm:block">{t(ORG.keysHint)}</p>
      </div>
    </div>
  )
}

// ── Visualizador do layout do PPT (páginas do editor, fiéis ao arquivo) ─────

/** Largura da página: ~min(90vw, altura útil·16/9), com folga p/ setas no desktop. */
function deckStageWidth(): number {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const maxByGutters = vw >= 640 ? vw - 136 : vw * 0.92 // folga p/ setas no desktop
  return Math.max(240, Math.min(vw * 0.9, maxByGutters, ((vh - 128) * 16) / 9))
}

export interface DeckViewerProps {
  report: WeeklyReport
  layout: DeckLayout
  open: boolean
  onClose: () => void
}

/**
 * Pré-visualização em tela cheia do PPT montado no editor: renderiza as
 * páginas 16:9 do layout salvo (StaticSlidePage), uma a uma, com setas,
 * teclado (← → Esc), contador e foco preso no diálogo.
 */
export function DeckViewer({ report, layout, open, onClose }: DeckViewerProps) {
  const { t } = useI18n()
  const slides = layout.slides ?? []
  const total = slides.length
  const [index, setIndex] = useState(0)
  const [width, setWidth] = useState(() => deckStageWidth())
  const containerRef = useRef<HTMLDivElement>(null)

  const goPrev = useCallback(() => setIndex(i => Math.max(0, i - 1)), [])
  const goNext = useCallback(() => setIndex(i => Math.min(total - 1, i + 1)), [total])

  // Reabrir (ou trocar de relatório) sempre volta à primeira página.
  useEffect(() => {
    if (open) setIndex(0)
  }, [open, report.id])

  useEffect(() => {
    if (!open) return
    const onResize = () => setWidth(deckStageWidth())
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [open])

  // Teclado (setas + Esc), foco preso simples (Tab) e trava do scroll da página.
  useEffect(() => {
    if (!open) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') goNext()
      else if (e.key === 'ArrowLeft') goPrev()
      else if (e.key === 'Escape') onClose()
      else if (e.key === 'Tab') {
        const focusables = containerRef.current?.querySelectorAll<HTMLElement>('button:not([disabled])')
        if (!focusables || focusables.length === 0) return
        const first = focusables[0]
        const last = focusables[focusables.length - 1]
        const active = document.activeElement
        if (!containerRef.current?.contains(active)) {
          e.preventDefault()
          first.focus()
        } else if (e.shiftKey && active === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && active === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', onKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    containerRef.current?.focus()
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [open, goNext, goPrev, onClose])

  if (!open || total === 0) return null

  const safeIndex = Math.min(index, total - 1)
  const slide = slides[safeIndex]
  const arrowClass =
    'absolute top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/30 text-white/80 backdrop-blur-sm transition-all hover:bg-white/15 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60 disabled:pointer-events-none disabled:opacity-30'

  return (
    <div
      ref={containerRef}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label={`${t(ORG.presentation)} · ${weekLabel({ year: report.year, week: report.week_number })} ${report.year}`}
      className="fixed inset-0 z-[90] flex flex-col bg-gray-950/95 outline-none animate-fade-in"
    >
      {/* Barra superior */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <p className="min-w-0 truncate text-sm font-medium text-white/80">
          {asString(report.title) ?? 'Weekly'} · {weekLabel({ year: report.year, week: report.week_number })}{' '}
          {report.year}
        </p>
        <button
          type="button"
          onClick={onClose}
          aria-label={t(COMMON.close)}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      {/* Palco: página centrada + setas sobrepostas */}
      <div className="relative flex min-h-0 flex-1 items-center justify-center px-2 sm:px-6">
        <button
          type="button"
          onClick={goPrev}
          disabled={safeIndex === 0}
          aria-label={t(ORG.prevSlide)}
          className={cn(arrowClass, 'left-1.5 sm:left-4')}
        >
          <ChevronLeft className="h-6 w-6" aria-hidden="true" />
        </button>

        {/* key = índice remonta a página → fade curto a cada troca */}
        <div key={safeIndex} className="max-w-full animate-fade-in">
          <StaticSlidePage slide={slide} width={width} className="shadow-2xl" />
        </div>

        <button
          type="button"
          onClick={goNext}
          disabled={safeIndex === total - 1}
          aria-label={t(ORG.nextSlide)}
          className={cn(arrowClass, 'right-1.5 sm:right-4')}
        >
          <ChevronRight className="h-6 w-6" aria-hidden="true" />
        </button>
      </div>

      {/* Rodapé: contador + dica */}
      <div className="flex flex-col items-center gap-1 px-4 py-3 sm:py-4">
        <p className="text-sm font-medium tabular-nums text-white/90" aria-live="polite">
          {safeIndex + 1} / {total}
        </p>
        <p className="hidden text-xs text-white/40 sm:block">{t(ORG.keysHint)}</p>
      </div>
    </div>
  )
}
