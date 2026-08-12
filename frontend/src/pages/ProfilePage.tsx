import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  Briefcase,
  Building2,
  Camera,
  Eye,
  EyeOff,
  Hash,
  KeyRound,
  Layers,
  Loader2,
  Mail,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { PageContainer } from '@/components/layout/PageContainer'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Avatar } from '@/components/ui/avatar'
import { useToast } from '@/components/ui/toast'
import { parseApiError, type FieldErrorInfo } from '@/lib/errors'
import { cn } from '@/lib/utils'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { PROFILE as M } from '@/i18n/messages/profile'
import {
  PHOTO_ACCEPT,
  passwordStrength,
  useChangePassword,
  useUpdateProfile,
  useUploadPhoto,
  validatePhotoFile,
  type PasswordStrength,
} from '@/hooks/useProfile'

// ── Senha: campos na ordem do formulário (para focar o primeiro com erro) ──
const PW_FIELD_ORDER = ['current_password', 'new_password', 'new_password_confirm'] as const
type PwField = (typeof PW_FIELD_ORDER)[number]

function isPwField(field: string): field is PwField {
  return (PW_FIELD_ORDER as readonly string[]).includes(field)
}

/** Caixa vermelha quando o campo está com erro (padrão do RegisterPage). */
const ERROR_INPUT_CLASS = 'bg-red-50 border-red-500 focus-visible:ring-red-300'

const STRENGTH_LABEL: Record<PasswordStrength['level'], Msg> = {
  weak: M.strengthWeak,
  medium: M.strengthMedium,
  strong: M.strengthStrong,
}

/** Mensagem + dica abaixo do campo, com ícone e role="alert". */
function FieldFeedback({ id, error }: { id: string; error?: FieldErrorInfo | null }) {
  if (!error) return null
  return (
    <div id={id} role="alert" className="space-y-0.5">
      <p className="flex items-center gap-1 text-xs font-medium text-red-600">
        <AlertCircle className="h-3 w-3 shrink-0" aria-hidden="true" />
        {error.message}
      </p>
      {error.hint && <p className="pl-4 text-xs text-red-500">{error.hint}</p>}
    </div>
  )
}

/** Linha somente leitura com ícone (email, matrícula, cargo, setor, depto). */
function ReadOnlyField({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex min-w-0 items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2.5">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-500">{label}</p>
        <p className="truncate text-sm text-gray-900" title={value}>{value}</p>
      </div>
    </div>
  )
}

interface PasswordFieldProps {
  id: PwField
  label: string
  value: string
  autoComplete: string
  error?: FieldErrorInfo
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  children?: React.ReactNode
}

/** Campo de senha com botão mostrar/ocultar. */
function PasswordField({ id, label, value, autoComplete, error, onChange, children }: PasswordFieldProps) {
  const { t } = useI18n()
  const [show, setShow] = useState(false)
  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-gray-700">{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={show ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          placeholder="••••••••"
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
          className={cn('pr-11', error && ERROR_INPUT_CLASS)}
        />
        <button
          type="button"
          onClick={() => setShow(s => !s)}
          aria-label={show ? t(M.hidePassword) : t(M.showPassword)}
          className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-2 text-gray-400 transition-colors hover:text-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {show ? (
            <EyeOff className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Eye className="h-4 w-4" aria-hidden="true" />
          )}
        </button>
      </div>
      {children}
      <FieldFeedback id={`${id}-error`} error={error} />
    </div>
  )
}

export function ProfilePage() {
  const { user } = useAuth()
  const { toast } = useToast()
  const { t, locale } = useI18n()

  // Foto
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [photoError, setPhotoError] = useState<FieldErrorInfo | null>(null)
  const uploadPhoto = useUploadPhoto()

  // Nome
  const [name, setName] = useState(user?.name ?? '')
  const [nameError, setNameError] = useState<FieldErrorInfo | null>(null)
  const updateProfile = useUpdateProfile()

  // Senha
  const [pw, setPw] = useState({ current_password: '', new_password: '', new_password_confirm: '' })
  const [pwErrors, setPwErrors] = useState<Partial<Record<PwField, FieldErrorInfo>>>({})
  const changePassword = useChangePassword()

  // Libera a URL de preview anterior (e a atual, ao desmontar).
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  if (!user) return null

  // ── Foto ──────────────────────────────────────────────────────────────────

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = '' // permite escolher o mesmo arquivo novamente
    if (!file) return
    const validation = validatePhotoFile(file)
    if (validation) {
      const parsed: FieldErrorInfo =
        validation.code === 'type'
          ? { message: t(M.photoBadType), hint: t(M.photoBadTypeHint) }
          : {
              message: t(M.photoTooLarge, {
                mb: validation.mb.toLocaleString(locale, { maximumFractionDigits: 1 }),
              }),
              hint: t(M.photoTooLargeHint),
            }
      setPhotoError(parsed)
      toast.error(parsed.message)
      return
    }
    setPhotoError(null)
    setPendingFile(file)
    setPreviewUrl(URL.createObjectURL(file)) // preview imediato, antes do upload
  }

  const handlePhotoCancel = () => {
    setPendingFile(null)
    setPreviewUrl(null)
    setPhotoError(null)
  }

  const handlePhotoSave = () => {
    if (!pendingFile) return
    uploadPhoto.mutate(pendingFile, {
      onSuccess: () => {
        toast.success(t(M.photoSaved))
        setPendingFile(null)
        setPreviewUrl(null)
        setPhotoError(null)
      },
      onError: (err) => {
        const parsed = parseApiError(err)
        const fieldError = parsed.fields.photo ?? { message: parsed.message }
        setPhotoError(fieldError)
        toast.error(fieldError.message)
      },
    })
  }

  // ── Nome ──────────────────────────────────────────────────────────────────

  const trimmedName = name.trim()
  const nameDirty = trimmedName.length > 0 && trimmedName !== user.name

  const handleNameSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!nameDirty) return
    if (trimmedName.length < 2) {
      setNameError({ message: t(M.nameTooShort), hint: t(M.nameTooShortHint) })
      document.getElementById('profile_name')?.focus()
      return
    }
    updateProfile.mutate(
      { name: trimmedName },
      {
        onSuccess: () => {
          setNameError(null)
          toast.success(t(M.saved))
        },
        onError: (err) => {
          const parsed = parseApiError(err)
          if (parsed.fields.name) {
            setNameError(parsed.fields.name)
            document.getElementById('profile_name')?.focus()
          } else {
            toast.error(parsed.message)
          }
        },
      }
    )
  }

  // ── Senha ─────────────────────────────────────────────────────────────────

  const focusFirstPwError = (errors: Partial<Record<PwField, FieldErrorInfo>>) => {
    const first = PW_FIELD_ORDER.find(field => errors[field])
    if (first) {
      const el = document.getElementById(first)
      el?.focus()
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  const updatePw = (field: PwField) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setPw(prev => ({ ...prev, [field]: value }))
    setPwErrors(prev => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const errors: Partial<Record<PwField, FieldErrorInfo>> = {}

    if (!pw.current_password) {
      errors.current_password = { message: t(M.currentRequired) }
    }
    if (!pw.new_password) {
      errors.new_password = { message: t(M.newRequired) }
    } else if (pw.new_password.length < 6) {
      errors.new_password = { message: t(M.newTooShort) }
    }
    if (!pw.new_password_confirm) {
      errors.new_password_confirm = { message: t(M.confirmRequired) }
    } else if (pw.new_password && pw.new_password !== pw.new_password_confirm) {
      errors.new_password_confirm = { message: t(M.passwordMismatch) }
    }

    setPwErrors(errors)
    if (Object.keys(errors).length > 0) {
      focusFirstPwError(errors)
      return
    }

    changePassword.mutate(pw, {
      onSuccess: () => {
        toast.success(t(M.passwordChanged))
        setPw({ current_password: '', new_password: '', new_password_confirm: '' })
        setPwErrors({})
      },
      onError: (err) => {
        // O backend aponta o campo (current_password / new_password /
        // new_password_confirm) com mensagem + dica — pinta e foca o campo.
        const parsed = parseApiError(err)
        if (parsed.kind === 'field' && Object.keys(parsed.fields).length > 0) {
          const serverErrors: Partial<Record<PwField, FieldErrorInfo>> = {}
          for (const [field, info] of Object.entries(parsed.fields)) {
            if (isPwField(field)) {
              serverErrors[field] = { message: info.message, hint: info.hint }
            }
          }
          if (Object.keys(serverErrors).length > 0) {
            setPwErrors(serverErrors)
            focusFirstPwError(serverErrors)
            return
          }
        }
        toast.error(parsed.message)
      },
    })
  }

  const strength = pw.new_password ? passwordStrength(pw.new_password) : null

  return (
    <PageContainer title={t(COMMON.profile)} maxWidth="3xl">
      <div className="space-y-6">
        {/* ── Card: foto ─────────────────────────────────────────────────── */}
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>{t(M.photoTitle)}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start sm:gap-6">
              <div className="relative shrink-0">
                <Avatar src={previewUrl ?? user.photo_url} name={user.name} size="xl" />
                {uploadPhoto.isPending && (
                  <div
                    role="status"
                    aria-label={t(M.uploadingPhotoAria)}
                    className="absolute inset-0 flex items-center justify-center rounded-full bg-white/70"
                  >
                    <Loader2 className="h-7 w-7 animate-spin text-brand" aria-hidden="true" />
                  </div>
                )}
              </div>

              <div className="flex w-full min-w-0 flex-1 flex-col items-center gap-3 sm:items-start">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={PHOTO_ACCEPT}
                  className="hidden"
                  onChange={handlePhotoSelect}
                />

                {pendingFile ? (
                  <>
                    <p className="max-w-full truncate text-sm font-medium text-gray-900" title={pendingFile.name}>
                      {pendingFile.name}
                    </p>
                    <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                      <Button onClick={handlePhotoSave} disabled={uploadPhoto.isPending}>
                        {uploadPhoto.isPending ? t(M.uploading) : t(COMMON.save)}
                      </Button>
                      <Button variant="outline" onClick={handlePhotoCancel} disabled={uploadPhoto.isPending}>
                        {t(COMMON.cancel)}
                      </Button>
                    </div>
                  </>
                ) : (
                  <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
                    <Camera aria-hidden="true" />
                    {t(M.changePhoto)}
                  </Button>
                )}

                {photoError && (
                  <div role="alert" className="w-full rounded-lg border border-red-200 bg-red-50 px-3 py-2">
                    <p className="flex items-center gap-1.5 text-xs font-medium text-red-700">
                      <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                      {photoError.message}
                    </p>
                    {photoError.hint && <p className="mt-0.5 pl-5 text-xs text-red-600">{photoError.hint}</p>}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ── Card: dados ────────────────────────────────────────────────── */}
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>{t(M.dataTitle)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <form onSubmit={handleNameSubmit} noValidate className="space-y-2">
              <Label htmlFor="profile_name" className="text-gray-700">{t(M.name)}</Label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  id="profile_name"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value)
                    if (nameError) setNameError(null)
                  }}
                  placeholder={t(M.name)}
                  autoComplete="name"
                  aria-invalid={!!nameError}
                  aria-describedby={nameError ? 'profile_name-error' : undefined}
                  className={cn('min-w-0', nameError && ERROR_INPUT_CLASS)}
                />
                <Button type="submit" disabled={!nameDirty || updateProfile.isPending} className="shrink-0">
                  {updateProfile.isPending ? (
                    <>
                      <Loader2 className="animate-spin" aria-hidden="true" />
                      {t(M.saving)}
                    </>
                  ) : (
                    t(COMMON.save)
                  )}
                </Button>
              </div>
              <FieldFeedback id="profile_name-error" error={nameError} />
            </form>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <ReadOnlyField icon={Mail} label={t(M.email)} value={user.email} />
              <ReadOnlyField icon={Hash} label={t(M.employeeId)} value={user.employee_id} />
              <ReadOnlyField icon={Briefcase} label={t(M.role)} value={user.role} />
              <ReadOnlyField icon={Layers} label={t(M.sector)} value={user.sector} />
              <ReadOnlyField icon={Building2} label={t(M.department)} value={user.department} />
            </div>
          </CardContent>
        </Card>

        {/* ── Card: senha ────────────────────────────────────────────────── */}
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle>{t(M.passwordTitle)}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePasswordSubmit} noValidate className="space-y-4">
              <PasswordField
                id="current_password"
                label={t(M.currentPassword)}
                value={pw.current_password}
                onChange={updatePw('current_password')}
                autoComplete="current-password"
                error={pwErrors.current_password}
              />

              <PasswordField
                id="new_password"
                label={t(M.newPassword)}
                value={pw.new_password}
                onChange={updatePw('new_password')}
                autoComplete="new-password"
                error={pwErrors.new_password}
              >
                {strength && (
                  <div className="space-y-1" aria-live="polite">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                      <div
                        className={cn('h-full rounded-full transition-all duration-300 ease-out', strength.barClass)}
                        style={{ width: `${strength.percent}%` }}
                      />
                    </div>
                    <p className={cn('text-xs font-medium', strength.textClass)}>
                      {t(M.strength, { label: t(STRENGTH_LABEL[strength.level]) })}
                    </p>
                  </div>
                )}
              </PasswordField>

              <PasswordField
                id="new_password_confirm"
                label={t(M.confirmPassword)}
                value={pw.new_password_confirm}
                onChange={updatePw('new_password_confirm')}
                autoComplete="new-password"
                error={pwErrors.new_password_confirm}
              />

              <div className="pt-1">
                <Button type="submit" disabled={changePassword.isPending} className="w-full sm:w-auto">
                  {changePassword.isPending ? (
                    <>
                      <Loader2 className="animate-spin" aria-hidden="true" />
                      {t(M.changing)}
                    </>
                  ) : (
                    <>
                      <KeyRound aria-hidden="true" />
                      {t(M.changePassword)}
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}
