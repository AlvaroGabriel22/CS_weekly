/**
 * Editor WYSIWYG de montagem do PPT — v2 "bloquinhos".
 *
 * Layout: [Conteúdo da semana | esquerda] [Página 16:9 | centro] [Slides | direita]
 *
 * - O deck nasce SÓ com a capa (editável). Nada é pré-populado.
 * - Cada conteúdo da semana vira um bloquinho (descrição, imagem, tabela de
 *   Excel, blocos da IA) na ordem de inserção; arraste para o slide e solte
 *   onde quiser (ou clique para inserir no centro).
 * - Elementos: mover (arrastar + snap), redimensionar (alças), editar texto
 *   (2 cliques), formas (retângulo/linha/elipse) com contorno e preenchimento,
 *   paleta de 16 cores, fixar (📌), duplicar, frente/trás, Ctrl+Z/Y.
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type DragEvent as ReactDragEvent,
  type PointerEvent as ReactPointerEvent,
} from 'react'
import {
  AlignCenter,
  AlignLeft,
  AlignRight,
  ArrowDown,
  ArrowUp,
  Bold,
  ChevronsDown,
  ChevronsUp,
  Circle,
  Copy,
  FileSpreadsheet,
  GripVertical,
  ImageIcon,
  Languages,
  Loader2,
  Minus,
  Pin,
  PinOff,
  Plus,
  Redo2,
  Slash,
  Sparkles,
  Square,
  Trash2,
  Type,
  Undo2,
} from 'lucide-react'
import api from '@/lib/api'
import { parseApiError } from '@/lib/errors'
import { useToast } from '@/components/ui/toast'
import { useI18n, type Msg } from '@/i18n'
import { REPORTS } from '@/i18n/messages/reports'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import { useAttachmentImage } from '@/hooks/useSlideEditor'
import {
  buildContentBlocks,
  DESIGN_WIDTH,
  elementFromBlock,
  newId,
  newShape,
  PALETTE,
  COLORS,
  type ContentBlock,
  type DeckLayout,
  type ElementBinding,
  type ShapeKind,
  type SlideDef,
  type SlideElement,
} from './slideLayout'
import type { Activity } from '@/types'

const MIN_SIZE = 0.03
const GRID = 0.005
const SNAP = 0.012
const FONT_SIZES = [8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 40, 48, 60]

const AI_LABELS: Record<ElementBinding, Msg> = {
  summary: REPORTS.aiSummaryBlock,
  highlights: REPORTS.aiSummaryBlock,
  kpis: REPORTS.aiKpisBlock,
  conclusions: REPORTS.aiConclusionsBlock,
  next_steps: REPORTS.aiNextStepsBlock,
}

type DragMode = 'move' | 'nw' | 'ne' | 'sw' | 'se'

interface DragState {
  mode: DragMode
  elementId: string
  startX: number
  startY: number
  origin: { x: number; y: number; w: number; h: number }
}

export interface SlideEditorProps {
  deck: DeckLayout
  onChange: (deck: DeckLayout) => void
  activities: Activity[]
  onPinnedChange?: (deck: DeckLayout) => void
}

// ── util imutável ────────────────────────────────────────────────────────────

function updateElement(
  deck: DeckLayout,
  slideId: string,
  elementId: string,
  patch: Partial<SlideElement>,
): DeckLayout {
  return {
    slides: deck.slides.map(slide =>
      slide.id !== slideId
        ? slide
        : {
            ...slide,
            elements: slide.elements.map(el => (el.id === elementId ? { ...el, ...patch } : el)),
          },
    ),
  }
}

function withElement(deck: DeckLayout, slideId: string, element: SlideElement): DeckLayout {
  return {
    slides: deck.slides.map(s =>
      s.id !== slideId ? s : { ...s, elements: [...s.elements, element] },
    ),
  }
}

function snap(value: number): number {
  return Math.round(value / GRID) * GRID
}

// ── conteúdo dos elementos ──────────────────────────────────────────────────

function ImageContent({ attachmentId }: { attachmentId?: string }) {
  const url = useAttachmentImage(attachmentId)
  if (url === null) return <div className="h-full w-full animate-pulse rounded-sm bg-gray-200" />
  if (url === '') {
    return (
      <div className="flex h-full w-full items-center justify-center rounded-sm bg-gray-100 text-gray-400">
        <ImageIcon className="h-6 w-6" aria-hidden />
      </div>
    )
  }
  return <img src={url} alt="" draggable={false} className="h-full w-full rounded-sm object-cover" />
}

function TableContent({
  element,
  scale,
  activities,
}: {
  element: SlideElement
  scale: number
  activities: Activity[]
}) {
  const table = useMemo(() => {
    for (const activity of activities) {
      const attachment = activity.attachments.find(a => a.id === element.attachment_id)
      if (attachment?.kpi_data?.table) return attachment.kpi_data.table
    }
    return null
  }, [activities, element.attachment_id])

  const fontSize = Math.max(element.font_size * scale, 4)
  if (!table) {
    return (
      <div className="flex h-full w-full items-center justify-center rounded-sm border border-dashed border-gray-300 bg-gray-50 text-gray-400">
        <FileSpreadsheet className="h-5 w-5" aria-hidden />
      </div>
    )
  }
  const header = element.color ?? COLORS.brand
  return (
    <div className="h-full w-full overflow-hidden">
      <table className="w-full border-collapse" style={{ fontSize }}>
        <thead>
          <tr>
            {table.columns.map((column, i) => (
              <th
                key={i}
                className="border border-white/40 px-1 text-left font-semibold text-white"
                style={{ background: header }}
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, r) => (
            <tr key={r} className={r % 2 ? 'bg-gray-50' : 'bg-white'}>
              {table.columns.map((_, c) => (
                <td key={c} className="border border-gray-200 px-1 text-gray-800">
                  {row[c] ?? ''}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ShapeContent({ element }: { element: SlideElement }) {
  const stroke = element.color ?? COLORS.brand
  const width = element.stroke_width ?? 2
  if (element.shape === 'line') {
    // w=0 → linha vertical; h=0 → horizontal (desenha no meio do wrapper,
    // que mantém uma área mínima só para dar o que clicar/arrastar).
    const x1 = element.w === 0 ? '50%' : '0'
    const x2 = element.w === 0 ? '50%' : '100%'
    const y1 = element.h === 0 ? '50%' : '0'
    const y2 = element.h === 0 ? '50%' : '100%'
    return (
      <svg className="h-full w-full overflow-visible" aria-hidden preserveAspectRatio="none">
        <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={stroke} strokeWidth={width} />
      </svg>
    )
  }
  return (
    <div
      className="h-full w-full"
      style={{
        border: `${width}px solid ${stroke}`,
        background: element.fill ?? 'transparent',
        borderRadius: element.shape === 'ellipse' ? '50%' : 2,
      }}
    />
  )
}

function ElementContent({
  element,
  scale,
  activities,
  t,
}: {
  element: SlideElement
  scale: number
  activities: Activity[]
  t: (m: Msg) => string
}) {
  if (element.type === 'image') return <ImageContent attachmentId={element.attachment_id} />
  if (element.type === 'table') return <TableContent element={element} scale={scale} activities={activities} />
  if (element.type === 'shape') return <ShapeContent element={element} />

  const style: CSSProperties = {
    fontSize: element.font_size * scale,
    fontWeight: element.bold ? 700 : 400,
    textAlign: element.align ?? 'left',
    color: element.color ?? COLORS.dark,
    lineHeight: 1.25,
    overflow: 'hidden',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    width: '100%',
    height: '100%',
  }
  if (element.binding) {
    return (
      <div style={{ ...style, fontStyle: 'italic', opacity: 0.8 }}>
        <span
          className="inline-flex items-center gap-1 rounded bg-brand-50 px-1 font-medium not-italic text-brand"
          style={{ fontSize: Math.max(9 * scale, 6) }}
        >
          <Sparkles style={{ width: 9 * scale, height: 9 * scale }} aria-hidden />
          {t(AI_LABELS[element.binding])}
        </span>
      </div>
    )
  }
  return <div style={style}>{element.text}</div>
}

// ── miniatura de slide (rail) ───────────────────────────────────────────────

export function SlideThumbnail({
  slide,
  width,
  activities,
  t,
}: {
  slide: SlideDef
  width: number
  activities: Activity[]
  t: (m: Msg) => string
}) {
  const scale = width / DESIGN_WIDTH
  return (
    <div
      className="relative overflow-hidden rounded border border-border bg-white"
      style={{ width, height: width * (9 / 16) }}
    >
      {slide.elements.map(el => (
        <div
          key={el.id}
          style={{
            position: 'absolute',
            left: `${el.x * 100}%`,
            top: `${el.y * 100}%`,
            width: `${Math.max(el.w, el.shape === 'line' ? 0.002 : 0) * 100}%`,
            height: `${Math.max(el.h, el.shape === 'line' ? 0.002 : 0) * 100}%`,
          }}
        >
          <ElementContent element={el} scale={scale} activities={activities} t={t} />
        </div>
      ))}
    </div>
  )
}

// ── bloquinho (painel esquerdo) ─────────────────────────────────────────────

function BlockThumb({ attachmentId }: { attachmentId: string }) {
  const url = useAttachmentImage(attachmentId)
  if (!url) return <div className="h-9 w-9 shrink-0 animate-pulse rounded bg-gray-200" />
  return <img src={url} alt="" draggable={false} className="h-9 w-9 shrink-0 rounded object-cover" />
}

function BlockCard({
  block,
  used,
  onInsert,
  t,
}: {
  block: ContentBlock
  used: boolean
  onInsert: (block: ContentBlock) => void
  t: (m: Msg, vars?: Record<string, string | number>) => string
}) {
  const label =
    block.kind === 'ai'
      ? t(AI_LABELS[block.binding])
      : block.kind === 'text'
        ? block.activity.title
        : block.attachment.original_filename

  const detail =
    block.kind === 'text'
      ? block.activity.description ?? ''
      : block.kind === 'table'
        ? `${t(REPORTS.tableBadge)} · ${t(REPORTS.blockRows, { n: block.table.n_rows })}`
        : block.kind === 'image'
          ? block.activity.title
          : t(REPORTS.blocksHint)

  const icon =
    block.kind === 'table' ? (
      <FileSpreadsheet className="h-4 w-4 shrink-0 text-green-600" aria-hidden />
    ) : block.kind === 'ai' ? (
      <Sparkles className="h-4 w-4 shrink-0 text-brand" aria-hidden />
    ) : block.kind === 'text' ? (
      <Type className="h-4 w-4 shrink-0 text-gray-500" aria-hidden />
    ) : null

  return (
    <button
      type="button"
      draggable
      onDragStart={event => {
        event.dataTransfer.setData('application/x-qwi-block', block.id)
        event.dataTransfer.effectAllowed = 'copy'
      }}
      onClick={() => onInsert(block)}
      title={t(REPORTS.blocksHint)}
      className={cn(
        'group flex w-full cursor-grab items-center gap-2 rounded-lg border bg-white p-2 text-left shadow-sm transition-all',
        'hover:-translate-y-px hover:border-brand-200 hover:shadow',
        'active:cursor-grabbing',
        used ? 'border-green-200 bg-green-50/40' : 'border-border/60',
      )}
    >
      <GripVertical className="h-4 w-4 shrink-0 text-gray-300 group-hover:text-gray-400" aria-hidden />
      {block.kind === 'image' ? <BlockThumb attachmentId={block.attachment.id} /> : icon}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-medium text-gray-900">{label}</span>
        {detail && <span className="block truncate text-[11px] text-gray-500">{detail}</span>}
      </span>
      {used && (
        <span className="shrink-0 rounded bg-green-100 px-1 py-0.5 text-[10px] font-medium text-green-700">
          {t(REPORTS.usedBadge)}
        </span>
      )}
    </button>
  )
}

// ── editor ───────────────────────────────────────────────────────────────────

export function SlideEditor({ deck, onChange, activities, onPinnedChange }: SlideEditorProps) {
  const { t } = useI18n()
  const { toast } = useToast()
  const [translating, setTranslating] = useState(false)
  const canvasRef = useRef<HTMLDivElement>(null)
  const [canvasWidth, setCanvasWidth] = useState(720)
  const [selectedSlideId, setSelectedSlideId] = useState<string | null>(deck.slides[0]?.id ?? null)
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null)
  const [editingElementId, setEditingElementId] = useState<string | null>(null)
  const [editingText, setEditingText] = useState('')
  const [guides, setGuides] = useState<{ v: boolean; h: boolean }>({ v: false, h: false })
  const [dropActive, setDropActive] = useState(false)
  const dragRef = useRef<DragState | null>(null)
  const dragSnapshotRef = useRef<DeckLayout | null>(null)
  const undoStack = useRef<DeckLayout[]>([])
  const redoStack = useRef<DeckLayout[]>([])
  const deckRef = useRef(deck)
  deckRef.current = deck

  const blocks = useMemo(() => buildContentBlocks(activities), [activities])
  const blockById = useMemo(() => new Map(blocks.map(b => [b.id, b])), [blocks])

  /** Ids de anexos/bindings já usados em algum slide (marca "No slide"). */
  const usedKeys = useMemo(() => {
    const keys = new Set<string>()
    for (const slide of deck.slides) {
      for (const el of slide.elements) {
        if (el.attachment_id) keys.add(`att:${el.attachment_id}`)
        if (el.binding) keys.add(`ai:${el.binding}`)
        if (el.type === 'text' && el.text) keys.add(`txt:${el.text.split('\n')[0]}`)
      }
    }
    return keys
  }, [deck.slides])

  const isUsed = (block: ContentBlock) =>
    block.kind === 'ai'
      ? usedKeys.has(`ai:${block.binding}`)
      : block.kind === 'text'
        ? usedKeys.has(`txt:${block.activity.title}`)
        : usedKeys.has(`att:${block.attachment.id}`)

  const slide = useMemo(
    () => deck.slides.find(s => s.id === selectedSlideId) ?? deck.slides[0] ?? null,
    [deck.slides, selectedSlideId],
  )
  const selected = slide?.elements.find(el => el.id === selectedElementId) ?? null
  const scale = canvasWidth / DESIGN_WIDTH

  useEffect(() => {
    if (!slide && deck.slides.length > 0) setSelectedSlideId(deck.slides[0].id)
  }, [slide, deck.slides])

  useEffect(() => {
    const el = canvasRef.current
    if (!el) return
    const observer = new ResizeObserver(entries => {
      const width = entries[0]?.contentRect.width
      if (width) setCanvasWidth(width)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const commit = useCallback(
    (next: DeckLayout, snapshot?: DeckLayout) => {
      undoStack.current.push(snapshot ?? deckRef.current)
      if (undoStack.current.length > 100) undoStack.current.shift()
      redoStack.current = []
      onChange(next)
    },
    [onChange],
  )

  const undo = useCallback(() => {
    const prev = undoStack.current.pop()
    if (!prev) return
    redoStack.current.push(deckRef.current)
    onChange(prev)
    setSelectedElementId(null)
    setEditingElementId(null)
  }, [onChange])

  const redo = useCallback(() => {
    const next = redoStack.current.pop()
    if (!next) return
    undoStack.current.push(deckRef.current)
    onChange(next)
    setSelectedElementId(null)
  }, [onChange])

  // ── inserção de blocos ────────────────────────────────────────────────────

  const insertBlock = (block: ContentBlock, cx = 0.5, cy = 0.5) => {
    if (!slide) return
    const element = elementFromBlock(block, cx, cy)
    commit(withElement(deckRef.current, slide.id, element))
    setSelectedElementId(element.id)
  }

  const onCanvasDragOver = (event: ReactDragEvent) => {
    if (event.dataTransfer.types.includes('application/x-qwi-block')) {
      event.preventDefault()
      event.dataTransfer.dropEffect = 'copy'
      if (!dropActive) setDropActive(true)
    }
  }

  const onCanvasDrop = (event: ReactDragEvent) => {
    setDropActive(false)
    const blockId = event.dataTransfer.getData('application/x-qwi-block')
    const block = blockById.get(blockId)
    if (!block || !canvasRef.current) return
    event.preventDefault()
    const rect = canvasRef.current.getBoundingClientRect()
    const cx = (event.clientX - rect.left) / rect.width
    const cy = (event.clientY - rect.top) / rect.height
    insertBlock(block, cx, cy)
  }

  // ── edição inline ─────────────────────────────────────────────────────────

  const startEditing = (element: SlideElement) => {
    if (element.type !== 'text' || element.binding) return
    setEditingElementId(element.id)
    setEditingText(element.text ?? '')
  }

  const commitEditing = useCallback(() => {
    if (!editingElementId || !slide) return
    const current = slide.elements.find(el => el.id === editingElementId)
    if (current && (current.text ?? '') !== editingText) {
      commit(updateElement(deckRef.current, slide.id, editingElementId, { text: editingText }))
    }
    setEditingElementId(null)
  }, [editingElementId, editingText, slide, commit])

  // ── drag / resize de elementos ────────────────────────────────────────────

  const onElementPointerDown = (event: ReactPointerEvent, element: SlideElement, mode: DragMode) => {
    if (event.button !== 0 || editingElementId === element.id || !slide) return
    event.preventDefault()
    event.stopPropagation()
    setSelectedElementId(element.id)
    dragRef.current = {
      mode,
      elementId: element.id,
      startX: event.clientX,
      startY: event.clientY,
      origin: { x: element.x, y: element.y, w: element.w, h: element.h },
    }
    dragSnapshotRef.current = deckRef.current
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  }

  const onPointerMove = (event: ReactPointerEvent) => {
    const drag = dragRef.current
    if (!drag || !slide) return
    const isLine = slide.elements.find(el => el.id === drag.elementId)?.shape === 'line'
    const canvasH = canvasWidth * (9 / 16)
    const dx = (event.clientX - drag.startX) / canvasWidth
    const dy = (event.clientY - drag.startY) / canvasH
    const { origin } = drag
    let patch: Partial<SlideElement> = {}
    const showGuides = { v: false, h: false }
    const minSize = isLine ? 0 : MIN_SIZE

    if (drag.mode === 'move') {
      let x = snap(origin.x + dx)
      let y = snap(origin.y + dy)
      const centerX = x + origin.w / 2
      const centerY = y + origin.h / 2
      if (Math.abs(centerX - 0.5) < SNAP) { x = 0.5 - origin.w / 2; showGuides.v = true }
      if (Math.abs(centerY - 0.5) < SNAP) { y = 0.5 - origin.h / 2; showGuides.h = true }
      x = Math.min(Math.max(x, 0), 1 - origin.w)
      y = Math.min(Math.max(y, 0), Math.max(1 - origin.h, 0))
      patch = { x, y }
    } else {
      let { x, y, w, h } = origin
      if (drag.mode === 'se') { w = origin.w + dx; h = origin.h + dy }
      if (drag.mode === 'ne') { w = origin.w + dx; y = origin.y + dy; h = origin.h - dy }
      if (drag.mode === 'sw') { x = origin.x + dx; w = origin.w - dx; h = origin.h + dy }
      if (drag.mode === 'nw') { x = origin.x + dx; y = origin.y + dy; w = origin.w - dx; h = origin.h - dy }
      w = Math.max(snap(w), minSize)
      h = Math.max(snap(h), minSize)
      x = Math.min(Math.max(snap(x), 0), 1 - minSize)
      y = Math.min(Math.max(snap(y), 0), 1 - minSize)
      w = Math.min(w, 1 - x)
      h = Math.min(h, 1 - y)
      // Linhas: snap ao eixo — perto da vertical vira w=0 (reta em pé),
      // perto da horizontal vira h=0 (reta deitada).
      if (isLine) {
        if (w < SNAP && w < h) w = 0
        else if (h < SNAP && h < w) h = 0
      }
      patch = { x, y, w, h }
    }
    setGuides(showGuides)
    onChange(updateElement(deckRef.current, slide.id, drag.elementId, patch))
  }

  const onPointerUp = () => {
    const drag = dragRef.current
    if (!drag) return
    dragRef.current = null
    setGuides({ v: false, h: false })
    const snapshot = dragSnapshotRef.current
    dragSnapshotRef.current = null
    if (snapshot) {
      undoStack.current.push(snapshot)
      if (undoStack.current.length > 100) undoStack.current.shift()
      redoStack.current = []
    }
  }

  // ── operações de elemento ────────────────────────────────────────────────

  const patchSelected = (patch: Partial<SlideElement>) => {
    if (!slide || !selected) return
    commit(updateElement(deckRef.current, slide.id, selected.id, patch))
  }

  const deleteSelected = useCallback(() => {
    if (!slide || !selectedElementId) return
    commit({
      slides: deckRef.current.slides.map(s =>
        s.id !== slide.id ? s : { ...s, elements: s.elements.filter(el => el.id !== selectedElementId) },
      ),
    })
    setSelectedElementId(null)
  }, [slide, selectedElementId, commit])

  const duplicateSelected = () => {
    if (!slide || !selected) return
    const copy: SlideElement = {
      ...selected,
      id: newId('el'),
      x: Math.min(selected.x + 0.03, 1 - selected.w),
      y: Math.min(selected.y + 0.05, Math.max(1 - selected.h, 0)),
      pinned: false,
    }
    commit(withElement(deckRef.current, slide.id, copy))
    setSelectedElementId(copy.id)
  }

  const reorderSelected = (direction: 'front' | 'back') => {
    if (!slide || !selected) return
    const elements = [...slide.elements]
    const index = elements.findIndex(el => el.id === selected.id)
    elements.splice(index, 1)
    if (direction === 'front') elements.push(selected)
    else elements.unshift(selected)
    commit({ slides: deckRef.current.slides.map(s => (s.id !== slide.id ? s : { ...s, elements })) })
  }

  const togglePin = () => {
    if (!slide || !selected) return
    const next = updateElement(deckRef.current, slide.id, selected.id, { pinned: !selected.pinned })
    commit(next)
    onPinnedChange?.(next)
  }

  const stepFont = (direction: 1 | -1) => {
    if (!selected) return
    const index = FONT_SIZES.findIndex(size => size >= selected.font_size)
    const currentIndex = index === -1 ? FONT_SIZES.length - 1 : index
    const nextIndex = Math.min(Math.max(currentIndex + direction, 0), FONT_SIZES.length - 1)
    patchSelected({ font_size: FONT_SIZES[nextIndex] })
  }

  const addText = () => {
    if (!slide) return
    const element: SlideElement = {
      id: newId('el'),
      type: 'text',
      x: 0.3,
      y: 0.42,
      w: 0.4,
      h: 0.12,
      text: t(REPORTS.addText),
      font_size: 18,
      color: COLORS.dark,
      align: 'left',
    }
    commit(withElement(deckRef.current, slide.id, element))
    setSelectedElementId(element.id)
  }

  const addShape = (shape: ShapeKind) => {
    if (!slide) return
    const element = newShape(shape)
    commit(withElement(deckRef.current, slide.id, element))
    setSelectedElementId(element.id)
  }

  /**
   * Traduz TODOS os textos escritos pelo usuário (todos os slides) via IA.
   * Aplica como um único commit — Ctrl+Z desfaz a tradução inteira.
   */
  const translateDeck = async (target: 'pt' | 'en' | 'ko') => {
    const current = deckRef.current
    const refs: { slideId: string; elementId: string }[] = []
    const texts: string[] = []
    for (const s of current.slides) {
      for (const el of s.elements) {
        if (el.type === 'text' && !el.binding && el.text?.trim()) {
          refs.push({ slideId: s.id, elementId: el.id })
          texts.push(el.text)
        }
      }
    }
    if (texts.length === 0) {
      toast.info(t(REPORTS.nothingToTranslate))
      return
    }
    setTranslating(true)
    try {
      const res = await api.post('/ai/translate', { texts, target })
      const translated: string[] = res.data.texts
      let next = current
      refs.forEach((ref, index) => {
        next = updateElement(next, ref.slideId, ref.elementId, { text: translated[index] })
      })
      commit(next, current)
      toast.success(t(REPORTS.translated))
    } catch (err) {
      toast.error(parseApiError(err).message)
    } finally {
      setTranslating(false)
    }
  }

  // ── operações de slide ───────────────────────────────────────────────────

  const addSlide = () => {
    const created: SlideDef = { id: newId('slide'), kind: 'custom', elements: [] }
    const index = slide ? deck.slides.findIndex(s => s.id === slide.id) + 1 : deck.slides.length
    const slides = [...deck.slides]
    slides.splice(index, 0, created)
    commit({ slides })
    setSelectedSlideId(created.id)
    setSelectedElementId(null)
  }

  const deleteSlide = (slideId: string) => {
    if (deck.slides.length <= 1) return // a capa permanece
    const index = deck.slides.findIndex(s => s.id === slideId)
    const slides = deck.slides.filter(s => s.id !== slideId)
    commit({ slides })
    setSelectedSlideId(slides[Math.min(index, slides.length - 1)]?.id ?? null)
    setSelectedElementId(null)
  }

  const moveSlide = (slideId: string, direction: -1 | 1) => {
    const index = deck.slides.findIndex(s => s.id === slideId)
    const target = index + direction
    if (index === -1 || target < 0 || target >= deck.slides.length) return
    const slides = [...deck.slides]
    const [moved] = slides.splice(index, 1)
    slides.splice(target, 0, moved)
    commit({ slides })
  }

  // ── teclado ───────────────────────────────────────────────────────────────

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (editingElementId) return
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
      event.preventDefault()
      if (event.shiftKey) redo()
      else undo()
      return
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'y') {
      event.preventDefault()
      redo()
      return
    }
    if (!selected || !slide) return
    if (event.key === 'Delete' || event.key === 'Backspace') {
      event.preventDefault()
      deleteSelected()
      return
    }
    const nudge = event.shiftKey ? 0.02 : GRID
    const moves: Record<string, Partial<SlideElement>> = {
      ArrowLeft: { x: Math.max(selected.x - nudge, 0) },
      ArrowRight: { x: Math.min(selected.x + nudge, 1 - selected.w) },
      ArrowUp: { y: Math.max(selected.y - nudge, 0) },
      ArrowDown: { y: Math.min(selected.y + nudge, Math.max(1 - selected.h, 0)) },
    }
    const patch = moves[event.key]
    if (patch) {
      event.preventDefault()
      patchSelected(patch)
    }
  }

  if (!slide) return null

  const slideIndex = deck.slides.findIndex(s => s.id === slide.id)
  const isTextSelected = selected?.type === 'text'
  const isShapeSelected = selected?.type === 'shape'

  const toolButton =
    'flex h-9 min-w-9 items-center justify-center rounded-md px-1.5 text-gray-600 transition-colors hover:bg-gray-100 disabled:opacity-35 disabled:hover:bg-transparent'

  return (
    <div className="flex flex-col gap-3 outline-none lg:flex-row" tabIndex={0} onKeyDown={onKeyDown}>
      {/* ── Painel de conteúdo (ESQUERDA) ── */}
      <aside className="order-2 shrink-0 lg:order-1 lg:w-60">
        <div className="rounded-xl border border-border/60 bg-gray-50/70 p-2.5">
          <p className="px-1 pb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            {t(REPORTS.blocksTitle)}
          </p>
          {blocks.length === 0 ? (
            <p className="px-1 pb-1 text-xs text-gray-400">{t(REPORTS.blocksEmpty)}</p>
          ) : (
            <div className="flex gap-2 overflow-x-auto pb-1 lg:max-h-[36rem] lg:flex-col lg:overflow-y-auto lg:overflow-x-visible lg:pb-0">
              {blocks.map(block => (
                <div key={block.id} className="w-56 shrink-0 lg:w-auto">
                  {block.kind === 'ai' && block.binding === 'summary' && (
                    <p className="px-1 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                      {t(REPORTS.aiBlocks)}
                    </p>
                  )}
                  <BlockCard block={block} used={isUsed(block)} onInsert={insertBlock} t={t} />
                </div>
              ))}
            </div>
          )}
          <p className="px-1 pt-2 text-[11px] text-gray-400">{t(REPORTS.blocksHint)}</p>
        </div>
      </aside>

      {/* ── Canvas + toolbar (CENTRO) ── */}
      <div className="order-1 min-w-0 flex-1 lg:order-2">
        <div className="mb-2 flex flex-wrap items-center gap-0.5 rounded-lg border border-border/60 bg-white p-1 shadow-sm">
          <button type="button" className={toolButton} onClick={undo} aria-label={t(REPORTS.undo)} title={t(REPORTS.undo)}>
            <Undo2 className="h-4 w-4" aria-hidden />
          </button>
          <button type="button" className={toolButton} onClick={redo} aria-label={t(REPORTS.redo)} title={t(REPORTS.redo)}>
            <Redo2 className="h-4 w-4" aria-hidden />
          </button>
          <span className="mx-1 h-5 w-px bg-border" aria-hidden />
          <button type="button" className={toolButton} onClick={addText} title={t(REPORTS.addText)}>
            <Type className="h-4 w-4" aria-hidden />
          </button>
          <button type="button" className={toolButton} onClick={() => addShape('rect')} aria-label={t(REPORTS.shapeRect)} title={t(REPORTS.shapeRect)}>
            <Square className="h-4 w-4" aria-hidden />
          </button>
          <button type="button" className={toolButton} onClick={() => addShape('line')} aria-label={t(REPORTS.shapeLine)} title={t(REPORTS.shapeLine)}>
            <Slash className="h-4 w-4" aria-hidden />
          </button>
          <button type="button" className={toolButton} onClick={() => addShape('ellipse')} aria-label={t(REPORTS.shapeEllipse)} title={t(REPORTS.shapeEllipse)}>
            <Circle className="h-4 w-4" aria-hidden />
          </button>

          {/* Tradução por IA de todos os textos do deck */}
          <DropdownMenu>
            <DropdownMenuTrigger
              className={toolButton}
              disabled={translating}
              aria-label={t(REPORTS.translate)}
              title={t(REPORTS.translate)}
            >
              {translating ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Languages className="h-4 w-4" aria-hidden />
              )}
              <span className="ml-1 hidden text-xs sm:inline">
                {translating ? t(REPORTS.translating) : t(REPORTS.translate)}
              </span>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuItem onSelect={() => translateDeck('pt')}>🇧🇷 Português</DropdownMenuItem>
              <DropdownMenuItem onSelect={() => translateDeck('en')}>🇺🇸 English</DropdownMenuItem>
              <DropdownMenuItem onSelect={() => translateDeck('ko')}>🇰🇷 한국어</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <span className="mx-1 h-5 w-px bg-border" aria-hidden />

          <button type="button" className={toolButton} disabled={!isTextSelected} onClick={() => stepFont(-1)} aria-label={t(REPORTS.fontSmaller)} title={t(REPORTS.fontSmaller)}>
            <Minus className="h-4 w-4" aria-hidden />
          </button>
          <span className="min-w-7 text-center text-xs tabular-nums text-gray-600">
            {isTextSelected ? `${selected?.font_size}` : '–'}
          </span>
          <button type="button" className={toolButton} disabled={!isTextSelected} onClick={() => stepFont(1)} aria-label={t(REPORTS.fontLarger)} title={t(REPORTS.fontLarger)}>
            <Plus className="h-4 w-4" aria-hidden />
          </button>
          <button
            type="button"
            className={cn(toolButton, selected?.bold && 'bg-brand-50 text-brand')}
            disabled={!isTextSelected}
            onClick={() => patchSelected({ bold: !selected?.bold })}
            aria-label={t(REPORTS.bold)}
            aria-pressed={!!selected?.bold}
            title={t(REPORTS.bold)}
          >
            <Bold className="h-4 w-4" aria-hidden />
          </button>
          {(
            [
              ['left', AlignLeft, REPORTS.alignLeft],
              ['center', AlignCenter, REPORTS.alignCenter],
              ['right', AlignRight, REPORTS.alignRight],
            ] as const
          ).map(([align, Icon, label]) => (
            <button
              key={align}
              type="button"
              className={cn(toolButton, selected?.align === align && 'bg-brand-50 text-brand')}
              disabled={!isTextSelected}
              onClick={() => patchSelected({ align })}
              aria-label={t(label)}
              title={t(label)}
            >
              <Icon className="h-4 w-4" aria-hidden />
            </button>
          ))}

          {/* Cor (texto/contorno/cabeçalho de tabela) */}
          <DropdownMenu>
            <DropdownMenuTrigger
              className={toolButton}
              disabled={!selected || selected.type === 'image'}
              aria-label={t(REPORTS.colorLabel)}
              title={t(REPORTS.colorLabel)}
            >
              <span className="h-4 w-4 rounded-full border border-border" style={{ background: selected?.color ?? COLORS.dark }} aria-hidden />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <div className="grid grid-cols-8 gap-1.5 p-1.5">
                {PALETTE.map(color => (
                  <button
                    key={color}
                    type="button"
                    className={cn('h-6 w-6 rounded-full border-2', selected?.color === color ? 'border-gray-900' : 'border-gray-200')}
                    style={{ background: color }}
                    onClick={() => patchSelected({ color })}
                    aria-label={color}
                  />
                ))}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Preenchimento (formas) */}
          {isShapeSelected && selected?.shape !== 'line' && (
            <DropdownMenu>
              <DropdownMenuTrigger className={toolButton} aria-label={t(REPORTS.fillLabel)} title={t(REPORTS.fillLabel)}>
                <span
                  className="h-4 w-4 rounded-sm border border-border"
                  style={
                    selected?.fill
                      ? { background: selected.fill }
                      : { background: 'repeating-linear-gradient(45deg,#fff,#fff 2px,#e5e7eb 2px,#e5e7eb 4px)' }
                  }
                  aria-hidden
                />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <div className="grid grid-cols-8 gap-1.5 p-1.5">
                  {PALETTE.map(color => (
                    <button
                      key={color}
                      type="button"
                      className={cn('h-6 w-6 rounded-sm border-2', selected?.fill === color ? 'border-gray-900' : 'border-gray-200')}
                      style={{ background: color }}
                      onClick={() => patchSelected({ fill: color })}
                      aria-label={color}
                    />
                  ))}
                </div>
                <DropdownMenuItem onSelect={() => patchSelected({ fill: null })}>
                  {t(REPORTS.noFill)}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          <span className="mx-1 h-5 w-px bg-border" aria-hidden />

          <button
            type="button"
            className={cn(toolButton, selected?.pinned && 'bg-amber-50 text-amber-600')}
            disabled={!isTextSelected}
            onClick={togglePin}
            aria-label={selected?.pinned ? t(REPORTS.unpin) : t(REPORTS.pin)}
            aria-pressed={!!selected?.pinned}
            title={selected?.pinned ? t(REPORTS.unpin) : t(REPORTS.pin)}
          >
            {selected?.pinned ? <PinOff className="h-4 w-4" aria-hidden /> : <Pin className="h-4 w-4" aria-hidden />}
          </button>
          <button type="button" className={toolButton} disabled={!selected} onClick={duplicateSelected} aria-label={t(REPORTS.duplicate)} title={t(REPORTS.duplicate)}>
            <Copy className="h-4 w-4" aria-hidden />
          </button>
          <button type="button" className={toolButton} disabled={!selected} onClick={() => reorderSelected('front')} aria-label={t(REPORTS.bringFront)} title={t(REPORTS.bringFront)}>
            <ChevronsUp className="h-4 w-4" aria-hidden />
          </button>
          <button type="button" className={toolButton} disabled={!selected} onClick={() => reorderSelected('back')} aria-label={t(REPORTS.sendBack)} title={t(REPORTS.sendBack)}>
            <ChevronsDown className="h-4 w-4" aria-hidden />
          </button>
          <button type="button" className={cn(toolButton, 'text-red-500 hover:bg-red-50')} disabled={!selected} onClick={deleteSelected} aria-label={t(REPORTS.deleteElement)} title={t(REPORTS.deleteElement)}>
            <Trash2 className="h-4 w-4" aria-hidden />
          </button>
        </div>

        {/* Canvas 16:9 */}
        <div
          ref={canvasRef}
          className={cn(
            'relative w-full select-none overflow-hidden rounded-lg border bg-white shadow-card transition-shadow',
            dropActive ? 'border-brand ring-2 ring-brand-200' : 'border-border',
          )}
          style={{ aspectRatio: '16 / 9', touchAction: 'none' }}
          onPointerDown={() => { setSelectedElementId(null); commitEditing() }}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onDragOver={onCanvasDragOver}
          onDragLeave={() => setDropActive(false)}
          onDrop={onCanvasDrop}
        >
          {guides.v && <div className="pointer-events-none absolute inset-y-0 left-1/2 z-40 w-px bg-blue-400" aria-hidden />}
          {guides.h && <div className="pointer-events-none absolute inset-x-0 top-1/2 z-40 h-px bg-blue-400" aria-hidden />}

          {slide.elements.map(element => {
            const isSelected = element.id === selectedElementId
            const isEditing = element.id === editingElementId
            const isLine = element.shape === 'line'
            const frame: CSSProperties = {
              left: `${element.x * 100}%`,
              top: `${element.y * 100}%`,
              width: isLine ? Math.max(element.w * 100, 0.5) + '%' : `${element.w * 100}%`,
              height: isLine ? Math.max(element.h * 100, 0.5) + '%' : `${element.h * 100}%`,
              minWidth: isLine ? 10 : undefined,
              minHeight: isLine ? 10 : undefined,
            }
            return (
              <div
                key={element.id}
                className={cn(
                  'absolute',
                  !isEditing && 'cursor-move',
                  isSelected && 'z-30 ring-2 ring-blue-500',
                  !isSelected && 'hover:ring-1 hover:ring-blue-300',
                )}
                style={frame}
                onPointerDown={e => onElementPointerDown(e, element, 'move')}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
                onDoubleClick={() => startEditing(element)}
              >
                {isEditing ? (
                  <textarea
                    autoFocus
                    value={editingText}
                    onChange={e => setEditingText(e.target.value)}
                    onBlur={commitEditing}
                    onKeyDown={e => {
                      e.stopPropagation()
                      if (e.key === 'Escape') setEditingElementId(null)
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) commitEditing()
                    }}
                    onPointerDown={e => e.stopPropagation()}
                    className="h-full w-full resize-none border-0 bg-blue-50/40 p-0 outline-none"
                    style={{
                      fontSize: element.font_size * scale,
                      fontWeight: element.bold ? 700 : 400,
                      textAlign: element.align ?? 'left',
                      color: element.color ?? COLORS.dark,
                      lineHeight: 1.25,
                    }}
                    aria-label={t(REPORTS.addText)}
                  />
                ) : (
                  <ElementContent element={element} scale={scale} activities={activities} t={t} />
                )}
                {element.pinned && !isEditing && (
                  <span className="absolute -right-1.5 -top-1.5 z-30 flex h-4 w-4 items-center justify-center rounded-full bg-amber-400 text-white shadow" title={t(REPORTS.pinned)}>
                    <Pin className="h-2.5 w-2.5" aria-hidden />
                  </span>
                )}
                {isSelected && !isEditing && (
                  <>
                    {/* Linha: só as duas extremidades; demais: 4 cantos. */}
                    {(isLine ? (['nw', 'se'] as const) : (['nw', 'ne', 'sw', 'se'] as const)).map(corner => (
                      <span
                        key={corner}
                        className={cn(
                          'absolute z-30 h-2.5 w-2.5 rounded-sm border border-blue-500 bg-white',
                          corner === 'nw' && '-left-1.5 -top-1.5 cursor-nwse-resize',
                          corner === 'ne' && '-right-1.5 -top-1.5 cursor-nesw-resize',
                          corner === 'sw' && '-bottom-1.5 -left-1.5 cursor-nesw-resize',
                          corner === 'se' && '-bottom-1.5 -right-1.5 cursor-nwse-resize',
                        )}
                        onPointerDown={e => onElementPointerDown(e, element, corner)}
                        onPointerMove={onPointerMove}
                        onPointerUp={onPointerUp}
                      />
                    ))}
                  </>
                )}
              </div>
            )
          })}
        </div>

        <p className="mt-1.5 flex items-center justify-between text-xs text-gray-400">
          <span>{t(REPORTS.slideOf, { n: slideIndex + 1, total: deck.slides.length })}</span>
          <span>{t(REPORTS.editHint)}</span>
        </p>
      </div>

      {/* ── Rail de slides (DIREITA) ── */}
      <aside className="order-3 shrink-0 lg:w-52">
        <div className="rounded-xl border border-border/60 bg-gray-50/70 p-2.5">
          <p className="px-1 pb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            {t(REPORTS.slides)}
          </p>
          <div
            className="flex gap-3 overflow-x-auto p-1 lg:max-h-[36rem] lg:flex-col lg:overflow-y-auto lg:overflow-x-visible"
            role="list"
            aria-label={t(REPORTS.slides)}
          >
            {deck.slides.map((item, index) => (
              <div key={item.id} role="listitem" className="group relative shrink-0">
                <button
                  type="button"
                  onClick={() => { setSelectedSlideId(item.id); setSelectedElementId(null) }}
                  className={cn(
                    'block rounded-md p-0.5 transition-all',
                    item.id === slide.id ? 'ring-2 ring-brand' : 'hover:ring-2 hover:ring-brand-200',
                  )}
                  aria-label={t(REPORTS.slideOf, { n: index + 1, total: deck.slides.length })}
                  aria-current={item.id === slide.id}
                >
                  <SlideThumbnail slide={item} width={160} activities={activities} t={t} />
                </button>
                <span className="absolute bottom-1.5 left-2 rounded bg-gray-900/60 px-1 text-[10px] font-medium text-white">
                  {index + 1}
                </span>
                <div className="absolute right-1 top-1 hidden gap-0.5 rounded-md bg-white/95 p-0.5 shadow-sm group-hover:flex">
                  <button type="button" className="rounded p-1 text-gray-500 hover:bg-gray-100" onClick={() => moveSlide(item.id, -1)} disabled={index === 0} aria-label={t(REPORTS.moveUp)}>
                    <ArrowUp className="h-3.5 w-3.5" aria-hidden />
                  </button>
                  <button type="button" className="rounded p-1 text-gray-500 hover:bg-gray-100" onClick={() => moveSlide(item.id, 1)} disabled={index === deck.slides.length - 1} aria-label={t(REPORTS.moveDown)}>
                    <ArrowDown className="h-3.5 w-3.5" aria-hidden />
                  </button>
                  {index > 0 && (
                    <button type="button" className="rounded p-1 text-red-500 hover:bg-red-50" onClick={() => deleteSlide(item.id)} aria-label={t(REPORTS.deleteSlide)}>
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                    </button>
                  )}
                </div>
              </div>
            ))}
            <button
              type="button"
              onClick={addSlide}
              className="flex h-[90px] w-40 shrink-0 items-center justify-center gap-1 rounded-md border-2 border-dashed border-border text-xs font-medium text-gray-500 transition-colors hover:border-brand hover:text-brand lg:w-full"
            >
              <Plus className="h-4 w-4" aria-hidden /> {t(REPORTS.addSlide)}
            </button>
          </div>
        </div>
      </aside>
    </div>
  )
}
