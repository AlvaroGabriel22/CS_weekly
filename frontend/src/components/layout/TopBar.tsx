import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, CalendarDays, CircleHelp, LogOut, Menu, Settings, User as UserIcon, X } from 'lucide-react'
import { useTour } from '@/components/tour/tourContext'
import { TOUR } from '@/i18n/messages/tour'
import { useAuth } from '@/contexts/AuthContext'
import { currentWeekRef, getWeekDaysOf, weekLabel, type WeekRef } from '@/lib/dates'
import { Avatar } from '@/components/ui/avatar'
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { defineMessages, useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { cn } from '@/lib/utils'

const M = defineMessages({
  openMenu: { pt: 'Abrir menu', en: 'Open menu', ko: '메뉴 열기' },
  closeMenu: { pt: 'Fechar menu', en: 'Close menu', ko: '메뉴 닫기' },
  userMenu: { pt: 'Menu do usuário', en: 'User menu', ko: '사용자 메뉴' },
  mainNav: { pt: 'Navegação principal', en: 'Main navigation', ko: '주 메뉴' },
})

const NAV_ITEMS: { to: string; label: Msg; end: boolean }[] = [
  { to: '/', label: COMMON.home, end: true },
  { to: '/agenda', label: COMMON.agenda, end: false },
  { to: '/relatorios', label: COMMON.reports, end: false },
  { to: '/departamentos', label: COMMON.departments, end: false },
]

/** Rotas onde a topbar entra no modo mínimo (só "Voltar"). */
const MINIMAL_PREFIXES = ['/departamentos', '/colegas']

/** Setor vindo do state de navegação (organograma → colega), se houver. */
function sectorFromState(state: unknown): string | undefined {
  if (typeof state !== 'object' || state === null) return undefined
  const sector = (state as { sector?: unknown }).sector
  return typeof sector === 'string' && sector.length > 0 ? sector : undefined
}

/**
 * Destino do "Voltar" hierárquico (uma tela por clique):
 * /colegas/:id → organograma do setor do colega (fallback /departamentos);
 * /departamentos/:sector → /departamentos; /departamentos → / (Início).
 */
function backTarget(pathname: string, state: unknown): string {
  const path = pathname.replace(/\/+$/, '')
  if (path.startsWith('/colegas')) {
    const sector = sectorFromState(state)
    return sector ? `/departamentos/${sector}` : '/departamentos'
  }
  if (path.startsWith('/departamentos/')) return '/departamentos'
  return '/'
}

function LogoMark({ withText = true }: { withText?: boolean }) {
  return (
    <span className="flex items-center gap-2">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-blue-700 text-sm font-bold text-white shadow-sm">
        Q
      </span>
      {withText && <span className="text-base font-bold tracking-tight text-gray-900">QWI</span>}
    </span>
  )
}

/** "10 de ago. – 16 de ago." no idioma ativo (seg→dom da semana). */
function weekRange(ref: WeekRef, locale: string): string {
  const days = getWeekDaysOf(ref)
  const fmt = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short' })
  return `${fmt.format(days[0])} – ${fmt.format(days[6])}`
}

/** Botão discreto para rever o guia de primeiro acesso. */
function TourReplayButton() {
  const { t } = useI18n()
  const { start, active } = useTour()
  return (
    <button
      type="button"
      data-tour="tour-replay"
      onClick={() => !active && start(false)}
      aria-label={t(TOUR.replay)}
      title={t(TOUR.replay)}
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
    >
      <CircleHelp className="h-5 w-5" aria-hidden />
    </button>
  )
}

function WeekChip() {
  const { locale } = useI18n()
  const week = useMemo(() => currentWeekRef(), [])
  return (
    <span className="hidden items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-700 sm:inline-flex">
      <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
      <span>
        {weekLabel(week)} · {weekRange(week, locale)}
      </span>
    </span>
  )
}

/**
 * Topbar fixa do app.
 * - Variante completa: logo + navegação + chip da semana + idioma + menu do usuário.
 * - Variante mínima (automática em /departamentos* e /colegas*): "Voltar ao início" + idioma.
 * - Mobile (<md): navegação vira menu hambúrguer com drawer lateral.
 */
export function TopBar() {
  const { user, logout } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()
  const location = useLocation()
  const { pathname } = location
  const [mobileOpen, setMobileOpen] = useState(false)

  const minimal = MINIMAL_PREFIXES.some(prefix => pathname.startsWith(prefix))

  // Fecha o drawer ao navegar e com Escape.
  useEffect(() => {
    setMobileOpen(false)
  }, [pathname])

  useEffect(() => {
    if (!mobileOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [mobileOpen])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (minimal) {
    return (
      <header className="sticky top-0 z-40 border-b border-border bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
          <Link
            to={backTarget(pathname, location.state)}
            className="-ml-2 inline-flex min-h-[40px] min-w-0 items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="truncate">{t(COMMON.back)}</span>
          </Link>
          <div className="flex shrink-0 items-center gap-1.5">
            <LanguageSwitcher variant="compact" />
            <Link to="/" aria-label={t(COMMON.home)} className="rounded-lg">
              <LogoMark withText={false} />
            </Link>
          </div>
        </div>
      </header>
    )
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-white">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:px-6">
        {/* Hambúrguer (mobile) */}
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          aria-label={t(M.openMenu)}
          className="-ml-2 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900 md:hidden"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>

        {/* Logo */}
        <Link to="/" aria-label={t(COMMON.home)} className="shrink-0 rounded-lg">
          <LogoMark />
        </Link>

        {/* Navegação (desktop) */}
        <nav aria-label={t(M.mainNav)} className="ml-4 hidden items-center gap-1 md:flex">
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )
              }
            >
              {t(item.label)}
            </NavLink>
          ))}
        </nav>

        {/* Direita: semana atual + idioma + guia + usuário */}
        <div className="ml-auto flex min-w-0 items-center gap-1.5 sm:gap-2">
          <WeekChip />
          <span data-tour="language">
            <LanguageSwitcher variant="compact" />
          </span>
          <TourReplayButton />

          {user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  aria-label={t(M.userMenu)}
                  className="shrink-0 rounded-full transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <Avatar src={user.photo_url} name={user.name} size="sm" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-60">
                <div className="px-2.5 py-2">
                  <p className="truncate text-sm font-medium text-gray-900">{user.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => navigate('/perfil')}>
                  <UserIcon aria-hidden="true" />
                  {t(COMMON.profile)}
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => navigate('/configuracoes')}>
                  <Settings aria-hidden="true" />
                  {t(COMMON.settings)}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onSelect={handleLogout}
                  className="text-red-600 focus:bg-red-50 focus:text-red-600 data-[highlighted]:bg-red-50 data-[highlighted]:text-red-600"
                >
                  <LogOut aria-hidden="true" />
                  {t(COMMON.logout)}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>

      {/* Drawer mobile */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/40 animate-fade-in"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-label={t(M.mainNav)}
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-white shadow-elevated animate-slide-in-left"
          >
            <div className="flex h-14 items-center justify-between border-b border-border px-4">
              <LogoMark />
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                aria-label={t(M.closeMenu)}
                className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>

            <nav aria-label={t(M.mainNav)} className="flex flex-col gap-1 p-3">
              {NAV_ITEMS.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      'rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-brand-50 text-brand-700'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    )
                  }
                >
                  {t(item.label)}
                </NavLink>
              ))}
            </nav>

            {user && (
              <div className="mt-auto border-t border-border p-3">
                <div className="flex items-center gap-3 px-3 py-2">
                  <Avatar src={user.photo_url} name={user.name} size="sm" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-gray-900">{user.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                  </div>
                </div>
                <Link
                  to="/perfil"
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
                >
                  <UserIcon className="h-4 w-4" aria-hidden="true" />
                  {t(COMMON.profile)}
                </Link>
                <Link
                  to="/configuracoes"
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
                >
                  <Settings className="h-4 w-4" aria-hidden="true" />
                  {t(COMMON.settings)}
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
                >
                  <LogOut className="h-4 w-4" aria-hidden="true" />
                  {t(COMMON.logout)}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
