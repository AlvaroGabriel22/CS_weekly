import { LayoutTemplate, Star } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { REPORTS } from '@/i18n/messages/reports'
import { EmptyState, ErrorState } from '@/components/feedback'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useTemplates } from '@/hooks/useWeekly'
import type { Template } from '@/types'

/** Extrai defensivamente os títulos dos slides de slides_config. */
function parseSlideTitles(
  config: Record<string, unknown>,
  fallback: (n: number) => string,
): string[] {
  const slides = (config as { slides?: unknown }).slides
  if (!Array.isArray(slides)) return []
  return slides.map((slide, index) => {
    if (typeof slide === 'object' && slide !== null) {
      const title = (slide as { title?: unknown }).title
      if (typeof title === 'string' && title.trim()) return title
    }
    return fallback(index + 1)
  })
}

/** Galeria (somente leitura) dos templates de apresentação disponíveis. */
export function TemplatesTab() {
  const { t } = useI18n()
  const { user } = useAuth()
  const query = useTemplates()
  const defaultTemplateId = user?.writing_profile?.default_template_id ?? null

  if (query.isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-label={t(COMMON.loading)}>
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-xl border border-border/60 bg-white p-5 shadow-card">
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <Skeleton className="h-4 w-32" />
            </div>
            <div className="mt-4 space-y-2">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-3/4" />
            </div>
            <div className="mt-4 flex gap-2">
              <Skeleton className="h-5 w-12 rounded-full" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  }

  const templates = query.data ?? []

  if (templates.length === 0) {
    return (
      <EmptyState
        icon={LayoutTemplate}
        title={t(REPORTS.templatesEmpty)}
        description={t(REPORTS.autoLayout)}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((template, index) => (
          <div
            key={template.id}
            className="animate-slide-up"
            style={{ animationDelay: `${Math.min(index, 8) * 50}ms`, animationFillMode: 'backwards' }}
          >
            <TemplateCard template={template} isDefault={template.id === defaultTemplateId} />
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-500">{t(REPORTS.readOnly)}</p>
    </div>
  )
}

function TemplateCard({ template, isDefault }: { template: Template; isDefault: boolean }) {
  const { t } = useI18n()
  const slideTitles = parseSlideTitles(template.slides_config, (n) => t(REPORTS.slideN, { n }))

  return (
    <div className="flex h-full flex-col rounded-xl border border-border/60 bg-white p-5 shadow-card transition-shadow duration-200 hover:shadow-elevated">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand/10">
            <LayoutTemplate className="h-5 w-5 text-brand" aria-hidden="true" />
          </div>
          <h3 className="min-w-0 truncate text-sm font-semibold text-gray-900">{template.name}</h3>
        </div>
        {isDefault && (
          <Badge className="shrink-0">
            <Star aria-hidden="true" />
            {t(REPORTS.templateDefaultTag)}
          </Badge>
        )}
      </div>

      {template.description && (
        <p className="mt-3 line-clamp-2 text-sm text-gray-600">{template.description}</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Badge variant="info" className="uppercase">
          {template.language}
        </Badge>
        <Badge variant="outline">{template.department}</Badge>
        {slideTitles.length > 0 && (
          <Badge variant="outline">{t(REPORTS.slidesCount, { n: slideTitles.length })}</Badge>
        )}
      </div>

      {slideTitles.length > 0 && (
        <ol className="mt-4 space-y-1 border-t border-border/60 pt-3">
          {slideTitles.slice(0, 6).map((title, index) => (
            <li key={`${index}-${title}`} className="flex items-center gap-2 text-xs text-gray-600">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-gray-100 text-[10px] font-semibold text-gray-500">
                {index + 1}
              </span>
              <span className="min-w-0 truncate">{title}</span>
            </li>
          ))}
          {slideTitles.length > 6 && (
            <li className="pl-7 text-xs text-gray-400">
              {t(REPORTS.moreSlides, { n: slideTitles.length - 6 })}
            </li>
          )}
        </ol>
      )}
    </div>
  )
}
