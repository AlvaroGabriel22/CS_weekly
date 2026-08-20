/**
 * Formatação por TRECHO dentro de uma caixa de texto.
 *
 * Por que existe: no editor, negrito/corpo/fonte/cor valem para a caixa
 * inteira. O usuário quer poder destacar só uma palavra — e isso não pode
 * custar a compatibilidade do que já existe. Daí o modelo:
 *
 * - `element.text` continua sendo o texto corrido, sempre. É o que a tradução,
 *   a medição de encaixe e o renderizador antigo leem.
 * - `element.runs` é OPCIONAL e só aparece quando há mais de um formato na
 *   caixa. Um deck sem formatação parcial sai byte a byte como antes.
 *
 * Todas as funções aqui são puras: recebem trechos e devolvem trechos novos.
 * A regra que evita o modelo inchar é a normalização — trechos vazios somem e
 * vizinhos com o mesmo formato viram um só. Sem isso, cada clique de negrito
 * deixaria um trecho a mais para sempre.
 */
import type { SlideElement, TextRun } from './slideLayout'

/** Atributos de formatação de um trecho (tudo menos o texto). */
export type RunFormat = Omit<TextRun, 'text'>

const FORMAT_KEYS = ['bold', 'italic', 'font_size', 'font_family', 'color'] as const

function formatOf(run: TextRun): RunFormat {
  const { text: _text, ...format } = run
  return format
}

function sameFormat(a: TextRun, b: TextRun): boolean {
  return FORMAT_KEYS.every(key => (a[key] ?? null) === (b[key] ?? null))
}

/** Texto corrido dos trechos — o que vai para `element.text`. */
export function runsText(runs: TextRun[]): string {
  return runs.map(run => run.text).join('')
}

/**
 * Junta vizinhos de mesmo formato e descarta os vazios.
 *
 * Devolve `[]` para uma caixa sem texto: quem chama decide se isso vira
 * "elemento sem runs" (o caso simples) ou um trecho vazio.
 */
export function normalizeRuns(runs: TextRun[]): TextRun[] {
  const out: TextRun[] = []
  for (const run of runs) {
    if (!run.text) continue
    const last = out[out.length - 1]
    if (last && sameFormat(last, run)) last.text += run.text
    else out.push({ ...run })
  }
  return out
}

/**
 * Trechos do elemento, sempre — mesmo quando ele não tem `runs`.
 *
 * A caixa sem formatação parcial vira UM trecho sem atributos próprios: assim
 * o resto do código trabalha com uma estrutura só, e o formato do elemento
 * segue valendo por herança na hora de renderizar.
 */
export function elementRuns(element: SlideElement): TextRun[] {
  const text = element.text ?? ''
  const runs = element.runs
  if (!runs || runs.length === 0) return text ? [{ text }] : []
  // `text` é a fonte da verdade: se os dois divergirem (edição por um caminho
  // que não conhece runs), o texto corrido vence e a formatação parcial cai.
  return runsText(runs) === text ? normalizeRuns(runs) : text ? [{ text }] : []
}

/**
 * Devolve o patch a aplicar no elemento para os trechos informados.
 *
 * Quando sobra um único trecho sem formato próprio, `runs` é REMOVIDO — a
 * caixa volta a ser o caso simples em vez de carregar uma estrutura inútil.
 */
export function runsPatch(runs: TextRun[]): Partial<SlideElement> {
  const limpos = normalizeRuns(runs)
  const text = runsText(limpos)
  const semFormato = Object.values(formatOf(limpos[0] ?? { text: '' }))
    .every(value => value === undefined)
  const trivial = limpos.length <= 1 && semFormato
  return { text, runs: trivial ? undefined : limpos }
}

/** Corta os trechos no deslocamento `at` (em caracteres do texto corrido). */
function splitAt(runs: TextRun[], at: number): TextRun[] {
  const out: TextRun[] = []
  let cursor = 0
  for (const run of runs) {
    const end = cursor + run.text.length
    if (at > cursor && at < end) {
      const corte = at - cursor
      out.push({ ...run, text: run.text.slice(0, corte) })
      out.push({ ...run, text: run.text.slice(corte) })
    } else {
      out.push({ ...run })
    }
    cursor = end
  }
  return out
}

/**
 * Aplica `format` ao intervalo [start, end) do texto corrido.
 *
 * `undefined` num campo do patch REMOVE o atributo do trecho (é assim que
 * "desnegritar" volta a herdar o formato da caixa em vez de fixar `false`).
 */
export function applyFormatToRange(
  runs: TextRun[],
  start: number,
  end: number,
  format: RunFormat,
): TextRun[] {
  if (end <= start) return runs
  const cortados = splitAt(splitAt(runs, start), end)
  const out: TextRun[] = []
  let cursor = 0
  for (const run of cortados) {
    const fim = cursor + run.text.length
    if (cursor >= start && fim <= end) {
      // O spread já grava os campos do patch; os pedidos como `undefined`
      // (ex.: tirar o negrito) precisam SAIR do trecho, para voltar a herdar
      // o formato da caixa em vez de fixar um valor.
      const novo: TextRun = { ...run, ...format }
      for (const key of FORMAT_KEYS) {
        if (key in format && format[key] === undefined) delete novo[key]
      }
      out.push(novo)
    } else {
      out.push(run)
    }
    cursor = fim
  }
  return normalizeRuns(out)
}

/**
 * Troca o texto do intervalo mantendo o formato do trecho onde ele começa.
 *
 * É o que a tradução de uma seleção usa: o texto muda, o destaque que o
 * usuário tinha aplicado ali continua.
 */
export function replaceRange(
  runs: TextRun[],
  start: number,
  end: number,
  replacement: string,
): TextRun[] {
  const cortados = splitAt(splitAt(runs, start), end)
  const out: TextRun[] = []
  let cursor = 0
  let inserido = false
  for (const run of cortados) {
    const fim = cursor + run.text.length
    const dentro = cursor >= start && fim <= end && fim > cursor
    if (dentro) {
      if (!inserido) {
        out.push({ ...run, text: replacement })
        inserido = true
      }
    } else {
      out.push(run)
    }
    cursor = fim
  }
  if (!inserido) {
    // Seleção vazia (start === end): insere no ponto, herdando o trecho anterior.
    const antes = out.filter((_, index) => index < out.length)
    let posicao = 0
    let alvo = antes.length
    for (let index = 0; index < antes.length; index += 1) {
      posicao += antes[index].text.length
      if (posicao >= start) { alvo = index + 1; break }
    }
    const modelo = antes[alvo - 1]
    out.splice(alvo, 0, { ...(modelo ? formatOf(modelo) : {}), text: replacement })
  }
  return normalizeRuns(out)
}

/**
 * Reaplica os trechos depois de o usuário editar o TEXTO da caixa.
 *
 * Sem isto, corrigir uma vírgula apagaria o negrito feito antes: o texto novo
 * não bate com os trechos e a formatação parcial inteira cairia. Comparamos o
 * começo e o fim iguais e tratamos só o miolo como substituição — o que ficou
 * fora da edição mantém o formato que tinha.
 */
export function applyTextEdit(runs: TextRun[], oldText: string, newText: string): TextRun[] {
  if (oldText === newText) return runs
  if (!runs.length) return newText ? [{ text: newText }] : []

  let prefixo = 0
  const maximo = Math.min(oldText.length, newText.length)
  while (prefixo < maximo && oldText[prefixo] === newText[prefixo]) prefixo += 1

  let sufixo = 0
  while (
    sufixo < maximo - prefixo &&
    oldText[oldText.length - 1 - sufixo] === newText[newText.length - 1 - sufixo]
  ) {
    sufixo += 1
  }

  return replaceRange(
    runs,
    prefixo,
    oldText.length - sufixo,
    newText.slice(prefixo, newText.length - sufixo),
  )
}

/**
 * Formato COMUM ao intervalo — o que a barra de ferramentas deve mostrar.
 *
 * Campo com valores diferentes ao longo da seleção volta `undefined`: o botão
 * fica neutro em vez de mentir que a seleção inteira está em negrito.
 */
export function formatOfRange(runs: TextRun[], start: number, end: number): RunFormat {
  const comum: RunFormat = {}
  let cursor = 0
  let primeiro = true
  for (const run of runs) {
    const fim = cursor + run.text.length
    const intersecta = cursor < end && fim > start
    if (intersecta) {
      const format = formatOf(run)
      if (primeiro) {
        Object.assign(comum, format)
        primeiro = false
      } else {
        for (const key of FORMAT_KEYS) {
          if ((comum[key] ?? null) !== (format[key] ?? null)) delete comum[key]
        }
      }
    }
    cursor = fim
  }
  return comum
}
