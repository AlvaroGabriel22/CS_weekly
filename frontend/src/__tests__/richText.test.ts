/**
 * Formatação por trecho (components/reports/richText.ts).
 *
 * O que estes testes protegem: o texto corrido e os trechos NUNCA podem
 * divergir (é o texto que o backend antigo e a tradução leem), e o modelo não
 * pode inchar a cada clique — trecho vazio some, vizinho igual funde.
 */
import { describe, expect, it } from 'vitest'

import {
  applyFormatToRange,
  applyTextEdit,
  elementRuns,
  formatOfRange,
  normalizeRuns,
  replaceRange,
  runsPatch,
  runsText,
} from '@/components/reports/richText'
import type { SlideElement } from '@/components/reports/slideLayout'

const el = (partial: Partial<SlideElement>): SlideElement => ({
  id: 'e1', type: 'text', x: 0, y: 0, w: 0.5, h: 0.2, font_size: 14, ...partial,
})

describe('elementRuns', () => {
  it('caixa sem runs vira um trecho único sem formato', () => {
    expect(elementRuns(el({ text: 'olá' }))).toEqual([{ text: 'olá' }])
  })

  it('caixa vazia não gera trecho', () => {
    expect(elementRuns(el({ text: '' }))).toEqual([])
  })

  it('usa os runs quando batem com o texto corrido', () => {
    const element = el({ text: 'ab', runs: [{ text: 'a', bold: true }, { text: 'b' }] })
    expect(elementRuns(element)).toEqual([{ text: 'a', bold: true }, { text: 'b' }])
  })

  it('runs divergentes do texto são descartados: o texto vence', () => {
    // Acontece quando o texto é editado por um caminho que não conhece runs.
    const element = el({ text: 'novo texto', runs: [{ text: 'antigo', bold: true }] })
    expect(elementRuns(element)).toEqual([{ text: 'novo texto' }])
  })
})

describe('normalizeRuns', () => {
  it('funde vizinhos de mesmo formato', () => {
    expect(normalizeRuns([{ text: 'a' }, { text: 'b' }])).toEqual([{ text: 'ab' }])
  })

  it('não funde formatos diferentes', () => {
    const runs = [{ text: 'a', bold: true }, { text: 'b' }]
    expect(normalizeRuns(runs)).toHaveLength(2)
  })

  it('descarta trechos vazios', () => {
    expect(normalizeRuns([{ text: '' }, { text: 'a' }, { text: '' }])).toEqual([{ text: 'a' }])
  })
})

describe('applyFormatToRange', () => {
  const runs = [{ text: 'Resultado: aprovado' }]

  it('aplica só ao intervalo selecionado', () => {
    const out = applyFormatToRange(runs, 11, 19, { bold: true })
    expect(out).toEqual([{ text: 'Resultado: ' }, { text: 'aprovado', bold: true }])
    expect(runsText(out)).toBe('Resultado: aprovado')
  })

  it('intervalo vazio não muda nada', () => {
    expect(applyFormatToRange(runs, 5, 5, { bold: true })).toEqual(runs)
  })

  it('cobrindo tudo, volta a um trecho só', () => {
    const out = applyFormatToRange(runs, 0, 19, { bold: true })
    expect(out).toEqual([{ text: 'Resultado: aprovado', bold: true }])
  })

  it('undefined REMOVE o atributo (volta a herdar da caixa)', () => {
    const negrito = [{ text: 'abc', bold: true }]
    const out = applyFormatToRange(negrito, 0, 3, { bold: undefined })
    expect(out).toEqual([{ text: 'abc' }])
  })

  it('aplicar no meio parte em três', () => {
    const out = applyFormatToRange([{ text: 'abcde' }], 1, 3, { font_size: 20 })
    expect(out).toEqual([
      { text: 'a' }, { text: 'bc', font_size: 20 }, { text: 'de' },
    ])
  })

  it('não perde texto ao aplicar sobre trechos já formatados', () => {
    const inicial = applyFormatToRange([{ text: 'abcdef' }], 2, 4, { bold: true })
    const final = applyFormatToRange(inicial, 1, 5, { color: '#DC2626' })
    expect(runsText(final)).toBe('abcdef')
    expect(final.filter(r => r.bold)).toHaveLength(1)
  })
})

describe('formatOfRange', () => {
  const runs = [{ text: 'ab', bold: true }, { text: 'cd' }]

  it('seleção homogênea devolve o formato', () => {
    expect(formatOfRange(runs, 0, 2)).toEqual({ bold: true })
  })

  it('seleção mista não afirma nada sobre o campo divergente', () => {
    expect(formatOfRange(runs, 0, 4).bold).toBeUndefined()
  })
})

describe('replaceRange', () => {
  it('troca o texto preservando o formato do trecho', () => {
    const runs = [{ text: 'Olá ' }, { text: 'mundo', bold: true }]
    const out = replaceRange(runs, 4, 9, 'world')
    expect(out).toEqual([{ text: 'Olá ' }, { text: 'world', bold: true }])
  })

  it('trocar tudo mantém o texto novo inteiro', () => {
    const out = replaceRange([{ text: 'abc' }], 0, 3, 'xyz')
    expect(runsText(out)).toBe('xyz')
  })
})

describe('runsPatch', () => {
  it('caixa de formato único não guarda runs', () => {
    const patch = runsPatch([{ text: 'simples' }])
    expect(patch).toEqual({ text: 'simples', runs: undefined })
  })

  it('formatação parcial guarda runs junto com o texto corrido', () => {
    const patch = runsPatch([{ text: 'a' }, { text: 'b', bold: true }])
    expect(patch.text).toBe('ab')
    expect(patch.runs).toHaveLength(2)
  })

  it('texto e runs saem sempre coerentes', () => {
    const patch = runsPatch(applyFormatToRange([{ text: 'abcdef' }], 2, 4, { italic: true }))
    expect(patch.text).toBe(runsText(patch.runs!))
  })
})

describe('applyTextEdit', () => {
  const runs = [{ text: 'Olá ' }, { text: 'mundo', bold: true }, { text: '!' }]

  it('editar fora do trecho preserva a formatação', () => {
    const out = applyTextEdit(runs, 'Olá mundo!', 'Oi mundo!')
    expect(runsText(out)).toBe('Oi mundo!')
    expect(out.find(r => r.bold)?.text).toBe('mundo')
  })

  it('digitar no fim não mexe no que já estava formatado', () => {
    const out = applyTextEdit(runs, 'Olá mundo!', 'Olá mundo!!')
    expect(runsText(out)).toBe('Olá mundo!!')
    expect(out.find(r => r.bold)?.text).toBe('mundo')
  })

  it('apagar dentro do trecho encurta o trecho, sem perder o formato', () => {
    const out = applyTextEdit(runs, 'Olá mundo!', 'Olá mund!')
    expect(runsText(out)).toBe('Olá mund!')
    expect(out.find(r => r.bold)?.text).toBe('mund')
  })

  it('texto igual devolve os mesmos trechos', () => {
    expect(applyTextEdit(runs, 'Olá mundo!', 'Olá mundo!')).toBe(runs)
  })

  it('caixa esvaziada não deixa trecho para trás', () => {
    expect(applyTextEdit(runs, 'Olá mundo!', '')).toEqual([])
  })

  it('caixa que estava vazia aceita o texto novo', () => {
    expect(applyTextEdit([], '', 'novo')).toEqual([{ text: 'novo' }])
  })
})
