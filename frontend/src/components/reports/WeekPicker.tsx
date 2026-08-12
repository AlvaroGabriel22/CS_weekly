import { ChevronLeft, ChevronRight, Undo2 } from 'lucide-react'
import {
  addWeeks,
  currentWeekRef,
  isSameWeek,
  weekLabel,
  weekRangeLabel,
  weeksInYear,
  type WeekRef,
} from '@/lib/dates'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { REPORTS } from '@/i18n/messages/reports'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

export interface WeekPickerProps {
  value: WeekRef
  onChange: (ref: WeekRef) => void
  className?: string
}

/**
 * Seletor de semana da convenção da empresa:
 * ‹ W30 W31 [W32] W33 W34 › + troca de ano.
 * A semana selecionada fica sempre no chip central.
 */
export function WeekPicker({ value, onChange, className }: WeekPickerProps) {
  const { t } = useI18n()
  const today = currentWeekRef()
  const chips = [-2, -1, 0, 1, 2].map((offset) => addWeeks(value, offset))

  const years: number[] = []
  for (let y = today.year - 2; y <= today.year + 1; y++) years.push(y)
  if (!years.includes(value.year)) {
    years.push(value.year)
    years.sort((a, b) => a - b)
  }

  const changeYear = (yearText: string) => {
    const year = Number(yearText)
    if (!Number.isFinite(year) || year === value.year) return
    onChange({ year, week: Math.min(value.week, weeksInYear(year)) })
  }

  return (
    <div className={cn('rounded-xl border border-border/60 bg-white p-4 shadow-card', className)}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-1.5">
          <button
            type="button"
            aria-label={t(REPORTS.prevWeek)}
            onClick={() => onChange(addWeeks(value, -1))}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-brand/5 hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ChevronLeft className="h-5 w-5" aria-hidden="true" />
          </button>

          <div className="flex min-w-0 items-center gap-1 overflow-x-auto py-1" role="group" aria-label={t(REPORTS.nearbyWeeks)}>
            {chips.map((chip, index) => {
              const selected = index === 2
              const isCurrent = isSameWeek(chip, today)
              const showYear = chip.year !== value.year
              return (
                <button
                  key={`${chip.year}-${chip.week}`}
                  type="button"
                  aria-pressed={selected}
                  title={`${weekLabel(chip)} · ${weekRangeLabel(chip)}`}
                  onClick={() => onChange(chip)}
                  className={cn(
                    'relative flex h-10 shrink-0 flex-col items-center justify-center rounded-lg px-3 text-sm font-medium transition-all duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    selected
                      ? 'scale-105 bg-brand text-white shadow-sm'
                      : 'text-gray-600 hover:bg-brand/5 hover:text-brand'
                  )}
                >
                  <span className="leading-none">{weekLabel(chip)}</span>
                  {showYear && (
                    <span className={cn('mt-0.5 text-[10px] leading-none', selected ? 'text-white/80' : 'text-gray-400')}>
                      {chip.year}
                    </span>
                  )}
                  {isCurrent && !selected && (
                    <span
                      aria-hidden="true"
                      className="absolute bottom-1 h-1 w-1 rounded-full bg-brand"
                      title={t(COMMON.currentWeek)}
                    />
                  )}
                </button>
              )
            })}
          </div>

          <button
            type="button"
            aria-label={t(REPORTS.nextWeek)}
            onClick={() => onChange(addWeeks(value, 1))}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-brand/5 hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ChevronRight className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          {!isSameWeek(value, today) && (
            <button
              type="button"
              onClick={() => onChange(today)}
              className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-brand transition-colors hover:bg-brand/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Undo2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {t(COMMON.currentWeek)}
            </button>
          )}
          <Select value={String(value.year)} onValueChange={changeYear}>
            <SelectTrigger className="h-10 w-[96px]" aria-label={t(REPORTS.year)}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {years.map((year) => (
                <SelectItem key={year} value={String(year)}>
                  {year}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <p className="mt-3 border-t border-border/60 pt-3 text-sm text-gray-600">
        <span className="font-semibold text-gray-900">{weekLabel(value)}</span>
        {' · '}
        {weekRangeLabel(value)}
      </p>
    </div>
  )
}
