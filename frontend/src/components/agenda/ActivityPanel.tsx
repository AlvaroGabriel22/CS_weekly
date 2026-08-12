/**
 * Painel do DIA da Agenda: lista as atividades do dia selecionado, permite
 * criar (formulário inline, otimista), editar, excluir e alternar
 * "incluir no weekly". Erros SEMPRE via parseApiError; textos via useI18n.
 *
 * Layout: o painel ocupa o espaço restante do flex pai (min-w-0, sem larguras
 * fixas) — botões sempre DENTRO do card, nada corta no viewport.
 */
import { useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import {
  CalendarPlus,
  FileSpreadsheet,
  Image as ImageIcon,
  Loader2,
  MoreVertical,
  Paperclip,
  Pencil,
  Plus,
  Trash2,
  X,
} from 'lucide-react'
import type { Activity, Attachment } from '@/types'
import { formatDateIso, getWeekRef, parseIsoDate, weekLabel } from '@/lib/dates'
import { parseApiError, type NormalizedError } from '@/lib/errors'
import {
  isOptimisticActivity,
  useCreateActivity,
  useDeleteActivity,
  useDeleteAttachment,
  useUpdateActivity,
  useUploadAttachment,
  type MonthRef,
} from '@/hooks/useActivities'
import { useAttachmentImage } from '@/hooks/useSlideEditor'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { EmptyState } from '@/components/feedback'
import { useToast } from '@/components/ui/toast'
import { useI18n, type Msg } from '@/i18n'
import { COMMON } from '@/i18n/messages/common'
import { AGENDA } from '@/i18n/messages/agenda'

export interface ActivityPanelProps {
  date: Date
  monthRef: MonthRef
  activities: Activity[]
  onClose: () => void
}

type BadgeVariant = 'default' | 'success' | 'warning' | 'info' | 'outline'

const STATUS_META: Record<string, { msg: Msg; variant: BadgeVariant }> = {
  draft: { msg: AGENDA.statusDraft, variant: 'outline' },
  pending: { msg: AGENDA.statusPending, variant: 'warning' },
  in_progress: { msg: AGENDA.statusInProgress, variant: 'info' },
  completed: { msg: AGENDA.statusDone, variant: 'success' },
  done: { msg: AGENDA.statusDone, variant: 'success' },
}

/** "Segunda-feira, 10 de agosto de 2026" no locale ativo. */
function longDate(date: Date, locale: string): string {
  const text = date.toLocaleDateString(locale, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
  return text.charAt(0).toUpperCase() + text.slice(1)
}

const fieldErrorClass = 'border-red-500 bg-red-50 focus-visible:ring-red-500'

/* ── Anexos: validação client-side (espelha o backend) ─────────────────── */

const ATTACH_ACCEPT = '.xlsx,.xls,.csv,.jpg,.jpeg,.png'
const ALLOWED_EXTENSIONS = ['xlsx', 'xls', 'csv', 'jpg', 'jpeg', 'png']
const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png']
const MAX_FILE_BYTES = 15 * 1024 * 1024

type Translator = (msg: Msg, vars?: Record<string, string | number>) => string

function fileExt(name: string): string {
  return name.slice(name.lastIndexOf('.') + 1).toLowerCase()
}

function isImageName(name: string): boolean {
  return IMAGE_EXTENSIONS.includes(fileExt(name))
}

function isImageAttachment(att: Attachment): boolean {
  return att.mime_type?.startsWith('image/') || isImageName(att.original_filename)
}

/** null = arquivo OK; string = mensagem de erro localizada. */
function fileProblem(file: File, t: Translator): string | null {
  if (!ALLOWED_EXTENSIONS.includes(fileExt(file.name))) {
    return t(AGENDA.fileInvalid, { name: file.name })
  }
  if (file.size > MAX_FILE_BYTES) {
    return t(AGENDA.fileTooLarge, { name: file.name })
  }
  return null
}

interface PendingFile {
  id: number
  file: File
}

let pendingFileSeq = 0

/** Chip de um anexo JÁ salvo (miniatura p/ imagem, exclusão em 2 passos). */
function AttachmentChip({
  attachment,
  onDelete,
  disabled,
}: {
  attachment: Attachment
  onDelete: () => void
  disabled?: boolean
}) {
  const { t } = useI18n()
  const isImage = isImageAttachment(attachment)
  const imgUrl = useAttachmentImage(isImage ? attachment.id : undefined)
  const [confirming, setConfirming] = useState(false)
  const table = attachment.kpi_data?.table

  return (
    <span className="inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-md border border-gray-200 bg-gray-50 py-0.5 pl-1.5 pr-0.5 text-xs text-gray-700">
      {isImage ? (
        imgUrl ? (
          <img
            src={imgUrl}
            alt={attachment.original_filename}
            className="h-6 w-6 shrink-0 rounded object-cover"
          />
        ) : imgUrl === '' ? (
          <ImageIcon className="h-3.5 w-3.5 shrink-0 text-gray-400" aria-hidden="true" />
        ) : (
          <span className="h-6 w-6 shrink-0 animate-pulse rounded bg-gray-200" aria-hidden="true" />
        )
      ) : (
        <FileSpreadsheet className="h-3.5 w-3.5 shrink-0 text-brand" aria-hidden="true" />
      )}
      <span className="max-w-[120px] truncate">{attachment.original_filename}</span>
      {table && (
        <span className="shrink-0 text-[10px] text-gray-500">
          {t(AGENDA.rowsCount, { n: table.n_rows })}
        </span>
      )}
      {confirming ? (
        <span className="flex shrink-0 items-center">
          <button
            type="button"
            onClick={() => {
              setConfirming(false)
              onDelete()
            }}
            aria-label={t(AGENDA.confirmDeleteAttachment)}
            className="flex h-7 w-7 items-center justify-center rounded text-red-600 transition-colors hover:bg-red-50"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            aria-label={t(COMMON.cancel)}
            className="flex h-7 w-7 items-center justify-center rounded text-gray-400 transition-colors hover:bg-gray-100"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </span>
      ) : (
        <button
          type="button"
          disabled={disabled}
          onClick={() => setConfirming(true)}
          aria-label={t(AGENDA.deleteAttachment, { name: attachment.original_filename })}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-gray-400 transition-colors hover:bg-gray-100 hover:text-red-600 disabled:opacity-50"
        >
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      )}
    </span>
  )
}

function FieldMessage({ id, error }: { id: string; error?: { message: string; hint?: string } }) {
  if (!error) return null
  return (
    <p id={id} role="alert" className="mt-1.5 text-xs text-red-600">
      {error.message}
      {error.hint && <span className="block text-red-500">{error.hint}</span>}
    </p>
  )
}

/** Formulário inline de NOVA atividade do dia. */
function NewActivityForm({
  date,
  monthRef,
  titleRef,
}: {
  date: Date
  monthRef: MonthRef
  titleRef: React.RefObject<HTMLInputElement>
}) {
  const { t } = useI18n()
  const { toast } = useToast()
  const create = useCreateActivity(monthRef)
  const upload = useUploadAttachment(monthRef)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [errors, setErrors] = useState<NormalizedError['fields']>({})
  const [files, setFiles] = useState<PendingFile[]>([])
  const [fileError, setFileError] = useState<string | null>(null)
  const [uploadingId, setUploadingId] = useState<number | null>(null)
  /** Atividade já criada cujos anexos falharam (habilita "Tentar novamente"). */
  const [retryActivityId, setRetryActivityId] = useState<string | null>(null)
  const descriptionRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const busy = create.isPending || uploadingId !== null

  const handlePickFiles = (e: ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? [])
    e.target.value = ''
    const problems: string[] = []
    const valid: PendingFile[] = []
    for (const file of picked) {
      const problem = fileProblem(file, t)
      if (problem) problems.push(problem)
      else valid.push({ id: ++pendingFileSeq, file })
    }
    if (valid.length > 0) setFiles(prev => [...prev, ...valid])
    setFileError(problems.length > 0 ? problems.join(' ') : null)
  }

  const removePending = (id: number) => {
    const next = files.filter(f => f.id !== id)
    setFiles(next)
    if (next.length === 0) setRetryActivityId(null)
  }

  /** Envia a fila em sequência; mantém na lista os que falharem. */
  const uploadFiles = async (activityId: string, queue: PendingFile[]) => {
    let lastError: unknown = null
    for (const pending of queue) {
      setUploadingId(pending.id)
      try {
        await upload.mutateAsync({ activityId, file: pending.file })
        setFiles(prev => prev.filter(f => f.id !== pending.id))
      } catch (err) {
        lastError = err
      }
    }
    setUploadingId(null)
    if (lastError !== null) {
      setRetryActivityId(activityId)
      toast.error(parseApiError(lastError).message)
    } else {
      setRetryActivityId(null)
      titleRef.current?.focus()
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (busy) return
    // Reenvio de anexos que falharam (atividade já existe).
    if (retryActivityId && files.length > 0) {
      void uploadFiles(retryActivityId, files)
      return
    }
    const trimmed = title.trim()
    if (!trimmed) {
      setErrors({ title: { message: t(AGENDA.titleRequired) } })
      titleRef.current?.focus()
      return
    }
    setErrors({})
    create.mutate(
      {
        title: trimmed,
        description: description.trim() || null,
        activity_date: formatDateIso(date),
      },
      {
        onSuccess: created => {
          const queue = files
          setTitle('')
          setDescription('')
          toast.success(t(AGENDA.added))
          if (queue.length > 0) void uploadFiles(created.id, queue)
          else titleRef.current?.focus()
        },
        onError: err => {
          const parsed = parseApiError(err)
          if (parsed.kind === 'field') {
            setErrors(parsed.fields)
            if (parsed.fields.title) titleRef.current?.focus()
            else if (parsed.fields.description) descriptionRef.current?.focus()
          } else {
            toast.error(parsed.message)
          }
        },
      }
    )
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="rounded-lg border border-gray-200 bg-gray-50/60 p-4">
      <p className="mb-2.5 text-sm font-medium text-gray-900">{t(AGENDA.newActivity)}</p>
      <div className="space-y-2.5">
        <div>
          <Label htmlFor="nova-atividade-titulo" className="sr-only">
            {t(AGENDA.titleLabel)}
          </Label>
          <Input
            id="nova-atividade-titulo"
            ref={titleRef}
            value={title}
            onChange={e => {
              setTitle(e.target.value)
              if (errors.title) setErrors(({ title: _removed, ...rest }) => rest)
            }}
            placeholder={t(AGENDA.titleLabel)}
            aria-invalid={Boolean(errors.title)}
            aria-describedby={errors.title ? 'nova-atividade-titulo-erro' : undefined}
            className={cn('bg-white', errors.title && fieldErrorClass)}
          />
          <FieldMessage id="nova-atividade-titulo-erro" error={errors.title} />
        </div>
        <div>
          <Label htmlFor="nova-atividade-descricao" className="sr-only">
            {t(AGENDA.detailsLabel)}
          </Label>
          <Textarea
            id="nova-atividade-descricao"
            ref={descriptionRef}
            value={description}
            onChange={e => {
              setDescription(e.target.value)
              if (errors.description) setErrors(({ description: _removed, ...rest }) => rest)
            }}
            placeholder={t(AGENDA.detailsPlaceholder)}
            rows={2}
            aria-invalid={Boolean(errors.description)}
            aria-describedby={errors.description ? 'nova-atividade-descricao-erro' : undefined}
            className={cn('min-h-[56px] bg-white', errors.description && fieldErrorClass)}
          />
          <FieldMessage id="nova-atividade-descricao-erro" error={errors.description} />
        </div>

        {files.length > 0 && (
          <div className="flex min-w-0 flex-wrap gap-1.5">
            {files.map(pending => (
              <span
                key={pending.id}
                className="inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-md border border-gray-200 bg-white py-0.5 pl-1.5 pr-0.5 text-xs text-gray-700"
              >
                {uploadingId === pending.id ? (
                  <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-brand" aria-hidden="true" />
                ) : isImageName(pending.file.name) ? (
                  <ImageIcon className="h-3.5 w-3.5 shrink-0 text-gray-500" aria-hidden="true" />
                ) : (
                  <FileSpreadsheet className="h-3.5 w-3.5 shrink-0 text-brand" aria-hidden="true" />
                )}
                <span className="max-w-[140px] truncate">{pending.file.name}</span>
                <button
                  type="button"
                  onClick={() => removePending(pending.id)}
                  disabled={uploadingId !== null}
                  aria-label={t(AGENDA.removeFile, { name: pending.file.name })}
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-gray-400 transition-colors hover:bg-gray-100 hover:text-red-600 disabled:opacity-50"
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </span>
            ))}
          </div>
        )}
        {fileError && (
          <p role="alert" className="text-xs text-red-600">
            {fileError}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ATTACH_ACCEPT}
            className="hidden"
            onChange={handlePickFiles}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={busy}
            onClick={() => fileInputRef.current?.click()}
            className="min-h-10 bg-white"
          >
            <Paperclip aria-hidden="true" />
            {t(AGENDA.attach)}
          </Button>
          <Button type="submit" size="sm" disabled={busy} className="min-h-10 px-4">
            {uploadingId !== null ? (
              <Loader2 className="animate-spin" aria-hidden="true" />
            ) : (
              <Plus aria-hidden="true" />
            )}
            {uploadingId !== null
              ? t(AGENDA.uploading)
              : retryActivityId
                ? t(COMMON.retry)
                : create.isPending
                  ? t(AGENDA.adding)
                  : t(COMMON.add)}
          </Button>
        </div>
      </div>
    </form>
  )
}

/** Diálogo de edição de uma atividade. */
function EditActivityDialog({
  activity,
  monthRef,
  onClose,
}: {
  activity: Activity
  monthRef: MonthRef
  onClose: () => void
}) {
  const { t, locale } = useI18n()
  const { toast } = useToast()
  const update = useUpdateActivity(monthRef)
  const [title, setTitle] = useState(activity.title)
  const [description, setDescription] = useState(activity.description ?? '')
  const [errors, setErrors] = useState<NormalizedError['fields']>({})
  const titleRef = useRef<HTMLInputElement>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = title.trim()
    if (!trimmed) {
      setErrors({ title: { message: t(AGENDA.titleRequired) } })
      titleRef.current?.focus()
      return
    }
    setErrors({})
    update.mutate(
      { id: activity.id, title: trimmed, description: description.trim() || null },
      {
        onSuccess: () => {
          toast.success(t(AGENDA.saved))
          onClose()
        },
        onError: err => {
          const parsed = parseApiError(err)
          if (parsed.kind === 'field') {
            setErrors(parsed.fields)
            if (parsed.fields.title) titleRef.current?.focus()
          } else {
            toast.error(parsed.message)
          }
        },
      }
    )
  }

  return (
    <Dialog open onOpenChange={open => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t(AGENDA.editActivity)}</DialogTitle>
          <DialogDescription>{longDate(parseIsoDate(activity.activity_date), locale)}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <Label htmlFor="editar-titulo">{t(AGENDA.titleLabel)}</Label>
            <Input
              id="editar-titulo"
              ref={titleRef}
              value={title}
              onChange={e => {
                setTitle(e.target.value)
                if (errors.title) setErrors(({ title: _removed, ...rest }) => rest)
              }}
              aria-invalid={Boolean(errors.title)}
              aria-describedby={errors.title ? 'editar-titulo-erro' : undefined}
              className={cn('mt-1.5', errors.title && fieldErrorClass)}
            />
            <FieldMessage id="editar-titulo-erro" error={errors.title} />
          </div>
          <div>
            <Label htmlFor="editar-descricao">{t(AGENDA.detailsLabel)}</Label>
            <Textarea
              id="editar-descricao"
              value={description}
              onChange={e => {
                setDescription(e.target.value)
                if (errors.description) setErrors(({ description: _removed, ...rest }) => rest)
              }}
              rows={4}
              aria-invalid={Boolean(errors.description)}
              aria-describedby={errors.description ? 'editar-descricao-erro' : undefined}
              className={cn('mt-1.5', errors.description && fieldErrorClass)}
            />
            <FieldMessage id="editar-descricao-erro" error={errors.description} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              {t(COMMON.cancel)}
            </Button>
            <Button type="submit" disabled={update.isPending}>
              {update.isPending ? t(AGENDA.saving) : t(COMMON.save)}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function ActivityCard({
  activity,
  monthRef,
  onEdit,
  onDelete,
}: {
  activity: Activity
  monthRef: MonthRef
  onEdit: () => void
  onDelete: () => void
}) {
  const { t } = useI18n()
  const { toast } = useToast()
  const update = useUpdateActivity(monthRef)
  const upload = useUploadAttachment(monthRef)
  const removeAttachment = useDeleteAttachment(monthRef)
  const [uploadingCount, setUploadingCount] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const optimistic = isOptimisticActivity(activity)
  const status = STATUS_META[activity.status]
  const switchId = `weekly-${activity.id}`
  const attachments = activity.attachments ?? []

  const toggleWeekly = (checked: boolean) => {
    update.mutate(
      { id: activity.id, include_in_weekly: checked },
      { onError: err => toast.error(parseApiError(err).message) }
    )
  }

  const handlePickFiles = async (e: ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? [])
    e.target.value = ''
    const valid: File[] = []
    for (const file of picked) {
      const problem = fileProblem(file, t)
      if (problem) toast.error(problem)
      else valid.push(file)
    }
    if (valid.length === 0) return
    setUploadingCount(valid.length)
    let ok = 0
    for (const file of valid) {
      try {
        await upload.mutateAsync({ activityId: activity.id, file })
        ok += 1
      } catch (err) {
        toast.error(parseApiError(err).message)
      }
      setUploadingCount(count => Math.max(0, count - 1))
    }
    if (ok > 0) toast.success(t(AGENDA.attached))
  }

  const deleteAttachment = (attachmentId: string) => {
    removeAttachment.mutate(
      { activityId: activity.id, attachmentId },
      {
        onSuccess: () => toast.success(t(AGENDA.attachmentDeleted)),
        onError: err => toast.error(parseApiError(err).message),
      }
    )
  }

  return (
    <article
      className={cn(
        'min-w-0 rounded-lg border border-gray-200 bg-white p-4 shadow-card transition-opacity animate-fade-in',
        optimistic && 'opacity-60'
      )}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h4 className="break-words text-sm font-semibold text-gray-900">{activity.title}</h4>
          {activity.description && (
            <p className="mt-0.5 line-clamp-2 break-words text-sm text-gray-600">{activity.description}</p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <Badge variant={status?.variant ?? 'outline'}>
              {status ? t(status.msg) : activity.status}
            </Badge>
            {activity.category && <Badge variant="outline">{activity.category}</Badge>}
          </div>
          <div className="mt-2 flex min-w-0 flex-wrap items-center gap-1.5">
            {attachments.map(att => (
              <AttachmentChip
                key={att.id}
                attachment={att}
                disabled={removeAttachment.isPending}
                onDelete={() => deleteAttachment(att.id)}
              />
            ))}
            {uploadingCount > 0 && (
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-brand" aria-hidden="true" />
            )}
            <button
              type="button"
              disabled={optimistic || uploadingCount > 0}
              onClick={() => fileInputRef.current?.click()}
              aria-label={t(AGENDA.attach)}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-dashed border-gray-300 text-gray-400 transition-colors hover:border-brand hover:text-brand disabled:opacity-50"
            >
              <Paperclip className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ATTACH_ACCEPT}
              className="hidden"
              onChange={handlePickFiles}
            />
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-10 w-10 shrink-0 text-gray-400 hover:text-gray-700"
              aria-label={t(AGENDA.activityOptions, { title: activity.title })}
              disabled={optimistic}
            >
              <MoreVertical aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={onEdit}>
              <Pencil aria-hidden="true" />
              {t(COMMON.edit)}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={onDelete} className="text-red-600 focus:bg-red-50 focus:text-red-700 data-[highlighted]:bg-red-50 data-[highlighted]:text-red-700">
              <Trash2 aria-hidden="true" />
              {t(COMMON.delete)}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2 border-t border-gray-100 pt-2.5">
        <Label htmlFor={switchId} className="min-w-0 cursor-pointer text-xs font-medium text-gray-600">
          {t(AGENDA.includeInWeekly)}
        </Label>
        <Switch
          id={switchId}
          checked={activity.include_in_weekly}
          onCheckedChange={toggleWeekly}
          disabled={optimistic}
          aria-label={t(AGENDA.includeInWeekly)}
        />
      </div>
    </article>
  )
}

export function ActivityPanel({ date, monthRef, activities, onClose }: ActivityPanelProps) {
  const { t, locale } = useI18n()
  const { toast } = useToast()
  const deleteActivity = useDeleteActivity(monthRef)
  const [editing, setEditing] = useState<Activity | null>(null)
  const [deleting, setDeleting] = useState<Activity | null>(null)
  const newTitleRef = useRef<HTMLInputElement>(null)
  const weekRef = getWeekRef(date)
  const dateLabel = longDate(date, locale)

  const confirmDelete = () => {
    if (!deleting) return
    const target = deleting
    setDeleting(null)
    deleteActivity.mutate(target.id, {
      onSuccess: () => toast.success(t(AGENDA.deleted)),
      onError: err => toast.error(parseApiError(err).message),
    })
  }

  return (
    <section
      aria-label={t(AGENDA.dayActivities, { date: dateLabel })}
      className="flex h-full min-w-0 flex-col rounded-xl border border-gray-200 bg-white shadow-card"
    >
      {/* Cabeçalho do dia */}
      <header className="flex items-start justify-between gap-3 border-b border-gray-100 px-4 py-3.5 sm:px-5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="break-words text-base font-semibold text-gray-900">{dateLabel}</h3>
            <Badge>{weekLabel(weekRef)}</Badge>
          </div>
          {activities.length > 0 && (
            <p className="mt-0.5 text-xs text-gray-500">
              {activities.length === 1
                ? t(AGENDA.oneActivity)
                : t(AGENDA.manyActivities, { n: activities.length })}
            </p>
          )}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-10 w-10 shrink-0 text-gray-400 hover:text-gray-700"
          aria-label={t(COMMON.close)}
          onClick={onClose}
        >
          <X aria-hidden="true" />
        </Button>
      </header>

      <div className="min-w-0 flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-5">
        <NewActivityForm date={date} monthRef={monthRef} titleRef={newTitleRef} />

        {activities.length === 0 ? (
          <EmptyState
            icon={CalendarPlus}
            title={t(AGENDA.emptyDay)}
            action={
              <Button type="button" variant="outline" size="sm" onClick={() => newTitleRef.current?.focus()}>
                <Plus aria-hidden="true" />
                {t(COMMON.add)}
              </Button>
            }
            className="py-8"
          />
        ) : (
          <div className="space-y-2.5">
            {activities.map(activity => (
              <ActivityCard
                key={activity.id}
                activity={activity}
                monthRef={monthRef}
                onEdit={() => setEditing(activity)}
                onDelete={() => setDeleting(activity)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Edição */}
      {editing && (
        <EditActivityDialog activity={editing} monthRef={monthRef} onClose={() => setEditing(null)} />
      )}

      {/* Confirmação de exclusão */}
      <Dialog open={deleting !== null} onOpenChange={open => !open && setDeleting(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t(AGENDA.deleteConfirmTitle)}</DialogTitle>
            <DialogDescription>
              {t(AGENDA.deleteConfirmDesc, { title: deleting?.title ?? '' })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeleting(null)}>
              {t(COMMON.cancel)}
            </Button>
            <Button type="button" variant="destructive" onClick={confirmDelete}>
              <Trash2 aria-hidden="true" />
              {t(COMMON.delete)}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
