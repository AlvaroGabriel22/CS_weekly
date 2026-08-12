/**
 * Mensagens da HomePage.
 */
import { defineMessages } from '@/i18n'

export const HOME = defineMessages({
  // Saudação
  goodMorning: { pt: 'Bom dia', en: 'Good morning', ko: '좋은 아침입니다' },
  goodAfternoon: { pt: 'Boa tarde', en: 'Good afternoon', ko: '좋은 오후입니다' },
  goodEvening: { pt: 'Boa noite', en: 'Good evening', ko: '좋은 저녁입니다' },

  // Banner da semana
  weekN: { pt: 'Semana {n}', en: 'Week {n}', ko: '{n}주차' },
  weekDaysAria: { pt: 'Dias da semana', en: 'Days of the week', ko: '요일' },

  // Estatísticas
  summary: { pt: 'Resumo', en: 'Summary', ko: '요약' },
  statActivities: { pt: 'Atividades', en: 'Activities', ko: '활동' },
  statDays: { pt: 'Dias preenchidos', en: 'Days filled', ko: '작성일' },
  statAttachments: { pt: 'Anexos', en: 'Attachments', ko: '첨부' },
  statWeekly: { pt: 'Weekly', en: 'Weekly', ko: '위클리' },
  weekComplete: { pt: 'Completa!', en: 'Complete!', ko: '완료!' },
  attachSub: { pt: '{i} imagens · {f} arquivos', en: '{i} images · {f} files', ko: '이미지 {i} · 파일 {f}' },
  generatedOn: { pt: 'Gerado em {date}', en: 'Generated {date}', ko: '{date} 생성' },

  // Status do weekly
  statusDraft: { pt: 'Rascunho', en: 'Draft', ko: '초안' },
  statusGenerating: { pt: 'Gerando', en: 'Generating', ko: '생성 중' },
  statusDone: { pt: 'Concluído', en: 'Done', ko: '완료' },
  statusFailed: { pt: 'Falhou', en: 'Failed', ko: '실패' },

  // Vazio
  emptyTitle: { pt: 'Semana vazia', en: 'Empty week', ko: '이번 주 활동 없음' },
  emptyDesc: { pt: 'Registre uma atividade.', en: 'Log an activity.', ko: '활동을 기록하세요.' },

  // Ações rápidas
  quickActions: { pt: 'Ações rápidas', en: 'Quick actions', ko: '빠른 작업' },
  actionLog: { pt: 'Registrar atividade', en: 'Log activity', ko: '활동 기록' },
  actionLogDesc: { pt: 'Direto na agenda', en: 'In your agenda', ko: '일정에서 바로' },
  actionWeekly: { pt: 'Gerar weekly', en: 'Generate weekly', ko: '위클리 생성' },
  actionWeeklyDesc: { pt: 'Relatório em PPT', en: 'PPT report', ko: 'PPT 보고서' },
  actionDeptsDesc: { pt: 'Organograma e weeklys', en: 'Org chart & weeklys', ko: '조직도와 위클리' },
})
