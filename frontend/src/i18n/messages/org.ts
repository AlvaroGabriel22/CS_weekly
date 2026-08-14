/**
 * Mensagens da área de departamentos/organograma/colegas e do SlideViewer.
 * Compartilhadas (nav, ações, estados) ficam em COMMON — não duplique aqui.
 */
import { defineMessages } from '@/i18n'

export const ORG = defineMessages({
  // Departamentos
  person: { pt: '1 pessoa', en: '1 person', ko: '1명' },
  people: { pt: '{n} pessoas', en: '{n} people', ko: '{n}명' },
  sectorNotFound: { pt: 'Setor não encontrado', en: 'Sector not found', ko: '부서 없음' },
  emptySector: { pt: 'Ninguém aqui', en: 'Nobody here', ko: '아무도 없음' },
  seeDepartments: { pt: 'Ver departamentos', en: 'View departments', ko: '부서 보기' },
  orgChart: { pt: 'Organograma', en: 'Org chart', ko: '조직도' },

  // Organograma / pessoas
  restricted: { pt: 'Acesso restrito', en: 'Restricted access', ko: '접근 제한' },
  viewWeeklysOf: { pt: 'Ver weeklys de {name}', en: 'View {name}’s weeklys', ko: '{name} 주간 보고 보기' },

  // Colega / weeklys
  colleagueNotFound: { pt: 'Colega não encontrado', en: 'Colleague not found', ko: '동료 없음' },
  year: { pt: 'Ano', en: 'Year', ko: '연도' },
  weeksOfYear: { pt: 'Semanas do ano', en: 'Weeks of the year', ko: '연간 주' },
  version: { pt: 'v{n}', en: 'v{n}', ko: 'v{n}' },
  noWeeklys: { pt: 'Sem weeklys', en: 'No weeklys', ko: '주간 보고 없음' },
  noWeeklyThisWeek: { pt: 'Sem weekly na {week}', en: 'No weekly in {week}', ko: '{week} 보고 없음' },
  futureWeek: { pt: 'Semana futura', en: 'Future week', ko: '미래 주' },
  nothingPublished: { pt: 'Nada publicado', en: 'Nothing published', ko: '게시 없음' },
  downloadStarted: { pt: 'Download iniciado.', en: 'Download started.', ko: '다운로드 시작.' },

  // Status de weekly
  statusDraft: { pt: 'Rascunho', en: 'Draft', ko: '초안' },
  statusGenerating: { pt: 'Gerando…', en: 'Generating…', ko: '생성 중…' },
  statusCompleted: { pt: 'Concluído', en: 'Completed', ko: '완료' },
  statusFailed: { pt: 'Falhou', en: 'Failed', ko: '실패' },

  // SlideViewer
  presentation: { pt: 'Apresentação', en: 'Presentation', ko: '프레젠테이션' },
  by: { pt: 'por {name}', en: 'by {name}', ko: '{name} 작성' },
  overview: { pt: 'Visão geral', en: 'Overview', ko: '개요' },
  summary: { pt: 'Resumo', en: 'Summary', ko: '요약' },
  highlights: { pt: 'Destaques', en: 'Highlights', ko: '하이라이트' },
  activityOf: { pt: 'Atividade {i} de {n}', en: 'Activity {i} of {n}', ko: '활동 {i}/{n}' },
  untitled: { pt: 'Sem título', en: 'Untitled', ko: '제목 없음' },
  impact: { pt: 'Impacto', en: 'Impact', ko: '영향' },
  facts: { pt: 'Fatos', en: 'Facts', ko: '사실' },
  actions: { pt: 'Ações', en: 'Actions', ko: '조치' },
  noDetails: { pt: 'Sem detalhes.', en: 'No details.', ko: '세부 정보 없음.' },
  indicators: { pt: 'Indicadores', en: 'Indicators', ko: '지표' },
  kpis: { pt: 'KPIs', en: 'KPIs', ko: 'KPI' },
  closing: { pt: 'Fechamento', en: 'Closing', ko: '마무리' },
  conclusions: { pt: 'Conclusões', en: 'Conclusions', ko: '결론' },
  nextSteps: { pt: 'Próximos passos', en: 'Next steps', ko: '다음 단계' },
  prevSlide: { pt: 'Slide anterior', en: 'Previous slide', ko: '이전 슬라이드' },
  nextSlide: { pt: 'Próximo slide', en: 'Next slide', ko: '다음 슬라이드' },
  keysHint: { pt: '← → navegar · Esc fechar', en: '← → navigate · Esc close', ko: '← → 이동 · Esc 닫기' },

  // Copiloto do gestor (IA)
  rollupBtn: { pt: 'Resumo da semana (IA)', en: 'Week summary (AI)', ko: '주간 요약 (AI)' },
  rollupTitle: { pt: 'Weekly do departamento', en: 'Department weekly', ko: '부서 위클리' },
  rollupGenerate: { pt: 'Gerar resumo', en: 'Generate summary', ko: '요약 생성' },
  rollupRegenerate: { pt: 'Regenerar', en: 'Regenerate', ko: '다시 생성' },
  rollupGenerating: { pt: 'Analisando a semana…', en: 'Analyzing the week…', ko: '주간 분석 중…' },
  rollupGeneratingHint: { pt: 'Pode levar alguns minutos.', en: 'May take a few minutes.', ko: '몇 분 걸릴 수 있음.' },
  rollupEmpty: { pt: 'Ainda sem resumo', en: 'No summary yet', ko: '요약 없음' },
  rollupHighlights: { pt: 'Destaques', en: 'Highlights', ko: '하이라이트' },
  rollupKpis: { pt: 'KPIs', en: 'KPIs', ko: 'KPI' },
  rollupRisks: { pt: 'Riscos', en: 'Risks', ko: '리스크' },
  rollupTeam: { pt: 'Por pessoa', en: 'By person', ko: '구성원별' },
  rollupNextSteps: { pt: 'Próximos passos', en: 'Next steps', ko: '다음 단계' },
  rollupHasWeekly: { pt: 'Weekly entregue', en: 'Weekly delivered', ko: '위클리 제출' },
  rollupNoWeekly: { pt: 'Sem weekly', en: 'No weekly', ko: '위클리 없음' },
  rollupGeneratedAt: { pt: 'Gerado em {date}', en: 'Generated {date}', ko: '{date} 생성' },
})
