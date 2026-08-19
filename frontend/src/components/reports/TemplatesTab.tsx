import { useRef, useState } from 'react'
import {
  AlertTriangle,
  FileText,
  LayoutTemplate,
  Loader2,
  SlidersHorizontal,
  Star,
  Trash2,
  Upload,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { REPORTS } from '@/i18n/messages/reports'
import { parseApiError } from '@/lib/errors'
import { EmptyState, ErrorState } from '@/components/feedback'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { useTemplates } from '@/hooks/useWeekly'
import {
  useDeletePptxTemplate,
  usePptxTemplates,
  useUploadPptxTemplate,
  type PptxTemplate,
} from '@/hooks/usePptxTemplates'
import { TemplateSlotsDialog } from './TemplateSlotsDialog'
import type { Template } from '@/types'

const PPTX_LIMIT = 2

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

/** Aba Templates: modelos de PPT do usuário + galeria (somente leitura). */
export function TemplatesTab() {
  return (
    <div className="space-y-8">
      <PptxTemplatesSection />
      <TemplateGallery />
    </div>
  )
}

/** Seção "Meus modelos de PPT": upload/gerência dos .pptx de referência. */
function PptxTemplatesSection() {
  const { t } = useI18n()
  const { toast } = useToast()
  const inputRef = useRef<HTMLInputElement>(null)
  const query = usePptxTemplates()
  const upload = useUploadPptxTemplate()
  const remove = useDeletePptxTemplate()
  /** Modelo aberto na tela de marcação de campos. */
  const [slotsFor, setSlotsFor] = useState<PptxTemplate | null>(null)

  const items = query.data ?? []
  const atLimit = items.length >= PPTX_LIMIT
  const disabled = atLimit || upload.isPending

  const handlePick = () => inputRef.current?.click()

  const handleFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = '' // permite reenviar o mesmo arquivo
    if (!file) return
    upload.mutate(file, {
      onSuccess: () => toast.success(t(REPORTS.pptxUploaded)),
      onError: (err) => toast.error(parseApiError(err).message),
    })
  }

  const handleRemove = (id: string) => {
    remove.mutate(id, {
      onSuccess: () => toast.success(t(REPORTS.pptxRemoved)),
      onError: (err) => toast.error(parseApiError(err).message),
    })
  }

  return (
    <section className="rounded-xl border border-border/60 bg-white p-5 shadow-card sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-900">{t(REPORTS.pptxTitle)}</h3>
          <p className="mt-1 text-xs text-gray-500">{t(REPORTS.pptxIntro)}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <input
            ref={inputRef}
            type="file"
            accept=".pptx"
            className="hidden"
            onChange={handleFile}
          />
          <Button
            type="button"
            size="sm"
            disabled={disabled}
            onClick={handlePick}
            title={atLimit ? t(REPORTS.pptxLimit) : undefined}
          >
            {upload.isPending ? (
              <>
                <Loader2 className="animate-spin" aria-hidden="true" />
                {t(REPORTS.pptxUploading)}
              </>
            ) : (
              <>
                <Upload aria-hidden="true" />
                {t(REPORTS.pptxUpload)}
              </>
            )}
          </Button>
          {atLimit && <p className="text-xs text-gray-400">{t(REPORTS.pptxLimit)}</p>}
        </div>
      </div>

      <div className="mt-4">
        {query.isLoading ? (
          <div className="space-y-2" role="status" aria-label={t(COMMON.loading)}>
            {[0, 1].map((i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-lg border border-border/40 p-3"
              >
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-3 w-1/4" />
                </div>
              </div>
            ))}
          </div>
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => query.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState icon={FileText} title={t(REPORTS.pptxEmpty)} />
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li
                key={item.id}
                className="flex items-center gap-3 rounded-lg border border-border/60 p-3 transition-shadow duration-200 hover:shadow-card"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand/10">
                  <FileText className="h-5 w-5 text-brand" aria-hidden="true" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{item.name}</p>
                  <p className="text-xs text-gray-500">
                    {t(REPORTS.pptxSlides, { n: item.slides_count })}
                  </p>
                  {item.available === false && (
                    <p className="mt-0.5 flex items-center gap-1 text-xs text-amber-600">
                      <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
                      {t(REPORTS.pptxUnavailable)}
                    </p>
                  )}
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="shrink-0"
                  onClick={() => setSlotsFor(item)}
                >
                  <SlidersHorizontal className="mr-1.5 h-4 w-4" aria-hidden="true" />
                  {t(REPORTS.slotsBtn)}
                </Button>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="shrink-0 text-destructive hover:bg-red-50 hover:text-destructive"
                  disabled={remove.isPending}
                  aria-label={t(REPORTS.pptxRemove)}
                  title={t(REPORTS.pptxRemove)}
                  onClick={() => handleRemove(item.id)}
                >
                  <Trash2 aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {slotsFor && (
        <TemplateSlotsDialog
          templateId={slotsFor.id}
          templateName={slotsFor.name}
          onClose={() => setSlotsFor(null)}
        />
      )}
    </section>
  )
}

/** Galeria (somente leitura) dos templates de apresentação disponíveis. */
function TemplateGallery() {
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
