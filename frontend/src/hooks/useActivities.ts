/**
 * Hooks de dados da Agenda (React Query v5).
 *
 * A agenda carrega as atividades do PERÍODO VISÍVEL do calendário mensal
 * (da primeira à última célula da matriz seg→dom, incluindo dias dos meses
 * vizinhos) e faz mutações OTIMISTAS sobre esse cache, com rollback em erro.
 *
 * Datas trafegam SEMPRE como "AAAA-MM-DD" via formatDateIso/parseIsoDate.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { Activity } from '@/types'
import { formatDateIso, getWeekRef, monthMatrix, parseIsoDate } from '@/lib/dates'

/** Mês exibido no calendário (month: 0–11, como Date#getMonth). */
export interface MonthRef {
  year: number
  month: number
}

export function monthActivitiesKey(ref: MonthRef) {
  return ['activities', 'month', ref.year, ref.month] as const
}

/** Primeiro e último dia VISÍVEIS na matriz do mês (inclui meses vizinhos). */
export function visibleMonthRange(ref: MonthRef): { start: Date; end: Date } {
  const rows = monthMatrix(ref.year, ref.month)
  return { start: rows[0][0], end: rows[rows.length - 1][6] }
}

/** GET /activities do período visível do mês. */
export function useMonthActivities(ref: MonthRef) {
  return useQuery({
    queryKey: monthActivitiesKey(ref),
    queryFn: async (): Promise<Activity[]> => {
      const { start, end } = visibleMonthRange(ref)
      const res = await api.get('/activities', {
        params: {
          start_date: formatDateIso(start),
          end_date: formatDateIso(end),
          page_size: 200,
        },
      })
      const items: unknown = res.data?.items
      return Array.isArray(items) ? (items as Activity[]) : []
    },
    // Mantém o mês anterior na tela durante a navegação (sem piscar skeleton).
    placeholderData: keepPreviousData,
  })
}

export interface ActivityCreatePayload {
  title: string
  description?: string | null
  /** "AAAA-MM-DD" — gere com formatDateIso(dia). */
  activity_date: string
  include_in_weekly?: boolean
}

export interface ActivityUpdatePayload {
  id: string
  title?: string
  description?: string | null
  /** "AAAA-MM-DD" — gere com formatDateIso(dia). */
  activity_date?: string
  include_in_weekly?: boolean
}

/** Prefixo dos ids otimistas (itens ainda não confirmados pelo servidor). */
export const OPTIMISTIC_ID_PREFIX = 'otimista-'

export function isOptimisticActivity(activity: Activity): boolean {
  return activity.id.startsWith(OPTIMISTIC_ID_PREFIX)
}

let optimisticSeq = 0

function buildOptimisticActivity(payload: ActivityCreatePayload): Activity {
  const day = parseIsoDate(payload.activity_date)
  const weekRef = getWeekRef(day)
  const nowIso = new Date().toISOString()
  return {
    id: `${OPTIMISTIC_ID_PREFIX}${++optimisticSeq}-${Date.now()}`,
    title: payload.title,
    description: payload.description ?? null,
    project: null,
    category: null,
    department: null,
    activity_date: payload.activity_date,
    tags: [],
    notes: null,
    include_in_weekly: payload.include_in_weekly ?? true,
    status: 'draft',
    week_number: weekRef.week,
    year: weekRef.year,
    created_at: nowIso,
    updated_at: nowIso,
    metadata_entry: null,
    attachments: [],
  }
}

/** POST /activities — insere otimista no cache do mês; reverte se falhar. */
export function useCreateActivity(ref: MonthRef) {
  const queryClient = useQueryClient()
  const key = monthActivitiesKey(ref)
  return useMutation({
    mutationFn: async (payload: ActivityCreatePayload): Promise<Activity> => {
      const res = await api.post('/activities', payload)
      return res.data as Activity
    },
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData<Activity[]>(key)
      const optimistic = buildOptimisticActivity(payload)
      queryClient.setQueryData<Activity[]>(key, (old = []) => [...old, optimistic])
      return { previous, optimisticId: optimistic.id }
    },
    onSuccess: (created, _payload, context) => {
      queryClient.setQueryData<Activity[]>(key, (old = []) =>
        old.map(activity => (activity.id === context.optimisticId ? created : activity))
      )
    },
    onError: (_err, _payload, context) => {
      if (context) queryClient.setQueryData(key, context.previous)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] })
    },
  })
}

/** PATCH /activities/:id — aplica otimista no cache do mês; reverte se falhar. */
export function useUpdateActivity(ref: MonthRef) {
  const queryClient = useQueryClient()
  const key = monthActivitiesKey(ref)
  return useMutation({
    mutationFn: async (payload: ActivityUpdatePayload): Promise<Activity> => {
      const { id, ...changes } = payload
      const res = await api.patch(`/activities/${id}`, changes)
      return res.data as Activity
    },
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData<Activity[]>(key)
      const { id, ...changes } = payload
      queryClient.setQueryData<Activity[]>(key, (old = []) =>
        old.map(activity => (activity.id === id ? { ...activity, ...changes } : activity))
      )
      return { previous }
    },
    onError: (_err, _payload, context) => {
      if (context) queryClient.setQueryData(key, context.previous)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] })
    },
  })
}

export interface AttachmentUploadPayload {
  activityId: string
  file: File
}

/**
 * POST /activities/:id/attachments (multipart, campo "file").
 * A resposta é o ActivityResponse COMPLETO — substitui a atividade no cache do mês.
 */
export function useUploadAttachment(ref: MonthRef) {
  const queryClient = useQueryClient()
  const key = monthActivitiesKey(ref)
  return useMutation({
    mutationFn: async ({ activityId, file }: AttachmentUploadPayload): Promise<Activity> => {
      const form = new FormData()
      form.append('file', file)
      const res = await api.post(`/activities/${activityId}/attachments`, form)
      return res.data as Activity
    },
    onSuccess: updated => {
      queryClient.setQueryData<Activity[]>(key, (old = []) =>
        old.map(activity => (activity.id === updated.id ? updated : activity))
      )
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'], refetchType: 'none' })
    },
  })
}

export interface AttachmentDeletePayload {
  activityId: string
  attachmentId: string
}

/**
 * DELETE /activities/:id/attachments/:attachmentId.
 * A resposta também é o ActivityResponse — substitui a atividade no cache do mês.
 */
export function useDeleteAttachment(ref: MonthRef) {
  const queryClient = useQueryClient()
  const key = monthActivitiesKey(ref)
  return useMutation({
    mutationFn: async ({ activityId, attachmentId }: AttachmentDeletePayload): Promise<Activity> => {
      const res = await api.delete(`/activities/${activityId}/attachments/${attachmentId}`)
      return res.data as Activity
    },
    onSuccess: updated => {
      queryClient.setQueryData<Activity[]>(key, (old = []) =>
        old.map(activity => (activity.id === updated.id ? updated : activity))
      )
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'], refetchType: 'none' })
    },
  })
}

/** DELETE /activities/:id — remove otimista do cache do mês; reverte se falhar. */
export function useDeleteActivity(ref: MonthRef) {
  const queryClient = useQueryClient()
  const key = monthActivitiesKey(ref)
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/activities/${id}`)
    },
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueryData<Activity[]>(key)
      queryClient.setQueryData<Activity[]>(key, (old = []) =>
        old.filter(activity => activity.id !== id)
      )
      return { previous }
    },
    onError: (_err, _id, context) => {
      if (context) queryClient.setQueryData(key, context.previous)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['activities'] })
    },
  })
}
