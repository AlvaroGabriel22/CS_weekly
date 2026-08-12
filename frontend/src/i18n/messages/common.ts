/**
 * Mensagens COMPARTILHADAS (navegação, ações genéricas, estados).
 * Mensagens específicas de página ficam em src/i18n/messages/<área>.ts.
 */
import { defineMessages } from '@/i18n'

export const COMMON = defineMessages({
  // Navegação
  home: { pt: 'Início', en: 'Home', ko: '홈' },
  agenda: { pt: 'Agenda', en: 'Agenda', ko: '일정' },
  reports: { pt: 'Relatórios', en: 'Reports', ko: '보고서' },
  departments: { pt: 'Departamentos', en: 'Departments', ko: '부서' },
  profile: { pt: 'Perfil', en: 'Profile', ko: '프로필' },
  settings: { pt: 'Configurações', en: 'Settings', ko: '설정' },
  backToHome: { pt: 'Voltar ao início', en: 'Back to home', ko: '홈으로' },
  logout: { pt: 'Sair', en: 'Log out', ko: '로그아웃' },
  language: { pt: 'Idioma', en: 'Language', ko: '언어' },

  // Ações genéricas
  add: { pt: 'Adicionar', en: 'Add', ko: '추가' },
  save: { pt: 'Salvar', en: 'Save', ko: '저장' },
  cancel: { pt: 'Cancelar', en: 'Cancel', ko: '취소' },
  delete: { pt: 'Excluir', en: 'Delete', ko: '삭제' },
  edit: { pt: 'Editar', en: 'Edit', ko: '편집' },
  close: { pt: 'Fechar', en: 'Close', ko: '닫기' },
  confirm: { pt: 'Confirmar', en: 'Confirm', ko: '확인' },
  back: { pt: 'Voltar', en: 'Back', ko: '뒤로' },
  next: { pt: 'Avançar', en: 'Next', ko: '다음' },
  download: { pt: 'Baixar', en: 'Download', ko: '다운로드' },
  view: { pt: 'Visualizar', en: 'View', ko: '보기' },
  retry: { pt: 'Tentar novamente', en: 'Try again', ko: '다시 시도' },
  search: { pt: 'Buscar', en: 'Search', ko: '검색' },
  today: { pt: 'Hoje', en: 'Today', ko: '오늘' },
  all: { pt: 'Tudo', en: 'All', ko: '전체' },
  loading: { pt: 'Carregando…', en: 'Loading…', ko: '로딩 중…' },

  // Estados
  empty: { pt: 'Nada aqui', en: 'Nothing here', ko: '비어 있음' },
  error: { pt: 'Algo deu errado', en: 'Something went wrong', ko: '오류 발생' },
  notFound: { pt: 'Não encontrado', en: 'Not found', ko: '찾을 수 없음' },
  noAccess: { pt: 'Sem acesso', en: 'No access', ko: '접근 불가' },

  // Semana
  week: { pt: 'Semana', en: 'Week', ko: '주' },
  currentWeek: { pt: 'Semana atual', en: 'Current week', ko: '이번 주' },
})
