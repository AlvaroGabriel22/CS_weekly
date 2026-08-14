import { useEffect, useState } from 'react'
import { Loader2, RotateCcw, Save } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/feedback'
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher'
import { useToast } from '@/components/ui/toast'
import { parseApiError } from '@/lib/errors'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { PROFILE as M } from '@/i18n/messages/profile'
import { useUpdateWritingProfile, useWritingProfile } from '@/hooks/useProfile'
import type { WritingProfile } from '@/types'

// ── Campos editáveis nesta tela (default_template_id fica fora) ────────────
const EDITABLE_KEYS = [
  'default_language',
  'writing_tone',
  'objectivity',
  'technical_level',
  'auto_conclusions',
  'auto_next_steps',
  'auto_impact',
  'auto_describe_images',
  'auto_explain_charts',
  'personal_prompt',
] as const
type EditableKey = (typeof EDITABLE_KEYS)[number]

type BoolKey =
  | 'auto_conclusions'
  | 'auto_next_steps'
  | 'auto_impact'
  | 'auto_describe_images'
  | 'auto_explain_charts'

const TONE_OPTIONS: { value: string; label: Msg }[] = [
  { value: 'analyst', label: M.toneAnalyst },
  { value: 'specialist', label: M.toneSpecialist },
  { value: 'supervisor', label: M.toneSupervisor },
  { value: 'manager', label: M.toneManager },
  { value: 'director', label: M.toneDirector },
]

const OBJECTIVITY_OPTIONS: { value: string; label: Msg }[] = [
  { value: 'low', label: M.objectivityLow },
  { value: 'medium', label: M.objectivityMedium },
  { value: 'high', label: M.objectivityHigh },
]

const TECHNICAL_OPTIONS: { value: string; label: Msg }[] = [
  { value: 'low', label: M.technicalLow },
  { value: 'medium', label: M.technicalMedium },
  { value: 'high', label: M.technicalHigh },
]

const AUTO_SWITCHES: { key: BoolKey; label: Msg }[] = [
  { key: 'auto_conclusions', label: M.autoConclusions },
  { key: 'auto_next_steps', label: M.autoNextSteps },
  { key: 'auto_impact', label: M.autoImpact },
  { key: 'auto_describe_images', label: M.autoDescribeImages },
  { key: 'auto_explain_charts', label: M.autoExplainCharts },
]

/** Atribuição tipada de uma chave editável em um Partial<WritingProfile>. */
function setChange<K extends EditableKey>(
  target: Partial<WritingProfile>,
  key: K,
  value: WritingProfile[K]
) {
  target[key] = value
}

function SettingsSkeleton() {
  const { t } = useI18n()
  return (
    <Card aria-busy="true" aria-label={t(COMMON.loading)}>
      <CardHeader>
        <Skeleton className="h-5 w-52" />
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </div>
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between gap-4">
              <Skeleton className="h-4 w-44" />
              <Skeleton className="h-5 w-9 rounded-full" />
            </div>
          ))}
        </div>
        <Skeleton className="h-24 w-full" />
        <div className="flex justify-end">
          <Skeleton className="h-10 w-40" />
        </div>
      </CardContent>
    </Card>
  )
}

export function SettingsPage() {
  const { toast } = useToast()
  const { t } = useI18n()
  const { data: saved, isLoading, isError, error, refetch } = useWritingProfile()
  const updateWritingProfile = useUpdateWritingProfile()

  // Cópia local editável; o "saved" (cache da query) é a linha de base do dirty.
  const [form, setForm] = useState<WritingProfile | null>(null)

  useEffect(() => {
    if (saved && form === null) setForm(saved)
  }, [saved, form])

  const setField = <K extends EditableKey>(key: K, value: WritingProfile[K]) => {
    setForm(prev => (prev ? { ...prev, [key]: value } : prev))
  }

  const dirty =
    form !== null && saved !== undefined && EDITABLE_KEYS.some(key => form[key] !== saved[key])
  const saving = updateWritingProfile.isPending

  const handleSave = () => {
    if (!form || !saved || !dirty) return
    const changes: Partial<WritingProfile> = {}
    for (const key of EDITABLE_KEYS) {
      if (form[key] !== saved[key]) setChange(changes, key, form[key])
    }
    updateWritingProfile.mutate(changes, {
      onSuccess: (data) => {
        setForm(data)
        toast.success(t(M.saved))
      },
      onError: (err) => toast.error(parseApiError(err).message),
    })
  }

  const handleDiscard = () => {
    if (saved) setForm(saved)
  }

  const renderWritingCard = () => {
    if (isError) return <ErrorState error={error} onRetry={() => refetch()} />
    if (isLoading || !form) return <SettingsSkeleton />

    return (
      <Card className="animate-fade-in">
        <CardHeader>
          <CardTitle>{t(M.writingTitle)}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Idioma e tom */}
          <section className="space-y-3" aria-labelledby="settings-language-tone">
            <h4 id="settings-language-tone" className="text-sm font-semibold text-gray-900">
              {t(M.langToneHeading)}
            </h4>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="default_language" className="text-gray-700">{t(M.reportLanguage)}</Label>
                <Select
                  value={form.default_language}
                  onValueChange={(v) => setField('default_language', v === 'en' ? 'en' : 'pt')}
                >
                  <SelectTrigger id="default_language">
                    <SelectValue placeholder={t(M.selectPlaceholder)} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pt">{t(M.langPt)}</SelectItem>
                    <SelectItem value="en">{t(M.langEn)}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="writing_tone" className="text-gray-700">{t(M.tone)}</Label>
                <Select value={form.writing_tone} onValueChange={(v) => setField('writing_tone', v)}>
                  <SelectTrigger id="writing_tone">
                    <SelectValue placeholder={t(M.selectPlaceholder)} />
                  </SelectTrigger>
                  <SelectContent>
                    {TONE_OPTIONS.map(opt => (
                      <SelectItem key={opt.value} value={opt.value}>{t(opt.label)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="objectivity" className="text-gray-700">{t(M.objectivity)}</Label>
                <Select value={form.objectivity} onValueChange={(v) => setField('objectivity', v)}>
                  <SelectTrigger id="objectivity">
                    <SelectValue placeholder={t(M.selectPlaceholder)} />
                  </SelectTrigger>
                  <SelectContent>
                    {OBJECTIVITY_OPTIONS.map(opt => (
                      <SelectItem key={opt.value} value={opt.value}>{t(opt.label)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="technical_level" className="text-gray-700">{t(M.technicalLevel)}</Label>
                <Select value={form.technical_level} onValueChange={(v) => setField('technical_level', v)}>
                  <SelectTrigger id="technical_level">
                    <SelectValue placeholder={t(M.selectPlaceholder)} />
                  </SelectTrigger>
                  <SelectContent>
                    {TECHNICAL_OPTIONS.map(opt => (
                      <SelectItem key={opt.value} value={opt.value}>{t(opt.label)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>

          {/* Conteúdo automático */}
          <section className="space-y-1 border-t border-gray-100 pt-5" aria-labelledby="settings-auto">
            <h4 id="settings-auto" className="pb-1 text-sm font-semibold text-gray-900">
              {t(M.autoHeading)}
            </h4>
            {AUTO_SWITCHES.map(item => (
              <div
                key={item.key}
                className="-mx-2 flex min-h-10 items-center justify-between gap-4 rounded-lg px-2 py-2 transition-colors duration-200 hover:bg-gray-50"
              >
                <Label htmlFor={item.key} className="min-w-0 cursor-pointer text-sm text-gray-900">
                  {t(item.label)}
                </Label>
                <Switch
                  id={item.key}
                  checked={form[item.key]}
                  onCheckedChange={(v) => setField(item.key, v)}
                />
              </div>
            ))}
          </section>

          {/* Instruções pessoais */}
          <section className="space-y-2 border-t border-gray-100 pt-5" aria-labelledby="settings-prompt">
            <h4 id="settings-prompt" className="text-sm font-semibold text-gray-900">
              {t(M.promptHeading)}
            </h4>
            <Textarea
              id="personal_prompt"
              rows={5}
              value={form.personal_prompt ?? ''}
              onChange={(e) => setField('personal_prompt', e.target.value)}
              placeholder={t(M.promptPlaceholder)}
              aria-label={t(M.promptHeading)}
            />
          </section>

          {/* Barra de salvar (dirty-state) */}
          <div className="flex flex-col gap-3 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="min-w-0 text-xs text-gray-500" aria-live="polite">
              {dirty ? (
                <span className="inline-flex items-center gap-1.5 font-medium text-amber-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden="true" />
                  {t(M.unsavedChanges)}
                </span>
              ) : (
                t(M.allSaved)
              )}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              {dirty && !saving && (
                <Button variant="ghost" onClick={handleDiscard}>
                  <RotateCcw aria-hidden="true" />
                  {t(M.discard)}
                </Button>
              )}
              <Button onClick={handleSave} disabled={!dirty || saving}>
                {saving ? (
                  <>
                    <Loader2 className="animate-spin" aria-hidden="true" />
                    {t(M.saving)}
                  </>
                ) : (
                  <>
                    <Save aria-hidden="true" />
                    {t(COMMON.save)}
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <PageContainer title={t(COMMON.settings)} maxWidth="4xl">
      <div className="space-y-6">
        {/* ── Card: idioma da interface (client-side, via useI18n) ────────── */}
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>{t(COMMON.language)}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto pb-1">
              <LanguageSwitcher variant="full" />
            </div>
          </CardContent>
        </Card>

        {/* ── Card: preferências de escrita da IA ─────────────────────────── */}
        {renderWritingCard()}
      </div>
    </PageContainer>
  )
}
