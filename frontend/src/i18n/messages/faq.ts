/**
 * Mensagens da área de FAQ / Suporte (pt/en/ko).
 */
import { defineMessages } from '@/i18n'

export const FAQ = defineMessages({
  // Navegação + título
  nav: { pt: 'Suporte', en: 'Support', ko: '지원' },
  title: { pt: 'Suporte', en: 'Support', ko: '지원' },

  // Formulário de abertura
  formTitle: { pt: 'Relatar problema', en: 'Report an issue', ko: '문제 신고' },
  fieldTitle: { pt: 'Título', en: 'Title', ko: '제목' },
  fieldTitlePh: { pt: 'Título', en: 'Title', ko: '제목' },
  fieldDescription: { pt: 'Descrição', en: 'Description', ko: '설명' },
  fieldDescriptionPh: { pt: 'Detalhes', en: 'Details', ko: '상세 내용' },
  submit: { pt: 'Enviar', en: 'Send', ko: '보내기' },
  submitting: { pt: 'Enviando…', en: 'Sending…', ko: '보내는 중…' },
  visibilityNote: {
    pt: 'Visível a todos. Enviado por e-mail aos administradores.',
    en: 'Visible to everyone. Emailed to admins.',
    ko: '모두에게 표시됩니다. 관리자에게 이메일로 전송됩니다.',
  },
  created: { pt: 'Enviado.', en: 'Sent.', ko: '전송됨.' },

  // Lista de solicitações
  listTitle: { pt: 'Solicitações', en: 'Requests', ko: '요청' },
  empty: { pt: 'Nenhuma solicitação', en: 'No requests', ko: '요청 없음' },
  statusOpen: { pt: 'Aberta', en: 'Open', ko: '열림' },
  statusClosed: { pt: 'Fechada', en: 'Closed', ko: '닫힘' },
  adminResponse: { pt: 'Resposta', en: 'Response', ko: '답변' },
  mine: { pt: 'Você', en: 'You', ko: '나' },

  // Resposta do admin
  answerPh: { pt: 'Resposta', en: 'Response', ko: '답변' },
  answerAndClose: { pt: 'Responder e fechar', en: 'Answer & close', ko: '답변 후 닫기' },
  answering: { pt: 'Enviando…', en: 'Sending…', ko: '보내는 중…' },
  answered: { pt: 'Respondido.', en: 'Answered.', ko: '답변 완료.' },

  // Destinatários dos e-mails
  notifyTitle: { pt: 'Quem recebe os e-mails', en: 'Who gets the emails', ko: '이메일 수신자' },
  notifyEmployeeIdPh: { pt: 'Matrícula', en: 'Employee ID', ko: '사번' },
  notifyEmpty: { pt: 'Ninguém cadastrado', en: 'Nobody added', ko: '등록된 사람 없음' },
  notifyAdded: { pt: 'Adicionado.', en: 'Added.', ko: '추가됨.' },
  notifyRemoved: { pt: 'Removido.', en: 'Removed.', ko: '삭제됨.' },
  remove: { pt: 'Remover', en: 'Remove', ko: '삭제' },
})
