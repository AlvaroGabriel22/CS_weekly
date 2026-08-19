/**
 * Mensagens da AGENDA (calendário mensal + painel do dia).
 * Ações genéricas (Adicionar, Salvar, Excluir, Hoje…) vêm de COMMON — não duplicar.
 */
import { defineMessages } from '@/i18n'

export const AGENDA = defineMessages({
  // Página
  subtitle: { pt: 'Registre suas atividades', en: 'Log your activities', ko: '활동을 기록하세요' },

  // Calendário
  prevMonth: { pt: 'Mês anterior', en: 'Previous month', ko: '이전 달' },
  nextMonth: { pt: 'Próximo mês', en: 'Next month', ko: '다음 달' },
  selectWeek: { pt: 'Selecionar semana {week}', en: 'Select week {week}', ko: '{week}주 선택' },
  withActivities: { pt: 'com atividades', en: 'has activities', ko: '활동 있음' },

  // Painel do dia
  dayActivities: { pt: 'Atividades de {date}', en: 'Activities on {date}', ko: '{date} 활동' },
  oneActivity: { pt: '1 atividade', en: '1 activity', ko: '활동 1개' },
  manyActivities: { pt: '{n} atividades', en: '{n} activities', ko: '활동 {n}개' },
  emptyDay: { pt: 'Nada neste dia', en: 'Nothing this day', ko: '활동 없음' },

  // Formulário
  newActivity: { pt: 'Nova atividade', en: 'New activity', ko: '새 활동' },
  editActivity: { pt: 'Editar atividade', en: 'Edit activity', ko: '활동 편집' },
  titleLabel: { pt: 'Título', en: 'Title', ko: '제목' },
  detailsLabel: { pt: 'Detalhes', en: 'Details', ko: '상세' },
  detailsPlaceholder: { pt: 'Detalhes (opcional)', en: 'Details (optional)', ko: '상세 (선택)' },
  titleRequired: { pt: 'Título obrigatório.', en: 'Title required.', ko: '제목을 입력하세요.' },
  adding: { pt: 'Adicionando…', en: 'Adding…', ko: '추가 중…' },
  saving: { pt: 'Salvando…', en: 'Saving…', ko: '저장 중…' },

  // Toasts
  added: { pt: 'Adicionada.', en: 'Added.', ko: '추가됨' },
  saved: { pt: 'Salvo.', en: 'Saved.', ko: '저장됨' },
  deleted: { pt: 'Excluída.', en: 'Deleted.', ko: '삭제됨' },

  // Cartão da atividade
  activityOptions: { pt: 'Opções de “{title}”', en: 'Options for “{title}”', ko: '“{title}” 옵션' },
  includeInWeekly: { pt: 'Incluir no weekly', en: 'Include in weekly', ko: '위클리에 포함' },
  deleteConfirmTitle: { pt: 'Excluir atividade?', en: 'Delete activity?', ko: '활동을 삭제할까요?' },
  deleteConfirmDesc: {
    pt: '“{title}” será removida.',
    en: '“{title}” will be removed.',
    ko: '“{title}” 항목이 삭제됩니다.',
  },

  // Status
  statusDraft: { pt: 'Rascunho', en: 'Draft', ko: '초안' },
  statusPending: { pt: 'Pendente', en: 'Pending', ko: '대기' },
  statusInProgress: { pt: 'Em andamento', en: 'In progress', ko: '진행 중' },
  statusDone: { pt: 'Concluída', en: 'Done', ko: '완료' },

  // Anexos
  attach: { pt: 'Anexar', en: 'Attach', ko: '첨부' },
  uploading: { pt: 'Enviando…', en: 'Uploading…', ko: '업로드 중…' },
  attached: { pt: 'Anexado.', en: 'Attached.', ko: '첨부됨' },
  attachmentDeleted: { pt: 'Anexo excluído.', en: 'Attachment deleted.', ko: '첨부 삭제됨' },
  fileInvalid: { pt: '{name}: tipo inválido.', en: '{name}: invalid type.', ko: '{name}: 잘못된 형식' },
  fileTooLarge: { pt: '{name}: máx. 15MB.', en: '{name}: max 15MB.', ko: '{name}: 최대 15MB' },
  removeFile: { pt: 'Remover {name}', en: 'Remove {name}', ko: '{name} 제거' },
  deleteAttachment: { pt: 'Excluir {name}', en: 'Delete {name}', ko: '{name} 삭제' },
  confirmDeleteAttachment: { pt: 'Confirmar exclusão', en: 'Confirm deletion', ko: '삭제 확인' },
  rowsCount: { pt: '{n} linhas', en: '{n} rows', ko: '{n}행' },

  // Anexos: erro por arquivo (chip)
  fileTypeChip: { pt: 'Tipo não suportado.', en: 'Unsupported type.', ko: '지원하지 않는 형식' },
  fileSizeChip: { pt: 'Máx. 15MB.', en: 'Max 15MB.', ko: '최대 15MB' },
  uploadFailedOne: { pt: '1 anexo falhou.', en: '1 attachment failed.', ko: '첨부 1개 실패' },
  uploadFailedMany: { pt: '{n} anexos falharam.', en: '{n} attachments failed.', ko: '첨부 {n}개 실패' },
  retryFile: { pt: 'Reenviar {name}', en: 'Retry {name}', ko: '{name} 다시 전송' },

  // Analisar planilha com IA
  analyze: { pt: 'Analisar', en: 'Analyze', ko: '분석' },
  analyzeFile: { pt: 'Analisar {name}', en: 'Analyze {name}', ko: '{name} 분석' },
  analysisTitle: { pt: 'Analisar planilha', en: 'Analyze spreadsheet', ko: '스프레드시트 분석' },
  analysisSavedIntro: {
    pt: 'Usar uma análise que você já aprovou:',
    en: 'Use an analysis you already approved:',
    ko: '이미 승인한 분석 사용:',
  },
  analysisAsk: {
    pt: 'O que você quer desta planilha?',
    en: 'What do you want from this spreadsheet?',
    ko: '이 스프레드시트에서 무엇이 필요하세요?',
  },
  analysisPlaceholder: {
    pt: 'percentual de Aprovados sobre Inspecionados por Linha',
    en: 'percentage of Approved over Inspected by Line',
    ko: '라인별 검사 대비 합격 비율',
  },
  analysisLoading: {
    pt: 'Analisando sua planilha… pode levar até 2 minutos.',
    en: 'Analyzing your spreadsheet… this can take up to 2 minutes.',
    ko: '스프레드시트를 분석하는 중… 최대 2분 걸릴 수 있습니다.',
  },
  analysisAskRequired: {
    pt: 'Escreva o que você quer.',
    en: 'Tell me what you want.',
    ko: '원하는 내용을 적어주세요.',
  },
  analysisRetry: { pt: 'Tentar de novo', en: 'Try again', ko: '다시 시도' },
  analysisApprove: { pt: 'Aprovar e salvar', en: 'Approve and save', ko: '승인 후 저장' },
  analysisApproving: { pt: 'Salvando…', en: 'Saving…', ko: '저장 중…' },
  analysisDiscard: { pt: 'Descartar', en: 'Discard', ko: '버리기' },
  analysisApproved: { pt: 'Análise salva.', en: 'Analysis saved.', ko: '분석 저장됨' },
  analysisRecipeDeleted: { pt: 'Análise removida.', en: 'Analysis removed.', ko: '분석 삭제됨' },
  analysisDeleteRecipe: { pt: 'Excluir “{label}”', en: 'Delete “{label}”', ko: '“{label}” 삭제' },
  analysisColumnsTitle: { pt: 'Confirme as colunas', en: 'Confirm the columns', ko: '열을 확인하세요' },
  analysisRecalc: { pt: 'Recalcular', en: 'Recalculate', ko: '다시 계산' },
  analysisNumerator: { pt: 'Numerador', en: 'Numerator', ko: '분자' },
  analysisDenominator: { pt: 'Denominador', en: 'Denominator', ko: '분모' },
  analysisValue: { pt: 'Valor', en: 'Value', ko: '값' },
  analysisGroupBy: { pt: 'Agrupar por', en: 'Group by', ko: '그룹 기준' },
  analysisPickColumn: { pt: 'Escolha a coluna', en: 'Pick a column', ko: '열 선택' },
  analysisChart: { pt: 'Gráfico', en: 'Chart', ko: '차트' },
  analysisSaved: { pt: 'Salva', en: 'Saved', ko: '저장됨' },
  analysisCount: { pt: '{n} análises', en: '{n} analyses', ko: '분석 {n}건' },
  analysisPartial: {
    pt: 'Algumas análises não puderam ser calculadas',
    en: 'Some analyses could not be calculated',
    ko: '일부 분석을 계산하지 못했습니다',
  },
})
