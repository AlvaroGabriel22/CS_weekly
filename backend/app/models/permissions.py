"""ACL and Permission models for PostgreSQL"""
import enum
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.postgres_models import EnumCol


def generate_uuid() -> str:
    """Generate UUID string for primary key"""
    return str(uuid.uuid4())


class PermissionLevel(str, enum.Enum):
    """Permission hierarchy levels"""
    OWNER = "owner"  # Full access (creator/owner)
    EDITOR = "editor"  # Can edit and view
    VIEWER = "viewer"  # Read-only access
    NONE = "none"  # No access


class AccessScope(str, enum.Enum):
    """Scope of access for permissions"""
    PERSONAL = "personal"  # Only for self
    DEPARTMENT = "department"  # Department-wide
    ORGANIZATION = "organization"  # Organization-wide


class ActivityShare(Base):
    """Activities compartilhadas entre usuários"""
    __tablename__ = "activity_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    activity_id: Mapped[str] = mapped_column(String(36), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    shared_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_with_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    permission_level: Mapped[PermissionLevel] = mapped_column(EnumCol(PermissionLevel), default=PermissionLevel.VIEWER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("activity_id", "shared_with_user_id", name="uq_activity_share_unique"),
        Index("ix_activity_shares_activity_id", "activity_id"),
        Index("ix_activity_shares_shared_with_user_id", "shared_with_user_id"),
        Index("ix_activity_shares_shared_by_user_id", "shared_by_user_id"),
    )


class WeeklyPermission(Base):
    """Weeklys acessíveis por departamento/role"""
    __tablename__ = "weekly_permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    weekly_report_id: Mapped[str] = mapped_column(String(36), ForeignKey("weekly_reports.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    permission_level: Mapped[PermissionLevel] = mapped_column(EnumCol(PermissionLevel), default=PermissionLevel.VIEWER)
    access_scope: Mapped[AccessScope] = mapped_column(EnumCol(AccessScope), default=AccessScope.PERSONAL)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("weekly_report_id", "user_id", name="uq_weekly_permission_unique"),
        Index("ix_weekly_permissions_weekly_report_id", "weekly_report_id"),
        Index("ix_weekly_permissions_user_id", "user_id"),
        Index("ix_weekly_permissions_department", "department"),
        Index("ix_weekly_permissions_expires_at", "expires_at"),
    )


class FileShare(Base):
    """Arquivos compartilhados entre departamento"""
    __tablename__ = "file_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    attachment_id: Mapped[str] = mapped_column(String(36), ForeignKey("attachments.id", ondelete="CASCADE"), nullable=False)
    shared_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_with_department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shared_with_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    permission_level: Mapped[PermissionLevel] = mapped_column(EnumCol(PermissionLevel), default=PermissionLevel.VIEWER)
    access_scope: Mapped[AccessScope] = mapped_column(EnumCol(AccessScope), default=AccessScope.DEPARTMENT)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_file_shares_attachment_id", "attachment_id"),
        Index("ix_file_shares_shared_by_user_id", "shared_by_user_id"),
        Index("ix_file_shares_shared_with_department", "shared_with_department"),
        Index("ix_file_shares_shared_with_user_id", "shared_with_user_id"),
        Index("ix_file_shares_expires_at", "expires_at"),
    )


class AuditLog(Base):
    """Audit log for compliance and tracking"""
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, failure, partial
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("ix_audit_log_user_id", "user_id"),
        Index("ix_audit_log_resource_type_id", "resource_type", "resource_id"),
        Index("ix_audit_log_action", "action"),
        Index("ix_audit_log_created_at_desc", "created_at"),
    )


class PermissionChange(Base):
    """Permission changes for compliance and audit trail"""
    __tablename__ = "permission_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    audit_log_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit_log.id", ondelete="CASCADE"), nullable=False)
    changed_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    old_permission_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_permission_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    old_access_scope: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_access_scope: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index("ix_permission_changes_target_user_id", "target_user_id"),
        Index("ix_permission_changes_changed_by_user_id", "changed_by_user_id"),
        Index("ix_permission_changes_resource_type_id", "resource_type", "resource_id"),
        Index("ix_permission_changes_created_at", "created_at"),
    )


class DepartmentRole(Base):
    """Mapeamento de roles por departamento para ACL"""
    __tablename__ = "department_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    can_share_activities: Mapped[bool] = mapped_column(Boolean, default=True)
    can_share_files: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_all_weekly: Mapped[bool] = mapped_column(Boolean, default=False)
    can_edit_weekly: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_share_files_with_department: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("department", "role", name="uq_department_role"),
        Index("ix_department_roles_department", "department"),
        Index("ix_department_roles_role", "role"),
    )
