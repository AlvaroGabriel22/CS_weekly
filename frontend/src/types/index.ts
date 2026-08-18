export interface User {
  id: string
  email: string
  employee_id: string
  name: string
  department: string
  role: string
  sector: 'QM' | 'QA' | 'OQC' | 'IQC' | 'FIELD' | 'CSI'
  photo_url: string | null
  is_active: boolean
  /** true apenas para o usuário root/admin (habilita gestão do FAQ). */
  is_admin?: boolean
  writing_profile: WritingProfile | null
  created_at: string
}

export interface WritingProfile {
  default_language: 'pt' | 'en' | 'ko'
  default_template_id: string | null
  writing_tone: string
  objectivity: string
  technical_level: string
  auto_conclusions: boolean
  auto_next_steps: boolean
  auto_impact: boolean
  auto_describe_images: boolean
  auto_explain_charts: boolean
  personal_prompt: string
}

export interface Activity {
  id: string
  title: string
  description: string | null
  project: string | null
  category: string | null
  department: string | null
  activity_date: string
  tags: string[]
  notes: string | null
  include_in_weekly: boolean
  status: string
  week_number: number
  year: number
  created_at: string
  updated_at: string
  metadata_entry: ActivityMetadata | null
  attachments: Attachment[]
}

export interface ActivityMetadata {
  project: string | null
  supplier: string | null
  line: string | null
  process: string | null
  product: string | null
  category: string | null
  activity_type: string | null
  defect_type: string | null
  related_kpis: string[]
  keywords: string[]
  technical_summary: string | null
}

export interface Attachment {
  id: string
  filename: string
  original_filename: string
  file_type: string
  file_size: number
  mime_type: string | null
  image_usage: string | null
  include_in_weekly: boolean
  manual_caption: string | null
  ai_caption: string | null
  /** Planilhas: {"table": {columns, rows, n_rows, n_cols, sheet, truncated}} extraída no upload. */
  kpi_data: { table?: ExtractedTable } | null
  created_at: string
}

/** Tabela extraída de um anexo xlsx/xls/csv (backend: table_extract.py). */
export interface ExtractedTable {
  columns: string[]
  rows: string[][]
  n_rows: number
  n_cols: number
  sheet?: string
  truncated: boolean
}

export interface DashboardStats {
  week_number: number
  year: number
  activities_count: number
  days_filled: number
  images_count: number
  spreadsheets_count: number
  files_count: number
  weekly_status: string | null
  last_report_generated_at: string | null
  coverage_score: number
}

export interface WeeklyReport {
  id: string
  week_number: number
  year: number
  status: string
  language: string
  version: number
  title: string | null
  /** content.layout = layout do editor WYSIWYG (quando o deck foi montado à mão). */
  content: (Record<string, unknown> & { layout?: import('@/components/reports/slideLayout').DeckLayout }) | null
  pptx_path: string | null
  ai_summary: string | null
  coverage: CoverageMetrics | null
  confidence_index: ConfidenceSlide[] | null
  quality_score: number | null
  generated_at: string | null
  created_at: string
  template?: Template | null
  /** true quando o deck foi gerado sem IA (fallback degradado). */
  ai_degraded?: boolean
}

export interface CoverageMetrics {
  activities_registered: number
  activities_used: number
  images_used: number
  files_used: number
  kpis_identified: number
  slides_filled: number
  missing_required_fields: string[]
  quality_score: number
}

export interface ConfidenceSlide {
  slide_number: number
  slide_title: string
  confidence: number
  missing_evidence: string[]
  notes: string | null
}

export interface Template {
  id: string
  name: string
  department: string
  language: string
  description: string | null
  file_path: string | null
  slides_config: Record<string, unknown>
  is_active: boolean
  created_at: string
}

// ── Novos tipos (área de departamentos / colegas) ──────────────────────────

/** Usuário no organograma (GET /users/org). */
/** Cargos de gestão — espelho de MANAGEMENT_ROLES do backend. */
export const MANAGEMENT_ROLES = [
  'Gerente Sr',
  'Gerente PL',
  'Gerente Jr',
  'Chefe',
  'Supervisor',
] as const

export function isManagementRole(role: string | undefined): boolean {
  return !!role && (MANAGEMENT_ROLES as readonly string[]).includes(role)
}

export interface OrgUser {
  id: string
  name: string
  role: string
  sector: 'QM' | 'QA' | 'OQC' | 'IQC' | 'FIELD' | 'CSI'
  department: string
  photo_url: string | null
  /** Calculado pelo backend: o usuário logado pode ver os weeklys desta pessoa. */
  viewer_can_access: boolean
}

/** Resumo de weekly na listagem de um colega (GET /weekly/user/:id). */
export interface WeeklySummary {
  id: string
  week_number: number
  year: number
  status: string
  title: string | null
  version: number
  generated_at: string | null
  has_pptx: boolean
}
