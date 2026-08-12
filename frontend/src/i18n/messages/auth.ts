/**
 * Mensagens das telas públicas de autenticação (LoginPage/RegisterPage).
 */
import { defineMessages } from '@/i18n'

export const AUTH = defineMessages({
  // Marca
  tagline: { pt: 'Seu weekly, sem retrabalho.', en: 'Your weekly, without rework.', ko: '주간 보고를 더 쉽게.' },

  // Títulos
  signInTitle: { pt: 'Entrar', en: 'Sign in', ko: '로그인' },
  registerTitle: { pt: 'Criar conta', en: 'Create account', ko: '회원가입' },

  // Campos
  email: { pt: 'Email', en: 'Email', ko: '이메일' },
  password: { pt: 'Senha', en: 'Password', ko: '비밀번호' },
  passwordConfirm: { pt: 'Confirmar senha', en: 'Confirm password', ko: '비밀번호 확인' },
  name: { pt: 'Nome', en: 'Name', ko: '이름' },
  employeeId: { pt: 'Matrícula', en: 'Employee ID', ko: '사번' },
  role: { pt: 'Cargo', en: 'Role', ko: '직급' },
  sector: { pt: 'Setor', en: 'Sector', ko: '부문' },

  // Placeholders
  namePh: { pt: 'Nome', en: 'Name', ko: '이름' },
  emailPh: { pt: 'nome@empresa.com', en: 'name@company.com', ko: 'name@company.com' },
  employeeIdPh: { pt: 'EMP-12345', en: 'EMP-12345', ko: 'EMP-12345' },
  selectPh: { pt: 'Selecione', en: 'Select', ko: '선택' },

  // Ações
  signIn: { pt: 'Entrar', en: 'Sign in', ko: '로그인' },
  signingIn: { pt: 'Entrando…', en: 'Signing in…', ko: '로그인 중…' },
  register: { pt: 'Criar conta', en: 'Create account', ko: '가입하기' },
  registering: { pt: 'Criando…', en: 'Creating…', ko: '가입 중…' },
  noAccount: { pt: 'Não tem conta?', en: 'No account?', ko: '계정이 없으신가요?' },
  hasAccount: { pt: 'Já tem conta?', en: 'Have an account?', ko: '이미 계정이 있으신가요?' },
  showPassword: { pt: 'Mostrar senha', en: 'Show password', ko: '비밀번호 표시' },
  hidePassword: { pt: 'Ocultar senha', en: 'Hide password', ko: '비밀번호 숨김' },

  // Credenciais (401)
  credError: { pt: 'Email ou senha incorretos.', en: 'Incorrect email or password.', ko: '이메일 또는 비밀번호가 올바르지 않습니다.' },
  credHint: { pt: 'Confira e tente novamente.', en: 'Check and try again.', ko: '다시 확인해 주세요.' },

  // Validação
  emailRequired: { pt: 'Informe seu email.', en: 'Enter your email.', ko: '이메일을 입력하세요.' },
  emailInvalid: { pt: 'Email inválido.', en: 'Invalid email.', ko: '이메일 형식이 올바르지 않습니다.' },
  passwordRequired: { pt: 'Informe sua senha.', en: 'Enter your password.', ko: '비밀번호를 입력하세요.' },
  nameRequired: { pt: 'Informe seu nome.', en: 'Enter your name.', ko: '이름을 입력하세요.' },
  nameShort: { pt: 'Nome muito curto.', en: 'Name too short.', ko: '이름이 너무 짧습니다.' },
  employeeIdRequired: { pt: 'Informe sua matrícula.', en: 'Enter your employee ID.', ko: '사번을 입력하세요.' },
  passwordCreate: { pt: 'Crie uma senha.', en: 'Create a password.', ko: '비밀번호를 설정하세요.' },
  passwordShort: { pt: 'Senha muito curta.', en: 'Password too short.', ko: '비밀번호가 너무 짧습니다.' },
  confirmRequired: { pt: 'Confirme sua senha.', en: 'Confirm your password.', ko: '비밀번호를 다시 입력하세요.' },
  passwordMismatch: { pt: 'Senhas não conferem.', en: "Passwords don't match.", ko: '비밀번호가 일치하지 않습니다.' },
  roleRequired: { pt: 'Selecione seu cargo.', en: 'Select your role.', ko: '직급을 선택하세요.' },
  sectorRequired: { pt: 'Selecione seu setor.', en: 'Select your sector.', ko: '부문을 선택하세요.' },

  // Dicas curtas por campo
  hintName: { pt: 'Ex.: Maria Silva.', en: 'E.g.: Maria Silva.', ko: '예: 김민수.' },
  hintEmail: { pt: 'Ex.: nome@empresa.com.', en: 'E.g.: name@company.com.', ko: '예: name@company.com.' },
  hintEmployeeId: { pt: 'Ex.: EMP-12345.', en: 'E.g.: EMP-12345.', ko: '예: EMP-12345.' },
  hintPassword: { pt: 'Mínimo 6 caracteres.', en: 'At least 6 characters.', ko: '6자 이상 입력하세요.' },
  hintPasswordConfirm: { pt: 'Repita a mesma senha.', en: 'Repeat the same password.', ko: '같은 비밀번호를 입력하세요.' },

  // Resumo de erros do formulário
  fixOne: { pt: 'Corrija o campo em vermelho.', en: 'Fix the highlighted field.', ko: '표시된 항목을 수정하세요.' },
  fixMany: { pt: 'Corrija os {n} campos em vermelho.', en: 'Fix the {n} highlighted fields.', ko: '표시된 {n}개 항목을 수정하세요.' },

  // Falha ao carregar cargos/setores
  optionsLoadError: { pt: 'Falha ao carregar opções.', en: "Couldn't load options.", ko: '목록을 불러오지 못했습니다.' },

  // Recuperação de senha (verificada pela matrícula)
  forgotPassword: { pt: 'Esqueci minha senha', en: 'Forgot password', ko: '비밀번호 찾기' },
  resetTitle: { pt: 'Recuperar senha', en: 'Reset password', ko: '비밀번호 재설정' },
  resetSubtitle: { pt: 'Confirme com sua matrícula.', en: 'Verify with your employee ID.', ko: '사번으로 확인하세요.' },
  newPassword: { pt: 'Nova senha', en: 'New password', ko: '새 비밀번호' },
  newPasswordConfirm: { pt: 'Confirmar nova senha', en: 'Confirm new password', ko: '새 비밀번호 확인' },
  resetSubmit: { pt: 'Redefinir senha', en: 'Reset password', ko: '재설정' },
  resetting: { pt: 'Redefinindo…', en: 'Resetting…', ko: '재설정 중…' },
  resetDone: { pt: 'Senha redefinida.', en: 'Password reset.', ko: '재설정 완료.' },
  backToLogin: { pt: 'Voltar ao login', en: 'Back to sign in', ko: '로그인으로' },
})
