import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertCircle, Eye, EyeOff, Loader2, RefreshCw } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { parseApiError, type FieldErrorInfo } from '@/lib/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { AUTH } from '@/i18n/messages/auth'

interface Option {
  value: string
  label: string
}

type Errors = Record<string, FieldErrorInfo>

/** Ordem dos campos no formulário — usada para focar o primeiro com erro. */
const FIELD_ORDER = ['name', 'email', 'employee_id', 'password', 'password_confirm', 'role', 'sector']

/** Dica padrão por campo, usada quando o erro vem do servidor sem dica própria. */
const DEFAULT_HINT_MSGS: Record<string, Msg> = {
  name: AUTH.hintName,
  email: AUTH.hintEmail,
  employee_id: AUTH.hintEmployeeId,
  password: AUTH.hintPassword,
  password_confirm: AUTH.hintPasswordConfirm,
}

/**
 * Painel institucional do split-screen (md+). Duplicado propositalmente em
 * LoginPage/RegisterPage: cada página é dona apenas do próprio arquivo.
 */
function BrandPanel() {
  const { t } = useI18n()
  return (
    <aside className="relative hidden overflow-hidden bg-gradient-to-br from-brand-600 to-brand-800 text-white md:sticky md:top-0 md:flex md:h-screen md:w-[45%] md:flex-col md:p-10 lg:p-12">
      <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-white/5 blur-3xl" />
      <div aria-hidden="true" className="pointer-events-none absolute -bottom-28 -left-20 h-80 w-80 rounded-full bg-white/5 blur-3xl" />

      <div className="relative flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/10 text-lg font-bold ring-1 ring-white/20">
          Q
        </div>
        <span className="text-lg font-semibold tracking-wide">QWI</span>
      </div>

      <div className="relative my-auto max-w-md animate-fade-in">
        <h2 className="text-3xl font-bold leading-tight lg:text-4xl">Quality Weekly Intelligence</h2>
        <p className="mt-3 text-white/75">{t(AUTH.tagline)}</p>
      </div>
    </aside>
  )
}

/** Cabeçalho compacto exibido apenas no mobile (painel da marca fica oculto). */
function MobileBrandHeader() {
  return (
    <div className="mb-8 flex flex-col items-center text-center md:hidden">
      <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 text-xl font-bold text-white shadow-lg">
        Q
      </div>
      <p className="text-xl font-bold text-gray-900">QWI</p>
      <p className="text-sm text-gray-600">Quality Weekly Intelligence</p>
    </div>
  )
}

export function RegisterPage() {
  const [form, setForm] = useState({
    email: '',
    employee_id: '',
    password: '',
    password_confirm: '',
    name: '',
    role: '',
    sector: 'CSI',
  })
  const [roles, setRoles] = useState<Option[]>([])
  const [sectors, setSectors] = useState<Option[]>([])
  const [errors, setErrors] = useState<Errors>({})
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(false)
  const [optionsLoading, setOptionsLoading] = useState(true)
  const [optionsError, setOptionsError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()
  const { t } = useI18n()

  /** Dica padrão traduzida (ou undefined quando o campo não tem dica). */
  const defaultHint = (field: string): string | undefined => {
    const msg = DEFAULT_HINT_MSGS[field]
    return msg ? t(msg) : undefined
  }

  /** Carrega cargos e setores (mesmo padrão), com "Tentar novamente" em caso de falha. */
  const loadOptions = useCallback(async () => {
    setOptionsLoading(true)
    setOptionsError('')
    try {
      const [rolesRes, sectorsRes] = await Promise.all([
        api.get<{ roles: Option[] }>('/auth/roles'),
        api.get<{ sectors: Option[] }>('/auth/sectors'),
      ])
      setRoles(rolesRes.data.roles)
      setSectors(sectorsRes.data.sectors)
    } catch (err: unknown) {
      setOptionsError(parseApiError(err).message)
    } finally {
      setOptionsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadOptions()
  }, [loadOptions])

  /** Move o foco para o primeiro campo com erro, para o usuário ver onde corrigir. */
  const focusFirstError = (newErrors: Errors) => {
    const first = FIELD_ORDER.find(field => newErrors[field])
    if (first) {
      const el = document.getElementById(first)
      el?.focus()
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  const validateForm = (): boolean => {
    const newErrors: Errors = {}

    if (!form.name.trim()) {
      newErrors.name = { message: t(AUTH.nameRequired), hint: t(AUTH.hintName) }
    } else if (form.name.trim().length < 2) {
      newErrors.name = { message: t(AUTH.nameShort), hint: t(AUTH.hintName) }
    }

    if (!form.email.trim()) {
      newErrors.email = { message: t(AUTH.emailRequired), hint: t(AUTH.hintEmail) }
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      newErrors.email = { message: t(AUTH.emailInvalid), hint: t(AUTH.hintEmail) }
    }

    if (!form.employee_id.trim()) {
      newErrors.employee_id = { message: t(AUTH.employeeIdRequired), hint: t(AUTH.hintEmployeeId) }
    }

    if (!form.password) {
      newErrors.password = { message: t(AUTH.passwordCreate), hint: t(AUTH.hintPassword) }
    } else if (form.password.length < 6) {
      newErrors.password = { message: t(AUTH.passwordShort), hint: t(AUTH.hintPassword) }
    }

    if (!form.password_confirm) {
      newErrors.password_confirm = { message: t(AUTH.confirmRequired), hint: t(AUTH.hintPasswordConfirm) }
    } else if (form.password !== form.password_confirm) {
      newErrors.password_confirm = { message: t(AUTH.passwordMismatch), hint: t(AUTH.hintPasswordConfirm) }
    }

    if (!form.role) {
      newErrors.role = { message: t(AUTH.roleRequired) }
    }

    if (!form.sector) {
      newErrors.sector = { message: t(AUTH.sectorRequired) }
    }

    setErrors(newErrors)
    if (Object.keys(newErrors).length > 0) {
      focusFirstError(newErrors)
      return false
    }
    return true
  }

  /**
   * Traduz a resposta de erro do backend para erros por campo, via parseApiError
   * (contrato único de @/lib/errors — cobre 400 {field,message,hint} e 422 do
   * Pydantic). Mantém o comportamento original: destaca o campo culpado, aplica
   * dica padrão quando o servidor não mandar uma e foca o primeiro erro.
   */
  const applyServerError = (err: unknown) => {
    const parsed = parseApiError(err)

    if (parsed.kind === 'field' && Object.keys(parsed.fields).length > 0) {
      const newErrors: Errors = {}
      for (const [field, info] of Object.entries(parsed.fields)) {
        if (FIELD_ORDER.includes(field)) {
          newErrors[field] = { message: info.message, hint: info.hint ?? defaultHint(field) }
        }
      }
      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors)
        focusFirstError(newErrors)
        return
      }
    }

    setFormError(parsed.message)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!validateForm()) return

    setLoading(true)
    try {
      await register({
        email: form.email.trim(),
        employee_id: form.employee_id.trim(),
        password: form.password,
        password_confirm: form.password_confirm,
        name: form.name.trim(),
        role: form.role,
        sector: form.sector,
      })
      navigate('/')
    } catch (err: unknown) {
      applyServerError(err)
    } finally {
      setLoading(false)
    }
  }

  /** Limpa o erro do campo assim que o usuário começa a corrigi-lo. */
  const clearFieldError = (field: string) => {
    setErrors(prev => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
    if (formError) setFormError('')
  }

  const update = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target
    setForm(prev => ({ ...prev, [field]: value }))
    clearFieldError(field)
  }

  /** Versão para os selects (Radix entrega o valor direto, não um evento). */
  const updateSelect = (field: string) => (value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
    clearFieldError(field)
  }

  const hasError = (field: string) => !!errors[field]

  /** Caixa em vermelho quando o campo está com erro. */
  const fieldClass = (field: string) =>
    hasError(field)
      ? 'border-red-500 bg-red-50 placeholder:text-red-300 focus-visible:ring-red-300 focus:ring-red-300'
      : ''

  /** Mensagem + dica abaixo do campo. */
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

  const errorCount = Object.keys(errors).length
  const selectPh = optionsLoading ? t(COMMON.loading) : t(AUTH.selectPh)

  return (
    <div className="flex min-h-screen bg-white">
      <BrandPanel />

      <main className="relative flex w-full justify-center px-4 sm:px-6 md:w-[55%] md:px-10">
        <div className="absolute right-4 top-4 sm:right-6 md:right-10">
          <LanguageSwitcher variant="compact" />
        </div>

        <div className="my-auto w-full max-w-md py-16 animate-fade-in">
          <MobileBrandHeader />

          <h1 className="mb-8 text-2xl font-bold text-gray-900">{t(AUTH.registerTitle)}</h1>

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {/* Resumo dos erros */}
            {errorCount > 0 && (
              <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3">
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" aria-hidden="true" />
                <p className="min-w-0 text-sm text-red-800">
                  {errorCount === 1 ? t(AUTH.fixOne) : t(AUTH.fixMany, { n: errorCount })}
                </p>
              </div>
            )}

            {/* Erro geral (falha de rede, servidor fora etc.) */}
            {formError && (
              <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3">
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" aria-hidden="true" />
                <p className="min-w-0 text-sm text-red-800">{formError}</p>
              </div>
            )}

            {/* Nome */}
            <div className="space-y-2">
              <Label htmlFor="name" className="text-gray-700">
                {t(AUTH.name)}
              </Label>
              <Input
                id="name"
                autoComplete="name"
                placeholder={t(AUTH.namePh)}
                value={form.name}
                onChange={update('name')}
                disabled={loading}
                aria-invalid={hasError('name')}
                aria-describedby={hasError('name') ? 'name-error' : undefined}
                className={fieldClass('name')}
              />
              <FieldFeedback field="name" />
            </div>

            {/* Email + Matrícula */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="min-w-0 space-y-2">
                <Label htmlFor="email" className="text-gray-700">
                  {t(AUTH.email)}
                </Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder={t(AUTH.emailPh)}
                  value={form.email}
                  onChange={update('email')}
                  disabled={loading}
                  aria-invalid={hasError('email')}
                  aria-describedby={hasError('email') ? 'email-error' : undefined}
                  className={fieldClass('email')}
                />
                <FieldFeedback field="email" />
              </div>

              <div className="min-w-0 space-y-2">
                <Label htmlFor="employee_id" className="text-gray-700">
                  {t(AUTH.employeeId)}
                </Label>
                <Input
                  id="employee_id"
                  placeholder={t(AUTH.employeeIdPh)}
                  value={form.employee_id}
                  onChange={update('employee_id')}
                  disabled={loading}
                  aria-invalid={hasError('employee_id')}
                  aria-describedby={hasError('employee_id') ? 'employee_id-error' : undefined}
                  className={fieldClass('employee_id')}
                />
                <FieldFeedback field="employee_id" />
              </div>
            </div>

            {/* Senha + Confirmação */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="min-w-0 space-y-2">
                <Label htmlFor="password" className="text-gray-700">
                  {t(AUTH.password)}
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="••••••••"
                    value={form.password}
                    onChange={update('password')}
                    disabled={loading}
                    aria-invalid={hasError('password')}
                    aria-describedby={hasError('password') ? 'password-error' : undefined}
                    className={`pr-10 ${fieldClass('password')}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(v => !v)}
                    aria-label={showPassword ? t(AUTH.hidePassword) : t(AUTH.showPassword)}
                    className="absolute inset-y-0 right-0 flex items-center rounded-r-lg px-3 text-gray-400 transition-colors hover:text-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" aria-hidden="true" />
                    ) : (
                      <Eye className="h-4 w-4" aria-hidden="true" />
                    )}
                  </button>
                </div>
                <FieldFeedback field="password" />
              </div>

              <div className="min-w-0 space-y-2">
                <Label htmlFor="password_confirm" className="text-gray-700">
                  {t(AUTH.passwordConfirm)}
                </Label>
                <div className="relative">
                  <Input
                    id="password_confirm"
                    type={showConfirm ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="••••••••"
                    value={form.password_confirm}
                    onChange={update('password_confirm')}
                    disabled={loading}
                    aria-invalid={hasError('password_confirm')}
                    aria-describedby={hasError('password_confirm') ? 'password_confirm-error' : undefined}
                    className={`pr-10 ${fieldClass('password_confirm')}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm(v => !v)}
                    aria-label={showConfirm ? t(AUTH.hidePassword) : t(AUTH.showPassword)}
                    className="absolute inset-y-0 right-0 flex items-center rounded-r-lg px-3 text-gray-400 transition-colors hover:text-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {showConfirm ? (
                      <EyeOff className="h-4 w-4" aria-hidden="true" />
                    ) : (
                      <Eye className="h-4 w-4" aria-hidden="true" />
                    )}
                  </button>
                </div>
                <FieldFeedback field="password_confirm" />
              </div>
            </div>

            {/* Falha ao carregar cargos/setores → aviso com "Tentar novamente" */}
            {optionsError && (
              <div role="alert" className="flex flex-col gap-3 rounded-lg border border-red-200 bg-red-50 p-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex min-w-0 items-start gap-2">
                  <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-600" aria-hidden="true" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-red-800">{t(AUTH.optionsLoadError)}</p>
                    <p className="mt-0.5 text-xs text-red-600">{optionsError}</p>
                  </div>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={() => void loadOptions()} className="shrink-0 self-start">
                  <RefreshCw aria-hidden="true" />
                  {t(COMMON.retry)}
                </Button>
              </div>
            )}

            {/* Cargo + Setor */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="min-w-0 space-y-2">
                <Label htmlFor="role" className="text-gray-700">
                  {t(AUTH.role)}
                </Label>
                <Select value={form.role} onValueChange={updateSelect('role')} disabled={optionsLoading || loading}>
                  <SelectTrigger
                    id="role"
                    aria-invalid={hasError('role')}
                    aria-describedby={hasError('role') ? 'role-error' : undefined}
                    className={fieldClass('role')}
                  >
                    <SelectValue placeholder={selectPh} />
                  </SelectTrigger>
                  <SelectContent>
                    {roles.map(role => (
                      <SelectItem key={role.value} value={role.value}>
                        {role.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldFeedback field="role" />
              </div>

              <div className="min-w-0 space-y-2">
                <Label htmlFor="sector" className="text-gray-700">
                  {t(AUTH.sector)}
                </Label>
                <Select value={form.sector} onValueChange={updateSelect('sector')} disabled={optionsLoading || loading}>
                  <SelectTrigger
                    id="sector"
                    aria-invalid={hasError('sector')}
                    aria-describedby={hasError('sector') ? 'sector-error' : undefined}
                    className={fieldClass('sector')}
                  >
                    <SelectValue placeholder={selectPh} />
                  </SelectTrigger>
                  <SelectContent>
                    {sectors.map(sector => (
                      <SelectItem key={sector.value} value={sector.value}>
                        {sector.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FieldFeedback field="sector" />
              </div>
            </div>

            <Button type="submit" disabled={loading || optionsLoading} className="w-full">
              {loading ? (
                <>
                  <Loader2 className="animate-spin" aria-hidden="true" />
                  {t(AUTH.registering)}
                </>
              ) : (
                t(AUTH.register)
              )}
            </Button>
          </form>

          <p className="mt-8 border-t border-gray-100 pt-6 text-center text-sm text-gray-600">
            {t(AUTH.hasAccount)}{' '}
            <Link to="/login" className="font-medium text-brand transition-colors hover:text-brand-600 hover:underline">
              {t(AUTH.signIn)}
            </Link>
          </p>
        </div>
      </main>
    </div>
  )
}
