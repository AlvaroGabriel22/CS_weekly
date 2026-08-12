import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertCircle, Eye, EyeOff, Loader2 } from 'lucide-react'
import api from '@/lib/api'
import { parseApiError, type FieldErrorInfo } from '@/lib/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher'
import { useToast } from '@/components/ui/toast'
import { useI18n } from '@/i18n'
import { AUTH } from '@/i18n/messages/auth'

type Errors = Record<string, FieldErrorInfo>

/** Ordem dos campos — usada para focar o primeiro com erro. */
const FIELD_ORDER = ['email', 'employee_id', 'new_password', 'new_password_confirm']

/**
 * Recuperação de senha SEM email: a identidade é confirmada pela MATRÍCULA.
 * Segue o mesmo padrão visual e de erros do LoginPage/RegisterPage.
 */
export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [employeeId, setEmployeeId] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<Errors>({})
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { toast } = useToast()
  const { t } = useI18n()

  const focusFirstError = (newErrors: Errors) => {
    const first = FIELD_ORDER.find(field => newErrors[field])
    if (first) document.getElementById(first)?.focus()
  }

  const fieldClass = (field: string) =>
    errors[field]
      ? 'border-red-500 bg-red-50 placeholder:text-red-300 focus-visible:ring-red-300'
      : ''

  const FieldFeedback = ({ field }: { field: string }) => {
    const error = errors[field]
    if (!error) return null
    return (
      <div id={`${field}-error`} role="alert" className="space-y-0.5">
        <p className="flex items-center gap-1 text-xs font-medium text-red-600">
          <AlertCircle className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          {error.message}
        </p>
        {error.hint && <p className="pl-4 text-xs text-red-500">{error.hint}</p>}
      </div>
    )
  }

  const clearFeedback = (field: string) => {
    if (formError) setFormError('')
    setErrors(prev => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')

    const newErrors: Errors = {}
    if (!email.trim()) {
      newErrors.email = { message: t(AUTH.emailRequired), hint: t(AUTH.hintEmail) }
    }
    if (!employeeId.trim()) {
      newErrors.employee_id = { message: t(AUTH.employeeIdRequired), hint: t(AUTH.hintEmployeeId) }
    }
    if (!newPassword) {
      newErrors.new_password = { message: t(AUTH.passwordCreate), hint: t(AUTH.hintPassword) }
    } else if (newPassword.length < 6) {
      newErrors.new_password = { message: t(AUTH.passwordShort), hint: t(AUTH.hintPassword) }
    }
    if (!newPasswordConfirm) {
      newErrors.new_password_confirm = { message: t(AUTH.confirmRequired), hint: t(AUTH.hintPasswordConfirm) }
    } else if (newPassword && newPassword !== newPasswordConfirm) {
      newErrors.new_password_confirm = { message: t(AUTH.passwordMismatch), hint: t(AUTH.hintPasswordConfirm) }
    }
    setErrors(newErrors)
    if (Object.keys(newErrors).length > 0) {
      focusFirstError(newErrors)
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/reset-password', {
        email: email.trim(),
        employee_id: employeeId.trim(),
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      })
      toast.success(t(AUTH.resetDone))
      navigate('/login')
    } catch (err: unknown) {
      const parsed = parseApiError(err)
      if (parsed.kind === 'field' && Object.keys(parsed.fields).length > 0) {
        const fieldErrors: Errors = {}
        for (const [field, info] of Object.entries(parsed.fields)) {
          if (FIELD_ORDER.includes(field)) fieldErrors[field] = info
        }
        if (Object.keys(fieldErrors).length > 0) {
          setErrors(fieldErrors)
          focusFirstError(fieldErrors)
        } else {
          setFormError(parsed.message)
        }
      } else {
        setFormError(parsed.message)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 sm:px-6">
      <div className="absolute right-4 top-4 sm:right-6">
        <LanguageSwitcher variant="compact" />
      </div>

      <main className="w-full max-w-md animate-fade-in">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 text-xl font-bold text-white shadow-lg">
            Q
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{t(AUTH.resetTitle)}</h1>
          <p className="mt-1 text-sm text-gray-600">{t(AUTH.resetSubtitle)}</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-2xl border border-border/60 bg-white p-6 shadow-card sm:p-8"
          noValidate
        >
          {formError && (
            <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3">
              <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" aria-hidden="true" />
              <p className="min-w-0 text-sm text-red-800">{formError}</p>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="email" className="text-gray-700">{t(AUTH.email)}</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              autoFocus
              placeholder={t(AUTH.emailPh)}
              value={email}
              onChange={e => { setEmail(e.target.value); clearFeedback('email') }}
              disabled={loading}
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? 'email-error' : undefined}
              className={fieldClass('email')}
            />
            <FieldFeedback field="email" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="employee_id" className="text-gray-700">{t(AUTH.employeeId)}</Label>
            <Input
              id="employee_id"
              autoComplete="off"
              placeholder={t(AUTH.employeeIdPh)}
              value={employeeId}
              onChange={e => { setEmployeeId(e.target.value); clearFeedback('employee_id') }}
              disabled={loading}
              aria-invalid={!!errors.employee_id}
              aria-describedby={errors.employee_id ? 'employee_id-error' : undefined}
              className={fieldClass('employee_id')}
            />
            <FieldFeedback field="employee_id" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new_password" className="text-gray-700">{t(AUTH.newPassword)}</Label>
            <div className="relative">
              <Input
                id="new_password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                placeholder="••••••••"
                value={newPassword}
                onChange={e => { setNewPassword(e.target.value); clearFeedback('new_password') }}
                disabled={loading}
                aria-invalid={!!errors.new_password}
                aria-describedby={errors.new_password ? 'new_password-error' : undefined}
                className={`pr-10 ${fieldClass('new_password')}`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                aria-label={showPassword ? t(AUTH.hidePassword) : t(AUTH.showPassword)}
                className="absolute inset-y-0 right-0 flex items-center rounded-r-lg px-3 text-gray-400 transition-colors hover:text-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
              </button>
            </div>
            <FieldFeedback field="new_password" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new_password_confirm" className="text-gray-700">{t(AUTH.newPasswordConfirm)}</Label>
            <Input
              id="new_password_confirm"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="••••••••"
              value={newPasswordConfirm}
              onChange={e => { setNewPasswordConfirm(e.target.value); clearFeedback('new_password_confirm') }}
              disabled={loading}
              aria-invalid={!!errors.new_password_confirm}
              aria-describedby={errors.new_password_confirm ? 'new_password_confirm-error' : undefined}
              className={fieldClass('new_password_confirm')}
            />
            <FieldFeedback field="new_password_confirm" />
          </div>

          <Button type="submit" disabled={loading} className="w-full">
            {loading ? (
              <>
                <Loader2 className="animate-spin" aria-hidden="true" />
                {t(AUTH.resetting)}
              </>
            ) : (
              t(AUTH.resetSubmit)
            )}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          <Link to="/login" className="font-medium text-brand transition-colors hover:text-brand-600 hover:underline">
            {t(AUTH.backToLogin)}
          </Link>
        </p>
      </main>
    </div>
  )
}
