import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Building2,
  CalendarCheck2,
  CalendarPlus,
  ClipboardList,
  FileText,
  Paperclip,
  Presentation,
  type LucideIcon,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useDashboard } from '@/hooks/useDashboard'
import { PageContainer } from '@/components/layout/PageContainer'
import { Card } from '@/components/ui/card'
import { Badge, type BadgeProps } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { currentWeekRef, getWeekDaysOf, isToday, parseIsoDate } from '@/lib/dates'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { HOME } from '@/i18n/messages/home'
import type { DashboardStats } from '@/types'

// ── Helpers ────────────────────────────────────────────────────────────────

/** Saudação pela hora local: 5–11 dia · 12–17 tarde · demais noite. */
function greetingMsg(hour: number): Msg {
  if (hour >= 5 && hour < 12) return HOME.goodMorning
  if (hour >= 12 && hour < 18) return HOME.goodAfternoon
  return HOME.goodEvening
}

type BadgeVariant = BadgeProps['variant']

/** Mapeia o status do weekly vindo do backend para rótulo + cor. */
function weeklyStatusBadge(status: string | null): { msg: Msg | null; variant: BadgeVariant } {
  switch ((status ?? '').toLowerCase()) {
    case 'draft':
      return { msg: HOME.statusDraft, variant: 'outline' }
    case 'pending':
    case 'processing':
    case 'generating':
      return { msg: HOME.statusGenerating, variant: 'warning' }
    case 'generated':
    case 'ready':
    case 'done':
    case 'completed':
      return { msg: HOME.statusDone, variant: 'success' }
    case 'failed':
    case 'error':
      return { msg: HOME.statusFailed, variant: 'danger' }
    default:
      return { msg: null, variant: 'outline' }
  }
}

// ── Banner da semana atual ─────────────────────────────────────────────────

function WeekBanner() {
  const { t, locale } = useI18n()
  const ref = currentWeekRef()
  const days = getWeekDaysOf(ref)
  const start = days[0]
  const end = days[6]
  const rangeLabel = `${start.toLocaleDateString(locale, { day: 'numeric', month: 'short' })} – ${end.toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' })}`

  return (
    <section
      aria-label={t(HOME.weekN, { n: ref.week })}
      className="rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 p-5 text-white shadow-card sm:p-6"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between md:gap-6">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-blue-200">{t(COMMON.currentWeek)}</p>
          <p className="mt-0.5 text-3xl font-bold leading-tight">{t(HOME.weekN, { n: ref.week })}</p>
          <p className="mt-1 text-sm text-blue-100">{rangeLabel}</p>
        </div>
        <ul aria-label={t(HOME.weekDaysAria)} className="grid grid-cols-7 gap-1 sm:gap-1.5 md:w-[340px] md:shrink-0">
          {days.map((day, i) => {
            const today = isToday(day)
            return (
              <li key={i}>
                <div
                  aria-current={today ? 'date' : undefined}
                  className={
                    today
                      ? 'rounded-lg bg-white px-1 py-1.5 text-center text-brand-700 shadow-sm'
                      : 'rounded-lg bg-white/10 px-1 py-1.5 text-center text-blue-100'
                  }
                >
                  <span className="block text-[10px] font-medium leading-tight">
                    {day.toLocaleDateString(locale, { weekday: 'short' })}
                  </span>
                  <span className="mt-0.5 block text-sm font-semibold leading-tight">{day.getDate()}</span>
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}

// ── Estatísticas ───────────────────────────────────────────────────────────

interface StatCardProps {
  icon: LucideIcon
  label: string
  value: ReactNode
  sub?: ReactNode
}

function StatCard({ icon: Icon, label, value, sub }: StatCardProps) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 text-sm font-medium text-gray-600">{label}</p>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50">
          <Icon className="h-[18px] w-[18px] text-brand" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-1 text-2xl font-bold text-gray-900">{value}</div>
      {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
    </Card>
  )
}

function StatsGrid({ stats }: { stats: DashboardStats }) {
  const { t, locale } = useI18n()
  const status = weeklyStatusBadge(stats.weekly_status)
  const attachmentsTotal = stats.images_count + stats.files_count
  const daysFilled = Math.min(stats.days_filled, 5)

  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4">
      <StatCard icon={ClipboardList} label={t(HOME.statActivities)} value={stats.activities_count} />
      <StatCard
        icon={CalendarCheck2}
        label={t(HOME.statDays)}
        value={`${daysFilled}/5`}
        sub={daysFilled >= 5 ? t(HOME.weekComplete) : undefined}
      />
      <StatCard
        icon={Paperclip}
        label={t(HOME.statAttachments)}
        value={attachmentsTotal}
        sub={t(HOME.attachSub, { i: stats.images_count, f: stats.files_count })}
      />
      <StatCard
        icon={FileText}
        label={t(HOME.statWeekly)}
        value={
          <Badge variant={status.variant} className="text-sm">
            {status.msg ? t(status.msg) : '—'}
          </Badge>
        }
        sub={
          stats.last_report_generated_at
            ? t(HOME.generatedOn, {
                date: parseIsoDate(stats.last_report_generated_at).toLocaleDateString(locale),
              })
            : undefined
        }
      />
    </div>
  )
}

// ── Ações rápidas ──────────────────────────────────────────────────────────

interface QuickActionProps {
  to: string
  icon: LucideIcon
  title: string
  description: string
}

function QuickActionCard({ to, icon: Icon, title, description }: QuickActionProps) {
  return (
    <Link
      to={to}
      className="group block h-full rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      <Card className="flex h-full items-start gap-4 p-5 group-hover:shadow-elevated">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 transition-colors duration-200 group-hover:bg-brand-100">
          <Icon className="h-5 w-5 text-brand" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-gray-900">{title}</p>
          <p className="mt-0.5 text-sm text-gray-600">{description}</p>
        </div>
        <ArrowRight
          className="mt-1 h-4 w-4 shrink-0 text-gray-300 transition-all duration-200 group-hover:translate-x-0.5 group-hover:text-brand"
          aria-hidden="true"
        />
      </Card>
    </Link>
  )
}

// ── Página ─────────────────────────────────────────────────────────────────

export function HomePage() {
  const { user } = useAuth()
  const { t, locale } = useI18n()
  const { data, isPending, isError, error, refetch } = useDashboard()

  const now = new Date()
  const greeting = t(greetingMsg(now.getHours()))
  const firstName = user?.name?.trim().split(/\s+/)[0]
  const dateLine = now.toLocaleDateString(locale, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  return (
    <PageContainer title="" maxWidth="6xl">
      <div className="space-y-8 animate-fade-in">
        {/* 1 · Hero */}
        <section>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
            {greeting}
            {firstName ? `, ${firstName}` : ''}!
          </h1>
          <p className="mt-1 text-sm text-gray-600 sm:text-base">{dateLine}</p>
          <div className="mt-4">
            <WeekBanner />
          </div>
        </section>

        {/* 2 · Resumo da semana */}
        <section aria-busy={isPending}>
          <h2 className="sr-only">{t(HOME.summary)}</h2>
          {isPending ? (
            <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-28 rounded-xl" />
              ))}
            </div>
          ) : isError ? (
            <Card>
              <ErrorState error={error} onRetry={() => refetch()} />
            </Card>
          ) : data && data.activities_count === 0 ? (
            <Card>
              <EmptyState
                icon={CalendarPlus}
                title={t(HOME.emptyTitle)}
                description={t(HOME.emptyDesc)}
                action={
                  <Button asChild>
                    <Link to="/agenda">
                      <CalendarPlus aria-hidden="true" />
                      {t(HOME.actionLog)}
                    </Link>
                  </Button>
                }
              />
            </Card>
          ) : data ? (
            <StatsGrid stats={data} />
          ) : null}
        </section>

        {/* 3 · Ações rápidas */}
        <section>
          <h2 className="mb-3 text-base font-semibold text-gray-900">{t(HOME.quickActions)}</h2>
          <div className="grid gap-3 sm:gap-4 md:grid-cols-3">
            <QuickActionCard
              to="/agenda"
              icon={CalendarPlus}
              title={t(HOME.actionLog)}
              description={t(HOME.actionLogDesc)}
            />
            <QuickActionCard
              to="/relatorios"
              icon={Presentation}
              title={t(HOME.actionWeekly)}
              description={t(HOME.actionWeeklyDesc)}
            />
            <QuickActionCard
              to="/departamentos"
              icon={Building2}
              title={t(COMMON.departments)}
              description={t(HOME.actionDeptsDesc)}
            />
          </div>
        </section>
      </div>
    </PageContainer>
  )
}
