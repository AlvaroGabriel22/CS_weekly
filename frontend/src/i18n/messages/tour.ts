/** Guia de primeiro acesso (tour com spotlight) — pt/en/ko. */
import { defineMessages } from '@/i18n'

export const TOUR = defineMessages({
  // Controles
  next: { pt: 'Próximo', en: 'Next', ko: '다음' },
  previous: { pt: 'Anterior', en: 'Back', ko: '이전' },
  finish: { pt: 'Começar a usar', en: 'Start using', ko: '시작하기' },
  stepOf: { pt: '{n} de {total}', en: '{n} of {total}', ko: '{total} 중 {n}' },
  replay: { pt: 'Rever o guia', en: 'Replay the guide', ko: '가이드 다시 보기' },
  close: { pt: 'Fechar guia', en: 'Close guide', ko: '가이드 닫기' },

  // Passos
  welcomeTitle: { pt: 'Bem-vindo ao QWI! 👋', en: 'Welcome to QWI! 👋', ko: 'QWI에 오신 것을 환영합니다! 👋' },
  welcomeBody: {
    pt: 'Este guia rápido mostra como transformar o registro do seu dia a dia em uma apresentação de weekly pronta. Leva menos de um minuto.',
    en: 'This quick guide shows how to turn your day-to-day records into a ready weekly presentation. It takes less than a minute.',
    ko: '이 빠른 가이드는 일상 기록을 완성된 위클리 발표 자료로 만드는 방법을 안내합니다. 1분이면 충분합니다.',
  },
  weekTitle: { pt: 'Sua semana atual', en: 'Your current week', ko: '이번 주' },
  weekBody: {
    pt: 'O QWI trabalha por semanas (W1 a W52). Aqui você vê a semana atual e o dia de hoje em destaque.',
    en: 'QWI works in weeks (W1 to W52). Here you see the current week with today highlighted.',
    ko: 'QWI는 주 단위(W1~W52)로 동작합니다. 여기에서 이번 주와 오늘 날짜를 확인할 수 있습니다.',
  },
  statsTitle: { pt: 'Seu progresso', en: 'Your progress', ko: '나의 진행 상황' },
  statsBody: {
    pt: 'Atividades registradas, dias preenchidos, anexos e o status do seu weekly — tudo em um olhar.',
    en: 'Registered activities, filled days, attachments and your weekly status — at a glance.',
    ko: '등록한 활동, 작성한 요일, 첨부 파일, 위클리 상태를 한눈에 볼 수 있습니다.',
  },
  agendaTitle: { pt: 'Agenda: registre aqui', en: 'Agenda: log here', ko: '일정: 여기에 기록' },
  agendaBody: {
    pt: 'Clique em um dia para registrar o que você fez. Anexe planilhas (xlsx) e fotos — o sistema extrai as tabelas automaticamente para a apresentação.',
    en: 'Click a day to log what you did. Attach spreadsheets (xlsx) and photos — tables are extracted automatically for your presentation.',
    ko: '날짜를 클릭해 한 일을 기록하세요. 엑셀(xlsx)과 사진을 첨부하면 표가 자동으로 추출되어 발표 자료에 사용됩니다.',
  },
  dayFormTitle: { pt: 'Registre a atividade', en: 'Log the activity', ko: '활동 기록' },
  dayFormBody: {
    pt: 'Ao clicar num dia, este painel abre: dê um título, descreva o que foi feito e salve. Cada registro vira matéria-prima do seu weekly.',
    en: 'Clicking a day opens this panel: add a title, describe what was done and save. Each record feeds your weekly.',
    ko: '날짜를 클릭하면 이 패널이 열립니다. 제목과 내용을 입력하고 저장하세요. 기록 하나하나가 위클리의 재료가 됩니다.',
  },
  attachTitle: { pt: 'Anexe evidências', en: 'Attach evidence', ko: '증빙 첨부' },
  attachBody: {
    pt: 'Aqui você anexa planilhas (xlsx/xls/csv) e fotos (jpg/png). As tabelas do Excel são extraídas automaticamente para usar nos slides.',
    en: 'Attach spreadsheets (xlsx/xls/csv) and photos (jpg/png) here. Excel tables are extracted automatically for your slides.',
    ko: '여기에서 엑셀(xlsx/xls/csv)과 사진(jpg/png)을 첨부합니다. 엑셀 표는 자동으로 추출되어 슬라이드에 사용됩니다.',
  },
  assembleTitle: { pt: 'Montagem manual', en: 'Manual layout', ko: '수동 구성' },
  assembleBody: {
    pt: 'Este botão abre o editor de slides: seus conteúdos viram bloquinhos que você arrasta para a página, posicionando tudo como quiser.',
    en: 'This button opens the slide editor: your content becomes blocks you drag onto the page, arranging everything your way.',
    ko: '이 버튼은 슬라이드 편집기를 엽니다. 콘텐츠가 블록이 되어 원하는 위치로 드래그해 배치할 수 있습니다.',
  },
  aiDeckTitle: { pt: 'Ou deixe com a IA', en: 'Or let AI do it', ko: 'AI에게 맡기기' },
  aiDeckBody: {
    pt: 'Sem tempo? A IA monta um rascunho completo do deck com suas atividades, tabelas e fotos — e você só ajusta.',
    en: 'Short on time? AI drafts the whole deck from your activities, tables and photos — you just adjust.',
    ko: '시간이 없다면 AI가 활동·표·사진으로 덱 초안을 만들어 줍니다. 다듬기만 하세요.',
  },
  reportsTitle: { pt: 'Relatórios: monte o weekly', en: 'Reports: build your weekly', ko: '보고서: 위클리 만들기' },
  reportsBody: {
    pt: 'Escolha a semana, selecione as atividades e monte os slides arrastando seus conteúdos — ou deixe a IA montar um rascunho em um clique.',
    en: 'Pick the week, select activities and build slides by dragging your content — or let AI draft the deck in one click.',
    ko: '주를 선택하고 활동을 골라 콘텐츠를 드래그해 슬라이드를 구성하세요. AI가 한 번의 클릭으로 초안을 만들어 줄 수도 있습니다.',
  },
  deptTitle: { pt: 'Departamentos', en: 'Departments', ko: '부서' },
  deptBody: {
    pt: 'Veja o organograma de cada setor e, se tiver acesso, os weeklys dos colegas — com pré-visualização página a página.',
    en: 'See each sector’s org chart and, with access, your colleagues’ weeklys — with page-by-page preview.',
    ko: '각 부문의 조직도를 보고, 권한이 있으면 동료의 위클리를 페이지별로 미리 볼 수 있습니다.',
  },
  langTitle: { pt: 'Três idiomas', en: 'Three languages', ko: '3개 언어' },
  langBody: {
    pt: 'Troque o idioma do sistema aqui (português, inglês e coreano). No editor, a IA também traduz os textos dos seus slides.',
    en: 'Switch the system language here (Portuguese, English and Korean). In the editor, AI also translates your slide texts.',
    ko: '여기에서 시스템 언어(포르투갈어·영어·한국어)를 바꿀 수 있습니다. 편집기에서는 AI가 슬라이드 텍스트도 번역해 줍니다.',
  },
  replayTitle: { pt: 'Reveja quando quiser', en: 'Replay anytime', ko: '언제든 다시 보기' },
  replayBody: {
    pt: 'Este guia fica sempre disponível neste botão. Bom trabalho! 🚀',
    en: 'This guide is always available on this button. Enjoy! 🚀',
    ko: '이 가이드는 이 버튼에서 언제든 다시 볼 수 있습니다. 좋은 한 주 되세요! 🚀',
  },
})
