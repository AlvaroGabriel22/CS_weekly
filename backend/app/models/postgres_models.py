"""PostgreSQL-optimized models with timezone and constraint support"""
import enum
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    false,
    true,
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def generate_uuid() -> str:
    """Generate UUID string for primary key"""
    return str(uuid.uuid4())


def EnumCol(enum_cls):
    """
    Coluna Enum que grava o VALUE do membro ("pt"), não o nome ("PT").

    Sem isto o SQLAlchemy grava o nome, e os server_default (escritos como
    valores) viram lixo que o próprio ORM não consegue reler.
    """
    return Enum(enum_cls, values_callable=lambda e: [m.value for m in e])


# Enums
class Language(str, enum.Enum):
    PT = "pt"
    EN = "en"
    KO = "ko"


class WritingTone(str, enum.Enum):
    ANALYST = "analyst"
    SPECIALIST = "specialist"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    DIRECTOR = "director"


class ObjectivityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TechnicalLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActivityStatus(str, enum.Enum):
    DRAFT = "draft"
    REGISTERED = "registered"
    PROCESSED = "processed"
    USED_IN_REPORT = "used_in_report"


class ImageUsage(str, enum.Enum):
    STORE_ONLY = "store_only"
    INSERT_REPORT = "insert_report"
    AI_INTERPRET = "ai_interpret"
    AI_CAPTION = "ai_caption"
    AI_EVIDENCE = "ai_evidence"


class WeeklyStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class QualitySector(str, enum.Enum):
    QM = "QM"
    QA = "QA"
    OQC = "OQC"
    IQC = "IQC"
    FIELD = "FIELD"
    CSI = "CSI"


class UserRole(str, enum.Enum):
    GERENTE_SR = "Gerente Sr"
    GERENTE_PL = "Gerente PL"
    GERENTE_JR = "Gerente Jr"
    CHEFE = "Chefe"
    SUPERVISOR = "Supervisor"
    ANALISTA_ENG_SR = "Analista de engenharia Sr"
    ANALISTA_ENG_PL = "Analista de engenharia PL"
    ANALISTA_ENG_JR = "Analista de engenharia Jr"
    ANALISTA_SR = "Analista Sr"
    ANALISTA_PL = "Analista PL"
    ANALISTA_JR = "Analista Jr"
    AUDITOR_SR = "Auditor Sr"
    AUDITOR_PL = "Auditor PL"
    AUDITOR_JR = "Auditor Jr"


# Cargos de gestão: enxergam weeklys/atividades de todos os departamentos.
# Fonte única — não repetir esta lista em repositories/services.
MANAGEMENT_ROLES = frozenset({
    UserRole.GERENTE_SR,
    UserRole.GERENTE_PL,
    UserRole.GERENTE_JR,
    UserRole.CHEFE,
    UserRole.SUPERVISOR,
})


class User(Base):
    """User model with timezone-aware timestamps"""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False, server_default="Qualidade")
    role: Mapped[UserRole] = mapped_column(EnumCol(UserRole), nullable=False)
    sector: Mapped[QualitySector] = mapped_column(EnumCol(QualitySector), nullable=False, server_default="CSI")
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    writing_profile: Mapped[Optional["WritingProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    activities: Mapped[list["Activity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    weekly_reports: Mapped[list["WeeklyReport"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_employee_id", "employee_id"),
        Index("ix_users_department_is_active", "department", "is_active"),
        Index("ix_users_created_at_desc", "created_at"),
    )


class WritingProfile(Base):
    """User writing preferences"""
    __tablename__ = "writing_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    default_language: Mapped[Language] = mapped_column(EnumCol(Language), nullable=False, server_default="pt")
    default_template_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    writing_tone: Mapped[WritingTone] = mapped_column(EnumCol(WritingTone), nullable=False, server_default="specialist")
    objectivity: Mapped[ObjectivityLevel] = mapped_column(EnumCol(ObjectivityLevel), nullable=False, server_default="high")
    technical_level: Mapped[TechnicalLevel] = mapped_column(EnumCol(TechnicalLevel), nullable=False, server_default="medium")
    auto_conclusions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    auto_next_steps: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    auto_impact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    auto_describe_images: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    auto_explain_charts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    # "Como quero a ajuda da IA" (preferências de escrita/tom).
    personal_prompt: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # "Sobre mim e meu trabalho" — fatos que o usuário declara (KPIs, linha,
    # como reporta). Semeia o perfil de conhecimento (tem precedência sobre o
    # que a IA deduz do histórico). Ver app/services/knowledge_profile.py.
    about_me: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    user: Mapped["User"] = relationship(back_populates="writing_profile")
    default_template: Mapped[Optional["Template"]] = relationship()

    __table_args__ = (
        Index("ix_writing_profiles_user_id", "user_id"),
    )


class Template(Base):
    """Report templates"""
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[Language] = mapped_column(EnumCol(Language), nullable=False, server_default="pt")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    slides_config: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    weekly_reports: Mapped[list["WeeklyReport"]] = relationship(back_populates="template")

    __table_args__ = (
        Index("ix_templates_department", "department"),
        Index("ix_templates_is_active", "is_active"),
        Index("ix_templates_created_at_desc", "created_at"),
    )


class Activity(Base):
    """Weekly activities log"""
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    activity_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    include_in_weekly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    status: Mapped[ActivityStatus] = mapped_column(EnumCol(ActivityStatus), nullable=False, server_default="registered")
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user: Mapped["User"] = relationship(back_populates="activities")
    metadata_entry: Mapped[Optional["ActivityMetadata"]] = relationship(back_populates="activity", uselist=False, cascade="all, delete-orphan")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="activity", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_activities_user_id", "user_id"),
        Index("ix_activities_week_number", "week_number"),
        Index("ix_activities_year", "year"),
        Index("ix_activities_department", "department"),
        Index("ix_activities_status", "status"),
        Index("ix_activities_user_week_year", "user_id", "year", "week_number"),
        Index("ix_activities_activity_date_desc", "activity_date"),
        Index("ix_activities_created_at_desc", "created_at"),
        CheckConstraint("week_number BETWEEN 1 AND 53", name="chk_activity_week_range"),
    )


class ActivityMetadata(Base):
    """AI-processed metadata for activities"""
    __tablename__ = "activity_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    activity_id: Mapped[str] = mapped_column(String(36), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, unique=True)
    project: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    supplier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    line: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    process: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    activity_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    defect_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    related_kpis: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
    keywords: Mapped[list] = mapped_column(JSON, nullable=False, server_default="[]")
    technical_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    activity: Mapped["Activity"] = relationship(back_populates="metadata_entry")

    __table_args__ = (
        Index("ix_activity_metadata_activity_id", "activity_id"),
    )


class Attachment(Base):
    """File attachments for activities"""
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    activity_id: Mapped[str] = mapped_column(String(36), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    image_usage: Mapped[Optional[ImageUsage]] = mapped_column(EnumCol(ImageUsage), nullable=True)
    include_in_weekly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    manual_caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    kpi_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    activity: Mapped["Activity"] = relationship(back_populates="attachments")

    __table_args__ = (
        Index("ix_attachments_activity_id", "activity_id"),
        Index("ix_attachments_file_type", "file_type"),
        Index("ix_attachments_created_at_desc", "created_at"),
    )


class WeeklyReport(Base):
    """Generated weekly reports"""
    __tablename__ = "weekly_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WeeklyStatus] = mapped_column(EnumCol(WeeklyStatus), nullable=False, server_default="draft")
    language: Mapped[Language] = mapped_column(EnumCol(Language), nullable=False, server_default="pt")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    pptx_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    prompt_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coverage: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence_index: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship(back_populates="weekly_reports")
    template: Mapped[Optional["Template"]] = relationship(back_populates="weekly_reports")

    __table_args__ = (
        # Versões coexistem: cada regeneração da mesma semana cria v+1.
        UniqueConstraint("user_id", "year", "week_number", "version", name="uq_user_year_week"),
        Index("ix_weekly_reports_user_id", "user_id"),
        Index("ix_weekly_reports_week_number", "week_number"),
        Index("ix_weekly_reports_status", "status"),
        Index("ix_weekly_reports_user_year_week", "user_id", "year", "week_number"),
        Index("ix_weekly_reports_created_at_desc", "created_at"),
        CheckConstraint("week_number BETWEEN 1 AND 53", name="chk_weekly_week_range"),
    )


class SlideLayoutPref(Base):
    """Layout fixado pelo usuário no editor de montagem do PPT.

    Guarda os elementos com pinned=true para pré-popular as próximas
    apresentações (regra: "fixar algo para as próximas apresentações").
    """
    __tablename__ = "slide_layout_prefs"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    layout: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class UserStyleProfile(Base):
    """Perfil de estilo de montagem aprendido POR USUÁRIO.

    Alimentado automaticamente a cada PPT gerado com layout (montagens
    manuais pesam mais que rascunhos da IA). O deck em um clique usa este
    perfil + o template ativo (um weekly do histórico escolhido pelo dono)
    para imitar o padrão individual de montagem.
    """
    __tablename__ = "user_style_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    profile: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Weekly do histórico marcado como "modelo da IA" (estrutura a imitar).
    template_report_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("weekly_reports.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class DepartmentRollup(Base):
    """Cache do 'weekly do departamento' gerado pela IA (copiloto do gestor).

    Uma linha por setor+semana; regenerar substitui. Evita repetir chamadas
    caras ao LLM (importante com APIs limitadas a poucas req/min).
    """
    __tablename__ = "department_rollups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    sector: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    generated_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("sector", "year", "week_number", name="uq_rollup_sector_week"),
    )


class UserFlags(Base):
    """Flags de experiência por usuário (ex.: guia de primeiro acesso).

    Tabela separada de propósito: create_all cria sem migração e novos flags
    entram como colunas aqui sem tocar na tabela users.
    """
    __tablename__ = "user_flags"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tour_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class WeeklyAccessGrant(Base):
    """Concessão PESSOAL de acesso aos weeklys do dono.

    O dono (owner) escolhe, pela matrícula, colegas de OUTROS setores que
    podem ver seus weeklys — além da regra padrão (mesmo setor / gestão).
    Inserir e retirar é decisão exclusiva do dono.
    """
    __tablename__ = "weekly_access_grants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    grantee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("owner_id", "grantee_id", name="uq_grant_owner_grantee"),
        Index("ix_grants_owner", "owner_id"),
        Index("ix_grants_grantee", "grantee_id"),
    )


class EmailRecipient(Base):
    """Lista pessoal de destinatários para envio do weekly por e-mail."""
    __tablename__ = "email_recipients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("user_id", "email", name="uq_email_recipient"),
        Index("ix_email_recipients_user", "user_id"),
    )


class BugStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class BugReport(Base):
    """Report de bug / FAQ interno.

    Qualquer usuário abre (título + descrição curta); fica visível para todos
    (para não abrirem a mesma solicitação). Só o admin/root fecha e responde.
    """
    __tablename__ = "bug_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Snapshot do autor (sobrevive se o usuário for apagado da listagem pública).
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[BugStatus] = mapped_column(
        EnumCol(BugStatus), nullable=False, default=BugStatus.OPEN
    )
    admin_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closed_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_bug_reports_status", "status"),
        Index("ix_bug_reports_created_at", "created_at"),
    )


class FaqNotifyUser(Base):
    """Usuários internos que recebem por e-mail as novas solicitações do FAQ.

    A lista é gerida SOMENTE pelo admin/root.
    """
    __tablename__ = "faq_notify_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class PptxTemplate(Base):
    """PPT enviado pelo usuário para servir de MODELO à IA.

    Guarda o arquivo original e o layout já convertido (DeckLayout) que a IA
    usa como esqueleto. Máx. 2 por usuário — regra aplicada na rota.
    """
    __tablename__ = "pptx_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    layout: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_pptx_templates_user", "user_id"),
    )


class UserKnowledgeProfile(Base):
    """O que a IA APRENDEU sobre o usuário a partir do histórico dele.

    Acumulado de forma determinística (sem LLM) a cada weekly gerado: KPIs que
    ele acompanha, entidades recorrentes (linhas, fornecedores, processos) e
    padrões. `ignored` guarda itens que o usuário descartou no card ("na
    verdade não acompanho isso"). O que o usuário DECLARA (WritingProfile.
    about_me) tem precedência sobre o aprendido.
    """
    __tablename__ = "user_knowledge_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # {"kpis": {nome: peso}, "entities": {tipo: {valor: peso}}, ...}
    knowledge: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Itens que o usuário removeu no card (não voltam a aparecer).
    ignored: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AnalysisRecipe(Base):
    """Receita de análise de planilha aprovada pelo usuário.

    Guarda o pedido em linguagem natural, a receita estruturada (interpretada
    pela IA, executada por código) e uma assinatura das colunas da planilha —
    para reofertar na semana seguinte quando o mesmo formato aparecer.
    """
    __tablename__ = "analysis_recipes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Pedido original ("FPY por linha e comparação com a semana passada").
    request_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Receita executável (ver app/services/analysis_engine.py).
    recipe: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Assinatura das colunas da planilha (normalizada) p/ reconhecer o formato.
    columns_signature: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    label: Mapped[str] = mapped_column(String(120), nullable=False, server_default="")
    # Último total calculado — base para a comparação com a semana anterior.
    last_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_analysis_recipes_user", "user_id"),
    )
