/**
 * Renderização SOMENTE LEITURA de um slide do layout (pré-visualização do PPT).
 *
 * Usada fora do editor (ex.: weeklys de colegas): desenha a página 16:9 com
 * os elementos do layout salvo no relatório. Tabelas usam os dados embutidos
 * pelo backend (element.table); imagens são baixadas autenticadas.
 */
import { useMemo, type CSSProperties } from 'react'
import { FileSpreadsheet, ImageIcon } from 'lucide-react'
import { useAttachmentImage } from '@/hooks/useSlideEditor'
import { COLORS, DESIGN_WIDTH, type SlideDef, type SlideElement } from './slideLayout'

function ImageBox({ attachmentId }: { attachmentId?: string }) {
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

function TableBox({ element, scale }: { element: SlideElement; scale: number }) {
  const table = element.table
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

function ShapeBox({ element }: { element: SlideElement }) {
  const stroke = element.color ?? COLORS.brand
  const width = element.stroke_width ?? 2
  if (element.shape === 'line') {
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

function StaticElement({ element, scale }: { element: SlideElement; scale: number }) {
  const style: CSSProperties = {
    position: 'absolute',
    left: `${element.x * 100}%`,
    top: `${element.y * 100}%`,
    width: `${Math.max(element.w, element.shape === 'line' ? 0.002 : 0) * 100}%`,
    height: `${Math.max(element.h, element.shape === 'line' ? 0.002 : 0) * 100}%`,
  }
  if (element.type === 'image') {
    return (
      <div style={style}>
        <ImageBox attachmentId={element.attachment_id} />
      </div>
    )
  }
  if (element.type === 'table') {
    return (
      <div style={style}>
        <TableBox element={element} scale={scale} />
      </div>
    )
  }
  if (element.type === 'shape') {
    return (
      <div style={style}>
        <ShapeBox element={element} />
      </div>
    )
  }
  if (element.binding) return null // conteúdo de IA (fora do MVP) — nada a exibir
  return (
    <div
      style={{
        ...style,
        fontSize: element.font_size * scale,
        fontWeight: element.bold ? 700 : 400,
        textAlign: element.align ?? 'left',
        color: element.color ?? COLORS.dark,
        lineHeight: 1.25,
        overflow: 'hidden',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}
    >
      {element.text}
    </div>
  )
}

export interface StaticSlidePageProps {
  slide: SlideDef
  /** Largura em px na tela (a escala das fontes deriva dela). */
  width: number
  className?: string
}

/** Uma página 16:9 do layout, fiel ao que vai para o PPT. */
export function StaticSlidePage({ slide, width, className }: StaticSlidePageProps) {
  const scale = width / DESIGN_WIDTH
  const elements = useMemo(() => slide.elements ?? [], [slide])
  return (
    <div
      className={`relative overflow-hidden rounded-lg border border-border bg-white shadow-card ${className ?? ''}`}
      style={{ width, height: width * (9 / 16) }}
    >
      {elements.map(el => (
        <StaticElement key={el.id} element={el} scale={scale} />
      ))}
    </div>
  )
}
