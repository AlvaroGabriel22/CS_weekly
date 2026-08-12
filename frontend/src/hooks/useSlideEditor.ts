/**
 * Hooks de apoio do editor WYSIWYG de montagem:
 * - useAttachmentImage: baixa a imagem do anexo AUTENTICADO (axios) e devolve
 *   um object URL cacheado (a tag <img> não envia Authorization).
 * - useSlideLayoutPrefs: GET/PUT /users/me/slide-layout (elementos fixados).
 */
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { SlideElement } from '@/components/reports/slideLayout'

const objectUrlCache = new Map<string, string>()
const pending = new Map<string, Promise<string>>()

async function fetchAttachmentUrl(attachmentId: string): Promise<string> {
  const cached = objectUrlCache.get(attachmentId)
  if (cached) return cached
  let promise = pending.get(attachmentId)
  if (!promise) {
    promise = api
      .get(`/activities/attachments/${attachmentId}/file`, { responseType: 'blob' })
      .then(res => {
        const url = URL.createObjectURL(res.data as Blob)
        objectUrlCache.set(attachmentId, url)
        pending.delete(attachmentId)
        return url
      })
      .catch(err => {
        pending.delete(attachmentId)
        throw err
      })
    pending.set(attachmentId, promise)
  }
  return promise
}

/** URL exibível da imagem do anexo (null enquanto carrega; '' se falhou). */
export function useAttachmentImage(attachmentId: string | undefined): string | null {
  const [url, setUrl] = useState<string | null>(
    attachmentId ? objectUrlCache.get(attachmentId) ?? null : null,
  )

  useEffect(() => {
    if (!attachmentId) return
    let alive = true
    fetchAttachmentUrl(attachmentId)
      .then(u => { if (alive) setUrl(u) })
      .catch(() => { if (alive) setUrl('') })
    return () => { alive = false }
  }, [attachmentId])

  return url
}

interface SlideLayoutPrefs {
  pinned: SlideElement[]
}

/** Elementos fixados do usuário (persistem entre apresentações). */
export function useSlideLayoutPrefs() {
  return useQuery({
    queryKey: ['slide-layout-prefs'],
    queryFn: async (): Promise<SlideLayoutPrefs> => {
      const res = await api.get('/users/me/slide-layout')
      const layout: unknown = res.data?.layout
      const pinned =
        layout && typeof layout === 'object' && Array.isArray((layout as { pinned?: unknown }).pinned)
          ? ((layout as { pinned: SlideElement[] }).pinned)
          : []
      return { pinned }
    },
    staleTime: 5 * 60_000,
  })
}

export function useSaveSlideLayoutPrefs() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (pinned: SlideElement[]) => {
      await api.put('/users/me/slide-layout', { layout: { pinned } })
    },
    onSuccess: (_data, pinned) => {
      queryClient.setQueryData(['slide-layout-prefs'], { pinned })
    },
  })
}
