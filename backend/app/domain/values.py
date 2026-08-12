"""Domain Value Objects - immutable, type-safe domain concepts"""
import enum
from dataclasses import dataclass
from datetime import datetime, date
from typing import Literal
from uuid import UUID, uuid4


# ============================================================================
# Identifiers - Type-safe ID value objects
# ============================================================================

@dataclass(frozen=True)
class UserId:
    """Type-safe user identifier"""
    value: str

    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("UserId must be a non-empty string")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ActivityId:
    """Type-safe activity identifier"""
    value: str

    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("ActivityId must be a non-empty string")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class WeeklyReportId:
    """Type-safe weekly report identifier"""
    value: str

    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("WeeklyReportId must be a non-empty string")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DepartmentId:
    """Type-safe department identifier"""
    value: str

    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("DepartmentId must be a non-empty string")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AttachmentId:
    """Type-safe attachment identifier"""
    value: str

    def __init__(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("AttachmentId must be a non-empty string")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Enumerations - Strong typing for domain concepts
# ============================================================================

class Permission(str, enum.Enum):
    """Permission levels in the system"""
    OWNER = "owner"        # Full control, can share, delete
    EDITOR = "editor"      # Can view and edit
    VIEWER = "viewer"      # Read-only access
    NONE = "none"          # Explicitly no access


class Role(str, enum.Enum):
    """User roles in the organization"""
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


class Sector(str, enum.Enum):
    """Quality sectors in the organization"""
    QM = "QM"           # Quality Management
    QA = "QA"           # Quality Assurance
    OQC = "OQC"         # Outgoing Quality Control
    IQC = "IQC"         # Incoming Quality Control
    FIELD = "FIELD"     # Field operations
    CSI = "CSI"         # Customer Service Index


class ActivityStatus(str, enum.Enum):
    """Status of an activity in its lifecycle"""
    DRAFT = "draft"
    REGISTERED = "registered"
    PROCESSED = "processed"
    USED_IN_REPORT = "used_in_report"


class WeeklyStatus(str, enum.Enum):
    """Status of a weekly report generation"""
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class AccessScope(str, enum.Enum):
    """Scope of access for permissions"""
    PERSONAL = "personal"              # Only for the owner
    DEPARTMENT = "department"          # Department-wide access
    ORGANIZATION = "organization"      # Organization-wide access


class ImageUsage(str, enum.Enum):
    """How images are used in the system"""
    STORE_ONLY = "store_only"          # Just storage
    INSERT_REPORT = "insert_report"    # Include in generated report
    AI_INTERPRET = "ai_interpret"      # AI will interpret the image
    AI_CAPTION = "ai_caption"          # Generate caption with AI
    AI_EVIDENCE = "ai_evidence"        # Use as evidence in analysis


class WritingTone(str, enum.Enum):
    """Writing tone preferences"""
    ANALYST = "analyst"
    SPECIALIST = "specialist"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    DIRECTOR = "director"


class Language(str, enum.Enum):
    """Supported languages"""
    PT = "pt"  # Portuguese
    EN = "en"  # English


class ObjectivityLevel(str, enum.Enum):
    """Technical objectivity level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TechnicalLevel(str, enum.Enum):
    """Technical detail level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# Date Range Value Objects
# ============================================================================

@dataclass(frozen=True)
class DateRange:
    """A period of time with start and end dates"""
    start_date: date
    end_date: date

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")

    def contains(self, check_date: date) -> bool:
        """Check if a date is within this range"""
        return self.start_date <= check_date <= self.end_date

    def overlaps(self, other: "DateRange") -> bool:
        """Check if this range overlaps with another"""
        return self.start_date <= other.end_date and other.start_date <= self.end_date

    def duration_days(self) -> int:
        """Get duration in days"""
        return (self.end_date - self.start_date).days + 1


@dataclass(frozen=True)
class WeekRange:
    """A specific week and year"""
    week_number: int
    year: int

    def __post_init__(self):
        if not 1 <= self.week_number <= 53:
            raise ValueError("week_number must be between 1 and 53")
        if self.year < 1900 or self.year > 2100:
            raise ValueError("year must be between 1900 and 2100")

    def __str__(self) -> str:
        return f"W{self.week_number:02d}/{self.year}"


# ============================================================================
# Complex Value Objects
# ============================================================================

@dataclass(frozen=True)
class WritingProfile:
    """User writing preferences and style"""
    default_language: Language = Language.PT
    writing_tone: WritingTone = WritingTone.SPECIALIST
    objectivity: ObjectivityLevel = ObjectivityLevel.HIGH
    technical_level: TechnicalLevel = TechnicalLevel.MEDIUM
    auto_conclusions: bool = True
    auto_next_steps: bool = True
    auto_impact: bool = True
    auto_describe_images: bool = True
    auto_explain_charts: bool = True
    personal_prompt: str = ""

    def __post_init__(self):
        if not isinstance(self.personal_prompt, str):
            raise ValueError("personal_prompt must be a string")


@dataclass(frozen=True)
class UserPreferences:
    """User preferences and settings"""
    writing_profile: WritingProfile
    preferred_sector: Sector = Sector.CSI
    preferred_department: str = "Qualidade"

    def __post_init__(self):
        if not self.preferred_department or not isinstance(self.preferred_department, str):
            raise ValueError("preferred_department must be a non-empty string")


@dataclass(frozen=True)
class FileMetadata:
    """Metadata for file attachments"""
    filename: str
    original_filename: str
    file_path: str
    file_type: str
    file_size: int
    mime_type: str = "application/octet-stream"

    def __post_init__(self):
        if self.file_size < 0:
            raise ValueError("file_size must be non-negative")
        if not self.filename or not self.file_path:
            raise ValueError("filename and file_path are required")


@dataclass(frozen=True)
class ActivityMetadata:
    """AI-processed metadata for activities"""
    project: str | None = None
    supplier: str | None = None
    line: str | None = None
    process: str | None = None
    product: str | None = None
    category: str | None = None
    activity_type: str | None = None
    defect_type: str | None = None
    related_kpis: list[str] | None = None
    keywords: list[str] | None = None
    technical_summary: str | None = None
    processed_at: datetime | None = None

    def __post_init__(self):
        # Normalize lists
        if self.related_kpis is None:
            object.__setattr__(self, "related_kpis", [])
        if self.keywords is None:
            object.__setattr__(self, "keywords", [])


@dataclass(frozen=True)
class ImageInfo:
    """Information about an image attachment"""
    usage: ImageUsage
    manual_caption: str | None = None
    ai_caption: str | None = None
    ai_analysis: dict | None = None
    kpi_data: dict | None = None


@dataclass(frozen=True)
class PermissionGrant:
    """Represents a permission granted to a user"""
    permission_level: Permission
    access_scope: AccessScope
    expires_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if the permission has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if permission is valid (not expired and not NONE)"""
        return self.permission_level != Permission.NONE and not self.is_expired()

    def can_view(self) -> bool:
        """Check if permission allows viewing"""
        return self.is_valid() and self.permission_level in [
            Permission.OWNER,
            Permission.EDITOR,
            Permission.VIEWER,
        ]

    def can_edit(self) -> bool:
        """Check if permission allows editing"""
        return self.is_valid() and self.permission_level in [
            Permission.OWNER,
            Permission.EDITOR,
        ]

    def can_share(self) -> bool:
        """Check if permission allows sharing"""
        return self.is_valid() and self.permission_level == Permission.OWNER
