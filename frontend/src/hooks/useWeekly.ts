/**
 * Hooks de dados da Central de Relatórios (weekly reports).
 *
 * Contratos do backend:
 * - GET  /weekly                  → WeeklyReport[]
 * - POST /weekly/generate         → WeeklyReport ({ activity_ids, week_number, year, template_id?, language })
 * - GET  /weekly/:id/download     → blob .pptx
 * - GET  /templates               → Template[]
 * - GET  /activities?week_number=&year= → { items, total }
 *
 * Erros: os consumidores tratam via parseApiError / <ErrorState /> (nunca ler
 * err.response.data direto).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { formatDateIso, getWeekDaysOf, type WeekRef } from '@/lib/dates'
import type { Activity, Template, WeeklyReport } from '@/types'

import type { DeckLayout } from '@/components/reports/slideLayout'

/** Payload do POST /weekly/generate. */
export interface GenerateWeeklyPayload {
  activity_ids: string[]
  week_number: number
  year: number
  template_id?: string
  language: 'pt' | 'en'
  /** Layout do editor WYSIWYG — o PPTX é renderizado exatamente assim. */
  layout?: DeckLayout
}

interface ActivityListResponse {
  items: Activity[]
  total: number
}

/** Weeklys já gerados pelo usuário logado. */
export function useWeeklyReports() {
  return useQuery<WeeklyReport[]>({
    queryKey: ['weekly-reports'],
    queryFn: async () => (await api.get<WeeklyReport[]>('/weekly')).data,
  })
}

/** Templates ativos disponíveis para a geração. */
export function useTemplates() {
  return useQuery<Template[]>({
    queryKey: ['templates'],
    queryFn: async () => (await api.get<Template[]>('/templates')).data,
    staleTime: 5 * 60 * 1000,
  })
}

/** Atividades de uma semana (convenção da empresa: W1 = 1ª segunda do ano). */
export function useWeekActivities(ref: WeekRef) {
  return useQuery<Activity[]>({
    queryKey: ['activities-week', ref.year, ref.week],
    queryFn: async () => {
      // Filtra pelo INTERVALO DE DATAS da semana (seg→dom) — mesma fonte de
      // verdade da Agenda. Nunca depende do week_number gravado na criação,
      // então TODA atividade da semana aparece na montagem do PPT.
      const days = getWeekDaysOf(ref)
      const response = await api.get<ActivityListResponse>('/activities', {
        params: {
          start_date: formatDateIso(days[0]),
          end_date: formatDateIso(days[6]),
          page_size: 200,
        },
      })
      return response.data.items
    },
  })
}

/** Dispara a geração do weekly e invalida histórico/dashboard ao concluir. */
export function useGenerateWeekly() {
  const queryClient = useQueryClient()
  return useMutation<WeeklyReport, unknown, GenerateWeeklyPayload>({
    mutationFn: async (payload) =>
      (await api.post<WeeklyReport>('/weekly/generate', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['weekly-reports'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

/** Baixa o .pptx de um weekly (blob → download local). */
export async function downloadWeeklyPptx(
  report: Pick<WeeklyReport, 'id' | 'week_number' | 'year' | 'version'>,
): Promise<void> {
  const response = await api.get(`/weekly/${report.id}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = `Weekly_W${report.week_number}_${report.year}_v${report.version}.pptx`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
