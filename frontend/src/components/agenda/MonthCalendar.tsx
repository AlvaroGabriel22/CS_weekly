/**
 * Calendário MENSAL da Agenda (seg→dom, convenção de semanas da empresa).
 *
 * - Cada linha exibe à esquerda o número da semana (W31, W32…), calculado
 *   EXCLUSIVAMENTE com getWeekRef — nunca na mão.
 * - Rótulos de mês/dia localizados via toLocaleDateString(locale) do useI18n;
 *   a MATEMÁTICA da semana continua vindo de @/lib/dates.
 * - Hoje: anel azul. Dia selecionado: fundo brand sólido. Dias fora do mês:
 *   cinza claro. Dias com atividades: pontinho azul.
 */
import { ChevronLeft, ChevronRight } from 'lucide-react'
import {
  currentWeekRef,
  getWeekRef,
  formatDateIso,
  isSameDay,
  isToday,
  monthMatrix,
  weekLabel,
} from '@/lib/dates'
import type { MonthRef } from '@/hooks/useActivities'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { AGENDA } from '@/i18n/messages/agenda'

export interface MonthCalendarProps {
  monthRef: MonthRef
  onMonthChange: (ref: MonthRef) => void
  selectedDate: Date | null
  onSelectDay: (day: Date) => void
  /** Dias (formatDateIso) que possuem atividades no período visível. */
  activityDays: ReadonlySet<string>
}

function shiftMonth(ref: MonthRef, delta: number): MonthRef {
  const d = new Date(ref.year, ref.month + delta, 1)
  return { year: d.getFullYear(), month: d.getMonth() }
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function MonthCalendar({
  monthRef,
  onMonthChange,
  selectedDate,
  onSelectDay,
  activityDays,
}: MonthCalendarProps) {
  const { t, locale } = useI18n()
  const rows = monthMatrix(monthRef.year, monthRef.month)
  const nowRef = currentWeekRef()

  const monthTitle = capitalize(
    new Date(monthRef.year, monthRef.month, 1).toLocaleDateString(locale, {
      month: 'long',
      year: 'numeric',
    })
  )

  const goToday = () => {
    const today = new Date()
    onMonthChange({ year: today.getFullYear(), month: today.getMonth() })
  }

  return (
    <div data-tour="calendar" className="rounded-xl border border-gray-200 bg-white p-4 shadow-card sm:p-5">
      {/* Cabeçalho: mês + chip da semana atual + navegação */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2.5">
          <h2 className="text-lg font-semibold text-gray-900">{monthTitle}</h2>
          <span className="inline-flex items-center rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700">
            {t(COMMON.currentWeek)}: {weekLabel(nowRef)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9"
            aria-label={t(AGENDA.prevMonth)}
            onClick={() => onMonthChange(shiftMonth(monthRef, -1))}
          >
            <ChevronLeft aria-hidden="true" />
          </Button>
          <Button type="button" variant="outline" size="sm" className="h-9" onClick={goToday}>
            {t(COMMON.today)}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9"
            aria-label={t(AGENDA.nextMonth)}
            onClick={() => onMonthChange(shiftMonth(monthRef, 1))}
          >
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>
      </div>

      {/* Rótulos das colunas (seg→dom, localizados), com coluna extra da semana */}
      <div className="mt-4 grid grid-cols-[2.25rem_repeat(7,minmax(0,1fr))] gap-1">
        <div aria-hidden="true" />
        {rows[0].map(day => (
          <div
            key={day.getDay()}
            className="py-1 text-center text-xs font-medium uppercase tracking-wide text-gray-400"
          >
            {day.toLocaleDateString(locale, { weekday: 'short' }).replace(/\.$/, '')}
          </div>
        ))}

        {rows.map(week => {
          const ref = getWeekRef(week[0])
          const isCurrentWeek = ref.year === nowRef.year && ref.week === nowRef.week
          return (
            <div key={`${ref.year}-${ref.week}`} className="contents">
              {/* Número da semana — discreto, clicável (seleciona a segunda) */}
              <button
                type="button"
                onClick={() => onSelectDay(week[0])}
                aria-label={t(AGENDA.selectWeek, { week: ref.week })}
                className={cn(
                  'flex items-center justify-center rounded-md text-[11px] font-medium tabular-nums transition-colors',
                  'text-gray-300 hover:bg-brand-50 hover:text-brand-600',
                  isCurrentWeek && 'text-brand-400'
                )}
              >
                {weekLabel(ref)}
              </button>

              {week.map(day => {
                const inMonth = day.getMonth() === monthRef.month
                const selected = selectedDate !== null && isSameDay(day, selectedDate)
                const today = isToday(day)
                const hasActivities = activityDays.has(formatDateIso(day))
                const dayLabel = day.toLocaleDateString(locale, {
                  weekday: 'long',
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric',
                })
                return (
                  <button
                    key={formatDateIso(day)}
                    type="button"
                    onClick={() => onSelectDay(day)}
                    {...(today ? { 'data-tour-today': '' } : {})}
                    aria-label={`${dayLabel}${hasActivities ? ` — ${t(AGENDA.withActivities)}` : ''}`}
                    aria-pressed={selected}
                    className={cn(
                      'relative mx-auto flex aspect-square w-full max-w-[3rem] min-h-10 flex-col items-center justify-center rounded-lg text-sm transition-all duration-200',
                      inMonth ? 'text-gray-700' : 'text-gray-300',
                      !selected && 'hover:bg-gray-100',
                      today && !selected && 'ring-2 ring-inset ring-brand font-semibold text-brand-700',
                      selected && 'bg-brand font-semibold text-white shadow-sm'
                    )}
                  >
                    <span className="tabular-nums leading-none">{day.getDate()}</span>
                    <span
                      aria-hidden="true"
                      className={cn(
                        'mt-1 h-1 w-1 rounded-full transition-colors',
                        hasActivities ? (selected ? 'bg-white' : 'bg-brand') : 'bg-transparent'
                      )}
                    />
                  </button>
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}
