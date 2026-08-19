/**
 * Perfil de conhecimento do usuário — "o que a IA já sabe sobre você".
 *
 * - useKnowledge: GET /ai/knowledge → o que o usuário DECLAROU (notas) vs. o
 *   que a IA APRENDEU do histórico dele (KPIs e entidades), com contagem de
 *   semanas usadas como base.
 * - useIgnoreKnowledge: POST /ai/knowledge/ignore → descarta um item aprendido
 *   ("não acompanho isso"); o backend devolve o card já atualizado, que
 *   escrevemos direto no cache.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

/** Campos de entidade que a IA pode aprender (chaves de `learned.entities`). */
export type EntityField = 'line' | 'supplier' | 'process' | 'product' | 'defect_type'

export interface KnowledgeProfile {
  declared: {
    about_me: string
    personal_prompt: string
  }
  learned: {
    kpis: string[]
    entities: Record<string, string[]>
  }
  sample_count: number
}

/** Descarte de um item aprendido. */
export interface IgnoreKnowledgePayload {
  kind: 'kpi' | 'entity'
  value: string
  /** Obrigatório quando kind === 'entity'. */
  entity_field?: string
}

export const KNOWLEDGE_KEY = ['ai-knowledge'] as const

/** GET /ai/knowledge. */
export function useKnowledge() {
  return useQuery<KnowledgeProfile>({
    queryKey: KNOWLEDGE_KEY,
    queryFn: async () => (await api.get<KnowledgeProfile>('/ai/knowledge')).data,
  })
}

/** POST /ai/knowledge/ignore — devolve o card atualizado → grava no cache. */
export function useIgnoreKnowledge() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: IgnoreKnowledgePayload) => {
      const res = await api.post<KnowledgeProfile>('/ai/knowledge/ignore', payload)
      return res.data
    },
    onSuccess: (data) => {
      queryClient.setQueryData(KNOWLEDGE_KEY, data)
    },
  })
}
