/**
 * Seletor de idioma (pt/en/ko) — usado no TopBar e em Configurações.
 * variant="compact": só a bandeira (TopBar). variant="full": lista com rótulos.
 */
import { Globe } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { LANGS, useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'

export function LanguageSwitcher({ variant = 'compact' }: { variant?: 'compact' | 'full' }) {
  const { lang, setLang, t } = useI18n()
  const current = LANGS.find(l => l.value === lang) ?? LANGS[0]

  if (variant === 'full') {
    return (
      <div className="flex gap-2" role="group" aria-label={t(COMMON.language)}>
        {LANGS.map(option => (
          <button
            key={option.value}
            type="button"
            onClick={() => setLang(option.value)}
            aria-pressed={option.value === lang}
            className={`flex min-h-10 items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
              option.value === lang
                ? 'border-brand bg-brand-50 font-medium text-brand'
                : 'border-border bg-white text-gray-600 hover:border-brand-200 hover:bg-gray-50'
            }`}
          >
            <span aria-hidden>{option.flag}</span>
            {option.label}
          </button>
        ))}
      </div>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        aria-label={t(COMMON.language)}
        title={current.label}
      >
        <Globe className="h-5 w-5" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {LANGS.map(option => (
          <DropdownMenuItem
            key={option.value}
            onSelect={() => setLang(option.value)}
            className={option.value === lang ? 'bg-brand-50 font-medium text-brand' : ''}
          >
            <span className="mr-2" aria-hidden>{option.flag}</span>
            {option.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
