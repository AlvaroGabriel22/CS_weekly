/**
 * Mensagens de PERFIL e CONFIGURAÇÕES (ProfilePage/SettingsPage).
 * Genéricas (Salvar, Cancelar, Idioma…) vêm de COMMON — não duplicar.
 */
import { defineMessages } from '@/i18n'

export const PROFILE = defineMessages({
  // ── Foto ──────────────────────────────────────────────────────────────────
  photoTitle: { pt: 'Foto', en: 'Photo', ko: '사진' },
  changePhoto: { pt: 'Alterar foto', en: 'Change photo', ko: '사진 변경' },
  uploading: { pt: 'Enviando…', en: 'Uploading…', ko: '업로드 중…' },
  uploadingPhotoAria: { pt: 'Enviando foto', en: 'Uploading photo', ko: '사진 업로드 중' },
  photoSaved: { pt: 'Foto salva.', en: 'Photo saved.', ko: '사진 저장 완료' },
  photoBadType: { pt: 'Formato não suportado.', en: 'Unsupported format.', ko: '지원하지 않는 형식입니다.' },
  photoBadTypeHint: { pt: 'Use JPG, PNG ou WEBP.', en: 'Use JPG, PNG or WEBP.', ko: 'JPG, PNG, WEBP만 가능합니다.' },
  photoTooLarge: {
    pt: 'Imagem acima de 5 MB ({mb} MB).',
    en: 'Image over 5 MB ({mb} MB).',
    ko: '5MB 초과 ({mb}MB)',
  },
  photoTooLargeHint: { pt: 'Escolha uma foto menor.', en: 'Choose a smaller photo.', ko: '더 작은 사진을 선택하세요.' },

  // ── Dados pessoais ────────────────────────────────────────────────────────
  dataTitle: { pt: 'Dados', en: 'Details', ko: '기본 정보' },
  name: { pt: 'Nome', en: 'Name', ko: '이름' },
  email: { pt: 'Email', en: 'Email', ko: '이메일' },
  employeeId: { pt: 'Matrícula', en: 'Employee ID', ko: '사번' },
  role: { pt: 'Cargo', en: 'Role', ko: '직책' },
  sector: { pt: 'Setor', en: 'Sector', ko: '부문' },
  department: { pt: 'Departamento', en: 'Department', ko: '부서' },
  saved: { pt: 'Salvo.', en: 'Saved.', ko: '저장 완료' },
  saving: { pt: 'Salvando…', en: 'Saving…', ko: '저장 중…' },
  nameTooShort: { pt: 'Nome muito curto.', en: 'Name too short.', ko: '이름이 너무 짧습니다.' },
  nameTooShortHint: { pt: 'Mínimo de 2 caracteres.', en: 'At least 2 characters.', ko: '최소 2자.' },

  // ── Senha ─────────────────────────────────────────────────────────────────
  passwordTitle: { pt: 'Senha', en: 'Password', ko: '비밀번호' },
  currentPassword: { pt: 'Senha atual', en: 'Current password', ko: '현재 비밀번호' },
  newPassword: { pt: 'Nova senha', en: 'New password', ko: '새 비밀번호' },
  confirmPassword: { pt: 'Confirmar nova senha', en: 'Confirm new password', ko: '새 비밀번호 확인' },
  changePassword: { pt: 'Alterar senha', en: 'Change password', ko: '비밀번호 변경' },
  changing: { pt: 'Alterando…', en: 'Changing…', ko: '변경 중…' },
  passwordChanged: { pt: 'Senha alterada.', en: 'Password changed.', ko: '비밀번호 변경 완료' },
  showPassword: { pt: 'Mostrar senha', en: 'Show password', ko: '비밀번호 표시' },
  hidePassword: { pt: 'Ocultar senha', en: 'Hide password', ko: '비밀번호 숨기기' },
  strength: { pt: 'Força: {label}', en: 'Strength: {label}', ko: '강도: {label}' },
  strengthWeak: { pt: 'Fraca', en: 'Weak', ko: '약함' },
  strengthMedium: { pt: 'Média', en: 'Medium', ko: '보통' },
  strengthStrong: { pt: 'Forte', en: 'Strong', ko: '강함' },
  currentRequired: { pt: 'Informe a senha atual.', en: 'Enter your current password.', ko: '현재 비밀번호를 입력하세요.' },
  newRequired: { pt: 'Crie uma senha nova.', en: 'Enter a new password.', ko: '새 비밀번호를 입력하세요.' },
  newTooShort: { pt: 'Mínimo de 6 caracteres.', en: 'At least 6 characters.', ko: '최소 6자.' },
  confirmRequired: { pt: 'Confirme a senha nova.', en: 'Confirm the new password.', ko: '새 비밀번호를 다시 입력하세요.' },
  passwordMismatch: { pt: 'As senhas não conferem.', en: 'Passwords do not match.', ko: '비밀번호가 일치하지 않습니다.' },

  // ── Configurações: preferências de escrita ────────────────────────────────
  writingTitle: { pt: 'Preferências de escrita', en: 'Writing preferences', ko: '작성 설정' },
  langToneHeading: { pt: 'Idioma e tom', en: 'Language & tone', ko: '언어와 톤' },
  reportLanguage: { pt: 'Idioma do relatório', en: 'Report language', ko: '보고서 언어' },
  langPt: { pt: 'Português', en: 'Portuguese', ko: '포르투갈어' },
  langEn: { pt: 'Inglês', en: 'English', ko: '영어' },
  tone: { pt: 'Tom', en: 'Tone', ko: '톤' },
  toneAnalyst: { pt: 'Analista', en: 'Analyst', ko: '분석가' },
  toneSpecialist: { pt: 'Especialista', en: 'Specialist', ko: '전문가' },
  toneSupervisor: { pt: 'Supervisor', en: 'Supervisor', ko: '수퍼바이저' },
  toneManager: { pt: 'Gerente', en: 'Manager', ko: '매니저' },
  toneDirector: { pt: 'Diretor', en: 'Director', ko: '디렉터' },
  objectivity: { pt: 'Objetividade', en: 'Objectivity', ko: '객관성' },
  objectivityLow: { pt: 'Baixa', en: 'Low', ko: '낮음' },
  objectivityMedium: { pt: 'Média', en: 'Medium', ko: '보통' },
  objectivityHigh: { pt: 'Alta', en: 'High', ko: '높음' },
  technicalLevel: { pt: 'Nível técnico', en: 'Technical level', ko: '기술 수준' },
  technicalLow: { pt: 'Baixo', en: 'Low', ko: '낮음' },
  technicalMedium: { pt: 'Médio', en: 'Medium', ko: '보통' },
  technicalHigh: { pt: 'Alto', en: 'High', ko: '높음' },
  selectPlaceholder: { pt: 'Selecione', en: 'Select', ko: '선택' },
  autoHeading: { pt: 'Conteúdo automático', en: 'Auto content', ko: '자동 콘텐츠' },
  autoConclusions: { pt: 'Conclusões', en: 'Conclusions', ko: '결론' },
  autoNextSteps: { pt: 'Próximos passos', en: 'Next steps', ko: '다음 단계' },
  autoImpact: { pt: 'Impacto', en: 'Impact', ko: '영향' },
  autoDescribeImages: { pt: 'Descrever imagens', en: 'Describe images', ko: '이미지 설명' },
  autoExplainCharts: { pt: 'Explicar gráficos', en: 'Explain charts', ko: '차트 설명' },
  // ── Meu perfil para a IA (dois blocos de notas) ───────────────────────────
  aiProfileHeading: { pt: 'Meu perfil para a IA', en: 'My profile for the AI', ko: 'AI를 위한 내 프로필' },
  aboutMeHeading: { pt: 'Sobre mim e meu trabalho', en: 'About me and my work', ko: '나와 내 업무 소개' },
  aboutMeHint: {
    pt: 'Ajuda a IA a te entender mais rápido.',
    en: 'Helps the AI understand you faster.',
    ko: 'AI가 당신을 더 빨리 이해하도록 돕습니다.',
  },
  aboutMePlaceholder: {
    pt: 'Conte à IA seus KPIs, sua linha, como você reporta. Ex.: Acompanho FPY (~92%) e PPM na linha 3; reporto NC com plano de ação 8D.',
    en: 'Tell the AI your KPIs, your line, how you report. E.g.: I track FPY (~92%) and PPM on line 3; I report NCs with an 8D action plan.',
    ko: 'AI에게 당신의 KPI, 담당 라인, 보고 방식을 알려주세요. 예: 3라인의 FPY(~92%)와 PPM을 관리하고, NC는 8D 조치 계획으로 보고합니다.',
  },
  promptHeading: { pt: 'Como quero a ajuda da IA', en: 'How I want the AI to help', ko: 'AI 지원 방식' },
  promptPlaceholder: {
    pt: 'Preferências de tom/estilo. Ex.: seja direto e executivo.',
    en: 'Tone/style preferences. E.g.: be direct and executive.',
    ko: '톤/스타일 선호. 예: 간결하고 임원 보고 스타일로.',
  },

  // ── Card: o que a IA já aprendeu ───────────────────────────────────────────
  knowledgeTitle: { pt: 'O que já aprendi sobre você', en: 'What I have learned about you', ko: '내가 파악한 당신에 대한 정보' },
  knowledgeSubtitle: {
    pt: 'aprendendo · com base em {count} semana(s)',
    en: 'learning · based on {count} week(s)',
    ko: '학습 중 · {count}주 기준',
  },
  knowledgeKpis: { pt: 'KPIs', en: 'KPIs', ko: 'KPI' },
  knowledgeEntities: { pt: 'Padrões', en: 'Patterns', ko: '패턴' },
  knowledgeDismissHint: {
    pt: 'Descartar diz à IA "não acompanho isso".',
    en: 'Dismissing tells the AI "I don’t track this".',
    ko: '항목을 제거하면 AI에 "관리하지 않음"이라고 알려줍니다.',
  },
  knowledgeEmpty: {
    pt: 'Ainda estou te conhecendo — gere alguns weeklys e eu vou aprendendo seus KPIs e padrões. Enquanto isso, me conte sobre você no campo acima.',
    en: 'Still getting to know you — generate a few weeklys and I’ll learn your KPIs and patterns. In the meantime, tell me about yourself in the field above.',
    ko: '아직 당신을 파악하는 중입니다 — 위클리를 몇 개 생성하면 KPI와 패턴을 배웁니다. 그동안 위 항목에 자신을 소개해 주세요.',
  },
  knowledgeDismiss: { pt: 'Descartar {value}', en: 'Dismiss {value}', ko: '{value} 제거' },
  entityLine: { pt: 'Linha', en: 'Line', ko: '라인' },
  entitySupplier: { pt: 'Fornecedor', en: 'Supplier', ko: '공급업체' },
  entityProcess: { pt: 'Processo', en: 'Process', ko: '공정' },
  entityProduct: { pt: 'Produto', en: 'Product', ko: '제품' },
  entityDefectType: { pt: 'Tipo de defeito', en: 'Defect type', ko: '불량 유형' },

  unsavedChanges: { pt: 'Alterações não salvas.', en: 'Unsaved changes.', ko: '저장되지 않은 변경 사항' },
  allSaved: { pt: 'Tudo salvo.', en: 'All saved.', ko: '모두 저장됨' },
  discard: { pt: 'Descartar', en: 'Discard', ko: '되돌리기' },

  // ── Configurações: abas ───────────────────────────────────────────────────
  tabGeneral: { pt: 'Geral', en: 'General', ko: '일반' },
  tabAccount: { pt: 'Conta', en: 'Account', ko: '계정' },
  tabSharing: { pt: 'Compartilhamento', en: 'Sharing', ko: '공유' },

  // ── Conta: mudança de cargo ───────────────────────────────────────────────
  roleChangeTitle: { pt: 'Mudança de cargo', en: 'Role change', ko: '직책 변경' },
  currentRole: { pt: 'Cargo atual', en: 'Current role', ko: '현재 직책' },
  newRole: { pt: 'Novo cargo', en: 'New role', ko: '새 직책' },
  roleRequired: { pt: 'Selecione um cargo.', en: 'Select a role.', ko: '직책을 선택하세요.' },
  managementNotice: {
    pt: 'Cargos de gestão passam a ver os weeklys de TODOS os departamentos imediatamente.',
    en: 'Management roles immediately see everyone’s weeklys across all departments.',
    ko: '관리자 직책은 즉시 모든 부서의 위클리를 볼 수 있습니다.',
  },
  changeRole: { pt: 'Mudar cargo', en: 'Change role', ko: '직책 변경' },
  changingRole: { pt: 'Mudando…', en: 'Changing…', ko: '변경 중…' },
  roleChanged: { pt: 'Cargo atualizado.', en: 'Role updated.', ko: '직책 변경 완료' },

  // ── Compartilhamento: acesso aos meus weeklys ─────────────────────────────
  grantsTitle: { pt: 'Acesso aos meus weeklys', en: 'Access to my weeklys', ko: '내 위클리 접근 권한' },
  grantsHint: {
    pt: 'Seu setor já tem acesso automático. Adicione exceções de outros setores — você decide quem entra ou sai.',
    en: 'Your sector already has automatic access. Add exceptions from other sectors — you decide.',
    ko: '같은 부문은 이미 자동으로 접근할 수 있습니다. 다른 부문의 예외만 추가하세요.',
  },
  employeeIdRequired: { pt: 'Informe a matrícula.', en: 'Enter the employee ID.', ko: '사번을 입력하세요.' },
  grantAdded: { pt: 'Acesso concedido.', en: 'Access granted.', ko: '접근 허용 완료' },
  grantRemoved: { pt: 'Acesso removido.', en: 'Access removed.', ko: '접근 해제 완료' },
  grantsEmpty: { pt: 'Nenhuma exceção.', en: 'No exceptions.', ko: '예외 없음' },
  removeAccess: { pt: 'Remover acesso de {name}', en: 'Remove access for {name}', ko: '{name} 접근 해제' },

  // ── Compartilhamento: e-mails do weekly ───────────────────────────────────
  emailsTitle: { pt: 'Lista de e-mails do weekly', en: 'Weekly email list', ko: '위클리 이메일 목록' },
  emailsHint: {
    pt: 'Pré-carregada ao clicar em "Enviar e-mail" na Central de Relatórios.',
    en: 'Preloaded when you click "Send email" in Reports.',
    ko: '보고서 센터에서 이메일을 보낼 때 자동으로 불러옵니다.',
  },
  emailRequired: { pt: 'Informe o e-mail.', en: 'Enter the email.', ko: '이메일을 입력하세요.' },
  nameOptional: { pt: 'Nome (opcional)', en: 'Name (optional)', ko: '이름 (선택)' },
  emailAdded: { pt: 'E-mail adicionado.', en: 'Email added.', ko: '이메일 추가 완료' },
  emailRemoved: { pt: 'E-mail removido.', en: 'Email removed.', ko: '이메일 삭제 완료' },
  emailsEmpty: { pt: 'Nenhum destinatário.', en: 'No recipients.', ko: '수신자 없음' },
  removeEmail: { pt: 'Remover {email}', en: 'Remove {email}', ko: '{email} 삭제' },
})
