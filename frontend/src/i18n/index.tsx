/**
 * i18n do QWI — pt (padrão), en, ko. Sem dependências externas.
 *
 * Padrão de uso:
 *   const { t, lang, locale } = useI18n()
 *   t(M.save)                          // M.save = { pt: 'Salvar', en: 'Save', ko: '저장' }
 *   t(M.count, { n: 3 })               // interpola {n}
 *   date.toLocaleDateString(locale, …) // datas localizadas via Intl
 *
 * Cada página/área define seu dicionário em src/i18n/messages/<área>.ts
 * (objetos Msg exportados) — nunca strings soltas na UI.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type Lang = 'pt' | 'en' | 'ko'

/** Uma mensagem localizada. pt é obrigatório (fallback). */
export interface Msg {
  pt: string
  en: string
  ko: string
}

export const LANGS: { value: Lang; label: string; flag: string }[] = [
  { value: 'pt', label: 'Português', flag: '🇧🇷' },
  { value: 'en', label: 'English', flag: '🇺🇸' },
  { value: 'ko', label: '한국어', flag: '🇰🇷' },
]

const LOCALES: Record<Lang, string> = { pt: 'pt-BR', en: 'en-US', ko: 'ko-KR' }
const STORAGE_KEY = 'qwi_lang'

function readStoredLang(): Lang {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === 'en' || stored === 'ko' || stored === 'pt' ? stored : 'pt'
}

interface I18nContextType {
  lang: Lang
  /** Locale BCP-47 para Intl/toLocaleDateString ('pt-BR' | 'en-US' | 'ko-KR'). */
  locale: string
  setLang: (lang: Lang) => void
  t: (msg: Msg, vars?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nContextType | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(readStoredLang)

  useEffect(() => {
    document.documentElement.lang = LOCALES[lang]
  }, [lang])

  const setLang = useCallback((next: Lang) => {
    localStorage.setItem(STORAGE_KEY, next)
    setLangState(next)
  }, [])

  const t = useCallback(
    (msg: Msg, vars?: Record<string, string | number>) => {
      let text = msg[lang] ?? msg.pt
      if (vars) {
        for (const [key, value] of Object.entries(vars)) {
          text = text.split(`{${key}}`).join(String(value))
        }
      }
      return text
    },
    [lang],
  )

  const value = useMemo(
    () => ({ lang, locale: LOCALES[lang], setLang, t }),
    [lang, setLang, t],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextType {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}

/** Atalho para definir dicionários com checagem de tipo. */
export function defineMessages<T extends Record<string, Msg>>(messages: T): T {
  return messages
}
