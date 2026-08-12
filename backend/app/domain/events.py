"""Domain Events - immutable events representing state changes in the business domain"""
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.values import (
    UserId,
    ActivityId,
    WeeklyReportId,
    DepartmentId,
    AttachmentId,
    Permission,
    AccessScope,
)


# ============================================================================
# Base Domain Event
# ============================================================================

@dataclass(frozen=True)
class DomainEvent(ABC):
    """Base class for all domain events"""

    event_id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str = ""

    def __init__(self, aggregate_id: str = "", **kwargs):
        object.__setattr__(self, "aggregate_id", aggregate_id)
        for key, value in kwargs.items():
            if hasattr(self, key):
                object.__setattr__(self, key, value)


# ============================================================================
# User-Related Events
# ============================================================================

@dataclass(frozen=True)
class UserCreated(DomainEvent):
    """A new user has been created"""

    user_id: UserId | str
    email: str
    employee_id: str
    name: str
    department: str
    role: str
    sector: str


@dataclass(frozen=True)
class UserActivated(DomainEvent):
    """A user account has been activated"""

    user_id: UserId | str


@dataclass(frozen=True)
class UserDeactivated(DomainEvent):
    """A user account has been deactivated"""

    user_id: UserId | str
    reason: str | None = None


@dataclass(frozen=True)
class UserPreferencesUpdated(DomainEvent):
    """User preferences have been updated"""

    user_id: UserId | str
    changes: dict


@dataclass(frozen=True)
class UserPermissionChanged(DomainEvent):
    """User's permission level has changed"""

    user_id: UserId | str
    resource_id: str
    resource_type: str
    old_permission: str
    new_permission: str


# ============================================================================
# Activity-Related Events
# ============================================================================

@dataclass(frozen=True)
class ActivityCreated(DomainEvent):
    """A new activity has been created"""

    activity_id: ActivityId | str
    user_id: UserId | str
    department_id: DepartmentId | str
    title: str
    description: str | None
    activity_date: datetime


@dataclass(frozen=True)
class ActivityRegistered(DomainEvent):
    """An activity has been registered"""

    activity_id: ActivityId | str
    user_id: UserId | str
    week_number: int
    year: int


@dataclass(frozen=True)
class ActivityProcessed(DomainEvent):
    """An activity has been processed by AI"""

    activity_id: ActivityId | str
    user_id: UserId | str
    metadata: dict
    processed_at: datetime


@dataclass(frozen=True)
class ActivityIncludedInWeekly(DomainEvent):
    """An activity has been included in a weekly report"""

    activity_id: ActivityId | str
    weekly_id: WeeklyReportId | str
    week_number: int
    year: int


@dataclass(frozen=True)
class ActivityShared(DomainEvent):
    """An activity has been shared with another user"""

    activity_id: ActivityId | str
    from_user_id: UserId | str
    to_user_id: UserId | str
    permission_level: str


@dataclass(frozen=True)
class ActivityShareRevoked(DomainEvent):
    """An activity share has been revoked"""

    activity_id: ActivityId | str
    from_user_id: UserId | str
    to_user_id: UserId | str


@dataclass(frozen=True)
class ActivityModified(DomainEvent):
    """An activity has been modified"""

    activity_id: ActivityId | str
    user_id: UserId | str
    changes: dict


@dataclass(frozen=True)
class ActivityDeleted(DomainEvent):
    """An activity has been deleted"""

    activity_id: ActivityId | str
    user_id: UserId | str
    reason: str | None = None


# ============================================================================
# Weekly Report Events
# ============================================================================

@dataclass(frozen=True)
class WeeklyReportCreated(DomainEvent):
    """A new weekly report has been created"""

    weekly_id: WeeklyReportId | str
    user_id: UserId | str
    week_number: int
    year: int
    template_id: str | None = None


@dataclass(frozen=True)
class WeeklyGenerationStarted(DomainEvent):
    """Weekly report generation has started"""

    weekly_id: WeeklyReportId | str
    user_id: UserId | str
    week_number: int
    year: int


@dataclass(frozen=True)
class WeeklyGenerated(DomainEvent):
    """A weekly report has been generated"""

    weekly_id: WeeklyReportId | str
    user_id: UserId | str
    week_number: int
    year: int
    content: dict | None = None
    pptx_path: str | None = None
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class WeeklyGenerationFailed(DomainEvent):
    """Weekly report generation failed"""

    weekly_id: WeeklyReportId | str
    user_id: UserId | str
    error_message: str
    error_code: str | None = None


@dataclass(frozen=True)
class WeeklyShared(DomainEvent):
    """A weekly report has been shared"""

    weekly_id: WeeklyReportId | str
    from_user_id: UserId | str
    to_user_id: UserId | str
    permission_level: str
    access_scope: str


@dataclass(frozen=True)
class WeeklyPermissionChanged(DomainEvent):
    """Weekly report permission has changed"""

    weekly_id: WeeklyReportId | str
    user_id: UserId | str
    old_permission: str
    new_permission: str
    old_scope: str | None = None
    new_scope: str | None = None


@dataclass(frozen=True)
class WeeklyPublished(DomainEvent):
    """A weekly report has been published"""

    weekly_id: WeeklyReportId | str
    user_id: UserId | str
    week_number: int
    year: int
    published_at: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# Attachment/File Events
# ============================================================================

@dataclass(frozen=True)
class FileAttached(DomainEvent):
    """A file has been attached to an activity"""

    attachment_id: AttachmentId | str
    activity_id: ActivityId | str
    user_id: UserId | str
    filename: str
    file_type: str
    file_size: int


@dataclass(frozen=True)
class FileShared(DomainEvent):
    """A file has been shared"""

    attachment_id: AttachmentId | str
    from_user_id: UserId | str
    to_user_id: UserId | str | None = None
    to_department: str | None = None
    permission_level: str = Permission.VIEWER.value
    access_scope: str = AccessScope.DEPARTMENT.value


@dataclass(frozen=True)
class FileShareRevoked(DomainEvent):
    """A file share has been revoked"""

    attachment_id: AttachmentId | str
    from_user_id: UserId | str
    to_user_id: UserId | str | None = None
    to_department: str | None = None


@dataclass(frozen=True)
class FileDeleted(DomainEvent):
    """A file has been deleted"""

    attachment_id: AttachmentId | str
    activity_id: ActivityId | str
    user_id: UserId | str
    reason: str | None = None


@dataclass(frozen=True)
class ImageCaptionGenerated(DomainEvent):
    """An AI-generated caption for an image has been created"""

    attachment_id: AttachmentId | str
    activity_id: ActivityId | str
    user_id: UserId | str
    caption: str


# ============================================================================
# Permission Events
# ============================================================================

@dataclass(frozen=True)
class PermissionGranted(DomainEvent):
    """A permission has been granted"""

    user_id: UserId | str
    resource_id: str
    resource_type: str
    permission_level: str
    access_scope: str
    granted_by: UserId | str
    expires_at: datetime | None = None


@dataclass(frozen=True)
class PermissionRevoked(DomainEvent):
    """A permission has been revoked"""

    user_id: UserId | str
    resource_id: str
    resource_type: str
    revoked_by: UserId | str
    reason: str | None = None


@dataclass(frozen=True)
class PermissionExpired(DomainEvent):
    """A permission has expired"""

    user_id: UserId | str
    resource_id: str
    resource_type: str


# ============================================================================
# Department Events
# ============================================================================

@dataclass(frozen=True)
class DepartmentCreated(DomainEvent):
    """A new department has been created"""

    department_id: DepartmentId | str
    name: str
    description: str | None = None


@dataclass(frozen=True)
class UserAddedToDepartment(DomainEvent):
    """A user has been added to a department"""

    user_id: UserId | str
    department_id: DepartmentId | str
    department_name: str


@dataclass(frozen=True)
class UserRemovedFromDepartment(DomainEvent):
    """A user has been removed from a department"""

    user_id: UserId | str
    department_id: DepartmentId | str
    department_name: str
    reason: str | None = None


@dataclass(frozen=True)
class DepartmentResourceShared(DomainEvent):
    """A resource has been shared with an entire department"""

    resource_id: str
    resource_type: str
    department_id: DepartmentId | str
    department_name: str
    from_user_id: UserId | str
    permission_level: str


# ============================================================================
# Audit Events
# ============================================================================

@dataclass(frozen=True)
class AccessAttempt(DomainEvent):
    """An access attempt has been made"""

    user_id: UserId | str | None
    resource_id: str
    resource_type: str
    action: str
    allowed: bool
    reason: str | None = None


@dataclass(frozen=True)
class SuspiciousActivityDetected(DomainEvent):
    """Suspicious activity has been detected"""

    user_id: UserId | str
    activity_type: str
    description: str
    severity: str  # low, medium, high, critical
