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

// ── Perfil de estilo + template do "Montar com IA" ──────────────────────────

export interface AiTemplateInfo {
  report_id: string
  week_number: number
  year: number
  version: number
}

export interface AiStyleResponse {
  /** Quantas montagens já alimentaram o aprendizado do padrão pessoal. */
  sample_count: number
  template: AiTemplateInfo | null
  profile_summary: {
    font: string | null
    title_size: number | null
    body_size: number | null
    content_slides: number | null
  } | null
}

const AI_STYLE_KEY = ['ai-style'] as const

export function useAiStyle() {
  return useQuery<AiStyleResponse>({
    queryKey: AI_STYLE_KEY,
    queryFn: async () => (await api.get('/ai/style')).data,
    staleTime: 30_000,
  })
}

/** Define/remove o weekly do histórico usado como modelo da IA. */
export function useSetAiTemplate() {
  const queryClient = useQueryClient()
  return useMutation<AiStyleResponse, unknown, { reportId: string | null }>({
    mutationFn: async ({ reportId }) =>
      (await api.put('/ai/template', { report_id: reportId })).data,
    onSuccess: data => queryClient.setQueryData(AI_STYLE_KEY, data),
  })
}

// ── Deck em um clique ───────────────────────────────────────────────────────

export interface DeckDraftResponse {
  layout: DeckLayout
  /**
   * "ai" = gerado pelo modelo; "template" = clonagem determinística do modelo
   * do usuário; "fallback" = montagem determinística padrão.
   */
  source: 'ai' | 'template' | 'fallback'
  model?: string | null
  duration_ms: number
  used_template?: boolean
  style_samples?: number
}

export interface DeckDraftInput {
  ref: WeekRef
  activityIds: string[]
  /**
   * undefined = usa o template ativo do usuário; 'none' = gerar sem modelo;
   * um report_id = usar este weekly como modelo nesta geração.
   */
  templateChoice?: string | 'none'
}

export function useDeckDraft() {
  return useMutation<DeckDraftResponse, unknown, DeckDraftInput>({
    mutationFn: async ({ ref, activityIds, templateChoice }) =>
      (
        await api.post('/ai/deck-draft', {
          year: ref.year,
          week_number: ref.week,
          activity_ids: activityIds,
          use_template: templateChoice !== 'none',
          template_report_id:
            templateChoice && templateChoice !== 'none' ? templateChoice : null,
        })
      ).data,
  })
}
