/**
 * Utilidades de data do QWI — CONVENÇÃO DE SEMANAS DA EMPRESA (não é ISO 8601).
 *
 * Regras:
 * - A semana começa na SEGUNDA-FEIRA.
 * - W1 do ano Y é a semana (seg–dom) que CONTÉM o dia 1º de janeiro de Y —
 *   mesmo que comece em dezembro do ano anterior.
 * - O ano de uma semana é o ano do seu DOMINGO: 29/12/2025–04/01/2026 = W1/2026.
 *
 * Âncora de validação: 10/08/2026 é SEGUNDA-FEIRA da W33.
 * O backend usa a mesma regra em app/core/dates.py — mantenha os dois em sincronia.
 *
 * Todas as funções operam em datas LOCAIS (nunca toISOString em datas de agenda,
 * que deslocaria o dia em fusos negativos como o de Manaus, UTC-4).
 */

export interface WeekRef {
  year: number
  week: number
}

const DAY_MS = 24 * 60 * 60 * 1000

function atMidnight(date: Date): Date {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return d
}

/** Segunda-feira da semana que contém a data (getDay: 0=dom … 6=sáb). */
export function mondayOf(date: Date): Date {
  const d = atMidnight(date)
  const shift = (d.getDay() + 6) % 7 // seg=0 … dom=6
  d.setDate(d.getDate() - shift)
  return d
}

/** Segunda-feira da W1: a segunda da semana que CONTÉM 1º/jan (pode cair
 *  em dezembro do ano anterior). Nome mantido por compatibilidade. */
export function firstMonday(year: number): Date {
  return mondayOf(new Date(year, 0, 1))
}

/** Semana (convenção da empresa) que contém a data. */
export function getWeekRef(date: Date): WeekRef {
  const monday = mondayOf(date)
  // O ano da semana é o ano do DOMINGO: a semana que contém 1º/jan
  // pertence ao ano novo (é a W1 dele).
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  const year = sunday.getFullYear()
  const week = Math.round((monday.getTime() - firstMonday(year).getTime()) / (7 * DAY_MS)) + 1
  return { year, week }
}

/** Semana atual (data local do navegador). */
export function currentWeekRef(): WeekRef {
  return getWeekRef(new Date())
}

/** Quantidade de semanas no ano (52 ou 53). */
export function weeksInYear(year: number): number {
  return Math.round((firstMonday(year + 1).getTime() - firstMonday(year).getTime()) / (7 * DAY_MS))
}

/** Segunda-feira da semana indicada. */
export function mondayOfWeek(ref: WeekRef): Date {
  const fm = firstMonday(ref.year)
  fm.setDate(fm.getDate() + (ref.week - 1) * 7)
  return fm
}

/** Soma n semanas (n pode ser negativo), cruzando viradas de ano corretamente. */
export function addWeeks(ref: WeekRef, n: number): WeekRef {
  const monday = mondayOfWeek(ref)
  monday.setDate(monday.getDate() + n * 7)
  return getWeekRef(monday)
}

/** Os 7 dias (seg→dom) da semana que contém a data. */
export function getWeekDays(date: Date): Date[] {
  const monday = mondayOf(date)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return d
  })
}

/** Os 7 dias (seg→dom) de uma semana referenciada. */
export function getWeekDaysOf(ref: WeekRef): Date[] {
  return getWeekDays(mondayOfWeek(ref))
}

/** Compat: número da semana da data (usar getWeekRef quando precisar do ano). */
export function getWeekNumber(date: Date): number {
  return getWeekRef(date).week
}

// ── Formatação (pt-BR) ─────────────────────────────────────────────────────

const MONTHS_SHORT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
const MONTHS_LONG = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]
export const WEEKDAYS_SHORT = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
export const WEEKDAYS_LONG = [
  'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
  'Sexta-feira', 'Sábado', 'Domingo',
]

/** Nome do dia (seg→dom) para uma data. */
export function weekdayLabel(date: Date, long = false): string {
  const idx = (date.getDay() + 6) % 7
  return (long ? WEEKDAYS_LONG : WEEKDAYS_SHORT)[idx]
}

export function getMonthName(month: number, long = false): string {
  return long ? MONTHS_LONG[month] : MONTHS_SHORT[month]
}

/** DD/MM/AAAA */
export function formatDateBR(date: Date): string {
  return date.toLocaleDateString('pt-BR', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

/** "10 de agosto de 2026" */
export function formatDateLong(date: Date): string {
  return `${date.getDate()} de ${MONTHS_LONG[date.getMonth()]} de ${date.getFullYear()}`
}

/**
 * AAAA-MM-DD em data LOCAL (para enviar à API).
 * NUNCA usar toISOString aqui — deslocaria o dia em UTC-4.
 */
export function formatDateIso(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** Interpreta "AAAA-MM-DD" como data LOCAL (new Date('AAAA-MM-DD') seria UTC). */
export function parseIsoDate(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** "10 – 16 ago 2026" (intervalo seg→dom da semana). */
export function weekRangeLabel(ref: WeekRef): string {
  const days = getWeekDaysOf(ref)
  const start = days[0]
  const end = days[6]
  const sameMonth = start.getMonth() === end.getMonth()
  const startLabel = sameMonth ? `${start.getDate()}` : `${start.getDate()} ${MONTHS_SHORT[start.getMonth()]}`
  return `${startLabel} – ${end.getDate()} ${MONTHS_SHORT[end.getMonth()]} ${end.getFullYear()}`
}

/** "W32" */
export function weekLabel(ref: WeekRef): string {
  return `W${ref.week}`
}

export function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

export function isToday(date: Date): boolean {
  return isSameDay(date, new Date())
}

export function isSameWeek(a: WeekRef, b: WeekRef): boolean {
  return a.year === b.year && a.week === b.week
}

/**
 * Matriz do mês para o calendário: linhas = semanas (seg→dom).
 * Inclui dias dos meses vizinhos para completar as linhas.
 */
export function monthMatrix(year: number, month: number): Date[][] {
  const first = new Date(year, month, 1)
  const last = new Date(year, month + 1, 0)
  const start = mondayOf(first)
  const rows: Date[][] = []
  const cursor = new Date(start)
  while (cursor <= last || rows.length === 0 || (cursor.getDay() + 6) % 7 !== 0) {
    if ((cursor.getDay() + 6) % 7 === 0) rows.push([])
    rows[rows.length - 1].push(new Date(cursor))
    cursor.setDate(cursor.getDate() + 1)
    if (rows.length > 6 && (cursor.getDay() + 6) % 7 === 0) break
  }
  return rows
}
