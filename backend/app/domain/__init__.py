"""Domain Layer - Core business logic and rules isolated from infrastructure"""

# ============================================================================
# Value Objects
# ============================================================================
from app.domain.values import (
    # Identifiers
    UserId,
    ActivityId,
    WeeklyReportId,
    DepartmentId,
    AttachmentId,
    # Enumerations
    Permission,
    Role,
    Sector,
    ActivityStatus,
    WeeklyStatus,
    AccessScope,
    ImageUsage,
    WritingTone,
    Language,
    ObjectivityLevel,
    TechnicalLevel,
    # Complex Value Objects
    DateRange,
    WeekRange,
    WritingProfile,
    UserPreferences,
    FileMetadata,
    ActivityMetadata,
    ImageInfo,
    PermissionGrant,
)

# ============================================================================
# Domain Entities (Aggregates)
# ============================================================================
from app.domain.entities import (
    UserAggregate,
    ActivityAggregate,
    WeeklyReportAggregate,
    DepartmentAggregate,
    AttachmentAggregate,
)

# ============================================================================
# Domain Events
# ============================================================================
from app.domain.events import (
    DomainEvent,
    # User Events
    UserCreated,
    UserActivated,
    UserDeactivated,
    UserPreferencesUpdated,
    UserPermissionChanged,
    # Activity Events
    ActivityCreated,
    ActivityRegistered,
    ActivityProcessed,
    ActivityIncludedInWeekly,
    ActivityShared,
    ActivityShareRevoked,
    ActivityModified,
    ActivityDeleted,
    # Weekly Events
    WeeklyReportCreated,
    WeeklyGenerationStarted,
    WeeklyGenerated,
    WeeklyGenerationFailed,
    WeeklyShared,
    WeeklyPermissionChanged,
    WeeklyPublished,
    # Attachment Events
    FileAttached,
    FileShared,
    FileShareRevoked,
    FileDeleted,
    ImageCaptionGenerated,
    # Permission Events
    PermissionGranted,
    PermissionRevoked,
    PermissionExpired,
    # Department Events
    DepartmentCreated,
    UserAddedToDepartment,
    UserRemovedFromDepartment,
    DepartmentResourceShared,
    # Audit Events
    AccessAttempt,
    SuspiciousActivityDetected,
)

# ============================================================================
# Domain Exceptions
# ============================================================================
from app.domain.exceptions import (
    DomainException,
    # Permission Exceptions
    PermissionDenied,
    UnauthorizedAccess,
    CannotShareWithSelf,
    InsufficientPermissions,
    PermissionExpired,
    # User Exceptions
    UserNotActive,
    UserAlreadyExists,
    UserNotFound,
    InvalidEmail,
    InvalidRole,
    # Activity Exceptions
    ActivityNotFound,
    CannotModifyActivity,
    InvalidActivityStatus,
    ActivityAlreadyShared,
    # Weekly Exceptions
    WeeklyReportNotFound,
    WeeklyAlreadyExists,
    CannotGenerateWeekly,
    InvalidWeeklyStatus,
    # Attachment Exceptions
    AttachmentNotFound,
    InvalidFileSize,
    InvalidFileType,
    FileAlreadyShared,
    # Department Exceptions
    DepartmentNotFound,
    InvalidDepartment,
    UserNotInDepartment,
    # Validation Exceptions
    InvalidDateRange,
    InvalidWeekRange,
    BusinessRuleViolation,
)

# ============================================================================
# Permission Rules
# ============================================================================
from app.domain.permission_rules import PermissionRules

# ============================================================================
# Public API
# ============================================================================
__all__ = [
    # Value Objects - Identifiers
    "UserId",
    "ActivityId",
    "WeeklyReportId",
    "DepartmentId",
    "AttachmentId",
    # Value Objects - Enumerations
    "Permission",
    "Role",
    "Sector",
    "ActivityStatus",
    "WeeklyStatus",
    "AccessScope",
    "ImageUsage",
    "WritingTone",
    "Language",
    "ObjectivityLevel",
    "TechnicalLevel",
    # Value Objects - Complex
    "DateRange",
    "WeekRange",
    "WritingProfile",
    "UserPreferences",
    "FileMetadata",
    "ActivityMetadata",
    "ImageInfo",
    "PermissionGrant",
    # Entities
    "UserAggregate",
    "ActivityAggregate",
    "WeeklyReportAggregate",
    "DepartmentAggregate",
    "AttachmentAggregate",
    # Domain Events
    "DomainEvent",
    "UserCreated",
    "UserActivated",
    "UserDeactivated",
    "UserPreferencesUpdated",
    "UserPermissionChanged",
    "ActivityCreated",
    "ActivityRegistered",
    "ActivityProcessed",
    "ActivityIncludedInWeekly",
    "ActivityShared",
    "ActivityShareRevoked",
    "ActivityModified",
    "ActivityDeleted",
    "WeeklyReportCreated",
    "WeeklyGenerationStarted",
    "WeeklyGenerated",
    "WeeklyGenerationFailed",
    "WeeklyShared",
    "WeeklyPermissionChanged",
    "WeeklyPublished",
    "FileAttached",
    "FileShared",
    "FileShareRevoked",
    "FileDeleted",
    "ImageCaptionGenerated",
    "PermissionGranted",
    "PermissionRevoked",
    "PermissionExpired",
    "DepartmentCreated",
    "UserAddedToDepartment",
    "UserRemovedFromDepartment",
    "DepartmentResourceShared",
    "AccessAttempt",
    "SuspiciousActivityDetected",
    # Exceptions
    "DomainException",
    "PermissionDenied",
    "UnauthorizedAccess",
    "CannotShareWithSelf",
    "InsufficientPermissions",
    "UserNotActive",
    "UserAlreadyExists",
    "UserNotFound",
    "InvalidEmail",
    "InvalidRole",
    "ActivityNotFound",
    "CannotModifyActivity",
    "InvalidActivityStatus",
    "ActivityAlreadyShared",
    "WeeklyReportNotFound",
    "WeeklyAlreadyExists",
    "CannotGenerateWeekly",
    "InvalidWeeklyStatus",
    "AttachmentNotFound",
    "InvalidFileSize",
    "InvalidFileType",
    "FileAlreadyShared",
    "DepartmentNotFound",
    "InvalidDepartment",
    "UserNotInDepartment",
    "InvalidDateRange",
    "InvalidWeekRange",
    "BusinessRuleViolation",
    # Permission Rules
    "PermissionRules",
]
