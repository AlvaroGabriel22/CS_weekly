/**
 * Agenda — interação central do QWI.
 *
 * Estado inicial: calendário mensal centralizado. Ao clicar num dia, o
 * calendário desliza para a esquerda (coluna compacta) e o painel do dia
 * surge à direita. Fechar (X ou clicar no mesmo dia) recentra o calendário.
 * Em telas < md o painel desliza por baixo do calendário.
 *
 * A animação usa apenas flexbox: espaçadores com flex-grow animado (1 → 0)
 * + largura do calendário (620px → 360px) + revelação do painel — tudo com
 * transition-all duration-300 ease-out, sem bibliotecas.
 *
 * Layout: padding lateral via PageContainer; o painel do dia SEMPRE cabe no
 * espaço restante (min-w-0, sem larguras mínimas fixas) — nada estoura o
 * viewport em nenhuma largura.
 */
import { useMemo, useRef, useState } from 'react'
import { MonthCalendar } from '@/components/agenda/MonthCalendar'
import { ActivityPanel } from '@/components/agenda/ActivityPanel'
import { useMonthActivities, type MonthRef } from '@/hooks/useActivities'
import { formatDateIso, isSameDay } from '@/lib/dates'
import { ErrorState } from '@/components/feedback'
import { Skeleton } from '@/components/ui/skeleton'
import { PageContainer } from '@/components/layout/PageContainer'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { AGENDA } from '@/i18n/messages/agenda'
import { cn } from '@/lib/utils'

/** Duração da animação de abertura/fechamento do painel (ms). */
const PANEL_ANIMATION_MS = 350

function CalendarSkeleton() {
  return (
    <div className="mx-auto w-full max-w-[620px] rounded-xl border border-gray-200 bg-white p-5 shadow-card">
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-9 w-32" />
      </div>
      <div className="mt-5 grid grid-cols-8 gap-2">
        {Array.from({ length: 48 }, (_, i) => (
          <Skeleton key={i} className="aspect-square w-full rounded-lg" />
        ))}
      </div>
    </div>
  )
}

export function AgendaPage() {
  const { t } = useI18n()
  const [monthRef, setMonthRef] = useState<MonthRef>(() => {
    const today = new Date()
    return { year: today.getFullYear(), month: today.getMonth() }
  })
  /** Dia exibido no painel — mantido durante a animação de fechamento. */
  const [panelDate, setPanelDate] = useState<Date | null>(null)
  const [open, setOpen] = useState(false)
  const closeTimer = useRef<number | undefined>(undefined)

  const { data, isLoading, isError, error, refetch } = useMonthActivities(monthRef)
  const activities = useMemo(() => data ?? [], [data])

  /** Dias (AAAA-MM-DD) do período visível que têm atividades → pontinhos. */
  const activityDays = useMemo(
    () => new Set(activities.map(a => a.activity_date.slice(0, 10))),
    [activities]
  )

  const dayActivities = useMemo(() => {
    if (!panelDate) return []
    const iso = formatDateIso(panelDate)
    return activities
      .filter(a => a.activity_date.slice(0, 10) === iso)
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
  }, [activities, panelDate])

  const openPanel = (day: Date) => {
    window.clearTimeout(closeTimer.current)
    setPanelDate(day)
    setOpen(true)
  }

  const closePanel = () => {
    setOpen(false)
    // Mantém o conteúdo montado até o fim da animação de recolhimento.
    window.clearTimeout(closeTimer.current)
    closeTimer.current = window.setTimeout(() => setPanelDate(null), PANEL_ANIMATION_MS)
  }

  const handleSelectDay = (day: Date) => {
    if (open && panelDate && isSameDay(day, panelDate)) closePanel()
    else openPanel(day)
  }

  return (
    <PageContainer title={t(COMMON.agenda)} description={t(AGENDA.subtitle)}>
      {isLoading ? (
        <CalendarSkeleton />
      ) : isError ? (
        <div className="mx-auto w-full max-w-[620px] rounded-xl border border-gray-200 bg-white shadow-card">
          <ErrorState error={error} onRetry={() => refetch()} />
        </div>
      ) : (
        <div className="flex min-w-0 flex-col md:flex-row md:items-start">
          {/* Espaçador esquerdo: some quando o painel abre (empurra o calendário à esquerda) */}
          <div
            aria-hidden="true"
            className={cn(
              'hidden basis-0 transition-all duration-300 ease-out md:block',
              open ? 'grow-0' : 'grow'
            )}
          />

          {/* Calendário: centralizado (620px) → coluna compacta (360px) */}
          <div
            className={cn(
              'w-full min-w-0 transition-all duration-300 ease-out md:shrink',
              open ? 'md:w-[360px]' : 'md:w-[620px]',
              'md:max-w-full'
            )}
          >
            <MonthCalendar
              monthRef={monthRef}
              onMonthChange={setMonthRef}
              selectedDate={open ? panelDate : null}
              onSelectDay={handleSelectDay}
              activityDays={activityDays}
            />
          </div>

          {/* Painel do dia: surge à direita (md+) ou desliza por baixo (mobile).
              min-w-0 + basis-0/grow: ocupa APENAS o espaço restante, sem estourar. */}
          <div
            className={cn(
              'min-w-0 overflow-hidden transition-all duration-300 ease-out md:basis-0',
              open
                ? 'mt-4 max-h-[3000px] opacity-100 md:ml-4 md:mt-0 md:max-h-none md:grow lg:ml-6'
                : 'max-h-0 opacity-0 md:ml-0 md:max-h-none md:grow-0'
            )}
            aria-hidden={!open}
          >
            {panelDate && (
              <ActivityPanel
                date={panelDate}
                monthRef={monthRef}
                activities={dayActivities}
                onClose={closePanel}
              />
            )}
          </div>

          {/* Espaçador direito */}
          <div
            aria-hidden="true"
            className={cn(
              'hidden basis-0 transition-all duration-300 ease-out md:block',
              open ? 'grow-0' : 'grow'
            )}
          />
        </div>
      )}
    </PageContainer>
  )
}
