from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models import Language, WeeklyStatus


class TemplateCreate(BaseModel):
    name: str
    department: str
    language: Language = Language.PT
    description: str | None = None
    slides_config: dict = {}


class TemplateResponse(BaseModel):
    id: str
    name: str
    department: str
    language: Language
    description: str | None
    file_path: str | None
    slides_config: dict
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WeeklyGenerateRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    activity_ids: list[str] = Field(min_length=1)
    week_number: int | None = None
    year: int | None = None
    template_id: str | None = None
    language: Language | None = None
    timezone: str | None = None
    regenerate: bool = False
    # Layout do editor WYSIWYG de montagem (ver app/services/pptx_layout.py).
    # Quando presente, o PPTX é renderizado exatamente com essas posições.
    layout: dict | None = None


class CoverageMetrics(BaseModel):
    activities_registered: int = 0
    activities_used: int = 0
    images_used: int = 0
    files_used: int = 0
    kpis_identified: int = 0
    slides_filled: int = 0
    missing_required_fields: list[str] = []
    quality_score: float = 0.0


class ConfidenceSlide(BaseModel):
    slide_number: int
    slide_title: str
    confidence: float
    missing_evidence: list[str] = []
    notes: str | None = None


class WeeklyReportResponse(BaseModel):
    id: str
    week_number: int
    year: int
    status: WeeklyStatus
    language: Language
    version: int
    title: str | None
    content: dict | None
    pptx_path: str | None
    ai_summary: str | None
    coverage: CoverageMetrics | None
    confidence_index: list[ConfidenceSlide] | None
    quality_score: float | None
    generated_at: datetime | None
    created_at: datetime
    template: TemplateResponse | None = None

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    week_number: int
    year: int
    activities_count: int
    days_filled: int
    images_count: int
    spreadsheets_count: int
    files_count: int
    weekly_status: WeeklyStatus | None
    last_report_generated_at: datetime | None = None
    coverage_score: float = 0.0
