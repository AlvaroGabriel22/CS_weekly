/**
 * Contrato ÚNICO de tratamento de erros do frontend QWI.
 *
 * O backend responde erros em três formatos:
 *  1. 400 regra de negócio:  { detail: { field, message, hint } }
 *  2. 422 validação Pydantic: { detail: [ { loc: [...,'campo'], msg }, ... ] }
 *  3. Demais:                 { detail: "mensagem" } ou sem corpo (rede)
 *
 * TODO componente deve consumir erros SOMENTE via parseApiError — nunca ler
 * err.response.data diretamente.
 */
import { AxiosError } from 'axios'

export interface FieldErrorInfo {
  message: string
  hint?: string
}

export type ErrorKind =
  | 'field'      // erro(s) apontando campo(s) de formulário
  | 'auth'       // 401 — sessão expirada
  | 'forbidden'  // 403 — sem permissão
  | 'notfound'   // 404
  | 'network'    // sem resposta do servidor
  | 'server'     // 5xx
  | 'message'    // demais erros com mensagem

export interface NormalizedError {
  kind: ErrorKind
  /** Mensagem geral, sempre presente e em pt-BR, segura para exibir. */
  message: string
  /** Erros por campo (vazio quando não houver). */
  fields: Record<string, FieldErrorInfo>
  status?: number
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

/** Normaliza qualquer erro (axios ou não) para o contrato NormalizedError. */
export function parseApiError(err: unknown): NormalizedError {
  const fallback: NormalizedError = {
    kind: 'message',
    message: 'Algo deu errado. Tente novamente.',
    fields: {},
  }

  if (!(err instanceof AxiosError)) {
    if (err instanceof Error && err.message) return { ...fallback, message: err.message }
    return fallback
  }

  if (!err.response) {
    return {
      kind: 'network',
      message: 'Sem conexão com o servidor. Verifique sua internet e tente novamente.',
      fields: {},
    }
  }

  const status = err.response.status
  const detail: unknown = isRecord(err.response.data) ? err.response.data.detail : undefined

  // 422 — lista de erros do Pydantic
  if (Array.isArray(detail)) {
    const fields: Record<string, FieldErrorInfo> = {}
    for (const item of detail) {
      if (!isRecord(item)) continue
      const loc = Array.isArray(item.loc) ? item.loc : []
      const field = String(loc[loc.length - 1] ?? '')
      if (field) {
        fields[field] = { message: translatePydanticMsg(String(item.msg ?? 'Valor inválido.')) }
      }
    }
    if (Object.keys(fields).length > 0) {
      return { kind: 'field', message: 'Corrija os campos destacados.', fields, status }
    }
  }

  // 400 — regra de negócio com campo apontado
  if (isRecord(detail) && typeof detail.field === 'string') {
    return {
      kind: 'field',
      message: String(detail.message ?? 'Corrija o campo destacado.'),
      fields: {
        [detail.field]: {
          message: String(detail.message ?? 'Valor inválido.'),
          hint: detail.hint ? String(detail.hint) : undefined,
        },
      },
      status,
    }
  }

  const detailMsg = typeof detail === 'string' ? detail : undefined

  if (status === 401) {
    return { kind: 'auth', message: 'Sua sessão expirou. Entre novamente.', fields: {}, status }
  }
  if (status === 403) {
    return {
      kind: 'forbidden',
      message: detailMsg ?? 'Você não tem permissão para acessar este recurso.',
      fields: {},
      status,
    }
  }
  if (status === 404) {
    return { kind: 'notfound', message: detailMsg ?? 'Não encontrado.', fields: {}, status }
  }
  if (status >= 500) {
    // 502/503 são erros operacionais que o backend emite de propósito com
    // mensagem amigável (ex.: SMTP não configurado, IA indisponível).
    const operational = (status === 502 || status === 503) && detailMsg
    return {
      kind: 'server',
      message: operational ? detailMsg : 'Erro no servidor. Tente novamente em instantes.',
      fields: {},
      status,
    }
  }

  return { kind: 'message', message: detailMsg ?? fallback.message, fields: {}, status }
}

/** Atalho: só a mensagem geral. */
export function getErrorMessage(err: unknown): string {
  return parseApiError(err).message
}

/** Traduções das mensagens mais comuns do Pydantic. */
function translatePydanticMsg(msg: string): string {
  const lower = msg.toLowerCase()
  if (lower.includes('valid email')) return 'Email inválido.'
  if (lower.includes('at least 6')) return 'Use no mínimo 6 caracteres.'
  if (lower.includes('at least 2')) return 'Muito curto (mínimo 2 caracteres).'
  if (lower.includes('field required')) return 'Campo obrigatório.'
  if (lower.includes('string should have')) return 'Tamanho inválido.'
  return msg
}
