import { useNavigate } from 'react-router-dom'
import { ArrowRight, Users } from 'lucide-react'
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
  { code: 'CSI', name: 'CS Innovation' },
]

/** Tela limpa de entrada da área de departamentos: só os 6 setores. */
export function DepartmentsPage() {
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: orgUsers, isLoading, isError, error, refetch } = useOrgUsers()

  const peopleLabel = (count: number): string =>
    count === 1 ? t(ORG.person) : t(ORG.people, { n: count })

  return (
    <div className="mx-auto flex min-h-[calc(100vh-3.5rem)] w-full max-w-4xl flex-col justify-center px-4 py-10 sm:px-6">
      <header className="mb-8 text-center animate-fade-in">
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
          {t(COMMON.departments)}
        </h1>
      </header>

      {isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        // p-1/-m-1: folga para ring/shadow dos cards nunca serem clipados.
        <div data-tour="departments" className="-m-1 grid grid-cols-1 gap-4 p-1 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">
          {SECTORS.map((sector, idx) =>
            isLoading ? (
              <div
                key={sector.code}
                className="rounded-2xl border border-border/60 bg-white p-6 shadow-card"
              >
                <div className="flex items-start justify-between gap-3">
                  <Skeleton className="h-9 w-20" />
                  <Skeleton className="h-9 w-9 rounded-lg" />
                </div>
                <Skeleton className="mt-3 h-4 w-full" />
                <Skeleton className="mt-5 h-3 w-24" />
              </div>
            ) : (
              <button
                key={sector.code}
                type="button"
                onClick={() => navigate(`/departamentos/${sector.code}`)}
                className="group relative flex min-w-0 flex-col items-start overflow-hidden rounded-2xl border border-border/60 bg-white p-6 text-left shadow-card transition-all duration-300 ease-out animate-slide-up hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                style={{ animationDelay: `${idx * 70}ms`, animationFillMode: 'backwards' }}
              >
                <span className="flex w-full items-start justify-between gap-3">
                  <span className="min-w-0 truncate text-3xl font-bold tracking-tight text-brand transition-colors duration-300 group-hover:text-brand-600 sm:text-4xl">
                    {sector.code}
                  </span>
                  <span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand transition-colors duration-300 group-hover:bg-brand-100"
                    aria-hidden="true"
                  >
                    <Users className="h-4 w-4" />
                  </span>
                </span>

                <span className="mt-2 w-full text-sm leading-snug text-gray-600">
                  {sector.name}
                </span>

                <span className="mt-5 flex w-full items-center justify-between gap-2">
                  <span className="text-xs font-medium text-gray-500">
                    {peopleLabel((orgUsers ?? []).filter(u => u.sector === sector.code).length)}
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-brand opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-focus-visible:opacity-100">
                    {t(ORG.orgChart)}
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                </span>

                {/* Barra azul que desliza no hover */}
                <span
                  className="pointer-events-none absolute inset-x-0 bottom-0 h-1 origin-left scale-x-0 bg-gradient-to-r from-blue-600 to-blue-700 transition-transform duration-300 ease-out group-hover:scale-x-100 group-focus-visible:scale-x-100"
                  aria-hidden="true"
                />
              </button>
            )
          )}
        </div>
      )}
    </div>
  )
}
