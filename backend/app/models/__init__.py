"""
QWI Models - PostgreSQL optimized with ACL support

This module re-exports all models from the postgres_models module.
All models are now PostgreSQL-optimized with timezone-aware timestamps
and proper constraints.
"""

# Import from postgres_models for backward compatibility
from app.models.postgres_models import (
    # Enums
    Language,
    WritingTone,
    ObjectivityLevel,
    TechnicalLevel,
    ActivityStatus,
    ImageUsage,
    WeeklyStatus,
    QualitySector,
    UserRole,
    MANAGEMENT_ROLES,
    # Models
    User,
    WritingProfile,
    Template,
    Activity,
    ActivityMetadata,
    Attachment,
    WeeklyReport,
    SlideLayoutPref,
    generate_uuid,
)

# Import ACL models
from app.models.permissions import (
    PermissionLevel,
    AccessScope,
    ActivityShare,
    WeeklyPermission,
    FileShare,
    AuditLog,
    PermissionChange,
    DepartmentRole,
)

__all__ = [
    # Enums
    "Language",
    "WritingTone",
    "ObjectivityLevel",
    "TechnicalLevel",
    "ActivityStatus",
    "ImageUsage",
    "WeeklyStatus",
    "QualitySector",
    "UserRole",
    "MANAGEMENT_ROLES",
    "PermissionLevel",
    "AccessScope",
    # Core Models
    "User",
    "WritingProfile",
    "Template",
    "Activity",
    "ActivityMetadata",
    "Attachment",
    "WeeklyReport",
    "SlideLayoutPref",
    # ACL Models
    "ActivityShare",
    "WeeklyPermission",
    "FileShare",
    "AuditLog",
    "PermissionChange",
    "DepartmentRole",
    # Functions
    "generate_uuid",
]
