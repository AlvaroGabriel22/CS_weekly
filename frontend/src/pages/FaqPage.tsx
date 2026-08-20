import { useState } from 'react'
import { AlertCircle, LifeBuoy, Loader2, Mail, Send, Trash2, UserPlus } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { parseApiError, type FieldErrorInfo } from '@/lib/errors'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { FAQ } from '@/i18n/messages/faq'
import { EmptyState, ErrorState } from '@/components/feedback'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { PageContainer } from '@/components/layout/PageContainer'
import { useToast } from '@/components/ui/toast'
import {
  useAddFaqNotifyUser,
  useAnswerFaqReport,
  useCreateFaqReport,
  useFaqNotifyUsers,
  useFaqReports,
  useRemoveFaqNotifyUser,
  type BugReport,
} from '@/hooks/useFaq'

/** FAQ / Suporte: abertura de chamados, lista pública e gestão (root). */
export function FaqPage() {
  const { user } = useAuth()
  const { t } = useI18n()
  const query = useFaqReports()
  const isAdmin = Boolean(user?.is_admin)

  return (
    <PageContainer title={t(FAQ.title)} maxWidth="4xl">
      <div className="space-y-6">
        <ReportForm />

        {isAdmin && <NotifyUsersCard />}

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-900">{t(FAQ.listTitle)}</h2>

          {query.isLoading ? (
            <div className="space-y-3" role="status" aria-label={t(COMMON.loading)}>
              {[0, 1, 2].map((i) => (
                <div key={i} className="rounded-xl border border-border/60 bg-white p-4 shadow-card">
                  <Skeleton className="h-4 w-40 max-w-full" />
                  <Skeleton className="mt-2 h-3 w-full" />
                  <Skeleton className="mt-1.5 h-3 w-2/3" />
                </div>
              ))}
            </div>
          ) : query.isError ? (
            <ErrorState error={query.error} onRetry={() => query.refetch()} />
          ) : (query.data ?? []).length === 0 ? (
            <EmptyState icon={LifeBuoy} title={t(FAQ.empty)} />
          ) : (
            <ul className="space-y-3">
              {(query.data ?? []).map((report, index) => (
                <li
                  key={report.id}
                  className="animate-slide-up"
                  style={{ animationDelay: `${Math.min(index, 8) * 50}ms`, animationFillMode: 'backwards' }}
                >
                  <ReportCard report={report} isAdmin={isAdmin} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </PageContainer>
  )
}

// ── Formulário de abertura ──────────────────────────────────────────────────

function ReportForm() {
  const { t } = useI18n()
  const { toast } = useToast()
  const create = useCreateFaqReport()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [errors, setErrors] = useState<Record<string, FieldErrorInfo>>({})

  const clear = (field: string) =>
    setErrors((prev) => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    create.mutate(
      { title: title.trim(), description: description.trim() },
      {
        onSuccess: () => {
          setTitle('')
          setDescription('')
          setErrors({})
          toast.success(t(FAQ.created))
        },
        onError: (err) => {
          const parsed = parseApiError(err)
          if (parsed.kind === 'field' && Object.keys(parsed.fields).length > 0) {
            setErrors(parsed.fields)
            const first = ['title', 'description'].find((f) => parsed.fields[f])
            if (first) document.getElementById(`faq-${first}`)?.focus()
          } else {
            toast.error(parsed.message)
          }
        },
      }
    )
  }

  const fieldClass = (field: string) =>
    errors[field]
      ? 'border-red-500 bg-red-50 placeholder:text-red-300 focus-visible:ring-red-300'
      : ''

  const Feedback = ({ field }: { field: string }) => {
    const error = errors[field]
    if (!error) return null
    return (
      <div id={`faq-${field}-error`} role="alert" className="space-y-0.5">
        <p className="flex items-center gap-1 text-xs font-medium text-red-600">
          <AlertCircle className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
          {error.message}
        </p>
        {error.hint && <p className="pl-4 text-xs text-red-500">{error.hint}</p>}
      </div>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-border/60 bg-white p-4 shadow-card sm:p-6"
      noValidate
    >
      <h2 className="text-sm font-semibold text-gray-900">{t(FAQ.formTitle)}</h2>

      <div className="space-y-2">
        <Label htmlFor="faq-title" className="text-gray-700">
          {t(FAQ.fieldTitle)}
        </Label>
        <Input
          id="faq-title"
          value={title}
          maxLength={300}
          placeholder={t(FAQ.fieldTitlePh)}
          onChange={(e) => {
            setTitle(e.target.value)
            clear('title')
          }}
          disabled={create.isPending}
          aria-invalid={Boolean(errors.title)}
          aria-describedby={errors.title ? 'faq-title-error' : undefined}
          className={fieldClass('title')}
        />
        <Feedback field="title" />
      </div>

      <div className="space-y-2">
        <Label htmlFor="faq-description" className="text-gray-700">
          {t(FAQ.fieldDescription)}
        </Label>
        <Textarea
          id="faq-description"
          value={description}
          maxLength={4000}
          rows={4}
          placeholder={t(FAQ.fieldDescriptionPh)}
          onChange={(e) => {
            setDescription(e.target.value)
            clear('description')
          }}
          disabled={create.isPending}
          aria-invalid={Boolean(errors.description)}
          aria-describedby={errors.description ? 'faq-description-error' : undefined}
          className={fieldClass('description')}
        />
        <Feedback field="description" />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="min-w-0 text-xs text-gray-500">{t(FAQ.visibilityNote)}</p>
        <Button
          type="submit"
          disabled={create.isPending || !title.trim() || !description.trim()}
          className="shrink-0"
        >
          {create.isPending ? (
            <>
              <Loader2 className="animate-spin" aria-hidden="true" />
              {t(FAQ.submitting)}
            </>
          ) : (
            <>
              <Send aria-hidden="true" />
              {t(FAQ.submit)}
            </>
          )}
        </Button>
      </div>
    </form>
  )
}

// ── Card de solicitação ─────────────────────────────────────────────────────

function ReportCard({ report, isAdmin }: { report: BugReport; isAdmin: boolean }) {
  const { t } = useI18n()
  const closed = report.status === 'closed'
  const showAnswer = isAdmin && !closed

  return (
    <div className="rounded-xl border border-border/60 bg-white p-4 shadow-card sm:p-5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <h3 className="min-w-0 break-words text-sm font-semibold text-gray-900">{report.title}</h3>
        <Badge variant={closed ? 'outline' : 'success'}>
          {closed ? t(FAQ.statusClosed) : t(FAQ.statusOpen)}
        </Badge>
      </div>

      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-gray-600">
        {report.description}
      </p>

      <p className="mt-2 text-xs text-gray-500">
        {report.author_name}
        {report.is_mine && ` · ${t(FAQ.mine)}`}
      </p>

      {report.admin_response && (
        <div className="mt-3 rounded-lg border border-brand-100 bg-brand-50/60 p-3">
          <p className="text-xs font-semibold text-brand-700">{t(FAQ.adminResponse)}</p>
          <p className="mt-1 whitespace-pre-wrap break-words text-sm text-gray-700">
            {report.admin_response}
          </p>
        </div>
      )}

      {showAnswer && <AnswerForm reportId={report.id} />}
    </div>
  )
}

// ── Resposta do admin (inline) ──────────────────────────────────────────────

function AnswerForm({ reportId }: { reportId: string }) {
  const { t } = useI18n()
  const { toast } = useToast()
  const answer = useAnswerFaqReport()
  const [response, setResponse] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    answer.mutate(
      { id: reportId, response: response.trim() || undefined, close: true },
      {
        onSuccess: () => toast.success(t(FAQ.answered)),
        onError: (err) => toast.error(parseApiError(err).message),
      }
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 space-y-2 border-t border-border/60 pt-3">
      <Textarea
        value={response}
        rows={2}
        placeholder={t(FAQ.answerPh)}
        onChange={(e) => setResponse(e.target.value)}
        disabled={answer.isPending}
      />
      <div className="flex justify-end">
        <Button type="submit" size="sm" disabled={answer.isPending}>
          {answer.isPending ? (
            <>
              <Loader2 className="animate-spin" aria-hidden="true" />
              {t(FAQ.answering)}
            </>
          ) : (
            t(FAQ.answerAndClose)
          )}
        </Button>
      </div>
    </form>
  )
}

// ── Gestão de destinatários (root) ──────────────────────────────────────────

function NotifyUsersCard() {
  const { t } = useI18n()
  const { toast } = useToast()
  const query = useFaqNotifyUsers(true)
  const add = useAddFaqNotifyUser()
  const remove = useRemoveFaqNotifyUser()
  const [email, setEmail] = useState('')
  const [fieldError, setFieldError] = useState<FieldErrorInfo | null>(null)

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    setFieldError(null)
    add.mutate(
      { email: email.trim() },
      {
        onSuccess: () => {
          setEmail('')
          toast.success(t(FAQ.notifyAdded))
        },
        onError: (err) => {
          const parsed = parseApiError(err)
          const info = parsed.fields.email
          if (info) setFieldError(info)
          else toast.error(parsed.message)
        },
      }
    )
  }

  const handleRemove = (userId: string) => {
    remove.mutate(userId, {
      onSuccess: () => toast.success(t(FAQ.notifyRemoved)),
      onError: (err) => toast.error(parseApiError(err).message),
    })
  }

  const users = query.data ?? []

  return (
    <section className="space-y-3 rounded-xl border border-border/60 bg-white p-4 shadow-card sm:p-6">
      <div className="flex items-center gap-2">
        <Mail className="h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-gray-900">{t(FAQ.notifyTitle)}</h2>
      </div>

      <form onSubmit={handleAdd} className="flex flex-wrap items-start gap-2" noValidate>
        <div className="min-w-0 flex-1 space-y-1">
          <Input
            type="email"
            autoComplete="email"
            value={email}
            placeholder={t(FAQ.notifyEmailPh)}
            onChange={(e) => {
              setEmail(e.target.value)
              setFieldError(null)
            }}
            disabled={add.isPending}
            aria-invalid={Boolean(fieldError)}
            aria-describedby={fieldError ? 'faq-notify-error' : undefined}
            className={fieldError ? 'border-red-500 bg-red-50 focus-visible:ring-red-300' : ''}
          />
          {fieldError && (
            <div id="faq-notify-error" role="alert" className="space-y-0.5">
              <p className="flex items-center gap-1 text-xs font-medium text-red-600">
                <AlertCircle className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                {fieldError.message}
              </p>
              {fieldError.hint && <p className="pl-4 text-xs text-red-500">{fieldError.hint}</p>}
            </div>
          )}
        </div>
        <Button type="submit" disabled={add.isPending || !email.trim()} className="shrink-0">
          {add.isPending ? (
            <Loader2 className="animate-spin" aria-hidden="true" />
          ) : (
            <UserPlus aria-hidden="true" />
          )}
          {t(COMMON.add)}
        </Button>
      </form>

      {query.isLoading ? (
        <div className="space-y-2" role="status" aria-label={t(COMMON.loading)}>
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : users.length === 0 ? (
        <p className="text-sm text-gray-500">{t(FAQ.notifyEmpty)}</p>
      ) : (
        <ul className="divide-y divide-border/60">
          {users.map((u) => (
            <li key={u.id} className="flex items-center gap-3 py-2">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-gray-900">
                  {u.name} · {u.employee_id}
                </p>
                <p className="truncate text-xs text-gray-500">{u.email}</p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`${t(FAQ.remove)} · ${u.name}`}
                disabled={remove.isPending}
                onClick={() => handleRemove(u.user_id)}
                className="shrink-0 text-red-600 hover:bg-red-50 hover:text-red-600"
              >
                <Trash2 aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
