/**
 * Hooks de dados do FAQ / Report de bug.
 *
 * Contratos do backend:
 * - GET    /faq                       → BugReport[]  (ordenado por mais recente)
 * - POST   /faq                       → BugReport    ({ title, description })
 * - PUT    /faq/:id                   → BugReport    ({ response?, close }) — SÓ root
 * - GET    /faq/notify-users          → FaqNotifyUser[] — SÓ root
 * - POST   /faq/notify-users          → FaqNotifyUser[] ({ employee_id }) — SÓ root
 * - DELETE /faq/notify-users/:userId  → FaqNotifyUser[] — SÓ root
 *
 * Erros: os consumidores tratam via parseApiError (nunca ler err.response.data direto).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export interface BugReport {
  id: string
  title: string
  description: string
  author_name: string
  status: 'open' | 'closed'
  admin_response: string | null
  is_mine: boolean
  created_at: string
  closed_at: string | null
}

export interface FaqNotifyUser {
  id: string
  user_id: string
  name: string
  employee_id: string
  email: string
}

const FAQ_KEY = ['faq'] as const
const NOTIFY_KEY = ['faq', 'notify-users'] as const

/** Todas as solicitações (abertas e fechadas), já ordenadas pelo backend. */
export function useFaqReports() {
  return useQuery<BugReport[]>({
    queryKey: FAQ_KEY,
    queryFn: async () => (await api.get<BugReport[]>('/faq')).data,
  })
}

/** Abre uma nova solicitação; invalida a lista ao concluir. */
export function useCreateFaqReport() {
  const queryClient = useQueryClient()
  return useMutation<BugReport, unknown, { title: string; description: string }>({
    mutationFn: async (body) => (await api.post<BugReport>('/faq', body)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FAQ_KEY }),
  })
}

/** Responde e fecha uma solicitação (SÓ root). */
export function useAnswerFaqReport() {
  const queryClient = useQueryClient()
  return useMutation<BugReport, unknown, { id: string; response?: string; close: boolean }>({
    mutationFn: async ({ id, ...body }) => (await api.put<BugReport>(`/faq/${id}`, body)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: FAQ_KEY }),
  })
}

/** Lista de destinatários dos e-mails do FAQ (SÓ root). */
export function useFaqNotifyUsers(enabled: boolean) {
  return useQuery<FaqNotifyUser[]>({
    queryKey: NOTIFY_KEY,
    enabled,
    queryFn: async () => (await api.get<FaqNotifyUser[]>('/faq/notify-users')).data,
  })
}

/** Adiciona um destinatário por matrícula (SÓ root). Retorna a lista atualizada. */
export function useAddFaqNotifyUser() {
  const queryClient = useQueryClient()
  return useMutation<FaqNotifyUser[], unknown, { employee_id: string }>({
    mutationFn: async (body) => (await api.post<FaqNotifyUser[]>('/faq/notify-users', body)).data,
    onSuccess: (data) => queryClient.setQueryData(NOTIFY_KEY, data),
  })
}

/** Remove um destinatário (SÓ root). Retorna a lista atualizada. */
export function useRemoveFaqNotifyUser() {
  const queryClient = useQueryClient()
  return useMutation<FaqNotifyUser[], unknown, string>({
    mutationFn: async (userId) =>
      (await api.delete<FaqNotifyUser[]>(`/faq/notify-users/${userId}`)).data,
    onSuccess: (data) => queryClient.setQueryData(NOTIFY_KEY, data),
  })
}
