/**
 * Roteiro do guia de primeiro acesso.
 *
 * Em arquivo separado do Tour.tsx de propósito: componentes React não podem
 * dividir módulo com constantes exportadas, senão o Fast Refresh do Vite
 * invalida o módulo inteiro e quebra o estado do tour em desenvolvimento.
 */
import type { Msg } from '@/i18n'
import { TOUR } from '@/i18n/messages/tour'

export interface TourStep {
  /** Rota onde o alvo vive (navegação automática). */
  route: string
  /** Valor do atributo data-tour do alvo; null = passo centralizado (boas-vindas). */
  target: string | null
  title: Msg
  body: Msg
  /** Ação de preparação (ex.: abrir o painel do dia clicando no calendário). */
  prepare?: keyof typeof PREPARES
}

/** Ações que deixam a tela pronta para o passo (sempre idempotentes). */
export const PREPARES = {
  /** Agenda: abre o painel do dia clicando no dia de HOJE (se ainda fechado). */
  'open-today': () => {
    if (!document.querySelector('[data-tour="day-form"]')) {
      const today = document.querySelector<HTMLElement>('[data-tour-today]')
      today?.click()
    }
  },
}

export const TOUR_STEPS: TourStep[] = [
  { route: '/', target: null, title: TOUR.welcomeTitle, body: TOUR.welcomeBody },
  { route: '/', target: 'week-banner', title: TOUR.weekTitle, body: TOUR.weekBody },
  { route: '/', target: 'stats', title: TOUR.statsTitle, body: TOUR.statsBody },
  { route: '/agenda', target: 'calendar', title: TOUR.agendaTitle, body: TOUR.agendaBody },
  { route: '/agenda', target: 'day-form', prepare: 'open-today', title: TOUR.dayFormTitle, body: TOUR.dayFormBody },
  { route: '/agenda', target: 'attach', prepare: 'open-today', title: TOUR.attachTitle, body: TOUR.attachBody },
  { route: '/relatorios', target: 'reports', title: TOUR.reportsTitle, body: TOUR.reportsBody },
  { route: '/relatorios', target: 'assemble-btn', title: TOUR.assembleTitle, body: TOUR.assembleBody },
  { route: '/relatorios', target: 'ai-deck-btn', title: TOUR.aiDeckTitle, body: TOUR.aiDeckBody },
  { route: '/departamentos', target: 'departments', title: TOUR.deptTitle, body: TOUR.deptBody },
  { route: '/', target: 'language', title: TOUR.langTitle, body: TOUR.langBody },
  { route: '/', target: 'tour-replay', title: TOUR.replayTitle, body: TOUR.replayBody },
]
