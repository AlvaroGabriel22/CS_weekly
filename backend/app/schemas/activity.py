from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models import ActivityStatus, ImageUsage


class _AcceptsDateOnly:
    """O frontend envia datas de agenda como "AAAA-MM-DD" (dia local, sem hora)."""

    @field_validator('activity_date', mode='before', check_fields=False)
    @classmethod
    def _date_only_as_midnight(cls, v: object) -> object:
        if isinstance(v, str) and len(v) == 10:
            return datetime.fromisoformat(v)
        return v


class ActivityCreate(_AcceptsDateOnly, BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    project: str | None = None
    category: str | None = None
    department: str | None = None
    activity_date: datetime | None = None
    tags: list[str] = []
    notes: str | None = None
    include_in_weekly: bool = True


class ActivityUpdate(_AcceptsDateOnly, BaseModel):
    title: str | None = None
    description: str | None = None
    project: str | None = None
    category: str | None = None
    department: str | None = None
    activity_date: datetime | None = None
    tags: list[str] | None = None
    notes: str | None = None
    include_in_weekly: bool | None = None
    status: ActivityStatus | None = None


class AttachmentUpdate(BaseModel):
    image_usage: ImageUsage | None = None
    manual_caption: str | None = None
    include_in_weekly: bool | None = None


class AttachmentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    mime_type: str | None
    image_usage: ImageUsage | None
    include_in_weekly: bool
    manual_caption: str | None
    ai_caption: str | None
    ai_analysis: dict | None
    kpi_data: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityMetadataResponse(BaseModel):
    project: str | None
    supplier: str | None
    line: str | None
    process: str | None
    product: str | None
    category: str | None
    activity_type: str | None
    defect_type: str | None
    related_kpis: list
    keywords: list
    technical_summary: str | None

    model_config = {"from_attributes": True}


class ActivityResponse(BaseModel):
    id: str
    title: str
    description: str | None
    project: str | None
    category: str | None
    department: str | None
    activity_date: datetime
    tags: list
    notes: str | None
    include_in_weekly: bool
    status: ActivityStatus
    week_number: int
    year: int
    created_at: datetime
    updated_at: datetime
    metadata_entry: ActivityMetadataResponse | None = None
    attachments: list[AttachmentResponse] = []

    model_config = {"from_attributes": True}


class ActivityListResponse(BaseModel):
    items: list[ActivityResponse]
    total: int
    page: int
    page_size: int
