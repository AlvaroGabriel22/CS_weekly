import { useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { UsersRound } from 'lucide-react'
import { EmptyState, ErrorState } from '@/components/feedback'
import { PageContainer } from '@/components/layout/PageContainer'
import { OrgChart } from '@/components/orgchart/OrgChart'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { useOrgUsers } from '@/hooks/useOrg'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { ORG } from '@/i18n/messages/org'
import type { OrgUser } from '@/types'

const SECTOR_NAMES: Record<OrgUser['sector'], string> = {
  QM: 'Quality Management',
  QA: 'Quality Assurance',
  OQC: 'Outgoing Quality Control',
  IQC: 'Incoming Quality Control',
  FIELD: 'Field Quality',
  CSI: 'Customer Satisfaction Index',
}

function isSectorCode(value: string): value is OrgUser['sector'] {
  return value in SECTOR_NAMES
}

/** Esqueleto em pirâmide, ecoando a forma do organograma. */
function OrgSkeleton() {
  const { t } = useI18n()
  return (
    <div role="status" aria-label={t(COMMON.loading)} className="overflow-x-auto pb-4 animate-fade-in">
      <div className="mx-auto min-w-max px-2">
        {[1, 2, 3].map(count => (
          <div key={count} className="mb-8 flex justify-center gap-4 sm:gap-6">
            {Array.from({ length: count }, (_, i) => (
              <div
                key={i}
                className="flex w-36 flex-col items-center gap-2 rounded-xl border border-border/60 bg-white px-3 py-4 shadow-card sm:w-40"
              >
                <Skeleton className="h-14 w-14 rounded-full" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-3 w-20" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

/** Organograma de um setor: hierarquia por cargo com linhas conectoras. */
export function DepartmentOrgPage() {
  const { sector: sectorParam } = useParams<{ sector: string }>()
  const navigate = useNavigate()
  const { t } = useI18n()
  const { toast } = useToast()
  const { data: orgUsers, isLoading, isError, error, refetch } = useOrgUsers()

  const sector = (sectorParam ?? '').toUpperCase()
  const validSector = isSectorCode(sector) ? sector : null

  const sectorUsers = useMemo(
    () => (orgUsers ?? []).filter(u => u.sector === validSector),
    [orgUsers, validSector]
  )

  if (!validSector) {
    return (
      <PageContainer title={t(COMMON.departments)} maxWidth="6xl">
        <EmptyState
          title={t(ORG.sectorNotFound)}
          action={<Button onClick={() => navigate('/departamentos')}>{t(ORG.seeDepartments)}</Button>}
        />
      </PageContainer>
    )
  }

  const handlePersonClick = (person: OrgUser) => {
    if (person.viewer_can_access) {
      navigate(`/colegas/${person.id}`)
    } else {
      toast.info(t(COMMON.noAccess))
    }
  }

  return (
    <PageContainer title={`${validSector} · ${SECTOR_NAMES[validSector]}`} maxWidth="7xl">
      {isLoading ? (
        <OrgSkeleton />
      ) : isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : sectorUsers.length === 0 ? (
        <EmptyState
          icon={UsersRound}
          title={t(ORG.emptySector)}
          action={
            <Button variant="outline" onClick={() => navigate('/departamentos')}>
              {t(COMMON.back)}
            </Button>
          }
        />
      ) : (
        <OrgChart users={sectorUsers} onPersonClick={handlePersonClick} />
      )}
    </PageContainer>
  )
}
