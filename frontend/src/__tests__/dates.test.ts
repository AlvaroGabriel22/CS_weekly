import { describe, it, expect } from 'vitest'
import {
  mondayOf,
  firstMonday,
  getWeekRef,
  getWeekNumber,
  weeksInYear,
  mondayOfWeek,
  addWeeks,
  getWeekDays,
  getWeekDaysOf,
  formatDateBR,
  formatDateIso,
  parseIsoDate,
  isSameDay,
  weekLabel,
} from '@/lib/dates'

/**
 * Convenção de semanas da EMPRESA (não ISO 8601):
 * W1 = semana que começa na primeira segunda-feira de janeiro.
 * Âncora oficial: 10/08/2026 é SEGUNDA-FEIRA da W32.
 */
describe('Semanas — convenção da empresa', () => {
  it('âncora: 10/08/2026 (segunda) está na W32 de 2026', () => {
    const anchor = new Date(2026, 7, 10)
    expect(anchor.getDay()).toBe(1) // segunda-feira
    expect(getWeekRef(anchor)).toEqual({ year: 2026, week: 32 })
    expect(getWeekNumber(anchor)).toBe(32)
  })

  it('primeira segunda de 2026 é 05/01 e inicia a W1', () => {
    const fm = firstMonday(2026)
    expect(formatDateIso(fm)).toBe('2026-01-05')
    expect(getWeekRef(fm)).toEqual({ year: 2026, week: 1 })
  })

  it('dias antes da primeira segunda pertencem ao ano anterior', () => {
    // 01–04/01/2026 vêm antes da primeira segunda → última semana de 2025
    expect(getWeekRef(new Date(2026, 0, 4))).toEqual({ year: 2025, week: 52 })
    expect(getWeekRef(new Date(2026, 0, 1))).toEqual({ year: 2025, week: 52 })
  })

  it('weeksInYear retorna 52 ou 53 conforme o calendário', () => {
    expect(weeksInYear(2025)).toBe(52)
    expect(weeksInYear(2026)).toBe(52)
    expect(weeksInYear(2029)).toBe(53) // ano longo na convenção da empresa
  })

  it('mondayOfWeek é o inverso de getWeekRef', () => {
    const monday = mondayOfWeek({ year: 2026, week: 32 })
    expect(formatDateIso(monday)).toBe('2026-08-10')
    for (const week of [1, 20, 32, 52]) {
      expect(getWeekRef(mondayOfWeek({ year: 2026, week }))).toEqual({ year: 2026, week })
    }
  })

  it('addWeeks cruza a virada de ano corretamente', () => {
    expect(addWeeks({ year: 2026, week: 52 }, 1)).toEqual({ year: 2027, week: 1 })
    expect(addWeeks({ year: 2027, week: 1 }, -1)).toEqual({ year: 2026, week: 52 })
    expect(addWeeks({ year: 2026, week: 32 }, 0)).toEqual({ year: 2026, week: 32 })
  })
})

describe('getWeekDays / getWeekDaysOf', () => {
  it('retorna 7 dias de segunda a domingo para qualquer dia da semana', () => {
    // 07/08/2026 é sexta-feira; a semana vai de 03/08 (seg) a 09/08 (dom)
    const days = getWeekDays(new Date(2026, 7, 7))
    expect(days).toHaveLength(7)
    expect(formatDateIso(days[0])).toBe('2026-08-03')
    expect(days[0].getDay()).toBe(1)
    expect(formatDateIso(days[6])).toBe('2026-08-09')
    expect(days[6].getDay()).toBe(0)
  })

  it('entrada no domingo permanece na mesma semana', () => {
    const days = getWeekDays(new Date(2026, 7, 9))
    expect(formatDateIso(days[0])).toBe('2026-08-03')
    expect(formatDateIso(days[6])).toBe('2026-08-09')
  })

  it('cruza fronteira de mês', () => {
    // 31/08/2026 é segunda; a semana termina em 06/09
    const days = getWeekDays(new Date(2026, 7, 31))
    expect(formatDateIso(days[0])).toBe('2026-08-31')
    expect(formatDateIso(days[6])).toBe('2026-09-06')
  })

  it('getWeekDaysOf(W32/2026) começa em 10/08', () => {
    const days = getWeekDaysOf({ year: 2026, week: 32 })
    expect(formatDateIso(days[0])).toBe('2026-08-10')
    expect(formatDateIso(days[6])).toBe('2026-08-16')
  })
})

describe('mondayOf', () => {
  it('retorna a própria data quando já é segunda', () => {
    expect(formatDateIso(mondayOf(new Date(2026, 7, 10)))).toBe('2026-08-10')
  })

  it('retorna a segunda anterior para domingo', () => {
    expect(formatDateIso(mondayOf(new Date(2026, 7, 16)))).toBe('2026-08-10')
  })
})

describe('formatação e parsing local (fuso de Manaus, UTC-4)', () => {
  it('formatDateIso usa a data LOCAL (nunca toISOString)', () => {
    // 00:30 local: toISOString retrocederia o dia em UTC-4
    expect(formatDateIso(new Date(2026, 7, 10, 0, 30))).toBe('2026-08-10')
  })

  it('parseIsoDate interpreta AAAA-MM-DD como data local', () => {
    const d = parseIsoDate('2026-08-10')
    expect(d.getFullYear()).toBe(2026)
    expect(d.getMonth()).toBe(7)
    expect(d.getDate()).toBe(10)
    expect(d.getDay()).toBe(1)
  })

  it('parseIsoDate e formatDateIso são inversos', () => {
    expect(formatDateIso(parseIsoDate('2026-12-31'))).toBe('2026-12-31')
  })

  it('formatDateBR produz DD/MM/AAAA', () => {
    expect(formatDateBR(new Date(2026, 7, 7))).toMatch(/07\/08\/2026/)
  })

  it('weekLabel produz "W32"', () => {
    expect(weekLabel({ year: 2026, week: 32 })).toBe('W32')
  })
})

describe('isSameDay', () => {
  it('ignora horário', () => {
    expect(isSameDay(new Date(2026, 7, 7, 10, 30), new Date(2026, 7, 7, 15, 45))).toBe(true)
    expect(isSameDay(new Date(2026, 7, 7), new Date(2026, 7, 8))).toBe(false)
  })
})
