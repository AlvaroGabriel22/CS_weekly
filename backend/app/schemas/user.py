from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import (
    ActivityStatus,
    ImageUsage,
    Language,
    ObjectivityLevel,
    QualitySector,
    TechnicalLevel,
    UserRole,
    WeeklyStatus,
    WritingTone,
)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    employee_id: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6)
    password_confirm: str = Field(min_length=6)
    name: str = Field(min_length=2, max_length=255)
    role: UserRole
    sector: QualitySector = QualitySector.CSI


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class WritingProfileUpdate(BaseModel):
    default_language: Language | None = None
    default_template_id: str | None = None
    writing_tone: WritingTone | None = None
    objectivity: ObjectivityLevel | None = None
    technical_level: TechnicalLevel | None = None
    auto_conclusions: bool | None = None
    auto_next_steps: bool | None = None
    auto_impact: bool | None = None
    auto_describe_images: bool | None = None
    auto_explain_charts: bool | None = None
    personal_prompt: str | None = None
    about_me: str | None = None


class WritingProfileResponse(BaseModel):
    default_language: Language
    default_template_id: str | None
    writing_tone: WritingTone
    objectivity: ObjectivityLevel
    technical_level: TechnicalLevel
    auto_conclusions: bool
    auto_next_steps: bool
    auto_impact: bool
    auto_describe_images: bool
    auto_explain_charts: bool
    personal_prompt: str
    about_me: str = ""

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: str
    email: str
    employee_id: str
    name: str
    department: str
    role: UserRole
    sector: QualitySector
    photo_url: str | None
    is_active: bool
    is_admin: bool = False
    writing_profile: WritingProfileResponse | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: str | None = None
    role: UserRole | None = None
    sector: QualitySector | None = None
    photo_url: str | None = None
