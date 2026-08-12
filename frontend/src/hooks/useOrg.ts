/**
 * Hooks da área de departamentos / colegas.
 *
 * - useOrgUsers            → GET /users/org                    (organograma)
 * - useColleagueWeeklys    → GET /weekly/user/:userId?year=    (lista de weeklys)
 * - useWeeklyReportFull    → GET /weekly/:id                   (relatório completo p/ SlideViewer)
 * - downloadWeeklyPptx     → GET /weekly/:id/download          (blob → Weekly_S{week}_{year}.pptx)
 */
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import { parseApiError } from '@/lib/errors'
import type { OrgUser, WeeklyReport, WeeklySummary } from '@/types'

/** Aceita a lista direta ou embrulhada em uma chave ({ users: [...] }). */
function asArray<T>(data: unknown, ...keys: string[]): T[] {
  if (Array.isArray(data)) return data as T[]
  if (data && typeof data === 'object') {
    for (const key of keys) {
      const value = (data as Record<string, unknown>)[key]
      if (Array.isArray(value)) return value as T[]
    }
  }
  return []
}

/** 403/404 não mudam ao repetir — evita retry inútil (e piscada dupla de erro). */
function smartRetry(failureCount: number, error: unknown): boolean {
  const kind = parseApiError(error).kind
  if (kind === 'forbidden' || kind === 'notfound') return false
  return failureCount < 1
}

/** Todos os usuários do organograma, com `viewer_can_access` calculado pelo backend. */
export function useOrgUsers() {
  return useQuery<OrgUser[]>({
    queryKey: ['org', 'users'],
    queryFn: async () => {
      const res = await api.get('/users/org')
      return asArray<OrgUser>(res.data, 'users', 'items')
    },
    staleTime: 5 * 60 * 1000,
    retry: smartRetry,
  })
}

/**
 * Weeklys de um colega. `year` indefinido → histórico completo ("Tudo").
 * Sempre ordenado por ano/semana/versão decrescentes.
 */
export function useColleagueWeeklys(userId: string | undefined, year?: number) {
  return useQuery<WeeklySummary[]>({
    queryKey: ['org', 'weeklys', userId, year ?? 'all'],
    enabled: Boolean(userId),
    queryFn: async () => {
      const res = await api.get(`/weekly/user/${userId}`, {
        params: year !== undefined ? { year } : undefined,
      })
      const items = asArray<WeeklySummary>(res.data, 'items', 'reports', 'weeklys')
      return [...items].sort(
        (a, b) => b.year - a.year || b.week_number - a.week_number || b.version - a.version
      )
    },
    staleTime: 60 * 1000,
    retry: smartRetry,
  })
}

/** Relatório completo (content) — habilita apenas quando há um id selecionado. */
export function useWeeklyReportFull(reportId: string | null) {
  return useQuery<WeeklyReport>({
    queryKey: ['org', 'weekly-report', reportId],
    enabled: Boolean(reportId),
    queryFn: async () => {
      const res = await api.get<WeeklyReport>(`/weekly/${reportId}`)
      return res.data
    },
    staleTime: 60 * 1000,
    retry: smartRetry,
  })
}

/** Baixa o .pptx do weekly como blob e dispara o download no navegador. */
export async function downloadWeeklyPptx(summary: {
  id: string
  week_number: number
  year: number
}): Promise<void> {
  const res = await api.get(`/weekly/${summary.id}/download`, { responseType: 'blob' })
  const blob = res.data as Blob
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `Weekly_S${summary.week_number}_${summary.year}.pptx`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
