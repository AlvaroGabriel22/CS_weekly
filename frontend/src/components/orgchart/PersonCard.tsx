import type { CSSProperties } from 'react'
import { Lock } from 'lucide-react'
import { Avatar } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { useI18n } from '@/i18n'
import { ORG } from '@/i18n/messages/org'
import { cn } from '@/lib/utils'
import type { OrgUser } from '@/types'

export interface PersonCardProps {
  user: OrgUser
  /** A página decide o que fazer (navegar ou avisar que o acesso é restrito). */
  onClick?: (user: OrgUser) => void
  className?: string
  style?: CSSProperties
}

/**
 * Cartão de pessoa do organograma: avatar + nome + cargo + setor.
 * Sem acesso (`viewer_can_access = false`) → cadeado no canto e visual esmaecido;
 * o clique continua ativo para a página explicar a regra em um toast.
 */
export function PersonCard({ user, onClick, className, style }: PersonCardProps) {
  const { t } = useI18n()
  const restricted = !user.viewer_can_access

  return (
    <button
      type="button"
      onClick={() => onClick?.(user)}
      style={style}
      title={restricted ? t(ORG.restricted) : t(ORG.viewWeeklysOf, { name: user.name })}
      aria-label={
        restricted
          ? `${user.name}, ${user.role} — ${t(ORG.restricted)}`
          : `${user.name}, ${user.role}`
      }
      className={cn(
        'group relative flex w-36 flex-col items-center gap-2 rounded-xl border border-border/60 bg-white px-3 py-4 text-center shadow-card',
        'transition-all duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:w-40',
        restricted
          ? 'opacity-60 saturate-50 hover:opacity-80'
          : 'hover:-translate-y-1 hover:border-brand-300 hover:shadow-elevated',
        className
      )}
    >
      {restricted && (
        <span
          className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-gray-100"
          aria-hidden="true"
        >
          <Lock className="h-3 w-3 text-gray-500" />
        </span>
      )}

      <Avatar src={user.photo_url} name={user.name} size="lg" />

      <span className="w-full min-w-0">
        <span className="block truncate text-sm font-semibold text-gray-900">{user.name}</span>
        <span className="mt-0.5 block truncate text-xs text-gray-500">{user.role}</span>
      </span>

      <Badge variant="default" className="pointer-events-none">
        {user.sector}
      </Badge>
    </button>
  )
}
