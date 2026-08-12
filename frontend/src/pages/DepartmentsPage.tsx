import { useNavigate } from 'react-router-dom'
import { Users } from 'lucide-react'
import { ErrorState } from '@/components/feedback'
import { Skeleton } from '@/components/ui/skeleton'
import { useOrgUsers } from '@/hooks/useOrg'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { ORG } from '@/i18n/messages/org'
import type { OrgUser } from '@/types'

const SECTORS: { code: OrgUser['sector']; name: string }[] = [
  { code: 'QM', name: 'Quality Management' },
  { code: 'QA', name: 'Quality Assurance' },
  { code: 'OQC', name: 'Outgoing Quality Control' },
  { code: 'IQC', name: 'Incoming Quality Control' },
  { code: 'FIELD', name: 'Field Quality' },
  { code: 'CSI', name: 'Customer Satisfaction Index' },
]

/** Tela limpa de entrada da área de departamentos: só os 6 setores. */
export function DepartmentsPage() {
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: orgUsers, isLoading, isError, error, refetch } = useOrgUsers()

  const peopleLabel = (count: number): string =>
    count === 1 ? t(ORG.person) : t(ORG.people, { n: count })

  return (
    <div className="mx-auto flex min-h-[calc(100vh-3.5rem)] w-full max-w-3xl flex-col justify-center px-4 py-10 sm:px-6">
      <header className="mb-8 text-center animate-fade-in">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
          {t(COMMON.departments)}
        </h1>
      </header>

      {isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3">
          {SECTORS.map((sector, idx) =>
            isLoading ? (
              <div
                key={sector.code}
                className="rounded-xl border border-border/60 bg-white p-5 shadow-card"
              >
                <Skeleton className="h-8 w-16" />
                <Skeleton className="mt-2 h-3 w-full" />
                <Skeleton className="mt-4 h-3 w-20" />
              </div>
            ) : (
              <button
                key={sector.code}
                type="button"
                onClick={() => navigate(`/departamentos/${sector.code}`)}
                className="group flex min-w-0 flex-col items-start rounded-xl border border-border/60 bg-white p-5 text-left shadow-card transition-all duration-300 ease-out animate-slide-up hover:-translate-y-1 hover:border-brand-400 hover:shadow-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                style={{ animationDelay: `${idx * 70}ms`, animationFillMode: 'backwards' }}
              >
                <span className="text-2xl font-bold tracking-tight text-brand transition-colors group-hover:text-brand-600 sm:text-3xl">
                  {sector.code}
                </span>
                <span className="mt-1 w-full text-xs leading-snug text-gray-600 sm:text-sm">
                  {sector.name}
                </span>
                <span className="mt-4 inline-flex items-center gap-1.5 text-xs text-gray-500">
                  <Users className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {peopleLabel((orgUsers ?? []).filter(u => u.sector === sector.code).length)}
                </span>
              </button>
            )
          )}
        </div>
      )}
    </div>
  )
}
