/**
 * Hooks dos recursos de IA (opcionais — o usuário usa se quiser).
 *
 * - useDepartmentRollup / useGenerateRollup: copiloto do gestor
 *   (GET cache + POST gera/regenera; restrito à gestão no backend).
 * - useDeckDraft: deck em um clique (devolve um DeckLayout pronto; o backend
 *   garante fallback determinístico se a IA falhar → nunca retorna vazio).
 *
 * As chamadas podem demorar minutos com o modelo local — sempre exibir
 * estado de progresso e nunca bloquear o fluxo manual.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { WeekRef } from '@/lib/dates'
import type { DeckLayout } from '@/components/reports/slideLayout'

// ── Copiloto do gestor ──────────────────────────────────────────────────────

export interface RollupPerson {
  name: string
  role: string
  has_weekly: boolean
  headline: string
}

export interface RollupContent {
  summary: string
  highlights: string[]
  kpis: string[]
  risks: string[]
  by_person: RollupPerson[]
  next_steps: string[]
}

export interface RollupResponse {
  content: RollupContent | null
  model?: string | null
  generated_at?: string
}

export function rollupKey(sector: string, ref: WeekRef) {
  return ['dept-rollup', sector, ref.year, ref.week] as const
}

/** Cache existente do resumo (não dispara geração). */
export function useDepartmentRollup(sector: string, ref: WeekRef, enabled: boolean) {
  return useQuery<RollupResponse>({
    queryKey: rollupKey(sector, ref),
    queryFn: async () =>
      (
        await api.get('/ai/department-rollup', {
          params: { sector, year: ref.year, week_number: ref.week },
        })
      ).data,
    enabled,
    staleTime: 60_000,
  })
}

export function useGenerateRollup(sector: string, ref: WeekRef) {
  const queryClient = useQueryClient()
  return useMutation<RollupResponse, unknown, { force?: boolean }>({
    mutationFn: async ({ force = false } = {}) =>
      (
        await api.post('/ai/department-rollup', {
          sector,
          year: ref.year,
          week_number: ref.week,
          force,
        })
      ).data,
    onSuccess: data => {
      queryClient.setQueryData(rollupKey(sector, ref), data)
    },
  })
}

// ── Deck em um clique ───────────────────────────────────────────────────────

export interface DeckDraftResponse {
  layout: DeckLayout
  /** "ai" = gerado pelo modelo; "fallback" = montagem determinística. */
  source: 'ai' | 'fallback'
  model?: string | null
  duration_ms: number
}

export function useDeckDraft() {
  return useMutation<DeckDraftResponse, unknown, { ref: WeekRef; activityIds: string[] }>({
    mutationFn: async ({ ref, activityIds }) =>
      (
        await api.post('/ai/deck-draft', {
          year: ref.year,
          week_number: ref.week,
          activity_ids: activityIds,
        })
      ).data,
  })
}
