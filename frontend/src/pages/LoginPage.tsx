import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertCircle, Eye, EyeOff, Loader2 } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { parseApiError, type FieldErrorInfo } from '@/lib/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher'
import { useI18n } from '@/i18n'
import { AUTH } from '@/i18n/messages/auth'

type Errors = Record<string, FieldErrorInfo>

/** Ordem dos campos — usada para focar o primeiro com erro. */
const FIELD_ORDER = ['email', 'password']

/**
 * O interceptor de src/lib/api.ts recarrega a página em QUALQUER resposta 401
 * (inclusive a do próprio /auth/login). Guardamos o erro de credenciais por
 * alguns segundos no sessionStorage para reexibi-lo após o reload — sem isso a
 * mensagem "Email ou senha incorretos" se perderia. Quando o interceptor for
 * ajustado, este código continua funcionando (apenas deixa de ser necessário).
 */
const LOGIN_401_KEY = 'qwi_login_401'
const LOGIN_401_TTL_MS = 6000

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

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<Errors>({})
  /** true quando o backend respondeu 401 — destaca email E senha. */
  const [invalidCredentials, setInvalidCredentials] = useState(false)
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const { t } = useI18n()

  // Restaura o erro de credenciais que sobreviveu ao reload do interceptor.
  useEffect(() => {
    const raw = sessionStorage.getItem(LOGIN_401_KEY)
    if (!raw) return
    sessionStorage.removeItem(LOGIN_401_KEY)
    try {
      const saved: unknown = JSON.parse(raw)
      if (typeof saved === 'object' && saved !== null) {
        const s = saved as { email?: unknown; t?: unknown }
        if (typeof s.t === 'number' && Date.now() - s.t < LOGIN_401_TTL_MS) {
          if (typeof s.email === 'string') setEmail(s.email)
          setInvalidCredentials(true)
        }
      }
    } catch {
      // valor corrompido — ignora em silêncio (é apenas um auxílio de UX)
    }
  }, [])

  const focusFirstError = (newErrors: Errors) => {
    const first = FIELD_ORDER.find(field => newErrors[field])
    if (first) document.getElementById(first)?.focus()
  }

  const hasError = (field: string) => !!errors[field] || invalidCredentials

  const describedBy = (field: string) => {
    if (errors[field]) return `${field}-error`
    if (invalidCredentials) return 'login-error'
    return undefined
  }

  /** Caixa em vermelho quando o campo está com erro. */
  const fieldClass = (field: string) =>
    hasError(field)
      ? 'border-red-500 bg-red-50 placeholder:text-red-300 focus-visible:ring-red-300'
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

  /** Ao digitar: limpa o erro do campo e o destaque de credenciais/mensagem geral. */
  const clearFeedback = (field: string) => {
    if (invalidCredentials) setInvalidCredentials(false)
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
    setInvalidCredentials(false)
    sessionStorage.removeItem(LOGIN_401_KEY)

    const newErrors: Errors = {}
    if (!email.trim()) {
      newErrors.email = { message: t(AUTH.emailRequired), hint: t(AUTH.hintEmail) }
    }
    if (!password) {
      newErrors.password = { message: t(AUTH.passwordRequired) }
    }
    setErrors(newErrors)
    if (Object.keys(newErrors).length > 0) {
      focusFirstError(newErrors)
      return
    }

    setLoading(true)
    try {
      await login(email.trim(), password)
      navigate('/')
    } catch (err: unknown) {
      const parsed = parseApiError(err)

      if (parsed.status === 401 || parsed.kind === 'auth') {
        // Grava ANTES de renderizar: sobrevive ao reload do interceptor.
        sessionStorage.setItem(
          LOGIN_401_KEY,
          JSON.stringify({ email: email.trim(), t: Date.now() })
        )
        setInvalidCredentials(true)
        document.getElementById('email')?.focus()
      } else if (parsed.kind === 'field' && Object.keys(parsed.fields).length > 0) {
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
    <div className="flex min-h-screen bg-white">
      <BrandPanel />

      <main className="relative flex w-full justify-center px-4 sm:px-6 md:w-[55%] md:px-10">
        <div className="absolute right-4 top-4 sm:right-6 md:right-10">
          <LanguageSwitcher variant="compact" />
        </div>

        <div className="my-auto w-full max-w-md py-16 animate-fade-in">
          <MobileBrandHeader />

          <h1 className="mb-8 text-2xl font-bold text-gray-900">{t(AUTH.signInTitle)}</h1>

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {/* Credenciais incorretas (401) — destaca os dois campos */}
            {invalidCredentials && (
              <div
                id="login-error"
                role="alert"
                className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3"
              >
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-red-800">{t(AUTH.credError)}</p>
                  <p className="mt-0.5 text-xs text-red-600">{t(AUTH.credHint)}</p>
                </div>
              </div>
            )}

            {/* Erro geral (rede, servidor fora etc.) */}
            {!invalidCredentials && formError && (
              <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3">
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" aria-hidden="true" />
                <p className="min-w-0 text-sm text-red-800">{formError}</p>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-gray-700">
                {t(AUTH.email)}
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                autoFocus
                placeholder={t(AUTH.emailPh)}
                value={email}
                onChange={e => {
                  setEmail(e.target.value)
                  clearFeedback('email')
                }}
                disabled={loading}
                aria-invalid={hasError('email')}
                aria-describedby={describedBy('email')}
                className={fieldClass('email')}
              />
              <FieldFeedback field="email" />
            </div>

            <div className="space-y-2">
              <div className="flex items-baseline justify-between gap-2">
                <Label htmlFor="password" className="text-gray-700">
                  {t(AUTH.password)}
                </Label>
                <Link
                  to="/recuperar-senha"
                  className="text-xs font-medium text-brand transition-colors hover:text-brand-600 hover:underline"
                >
                  {t(AUTH.forgotPassword)}
                </Link>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => {
                    setPassword(e.target.value)
                    clearFeedback('password')
                  }}
                  disabled={loading}
                  aria-invalid={hasError('password')}
                  aria-describedby={describedBy('password')}
                  className={`pr-10 ${fieldClass('password')}`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  aria-label={showPassword ? t(AUTH.hidePassword) : t(AUTH.showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-400 transition-colors hover:text-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-r-lg"
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

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? (
                <>
                  <Loader2 className="animate-spin" aria-hidden="true" />
                  {t(AUTH.signingIn)}
                </>
              ) : (
                t(AUTH.signIn)
              )}
            </Button>
          </form>

          <p className="mt-8 border-t border-gray-100 pt-6 text-center text-sm text-gray-600">
            {t(AUTH.noAccount)}{' '}
            <Link to="/register" className="font-medium text-brand transition-colors hover:text-brand-600 hover:underline">
              {t(AUTH.registerTitle)}
            </Link>
          </p>
        </div>
      </main>
    </div>
  )
}
