/**
 * Modelo do editor WYSIWYG de montagem do PPT.
 *
 * Espelha o contrato do backend (app/services/pptx_layout.py):
 * posições/tamanhos são FRAÇÕES (0–1) da página 16:9 (13.333in × 7.5in).
 * `font_size` em pontos (pt). Na tela: 1pt = canvasWidthPx / 960 px.
 *
 * Tipos de elemento:
 * - text  : literal (usuário edita) OU `binding` (IA preenche na geração)
 * - image : anexo de imagem (attachment_id)
 * - table : tabela extraída de planilha anexada (attachment_id → kpi_data.table)
 * - shape : forma (rect | line | ellipse), com contorno e preenchimento
 *
 * O deck NASCE só com a capa (fixa porém 100% editável); o conteúdo entra
 * pelos BLOQUINHOS do painel esquerdo, arrastados para o slide.
 */
import type { Activity, Attachment, ExtractedTable } from '@/types'

export type ElementBinding = 'summary' | 'highlights' | 'kpis' | 'conclusions' | 'next_steps'
export type ShapeKind = 'rect' | 'line' | 'ellipse'

export interface SlideElement {
  id: string
  type: 'text' | 'image' | 'table' | 'shape'
  x: number
  y: number
  w: number
  h: number
  text?: string
  binding?: ElementBinding
  attachment_id?: string
  shape?: ShapeKind
  /** Preenchimento da forma (hex) ou null/ausente = sem preenchimento. */
  fill?: string | null
  stroke_width?: number
  font_size: number
  bold?: boolean
  align?: 'left' | 'center' | 'right'
  color?: string
  pinned?: boolean
}

export type SlideKind = 'cover' | 'custom'

export interface SlideDef {
  id: string
  kind: SlideKind
  elements: SlideElement[]
}

export interface DeckLayout {
  slides: SlideDef[]
}

/** Proporção da página (16:9). */
export const SLIDE_ASPECT = 16 / 9
/** Largura de projeto em px (13.333in × 72pt): 1pt de fonte = 1px nessa largura. */
export const DESIGN_WIDTH = 960

/** Paleta ampliada do editor (contorno/texto e preenchimento). */
export const PALETTE = [
  '#1F2937', '#6B7280', '#9CA3AF', '#FFFFFF',
  '#0C379C', '#2563EB', '#60A5FA', '#0EA5E9',
  '#16A34A', '#84CC16', '#EAB308', '#F97316',
  '#DC2626', '#EC4899', '#9333EA', '#78350F',
]

export const COLORS = {
  dark: '#1F2937',
  gray: '#6B7280',
  brand: '#0C379C',
}

let elementCounter = 0
export function newId(prefix: string): string {
  elementCounter += 1
  return `${prefix}-${Date.now().toString(36)}-${elementCounter}`
}

function text(partial: Partial<SlideElement> & Pick<SlideElement, 'x' | 'y' | 'w' | 'h'>): SlideElement {
  return {
    id: newId('el'),
    type: 'text',
    font_size: 14,
    color: COLORS.dark,
    align: 'left',
    ...partial,
  }
}

export interface DeckLabels {
  coverTitle: string
  coverSubtitle: string
}

/** Deck inicial: SÓ a capa (editável). Conteúdo entra pelos bloquinhos. */
export function buildCoverDeck(labels: DeckLabels, pinned: SlideElement[] = []): DeckLayout {
  return {
    slides: [
      {
        id: newId('slide'),
        kind: 'cover',
        elements: [
          text({ x: 0.06, y: 0.32, w: 0.88, h: 0.16, text: labels.coverTitle, font_size: 40, bold: true, color: COLORS.brand }),
          text({ x: 0.06, y: 0.5, w: 0.88, h: 0.08, text: labels.coverSubtitle, font_size: 18, color: COLORS.gray }),
          ...pinned.filter(p => p.pinned).map(p => ({ ...p, id: newId('el') })),
        ],
      },
    ],
  }
}

/** Elementos fixados (pinned) de todo o deck — persistidos entre apresentações. */
export function pinnedElements(deck: DeckLayout): SlideElement[] {
  return deck.slides.flatMap(slide => slide.elements.filter(el => el.pinned && el.type === 'text'))
}

// ── Bloquinhos de conteúdo (painel esquerdo) ────────────────────────────────

export type ContentBlock =
  | { kind: 'text'; id: string; activity: Activity }
  | { kind: 'image'; id: string; activity: Activity; attachment: Attachment }
  | { kind: 'table'; id: string; activity: Activity; attachment: Attachment; table: ExtractedTable }
  | { kind: 'ai'; id: string; binding: ElementBinding }

export const AI_BINDINGS: ElementBinding[] = ['summary', 'kpis', 'conclusions', 'next_steps']

/**
 * Bloquinhos na ORDEM DE INSERÇÃO: para cada atividade (por data/criação),
 * a descrição, depois cada anexo (imagem/tabela) na ordem de upload.
 * Ao final, os blocos de conteúdo da IA.
 */
export function buildContentBlocks(activities: Activity[]): ContentBlock[] {
  const blocks: ContentBlock[] = []
  for (const activity of activities) {
    blocks.push({ kind: 'text', id: `blk-text-${activity.id}`, activity })
    for (const attachment of activity.attachments) {
      const table = attachment.kpi_data?.table
      if (table && table.columns.length > 0) {
        blocks.push({ kind: 'table', id: `blk-tbl-${attachment.id}`, activity, attachment, table })
      } else if (
        attachment.file_type === 'image' ||
        (attachment.mime_type ?? '').startsWith('image/')
      ) {
        blocks.push({ kind: 'image', id: `blk-img-${attachment.id}`, activity, attachment })
      }
    }
  }
  for (const binding of AI_BINDINGS) {
    blocks.push({ kind: 'ai', id: `blk-ai-${binding}`, binding })
  }
  return blocks
}

/** Cria o elemento correspondente a um bloco, centrado em (cx, cy) do slide. */
export function elementFromBlock(block: ContentBlock, cx: number, cy: number): SlideElement {
  const place = (w: number, h: number) => ({
    x: Math.min(Math.max(cx - w / 2, 0), 1 - w),
    y: Math.min(Math.max(cy - h / 2, 0), 1 - h),
    w,
    h,
  })
  switch (block.kind) {
    case 'text': {
      const body = block.activity.description?.trim()
      return text({
        ...place(0.5, 0.28),
        text: body ? `${block.activity.title}\n${body}` : block.activity.title,
        font_size: 14,
      })
    }
    case 'image':
      return {
        id: newId('el'),
        type: 'image',
        attachment_id: block.attachment.id,
        font_size: 14,
        ...place(0.34, 0.4),
      }
    case 'table': {
      const rows = Math.min(block.table.n_rows + 1, 12)
      return {
        id: newId('el'),
        type: 'table',
        attachment_id: block.attachment.id,
        font_size: 11,
        color: COLORS.brand,
        ...place(0.6, Math.min(0.08 * rows, 0.7)),
      }
    }
    case 'ai':
      return text({ ...place(0.55, 0.4), binding: block.binding, font_size: 14 })
  }
}

/** Nova forma inserida pela toolbar, no centro do slide. */
export function newShape(shape: ShapeKind): SlideElement {
  const base = {
    id: newId('el'),
    type: 'shape' as const,
    shape,
    color: COLORS.brand,
    fill: null,
    stroke_width: 2,
    font_size: 14,
  }
  if (shape === 'line') return { ...base, x: 0.3, y: 0.5, w: 0.4, h: 0 }
  return { ...base, x: 0.38, y: 0.36, w: 0.24, h: shape === 'ellipse' ? 0.24 : 0.2 }
}
