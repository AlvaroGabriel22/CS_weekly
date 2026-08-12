import { useMemo } from 'react'
import { PersonCard } from './PersonCard'
import { cn } from '@/lib/utils'
import type { OrgUser } from '@/types'

export interface OrgChartProps {
  users: OrgUser[]
  onPersonClick: (user: OrgUser) => void
}

/** Normaliza o cargo para comparação (minúsculas, espaços colapsados). */
function normalizeRole(role: string): string {
  return role.trim().toLowerCase().replace(/\s+/g, ' ')
}

/** Ordem canônica dentro de cada nível (Sr → PL → Jr; Chefe antes de Supervisor). */
const ROLE_ORDER = [
  'gerente sr',
  'gerente pl',
  'gerente jr',
  'chefe',
  'supervisor',
  'analista de engenharia sr',
  'analista de engenharia pl',
  'analista de engenharia jr',
  'analista sr',
  'analista pl',
  'analista jr',
  'auditor sr',
  'auditor pl',
  'auditor jr',
]

function roleRank(role: string): number {
  const idx = ROLE_ORDER.indexOf(normalizeRole(role))
  return idx === -1 ? ROLE_ORDER.length : idx
}

interface LevelDef {
  key: string
  matches: (normalizedRole: string) => boolean
}

/** Hierarquia EXATA do organograma (níveis vazios são omitidos na renderização). */
const LEVELS: LevelDef[] = [
  { key: 'gerencia', matches: r => r.startsWith('gerente') },
  { key: 'chefia', matches: r => r.startsWith('chefe') || r.startsWith('supervisor') },
  { key: 'analistas-eng', matches: r => r.includes('analista de engenharia') },
  {
    key: 'analistas',
    matches: r => r.startsWith('analista') && !r.includes('engenharia'),
  },
  { key: 'auditores', matches: r => r.startsWith('auditor') },
  // Defensivo: cargos fora da hierarquia oficial não somem do organograma.
  { key: 'outros', matches: () => true },
]

function buildLevels(users: OrgUser[]): { key: string; people: OrgUser[] }[] {
  const remaining = [...users]
  const levels: { key: string; people: OrgUser[] }[] = []
  for (const level of LEVELS) {
    const people = remaining.filter(u => level.matches(normalizeRole(u.role)))
    for (const person of people) {
      remaining.splice(remaining.indexOf(person), 1)
    }
    if (people.length > 0) {
      people.sort((a, b) => roleRank(a.role) - roleRank(b.role) || a.name.localeCompare(b.name))
      levels.push({ key: level.key, people })
    }
  }
  return levels
}

const CONNECTOR = 'bg-brand-200'

/**
 * Organograma em árvore: níveis centrados, um abaixo do outro, com linhas
 * conectoras (vertical central + horizontal por nível). Os níveis entram em
 * cascata (fade + translateY com stagger de cima para baixo).
 */
export function OrgChart({ users, onPersonClick }: OrgChartProps) {
  const levels = useMemo(() => buildLevels(users), [users])

  if (levels.length === 0) return null

  return (
    // Árvores largas rolam dentro do próprio bloco — a página nunca rola na horizontal.
    <div className="overflow-x-auto pb-4">
      <div className="mx-auto min-w-max px-2">
        {levels.map((level, levelIdx) => {
          const hasParent = levelIdx > 0
          const many = level.people.length > 1
          return (
            <div
              key={level.key}
              className="animate-slide-up"
              style={{ animationDelay: `${levelIdx * 130}ms`, animationFillMode: 'backwards' }}
            >
              {/* Tronco vertical descendo do nível anterior */}
              {hasParent && <div className={cn('mx-auto h-7 w-px', CONNECTOR)} aria-hidden="true" />}

              <div className="flex justify-center">
                {level.people.map((person, personIdx) => {
                  const first = personIdx === 0
                  const last = personIdx === level.people.length - 1
                  return (
                    <div
                      key={person.id}
                      className={cn(
                        'relative flex flex-col items-center px-2 sm:px-3',
                        hasParent && 'pt-4'
                      )}
                    >
                      {/* Linha horizontal do nível (some nas pontas externas) */}
                      {hasParent && many && !(first && last) && (
                        <div
                          className={cn(
                            'absolute top-0 h-px',
                            CONNECTOR,
                            first ? 'left-1/2 right-0' : last ? 'left-0 right-1/2' : 'left-0 right-0'
                          )}
                          aria-hidden="true"
                        />
                      )}
                      {/* Pino vertical da linha até o cartão */}
                      {hasParent && (
                        <div
                          className={cn('absolute left-1/2 top-0 h-4 w-px -translate-x-1/2', CONNECTOR)}
                          aria-hidden="true"
                        />
                      )}
                      <PersonCard user={person} onClick={onPersonClick} />
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
