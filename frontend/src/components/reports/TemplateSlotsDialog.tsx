/**
 * "Marcar campos" — diz ao sistema o que cada elemento do MODELO recebe.
 *
 * A geração por mutação abre o .pptx do usuário e troca só o conteúdo dos
 * campos marcados. Por isso aqui NÃO se move, redimensiona nem edita texto:
 * posição, fonte e cor vêm do arquivo original e são preservadas. O usuário
 * clica num elemento e escolhe o papel dele.
 *
 * Erros SEMPRE via parseApiError.
 */
import { useEffect, useMemo, useState } from 'react'
import { Info, Loader2 } from 'lucide-react'
import { parseApiError } from '@/lib/errors'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useToast } from '@/components/ui/toast'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { REPORTS } from '@/i18n/messages/reports'
import {
  usePptxTemplate,
  useSaveTemplateSlots,
  type SlotMarks,
} from '@/hooks/usePptxTemplates'
import { ELEMENT_SLOTS, type ElementSlot, type SlideElement } from './slideLayout'
import { StaticSlidePage } from './SlideStatic'

const SLOT_LABEL: Record<ElementSlot, Msg> = {
  title: REPORTS.slotTitle,
  body: REPORTS.slotBody,
  activity_date: REPORTS.slotActivityDate,
  table: REPORTS.slotTable,
  image: REPORTS.slotImage,
  chart: REPORTS.slotChart,
  week_label: REPORTS.slotWeekLabel,
  static: REPORTS.slotStatic,
}

/** Slots que fazem sentido para cada tipo de elemento. */
function allowedSlots(element: SlideElement): ElementSlot[] {
  if (element.type === 'table') return ['table', 'static']
  if (element.type === 'image') return ['image', 'chart', 'static']
  if (element.type === 'shape') return ['static']
  return ['title', 'body', 'activity_date', 'week_label', 'static']
}

export interface TemplateSlotsDialogProps {
  templateId: string
  templateName: string
  onClose: () => void
}

export function TemplateSlotsDialog({
  templateId,
  templateName,
  onClose,
}: TemplateSlotsDialogProps) {
  const { t } = useI18n()
  const { toast } = useToast()
  const detail = usePptxTemplate(templateId)
  const save = useSaveTemplateSlots(templateId)

  const [slideIndex, setSlideIndex] = useState(0)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  /** Alterações ainda não salvas, por slide. */
  const [marks, setMarks] = useState<SlotMarks>({})

  const slides = useMemo(() => detail.data?.layout?.slides ?? [], [detail.data])
  const slide = slides[slideIndex] ?? null

  useEffect(() => {
    setSelectedId(null)
  }, [slideIndex])

  if (detail.isError) {
    return (
      <Dialog open onOpenChange={onClose}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t(REPORTS.slotsTitle)}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-destructive">{parseApiError(detail.error).message}</p>
          <DialogFooter>
            <Button variant="outline" onClick={onClose}>{t(COMMON.close)}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  const slotOf = (element: SlideElement): ElementSlot => {
    const pending = slide ? marks[slide.id]?.[element.id] : undefined
    return (pending as ElementSlot) ?? element.slot ?? 'static'
  }

  const assign = (element: SlideElement, slot: ElementSlot) => {
    if (!slide) return
    setMarks(current => ({
      ...current,
      [slide.id]: { ...(current[slide.id] ?? {}), [element.id]: slot },
    }))
  }

  const selected = slide?.elements.find(el => el.id === selectedId) ?? null
  const dirty = Object.values(marks).some(byElement => Object.keys(byElement).length > 0)

  const handleSave = () => {
    save.mutate(marks, {
      onSuccess: () => {
        setMarks({})
        toast.success(t(REPORTS.slotsSaved))
      },
      onError: (error) => toast.error(parseApiError(error).message),
    })
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-h-[92vh] max-w-5xl overflow-hidden">
        <DialogHeader>
          <DialogTitle>{templateName}</DialogTitle>
          <DialogDescription>{t(REPORTS.slotsIntro)}</DialogDescription>
        </DialogHeader>

        {detail.isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-brand" aria-hidden />
          </div>
        ) : (
          <div className="flex max-h-[64vh] flex-col gap-4 overflow-y-auto md:flex-row">
            {/* slides do modelo */}
            <div className="flex shrink-0 gap-2 overflow-x-auto md:w-28 md:flex-col md:overflow-y-auto">
              {slides.map((item, index) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSlideIndex(index)}
                  className={`shrink-0 rounded-lg border px-2 py-1 text-xs ${
                    index === slideIndex
                      ? 'border-brand bg-brand/10 font-semibold text-brand'
                      : 'border-border text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {t(REPORTS.slotsSlide, { n: index + 1 })}
                </button>
              ))}
            </div>

            {/* página do slide, clicável */}
            <div className="min-w-0 flex-1 overflow-x-auto">
              {slide && (
                <StaticSlidePage
                  slide={slide}
                  width={620}
                  onSelectElement={setSelectedId}
                  selectedElementId={selectedId}
                  // O badge aparece em TODO elemento, inclusive nos fixos: o
                  // usuário precisa ver o que vai repetir igual toda semana.
                  elementBadge={el => {
                    const slot = slotOf(el)
                    return { text: t(SLOT_LABEL[slot]), muted: slot === 'static' }
                  }}
                />
              )}
            </div>

            {/* painel do elemento selecionado */}
            <div className="w-full shrink-0 md:w-56">
              {!selected ? (
                <p className="rounded-lg border border-dashed border-border p-3 text-sm text-gray-500">
                  {t(REPORTS.slotsPick)}
                </p>
              ) : (
                <div className="space-y-2">
                  <p className="truncate text-xs text-gray-500">
                    {selected.type === 'text'
                      ? (selected.text || '—').slice(0, 60)
                      : selected.type}
                  </p>
                  {allowedSlots(selected).map(slot => (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => assign(selected, slot)}
                      className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                        slotOf(selected) === slot
                          ? 'border-brand bg-brand/10 font-medium text-brand'
                          : 'border-border hover:bg-gray-50'
                      }`}
                    >
                      {t(SLOT_LABEL[slot])}
                    </button>
                  ))}
                  {ELEMENT_SLOTS.length > 0 && (
                    <p className="flex gap-1.5 pt-1 text-[11px] leading-4 text-gray-500">
                      <Info className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
                      <span>{t(REPORTS.slotStaticHint)}</span>
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={save.isPending}>
            {t(COMMON.close)}
          </Button>
          <Button onClick={handleSave} disabled={!dirty || save.isPending}>
            {save.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
            {t(REPORTS.slotsSave)}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
