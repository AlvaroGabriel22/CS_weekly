/**
 * Diálogo de envio do weekly por e-mail, em 2 passos:
 *  1. Destinatários — a lista pré-cadastrada em Configurações aparece para
 *     confirmação e é editável ali mesmo (marcar/desmarcar, adicionar, remover).
 *  2. Mensagem — título + corpo, com sugestão opcional da IA em pt/en/ko.
 * O .pptx do weekly vai anexado pelo backend.
 */
import { useEffect, useRef, useState } from 'react'
import { Loader2, Mail, Plus, Send, Sparkles, Trash2 } from 'lucide-react'
import { parseApiError } from '@/lib/errors'
import { useI18n } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { REPORTS } from '@/i18n/messages/reports'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/components/ui/toast'
import {
  useAddEmailRecipient,
  useEmailRecipients,
  useEmailSuggestion,
  useRemoveEmailRecipient,
  useSendWeeklyEmail,
} from '@/hooks/useSharing'
import type { WeeklyReport } from '@/types'

const SUGGEST_LANGS = [
  { code: 'pt', label: 'PT' },
  { code: 'en', label: 'EN' },
  { code: 'ko', label: 'KO' },
] as const

export interface SendEmailDialogProps {
  report: WeeklyReport
  open: boolean
  onClose: () => void
}

export function SendEmailDialog({ report, open, onClose }: SendEmailDialogProps) {
  const { t } = useI18n()
  const { toast } = useToast()

  const recipientsQuery = useEmailRecipients()
  const addRecipient = useAddEmailRecipient()
  const removeRecipient = useRemoveEmailRecipient()
  const sendEmail = useSendWeeklyEmail()
  const suggestion = useEmailSuggestion()

  const [step, setStep] = useState<0 | 1>(0)
  const [checked, setChecked] = useState<Record<string, boolean>>({})
  const [newEmail, setNewEmail] = useState('')
  const [newName, setNewName] = useState('')
  const [addError, setAddError] = useState<{ message: string; hint?: string } | null>(null)
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [subjectError, setSubjectError] = useState('')
  const [suggestLang, setSuggestLang] = useState<'pt' | 'en' | 'ko'>('pt')
  const emailInputRef = useRef<HTMLInputElement>(null)

  const recipients = recipientsQuery.data ?? []

  // Reabre limpo e com todos os salvos marcados por padrão.
  useEffect(() => {
    if (!open) return
    setStep(0)
    setNewEmail('')
    setNewName('')
    setAddError(null)
    setSubject('')
    setBody('')
    setSubjectError('')
  }, [open])

  useEffect(() => {
    setChecked(prev => {
      const next: Record<string, boolean> = {}
      for (const r of recipients) next[r.id] = prev[r.id] ?? true
      return next
    })
  }, [recipients])

  const selected = recipients.filter(r => checked[r.id])

  const handleAdd = async () => {
    const email = newEmail.trim()
    if (!email) return
    setAddError(null)
    try {
      const list = await addRecipient.mutateAsync({ email, name: newName.trim() || undefined })
      setNewEmail('')
      setNewName('')
      const created = list.find(r => r.email.toLowerCase() === email.toLowerCase())
      if (created) setChecked(prev => ({ ...prev, [created.id]: true }))
      emailInputRef.current?.focus()
    } catch (err) {
      const parsed = parseApiError(err)
      const field = parsed.fields.email ?? { message: parsed.message }
      setAddError(field)
    }
  }

  const handleRemove = async (recipientId: string) => {
    try {
      await removeRecipient.mutateAsync({ recipientId })
    } catch (err) {
      toast.error(parseApiError(err).message)
    }
  }

  const handleSuggest = async () => {
    try {
      const result = await suggestion.mutateAsync({ reportId: report.id, language: suggestLang })
      setSubject(result.subject)
      setBody(result.body)
      setSubjectError('')
    } catch (err) {
      toast.error(parseApiError(err).message)
    }
  }

  const handleSend = async () => {
    if (!subject.trim()) {
      setSubjectError(t(REPORTS.emailNeedSubject))
      return
    }
    try {
      const result = await sendEmail.mutateAsync({
        reportId: report.id,
        recipients: selected.map(r => r.email),
        subject: subject.trim(),
        body: body.trim(),
      })
      toast.success(t(REPORTS.emailSent, { n: result.recipients }))
      onClose()
    } catch (err) {
      toast.error(parseApiError(err).message)
    }
  }

  return (
    <Dialog open={open} onOpenChange={value => !value && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-brand" aria-hidden="true" />
            {t(REPORTS.emailDialogTitle)} · W{report.week_number}/{report.year}
          </DialogTitle>
          <DialogDescription>
            {step === 0 ? t(REPORTS.emailRecipientsHint) : t(REPORTS.emailSuggestHint)}
          </DialogDescription>
        </DialogHeader>

        {step === 0 ? (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-900">{t(REPORTS.emailRecipientsStep)}</h3>

            {recipientsQuery.isLoading ? (
              <div className="flex justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-brand" aria-hidden="true" />
              </div>
            ) : recipients.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border bg-gray-50/60 p-4 text-center">
                <p className="text-sm font-medium text-gray-700">{t(REPORTS.emailNoRecipients)}</p>
                <p className="mt-1 text-xs text-gray-500">{t(REPORTS.emailNoRecipientsHint)}</p>
              </div>
            ) : (
              <ul className="max-h-56 space-y-1.5 overflow-y-auto pr-1">
                {recipients.map(r => (
                  <li
                    key={r.id}
                    className="flex items-center gap-3 rounded-lg border border-border/60 bg-white px-3 py-2 transition-colors hover:border-brand/40"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 shrink-0 accent-blue-600"
                      checked={checked[r.id] ?? false}
                      onChange={e => setChecked(prev => ({ ...prev, [r.id]: e.target.checked }))}
                      aria-label={r.email}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-gray-900">{r.email}</p>
                      {r.name && <p className="truncate text-xs text-gray-500">{r.name}</p>}
                    </div>
                    <button
                      type="button"
                      className="shrink-0 rounded-md p-1.5 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-600"
                      onClick={() => handleRemove(r.id)}
                      disabled={removeRecipient.isPending}
                      aria-label={`${t(REPORTS.emailRemoveFromList)} · ${r.email}`}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {/* Adicionar direto daqui — a lista salva em Configurações é atualizada */}
            <div className="space-y-2 rounded-lg border border-border/60 bg-gray-50/60 p-3">
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  ref={emailInputRef}
                  type="email"
                  value={newEmail}
                  onChange={e => {
                    setNewEmail(e.target.value)
                    setAddError(null)
                  }}
                  onKeyDown={e => e.key === 'Enter' && handleAdd()}
                  placeholder={t(REPORTS.emailAddPlaceholder)}
                  className={addError ? 'border-red-400 focus-visible:ring-red-400' : ''}
                  aria-invalid={Boolean(addError)}
                />
                <Input
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleAdd()}
                  placeholder={t(REPORTS.emailNamePlaceholder)}
                  className="sm:max-w-[160px]"
                />
                <Button
                  variant="outline"
                  onClick={handleAdd}
                  disabled={!newEmail.trim() || addRecipient.isPending}
                >
                  {addRecipient.isPending ? (
                    <Loader2 className="animate-spin" aria-hidden="true" />
                  ) : (
                    <Plus aria-hidden="true" />
                  )}
                  {t(COMMON.add)}
                </Button>
              </div>
              {addError && (
                <p className="text-xs font-medium text-red-600" role="alert">
                  {addError.message}
                  {addError.hint && <span className="font-normal text-red-500"> {addError.hint}</span>}
                </p>
              )}
            </div>

            <div className="flex items-center justify-between gap-2 pt-1">
              <span className="text-xs text-gray-500">
                {t(REPORTS.emailRecipientsCount, { n: selected.length })}
              </span>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={onClose}>
                  {t(COMMON.cancel)}
                </Button>
                <Button
                  disabled={selected.length === 0}
                  title={selected.length === 0 ? t(REPORTS.emailNeedRecipient) : undefined}
                  onClick={() => setStep(1)}
                >
                  {t(COMMON.next)}
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-900">{t(REPORTS.emailWriteStep)}</h3>

            {/* Sugestão da IA — opcional, com escolha de idioma */}
            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-brand/20 bg-brand/[0.04] p-3">
              <Sparkles className="h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
              <div className="flex overflow-hidden rounded-md border border-border bg-white" role="group" aria-label={t(REPORTS.language)}>
                {SUGGEST_LANGS.map(lang => (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => setSuggestLang(lang.code)}
                    className={`px-2.5 py-1 text-xs font-semibold transition-colors ${
                      suggestLang === lang.code
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>
              <Button
                variant="outline"
                size="sm"
                className="ml-auto"
                disabled={suggestion.isPending}
                onClick={handleSuggest}
              >
                {suggestion.isPending ? (
                  <>
                    <Loader2 className="animate-spin" aria-hidden="true" />
                    {t(REPORTS.emailSuggesting)}
                  </>
                ) : (
                  <>
                    <Sparkles aria-hidden="true" />
                    {t(REPORTS.emailSuggest)}
                  </>
                )}
              </Button>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="email-subject" className="text-sm font-medium text-gray-700">
                {t(REPORTS.emailSubject)}
              </label>
              <Input
                id="email-subject"
                value={subject}
                onChange={e => {
                  setSubject(e.target.value)
                  setSubjectError('')
                }}
                maxLength={200}
                className={subjectError ? 'border-red-400 focus-visible:ring-red-400' : ''}
                aria-invalid={Boolean(subjectError)}
              />
              {subjectError && (
                <p className="text-xs font-medium text-red-600" role="alert">
                  {subjectError}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="email-body" className="text-sm font-medium text-gray-700">
                {t(REPORTS.emailBody)}
              </label>
              <Textarea
                id="email-body"
                value={body}
                onChange={e => setBody(e.target.value)}
                rows={6}
                maxLength={4000}
              />
            </div>

            <p className="text-xs text-gray-500">
              {t(REPORTS.emailAttachmentNote)} · {t(REPORTS.emailRecipientsCount, { n: selected.length })}
            </p>

            <div className="flex justify-between gap-2 pt-1">
              <Button variant="ghost" onClick={() => setStep(0)} disabled={sendEmail.isPending}>
                {t(COMMON.back)}
              </Button>
              <Button disabled={sendEmail.isPending} onClick={handleSend}>
                {sendEmail.isPending ? (
                  <>
                    <Loader2 className="animate-spin" aria-hidden="true" />
                    {t(REPORTS.emailSending)}
                  </>
                ) : (
                  <>
                    <Send aria-hidden="true" />
                    {t(REPORTS.emailSend)}
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
