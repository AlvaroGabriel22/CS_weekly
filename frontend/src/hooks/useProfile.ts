/**
 * Hooks e utilidades do perfil do usuário: foto, nome, senha e preferências
 * de escrita (writing profile). Toda mutação que altera dados exibidos no
 * restante do app (foto/nome/preferências) chama refreshUser() para manter
 * o AuthContext em dia — a foto aparece no topbar e no organograma.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import type { User, WritingProfile } from '@/types'

// ── Foto de perfil ──────────────────────────────────────────────────────────

/** Tipos aceitos pelo backend (JPG, PNG, WEBP) — usar no accept do input. */
export const PHOTO_ACCEPT = 'image/jpeg,image/png,image/webp'
export const PHOTO_MAX_BYTES = 5 * 1024 * 1024
const PHOTO_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp']

/** Código de erro para a UI traduzir (mb = tamanho em MB, 1 casa decimal). */
export type PhotoValidationError = { code: 'type' } | { code: 'size'; mb: number }

/** Validação NO CLIENTE antes do upload — espelha as regras do backend. */
export function validatePhotoFile(file: File): PhotoValidationError | null {
  if (!PHOTO_MIME_TYPES.includes(file.type)) {
    return { code: 'type' }
  }
  if (file.size > PHOTO_MAX_BYTES) {
    return { code: 'size', mb: Math.round((file.size / (1024 * 1024)) * 10) / 10 }
  }
  return null
}

/** POST /users/me/photo (multipart, campo "file") + refreshUser(). */
export function useUploadPhoto() {
  const { refreshUser } = useAuth()
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.post<User>('/users/me/photo', formData, {
        // Sobrescreve o application/json padrão do cliente; o navegador
        // completa o boundary do multipart automaticamente.
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data
    },
    onSuccess: async () => {
      await refreshUser()
    },
  })
}

// ── Dados pessoais ──────────────────────────────────────────────────────────

/** PATCH /users/profile (nome) + refreshUser(). */
export function useUpdateProfile() {
  const { refreshUser } = useAuth()
  return useMutation({
    mutationFn: async (payload: { name: string }) => {
      const res = await api.patch<User>('/users/profile', payload)
      return res.data
    },
    onSuccess: async () => {
      await refreshUser()
    },
  })
}

// ── Senha ───────────────────────────────────────────────────────────────────

export interface PasswordChangePayload {
  current_password: string
  new_password: string
  new_password_confirm: string
}

/** PUT /users/me/password — erros de campo vêm via parseApiError(err).fields. */
export function useChangePassword() {
  return useMutation({
    mutationFn: async (payload: PasswordChangePayload) => {
      const res = await api.put<User>('/users/me/password', payload)
      return res.data
    },
  })
}

export interface PasswordStrength {
  /** Nível para a UI traduzir (weak/medium/strong). */
  level: 'weak' | 'medium' | 'strong'
  /** Largura da barra (0–100). */
  percent: number
  barClass: string
  textClass: string
}

/** Medidor simples por comprimento: <8 fraca, 8–9 média, ≥10 forte. */
export function passwordStrength(password: string): PasswordStrength {
  const len = password.length
  if (len >= 10) {
    return { level: 'strong', percent: 100, barClass: 'bg-green-500', textClass: 'text-green-700' }
  }
  if (len >= 8) {
    return { level: 'medium', percent: 66, barClass: 'bg-yellow-500', textClass: 'text-yellow-700' }
  }
  return {
    level: 'weak',
    percent: Math.max(8, Math.round((len / 8) * 33)),
    barClass: 'bg-orange-500',
    textClass: 'text-orange-700',
  }
}

// ── Preferências de escrita ─────────────────────────────────────────────────

export const WRITING_PROFILE_KEY = ['writing-profile']

/** GET /users/writing-profile. */
export function useWritingProfile() {
  return useQuery({
    queryKey: WRITING_PROFILE_KEY,
    queryFn: async () => {
      const res = await api.get<WritingProfile>('/users/writing-profile')
      return res.data
    },
  })
}

/** PATCH /users/writing-profile — atualiza o cache e o AuthContext. */
export function useUpdateWritingProfile() {
  const queryClient = useQueryClient()
  const { refreshUser } = useAuth()
  return useMutation({
    mutationFn: async (payload: Partial<WritingProfile>) => {
      const res = await api.patch<WritingProfile>('/users/writing-profile', payload)
      return res.data
    },
    onSuccess: async (data) => {
      queryClient.setQueryData(WRITING_PROFILE_KEY, data)
      // user.writing_profile também vive no /auth/me — mantém tudo em sincronia.
      await refreshUser()
    },
  })
}
