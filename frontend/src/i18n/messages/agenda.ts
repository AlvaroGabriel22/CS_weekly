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
})
