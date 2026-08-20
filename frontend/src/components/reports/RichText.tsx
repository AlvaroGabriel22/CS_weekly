/**
 * Desenha uma caixa de texto respeitando a formatação por TRECHO.
 *
 * Fica num arquivo próprio porque as duas telas precisam dele e precisam
 * concordar: o editor (o que o usuário monta) e a pré-visualização estática (o
 * que ele confere antes de gerar). Divergir aqui é prometer um PPT diferente
 * do que sai.
 *
 * Só o que o trecho define é escrito no `span`; o resto herda do elemento —
 * é a mesma herança que o backend aplica ao montar os runs do .pptx.
 */
import type { CSSProperties } from 'react'

import { elementRuns } from './richText'
import { fontStack, type SlideElement, type TextRun } from './slideLayout'

function runStyle(run: TextRun, scale: number): CSSProperties {
  const style: CSSProperties = {}
  if (run.bold !== undefined) style.fontWeight = run.bold ? 700 : 400
  if (run.italic !== undefined) style.fontStyle = run.italic ? 'italic' : 'normal'
  if (run.font_size !== undefined) style.fontSize = run.font_size * scale
  if (run.font_family !== undefined) style.fontFamily = fontStack(run.font_family)
  if (run.color !== undefined) style.color = run.color
  return style
}

export function RichText({ element, scale }: { element: SlideElement; scale: number }) {
  // Caso simples (a esmagadora maioria): sem trechos, o texto vai cru e a
  // caixa inteira usa o formato do elemento.
  if (!element.runs?.length) return <>{element.text}</>
  return (
    <>
      {elementRuns(element).map((run, index) => (
        <span key={index} style={runStyle(run, scale)}>
          {run.text}
        </span>
      ))}
    </>
  )
}
