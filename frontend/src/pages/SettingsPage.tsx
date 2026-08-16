import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Info,
  Loader2,
  Mail,
  Plus,
  RotateCcw,
  Save,
  Share2,
  SlidersHorizontal,
  Trash2,
  UserCog,
} from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Avatar } from '@/components/ui/avatar'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, ErrorState } from '@/components/feedback'
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher'
import { useToast } from '@/components/ui/toast'
import { parseApiError, type FieldErrorInfo } from '@/lib/errors'
import api from '@/lib/api'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { PROFILE as M } from '@/i18n/messages/profile'
import { useUpdateWritingProfile, useWritingProfile } from '@/hooks/useProfile'
import {
  useAccessGrants,
  useAddAccessGrant,
  useAddEmailRecipient,
  useChangeRole,
  useEmailRecipients,
  useRemoveAccessGrant,
  useRemoveEmailRecipient,
} from '@/hooks/useSharing'
import { useAuth } from '@/contexts/AuthContext'
import { isManagementRole, type WritingProfile } from '@/types'

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

// ── Helpers de erro de campo (padrão RegisterPage) ─────────────────────────

const errorInputClass = 'border-red-500 bg-red-50 focus-visible:ring-red-500'

function FieldMessage({ id, error }: { id: string; error?: FieldErrorInfo }) {
  if (!error) return null
  return (
    <div id={id} role="alert" className="space-y-0.5">
      <p className="text-sm font-medium text-red-600">{error.message}</p>
      {error.hint && <p className="text-xs text-red-500">{error.hint}</p>}
    </div>
  )
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

/** Skeleton compacto para os cards de listas (compartilhamento). */
function ListSkeleton({ rows = 3 }: { rows?: number }) {
  const { t } = useI18n()
  return (
    <div className="space-y-3" aria-busy="true" aria-label={t(COMMON.loading)}>
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="min-w-0 flex-1 space-y-1.5">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-28" />
          </div>
          <Skeleton className="h-9 w-9 rounded-lg" />
        </div>
      ))}
    </div>
  )
}

// ── Aba GERAL: idioma da interface + preferências de escrita ───────────────

function GeneralTab() {
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
  )
}

// ── Aba CONTA: mudança de cargo ────────────────────────────────────────────

interface RoleOption {
  value: string
  label: string
}

function RoleChangeCard() {
  const { toast } = useToast()
  const { t } = useI18n()
  const { user, refreshUser } = useAuth()
  const changeRole = useChangeRole()

  const [role, setRole] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, FieldErrorInfo>>({})

  const rolesQuery = useQuery<RoleOption[]>({
    queryKey: ['auth-roles'],
    queryFn: async () => (await api.get<{ roles: RoleOption[] }>('/auth/roles')).data.roles,
    staleTime: Infinity,
  })

  const clearError = (field: string) => {
    setErrors(prev => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  const focusFirstError = (errs: Record<string, FieldErrorInfo>) => {
    const first = ['role', 'password'].find(f => errs[f])
    if (first) document.getElementById(first === 'role' ? 'new_role' : 'role_password')?.focus()
  }

  const handleSubmit = () => {
    const localErrors: Record<string, FieldErrorInfo> = {}
    if (!role) localErrors.role = { message: t(M.roleRequired) }
    if (!password) localErrors.password = { message: t(M.currentRequired) }
    if (Object.keys(localErrors).length > 0) {
      setErrors(localErrors)
      focusFirstError(localErrors)
      return
    }
    setErrors({})
    changeRole.mutate(
      { role, password },
      {
        onSuccess: () => {
          toast.success(t(M.roleChanged))
          setRole('')
          setPassword('')
          void refreshUser()
        },
        onError: (err) => {
          const parsed = parseApiError(err)
          if (parsed.kind === 'field' && Object.keys(parsed.fields).length > 0) {
            setErrors(parsed.fields)
            focusFirstError(parsed.fields)
          } else {
            toast.error(parsed.message)
          }
        },
      }
    )
  }

  const saving = changeRole.isPending
  const managementSelected = isManagementRole(role)

  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <CardTitle>{t(M.roleChangeTitle)}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-gray-600">
          {t(M.currentRole)}: <span className="font-medium text-gray-900">{user?.role ?? '—'}</span>
        </p>

        {rolesQuery.isError ? (
          <ErrorState error={rolesQuery.error} onRetry={() => rolesQuery.refetch()} />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="new_role" className="text-gray-700">{t(M.newRole)}</Label>
                {rolesQuery.isLoading ? (
                  <Skeleton className="h-10 w-full" />
                ) : (
                  <Select
                    value={role}
                    onValueChange={(v) => {
                      setRole(v)
                      clearError('role')
                    }}
                  >
                    <SelectTrigger
                      id="new_role"
                      className={errors.role ? errorInputClass : undefined}
                      aria-invalid={errors.role ? true : undefined}
                      aria-describedby={errors.role ? 'new_role-error' : undefined}
                    >
                      <SelectValue placeholder={t(M.selectPlaceholder)} />
                    </SelectTrigger>
                    <SelectContent>
                      {(rolesQuery.data ?? []).map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                <FieldMessage id="new_role-error" error={errors.role} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="role_password" className="text-gray-700">{t(M.currentPassword)}</Label>
                <Input
                  id="role_password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    clearError('password')
                  }}
                  placeholder={t(M.passwordTitle)}
                  className={errors.password ? errorInputClass : undefined}
                  aria-invalid={errors.password ? true : undefined}
                  aria-describedby={errors.password ? 'role_password-error' : undefined}
                />
                <FieldMessage id="role_password-error" error={errors.password} />
              </div>
            </div>

            {managementSelected && (
              <div
                role="status"
                className="flex items-start gap-2.5 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800 animate-fade-in"
              >
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" aria-hidden="true" />
                <p className="min-w-0">{t(M.managementNotice)}</p>
              </div>
            )}

            <div className="flex justify-end">
              <Button onClick={handleSubmit} disabled={saving}>
                {saving ? (
                  <>
                    <Loader2 className="animate-spin" aria-hidden="true" />
                    {t(M.changingRole)}
                  </>
                ) : (
                  <>
                    <UserCog aria-hidden="true" />
                    {t(M.changeRole)}
                  </>
                )}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// ── Aba COMPARTILHAMENTO: acesso aos meus weeklys ──────────────────────────

function AccessGrantsCard() {
  const { toast } = useToast()
  const { t } = useI18n()
  const grantsQuery = useAccessGrants()
  const addGrant = useAddAccessGrant()
  const removeGrant = useRemoveAccessGrant()

  const [employeeId, setEmployeeId] = useState('')
  const [fieldError, setFieldError] = useState<FieldErrorInfo | undefined>()
  const inputRef = useRef<HTMLInputElement>(null)

  const handleAdd = () => {
    const value = employeeId.trim()
    if (!value) {
      setFieldError({ message: t(M.employeeIdRequired) })
      inputRef.current?.focus()
      return
    }
    setFieldError(undefined)
    addGrant.mutate(
      { employeeId: value },
      {
        onSuccess: () => {
          toast.success(t(M.grantAdded))
          setEmployeeId('')
        },
        onError: (err) => {
          const parsed = parseApiError(err)
          if (parsed.kind === 'field' && parsed.fields.employee_id) {
            setFieldError(parsed.fields.employee_id)
            inputRef.current?.focus()
          } else {
            toast.error(parsed.message)
          }
        },
      }
    )
  }

  const handleRemove = (userId: string) => {
    removeGrant.mutate(
      { userId },
      {
        onSuccess: () => toast.success(t(M.grantRemoved)),
        onError: (err) => toast.error(parseApiError(err).message),
      }
    )
  }

  const renderBody = () => {
    if (grantsQuery.isError) {
      return <ErrorState error={grantsQuery.error} onRetry={() => grantsQuery.refetch()} />
    }
    if (grantsQuery.isLoading) return <ListSkeleton />

    const grants = grantsQuery.data ?? []

    return (
      <>
        {/* Formulário: matrícula + adicionar */}
        <div className="space-y-2">
          <div className="flex flex-wrap items-start gap-2">
            <div className="min-w-0 flex-1 basis-40">
              <Label htmlFor="grant_employee_id" className="sr-only">{t(M.employeeId)}</Label>
              <Input
                id="grant_employee_id"
                ref={inputRef}
                value={employeeId}
                onChange={(e) => {
                  setEmployeeId(e.target.value)
                  setFieldError(undefined)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAdd()
                }}
                placeholder={t(M.employeeId)}
                className={fieldError ? errorInputClass : undefined}
                aria-invalid={fieldError ? true : undefined}
                aria-describedby={fieldError ? 'grant_employee_id-error' : undefined}
              />
            </div>
            <Button onClick={handleAdd} disabled={addGrant.isPending} className="shrink-0">
              {addGrant.isPending ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : (
                <Plus aria-hidden="true" />
              )}
              {t(COMMON.add)}
            </Button>
          </div>
          <FieldMessage id="grant_employee_id-error" error={fieldError} />
        </div>

        {/* Lista de exceções */}
        {grants.length === 0 ? (
          <EmptyState title={t(M.grantsEmpty)} className="py-6" />
        ) : (
          <ul className="divide-y divide-gray-100">
            {grants.map(person => {
              const removing = removeGrant.isPending && removeGrant.variables?.userId === person.id
              return (
                <li key={person.id} className="flex items-center gap-3 py-3">
                  <Avatar src={person.photo_url} name={person.name} size="md" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">{person.name}</p>
                    <p className="truncate text-xs text-gray-500">
                      {person.employee_id} · {person.sector} · {person.role}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemove(person.id)}
                    disabled={removeGrant.isPending}
                    aria-label={t(M.removeAccess, { name: person.name })}
                    className="shrink-0 text-gray-400 transition-colors duration-200 hover:bg-red-50 hover:text-red-600"
                  >
                    {removing ? (
                      <Loader2 className="animate-spin" aria-hidden="true" />
                    ) : (
                      <Trash2 aria-hidden="true" />
                    )}
                  </Button>
                </li>
              )
            })}
          </ul>
        )}
      </>
    )
  }

  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <CardTitle>{t(M.grantsTitle)}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-gray-600">{t(M.grantsHint)}</p>
        {renderBody()}
      </CardContent>
    </Card>
  )
}

// ── Aba COMPARTILHAMENTO: lista de e-mails do weekly ───────────────────────

function EmailRecipientsCard() {
  const { toast } = useToast()
  const { t } = useI18n()
  const recipientsQuery = useEmailRecipients()
  const addRecipient = useAddEmailRecipient()
  const removeRecipient = useRemoveEmailRecipient()

  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [fieldError, setFieldError] = useState<FieldErrorInfo | undefined>()
  const emailRef = useRef<HTMLInputElement>(null)

  const handleAdd = () => {
    const value = email.trim()
    if (!value) {
      setFieldError({ message: t(M.emailRequired) })
      emailRef.current?.focus()
      return
    }
    setFieldError(undefined)
    const trimmedName = name.trim()
    addRecipient.mutate(
      { email: value, ...(trimmedName ? { name: trimmedName } : {}) },
      {
        onSuccess: () => {
          toast.success(t(M.emailAdded))
          setEmail('')
          setName('')
        },
        onError: (err) => {
          const parsed = parseApiError(err)
          if (parsed.kind === 'field' && parsed.fields.email) {
            setFieldError(parsed.fields.email)
            emailRef.current?.focus()
          } else {
            toast.error(parsed.message)
          }
        },
      }
    )
  }

  const handleRemove = (recipientId: string) => {
    removeRecipient.mutate(
      { recipientId },
      {
        onSuccess: () => toast.success(t(M.emailRemoved)),
        onError: (err) => toast.error(parseApiError(err).message),
      }
    )
  }

  const renderBody = () => {
    if (recipientsQuery.isError) {
      return <ErrorState error={recipientsQuery.error} onRetry={() => recipientsQuery.refetch()} />
    }
    if (recipientsQuery.isLoading) return <ListSkeleton />

    const recipients = recipientsQuery.data ?? []

    return (
      <>
        {/* Formulário: e-mail + nome opcional + adicionar */}
        <div className="space-y-2">
          <div className="flex flex-wrap items-start gap-2">
            <div className="min-w-0 flex-1 basis-52">
              <Label htmlFor="recipient_email" className="sr-only">{t(M.email)}</Label>
              <Input
                id="recipient_email"
                ref={emailRef}
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  setFieldError(undefined)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAdd()
                }}
                placeholder={t(M.email)}
                className={fieldError ? errorInputClass : undefined}
                aria-invalid={fieldError ? true : undefined}
                aria-describedby={fieldError ? 'recipient_email-error' : undefined}
              />
            </div>
            <div className="min-w-0 flex-1 basis-40">
              <Label htmlFor="recipient_name" className="sr-only">{t(M.nameOptional)}</Label>
              <Input
                id="recipient_name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAdd()
                }}
                placeholder={t(M.nameOptional)}
              />
            </div>
            <Button onClick={handleAdd} disabled={addRecipient.isPending} className="shrink-0">
              {addRecipient.isPending ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : (
                <Plus aria-hidden="true" />
              )}
              {t(COMMON.add)}
            </Button>
          </div>
          <FieldMessage id="recipient_email-error" error={fieldError} />
        </div>

        {/* Lista de destinatários */}
        {recipients.length === 0 ? (
          <EmptyState icon={Mail} title={t(M.emailsEmpty)} className="py-6" />
        ) : (
          <ul className="divide-y divide-gray-100">
            {recipients.map(recipient => {
              const removing =
                removeRecipient.isPending && removeRecipient.variables?.recipientId === recipient.id
              return (
                <li key={recipient.id} className="flex items-center gap-3 py-3">
                  <span
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand"
                    aria-hidden="true"
                  >
                    <Mail className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">{recipient.email}</p>
                    {recipient.name && (
                      <p className="truncate text-xs text-gray-500">{recipient.name}</p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemove(recipient.id)}
                    disabled={removeRecipient.isPending}
                    aria-label={t(M.removeEmail, { email: recipient.email })}
                    className="shrink-0 text-gray-400 transition-colors duration-200 hover:bg-red-50 hover:text-red-600"
                  >
                    {removing ? (
                      <Loader2 className="animate-spin" aria-hidden="true" />
                    ) : (
                      <Trash2 aria-hidden="true" />
                    )}
                  </Button>
                </li>
              )
            })}
          </ul>
        )}
      </>
    )
  }

  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <CardTitle>{t(M.emailsTitle)}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-gray-600">{t(M.emailsHint)}</p>
        {renderBody()}
      </CardContent>
    </Card>
  )
}

// ── Página ─────────────────────────────────────────────────────────────────

export function SettingsPage() {
  const { t } = useI18n()
  const [tab, setTab] = useState('geral')

  return (
    <PageContainer title={t(COMMON.settings)} maxWidth="4xl">
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="geral">
            <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
            {t(M.tabGeneral)}
          </TabsTrigger>
          <TabsTrigger value="conta">
            <UserCog className="h-4 w-4" aria-hidden="true" />
            {t(M.tabAccount)}
          </TabsTrigger>
          <TabsTrigger value="compartilhamento">
            <Share2 className="h-4 w-4" aria-hidden="true" />
            {t(M.tabSharing)}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="geral">
          <GeneralTab />
        </TabsContent>

        <TabsContent value="conta">
          <RoleChangeCard />
        </TabsContent>

        <TabsContent value="compartilhamento">
          <div className="space-y-6">
            <AccessGrantsCard />
            <EmailRecipientsCard />
          </div>
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
