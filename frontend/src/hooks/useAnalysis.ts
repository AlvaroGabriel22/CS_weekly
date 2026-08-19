/**
 * Hooks de "Analisar planilha com IA" (React Query v5).
 *
 * Fluxo: o usuário escreve em PT o que quer da planilha anexada; a IA apenas
 * INTERPRETA o pedido e o backend CALCULA (aritmética determinística). Se ele
 * aprovar, a receita fica salva e nas próximas semanas basta selecioná-la
 * (roda instantâneo, sem IA).
 *
 * A prévia pode demorar (~30s a 2min) quando a IA interpreta — sempre exibir
 * estado de progresso. Erros SEMPRE pelo chamador via parseApiError.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

/** Receita (vocabulário fechado do backend): operation, colunas, rótulo… */
export type AnalysisRecipeSpec = Record<string, unknown>

export interface AnalysisChartSeries {
  name: string
  values: number[]
}

export interface AnalysisChart {
  /** column | bar | line | pie */
  chart_type: string
  categories: string[]
  series: AnalysisChartSeries[]
}

export interface AnalysisResult {
  label: string
  /** [rótulo do grupo, rótulo do valor] */
  columns: string[]
  /** [grupo, valor já formatado] */
  rows: string[][]
  chart: AnalysisChart | null
  summary: string
  total: number | null
}

/** Uma análise da prévia: receita interpretada + resultado calculado. */
export interface AnalysisResultItem {
  recipe: AnalysisRecipeSpec
  result: AnalysisResult
}

/** Prévia calculada com sucesso (pode trazer VÁRIAS análises em `results`). */
export interface AnalysisPreviewOk {
  ok: true
  source: 'ai' | 'heuristic' | 'saved'
  /** Compat: receita da 1ª análise. */
  recipe: AnalysisRecipeSpec
  columns: string[]
  /** Compat: resultado da 1ª análise. */
  result: AnalysisResult
  /** Todas as análises do pedido (pode faltar em respostas antigas). */
  results?: AnalysisResultItem[] | null
  comparison: string | null
  /** Mensagens das análises que não puderam ser calculadas. */
  partial?: string[] | null
}

/** Prévia sem colunas casadas — a UI pede confirmação (status HTTP 200!). */
export interface AnalysisPreviewNeedsColumns {
  ok: false
  message: string
  needs_columns: boolean
  columns: string[]
  recipe: AnalysisRecipeSpec
  source: string
}

export type AnalysisPreviewResponse = AnalysisPreviewOk | AnalysisPreviewNeedsColumns

/** Análise salva do usuário (reofertada quando o formato da planilha bate). */
export interface SavedAnalysis {
  id: string
  label: string
  request_text: string
  last_used_at: string | null
  matches_current_file: boolean
}

/** Chaves de override aceitas pelo backend. */
export type ColumnRole = 'numerator' | 'denominator' | 'value' | 'group_by'

export function recipesKey(attachmentId: string) {
  return ['analysis', 'recipes', attachmentId] as const
}

/** Lê um campo textual da receita (ex.: recipe.numerator) com segurança. */
export function recipeColumn(recipe: AnalysisRecipeSpec | undefined, key: ColumnRole): string {
  const raw = recipe?.[key]
  return typeof raw === 'string' ? raw : ''
}

/** 'ratio' precisa de numerador/denominador; as demais, de uma coluna de valor. */
export function recipeOperation(recipe: AnalysisRecipeSpec | undefined): string {
  const raw = recipe?.operation
  return typeof raw === 'string' ? raw : ''
}

/** GET /analysis/recipes — análises salvas (marca as que combinam com o arquivo). */
export function useAnalysisRecipes(attachmentId: string, enabled = true) {
  return useQuery({
    queryKey: recipesKey(attachmentId),
    queryFn: async (): Promise<SavedAnalysis[]> => {
      const res = await api.get('/analysis/recipes', { params: { attachment_id: attachmentId } })
      return Array.isArray(res.data) ? (res.data as SavedAnalysis[]) : []
    },
    enabled: enabled && Boolean(attachmentId),
    staleTime: 30_000,
  })
}

export interface AnalysisPreviewInput {
  attachmentId: string
  requestText: string
  /** Reexecuta uma análise salva (instantâneo, sem IA). */
  recipeId?: string | null
  /** Confirmação manual das colunas quando a IA não teve certeza. */
  columnOverrides?: Partial<Record<ColumnRole, string>> | null
}

/**
 * POST /analysis/preview — calcula a prévia (não salva nada).
 * Pode demorar até ~2 min quando a IA interpreta o pedido; instantâneo com recipeId.
 * Atenção: o "precisa confirmar colunas" volta com HTTP 200 e `ok: false`.
 */
export function useAnalysisPreview() {
  return useMutation<AnalysisPreviewResponse, unknown, AnalysisPreviewInput>({
    mutationFn: async ({ attachmentId, requestText, recipeId, columnOverrides }) =>
      (
        await api.post('/analysis/preview', {
          attachment_id: attachmentId,
          request_text: requestText,
          recipe_id: recipeId ?? null,
          column_overrides:
            columnOverrides && Object.keys(columnOverrides).length > 0 ? columnOverrides : null,
        })
      ).data,
  })
}

export interface ApproveAnalysisInput {
  attachmentId: string
  requestText: string
  recipe: AnalysisRecipeSpec
  label: string
  total: number | null
}

/** POST /analysis/approve — salva a receita para reofertar nas próximas semanas. */
export function useApproveAnalysis() {
  const queryClient = useQueryClient()
  return useMutation<SavedAnalysis, unknown, ApproveAnalysisInput>({
    mutationFn: async ({ attachmentId, requestText, recipe, label, total }) =>
      (
        await api.post('/analysis/approve', {
          attachment_id: attachmentId,
          request_text: requestText,
          recipe,
          label,
          total,
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysis', 'recipes'] })
    },
  })
}

/** DELETE /analysis/recipes/:id — remove uma análise salva. */
export function useDeleteAnalysisRecipe() {
  const queryClient = useQueryClient()
  return useMutation<void, unknown, string>({
    mutationFn: async (recipeId: string) => {
      await api.delete(`/analysis/recipes/${recipeId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysis', 'recipes'] })
    },
  })
}
