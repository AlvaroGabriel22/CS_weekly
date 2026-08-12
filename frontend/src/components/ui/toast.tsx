import * as React from "react"
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * Sistema de toasts do QWI.
 *
 * Uso:
 *   const { toast } = useToast()
 *   toast.success('Salvo com sucesso!')
 *   toast.error(parseApiError(err).message)
 *   toast.info('Gerando relatório…')
 *
 * <Toaster /> é montado uma única vez pelo AppLayout.
 *
 * Nota de implementação: store externa no padrão zustand (subscribe/getSnapshot
 * + useSyncExternalStore do React 18). O pacote `zustand` consta no package.json
 * mas não está presente em node_modules — e instalar dependências é proibido —
 * então a store é local, mantendo o MESMO contrato público.
 */

type ToastKind = "success" | "error" | "info"

export interface ToastItem {
  id: number
  kind: ToastKind
  message: string
}

const AUTO_DISMISS_MS = 5000

// ── Store externa (padrão zustand: subscribe + getSnapshot + ações) ─────────
let toasts: ToastItem[] = []
let nextId = 1
const listeners = new Set<() => void>()
const timers = new Map<number, ReturnType<typeof setTimeout>>()

function emit() {
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function getSnapshot(): ToastItem[] {
  return toasts
}

function dismissToast(id: number) {
  const timer = timers.get(id)
  if (timer) {
    clearTimeout(timer)
    timers.delete(id)
  }
  toasts = toasts.filter(t => t.id !== id)
  emit()
}

function addToast(kind: ToastKind, message: string) {
  const id = nextId++
  toasts = [...toasts, { id, kind, message }]
  timers.set(id, setTimeout(() => dismissToast(id), AUTO_DISMISS_MS))
  emit()
}

/** API estável — pode ser usada dentro ou fora de componentes React. */
export const toast = {
  success: (message: string) => addToast("success", message),
  error: (message: string) => addToast("error", message),
  info: (message: string) => addToast("info", message),
}

/** Hook padrão de consumo: const { toast } = useToast() */
export function useToast() {
  return { toast }
}

// ── Apresentação ────────────────────────────────────────────────────────────

const kindStyles: Record<ToastKind, { container: string; icon: string }> = {
  success: { container: "border-green-200 bg-green-50 text-green-800", icon: "text-green-600" },
  error: { container: "border-red-200 bg-red-50 text-red-800", icon: "text-red-600" },
  info: { container: "border-blue-200 bg-blue-50 text-blue-800", icon: "text-blue-600" },
}

const kindIcons: Record<ToastKind, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
}

function ToastCard({ item }: { item: ToastItem }) {
  const Icon = kindIcons[item.kind]
  const styles = kindStyles[item.kind]
  return (
    <div
      role={item.kind === "error" ? "alert" : "status"}
      className={cn(
        "pointer-events-auto flex w-full items-start gap-3 rounded-xl border p-4 shadow-elevated animate-slide-up",
        styles.container
      )}
    >
      <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", styles.icon)} aria-hidden="true" />
      <p className="min-w-0 flex-1 break-words text-sm font-medium">{item.message}</p>
      <button
        type="button"
        onClick={() => dismissToast(item.id)}
        aria-label="Fechar notificação"
        className="shrink-0 rounded-md p-1 opacity-60 transition-opacity hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  )
}

/** Monte UMA vez (AppLayout já monta). Canto superior direito, empilha. */
export function Toaster() {
  const items = React.useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed right-4 top-4 z-[100] flex w-[calc(100vw-2rem)] max-w-sm flex-col gap-2"
    >
      {items.map(item => (
        <ToastCard key={item.id} item={item} />
      ))}
    </div>
  )
}
