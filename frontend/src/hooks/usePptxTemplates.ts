/**
 * Modelos de PPT do usuário (.pptx enviados para a IA usar de referência).
 *
 * - usePptxTemplates: lista (até 2) os modelos enviados.
 * - useUploadPptxTemplate: envia um .pptx (multipart). O backend converte o
 *   arquivo e devolve o PptxTemplate criado. Erros (409 limite, 422 inválido,
 *   413 tamanho) já vêm com mensagem pronta — consumir via parseApiError.
 * - useDeletePptxTemplate: remove um modelo (DELETE → 204).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { DeckLayout } from '@/components/reports/slideLayout'

export interface PptxTemplate {
  id: string
  name: string
  slides_count: number
  created_at: string
  /** false = o registro existe mas o .pptx sumiu do disco (precisa reenviar). */
  available: boolean
}

export interface PptxTemplateDetail extends PptxTemplate {
  layout: DeckLayout
}

/** Marcação: { [slideId]: { [elementId]: slot } }. */
export type SlotMarks = Record<string, Record<string, string>>

const PPTX_TEMPLATES_KEY = ['pptx-templates'] as const

export function usePptxTemplates() {
  return useQuery<PptxTemplate[]>({
    queryKey: PPTX_TEMPLATES_KEY,
    queryFn: async () => (await api.get('/pptx-templates')).data,
    staleTime: 30_000,
  })
}

export function useUploadPptxTemplate() {
  const queryClient = useQueryClient()
  return useMutation<PptxTemplate, unknown, File>({
    mutationFn: async (file) => {
      const form = new FormData()
      form.append('file', file)
      // Sem header manual: o interceptor de api.ts remove o Content-Type
      // para FormData, deixando o navegador definir o multipart/boundary.
      return (await api.post('/pptx-templates', form)).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PPTX_TEMPLATES_KEY })
    },
  })
}

/** Modelo com o layout completo — usado na tela de marcação de slots. */
export function usePptxTemplate(id: string | null) {
  return useQuery<PptxTemplateDetail>({
    queryKey: [...PPTX_TEMPLATES_KEY, id],
    queryFn: async () => (await api.get(`/pptx-templates/${id}`)).data,
    enabled: Boolean(id),
  })
}

/** Salva o papel (slot) de cada elemento do modelo. */
export function useSaveTemplateSlots(id: string | null) {
  const queryClient = useQueryClient()
  return useMutation<PptxTemplateDetail, unknown, SlotMarks>({
    mutationFn: async (slots) =>
      (await api.patch(`/pptx-templates/${id}/slots`, { slots })).data,
    onSuccess: (detail) => {
      queryClient.setQueryData([...PPTX_TEMPLATES_KEY, id], detail)
      queryClient.invalidateQueries({ queryKey: PPTX_TEMPLATES_KEY })
    },
  })
}

export function useDeletePptxTemplate() {
  const queryClient = useQueryClient()
  return useMutation<void, unknown, string>({
    mutationFn: async (id) => {
      await api.delete(`/pptx-templates/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PPTX_TEMPLATES_KEY })
    },
  })
}
