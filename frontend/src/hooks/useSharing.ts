/**
 * Hooks de compartilhamento e conta:
 * - Concessões de acesso aos meus weeklys (por matrícula) — decisão do dono.
 * - Lista pessoal de destinatários de e-mail.
 * - Mudança de cargo (exige senha; o backend reflete os acessos na hora).
 * - Envio do weekly por e-mail + sugestão de assunto/corpo pela IA.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

// ── Concessões de acesso ────────────────────────────────────────────────────

export interface GrantedUser {
  id: string
  name: string
  employee_id: string
  role: string
  sector: string
  photo_url: string | null
}

const GRANTS_KEY = ['access-grants'] as const

export function useAccessGrants() {
  return useQuery<GrantedUser[]>({
    queryKey: GRANTS_KEY,
    queryFn: async () => (await api.get('/users/me/access-grants')).data,
  })
}

export function useAddAccessGrant() {
  const queryClient = useQueryClient()
  return useMutation<GrantedUser[], unknown, { employeeId: string }>({
    mutationFn: async ({ employeeId }) =>
      (await api.post('/users/me/access-grants', { employee_id: employeeId })).data,
    onSuccess: list => {
      queryClient.setQueryData(GRANTS_KEY, list)
      // cadeados do organograma podem mudar para o colega — invalida por via das dúvidas
      queryClient.invalidateQueries({ queryKey: ['org-users'], refetchType: 'none' })
    },
  })
}

export function useRemoveAccessGrant() {
  const queryClient = useQueryClient()
  return useMutation<GrantedUser[], unknown, { userId: string }>({
    mutationFn: async ({ userId }) =>
      (await api.delete(`/users/me/access-grants/${userId}`)).data,
    onSuccess: list => queryClient.setQueryData(GRANTS_KEY, list),
  })
}

// ── Destinatários de e-mail ─────────────────────────────────────────────────

export interface EmailRecipient {
  id: string
  email: string
  name: string | null
}

const RECIPIENTS_KEY = ['email-recipients'] as const

export function useEmailRecipients() {
  return useQuery<EmailRecipient[]>({
    queryKey: RECIPIENTS_KEY,
    queryFn: async () => (await api.get('/users/me/email-recipients')).data,
  })
}

export function useAddEmailRecipient() {
  const queryClient = useQueryClient()
  return useMutation<EmailRecipient[], unknown, { email: string; name?: string }>({
    mutationFn: async payload =>
      (await api.post('/users/me/email-recipients', payload)).data,
    onSuccess: list => queryClient.setQueryData(RECIPIENTS_KEY, list),
  })
}

export function useRemoveEmailRecipient() {
  const queryClient = useQueryClient()
  return useMutation<EmailRecipient[], unknown, { recipientId: string }>({
    mutationFn: async ({ recipientId }) =>
      (await api.delete(`/users/me/email-recipients/${recipientId}`)).data,
    onSuccess: list => queryClient.setQueryData(RECIPIENTS_KEY, list),
  })
}

// ── Mudança de cargo (exige senha) ──────────────────────────────────────────

export function useChangeRole() {
  const queryClient = useQueryClient()
  return useMutation<unknown, unknown, { role: string; password: string }>({
    mutationFn: async payload => (await api.put('/users/me/role', payload)).data,
    onSuccess: () => {
      // o cargo muda os acessos em tempo real — atualiza tudo que depende dele
      queryClient.invalidateQueries()
    },
  })
}

// ── Envio do weekly por e-mail ──────────────────────────────────────────────

export function useSendWeeklyEmail() {
  return useMutation<
    { sent: boolean; recipients: number },
    unknown,
    { reportId: string; recipients: string[]; subject: string; body: string }
  >({
    mutationFn: async ({ reportId, ...payload }) =>
      (await api.post(`/weekly/${reportId}/send-email`, payload)).data,
  })
}

export function useEmailSuggestion() {
  return useMutation<
    { subject: string; body: string },
    unknown,
    { reportId: string; language: 'pt' | 'en' | 'ko' }
  >({
    mutationFn: async ({ reportId, language }) =>
      (await api.post('/ai/email-suggestion', { report_id: reportId, language })).data,
  })
}
