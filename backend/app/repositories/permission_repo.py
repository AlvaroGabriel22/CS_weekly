"""Permission Repository - Optimized ACL queries"""
from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from sqlalchemy import (
    and_, or_, not_, desc, func, select, outerjoin,
    Subquery, exists
)

from app.models import User, Activity, WeeklyReport, Attachment, UserRole, MANAGEMENT_ROLES
from app.models.permissions import (
    ActivityShare,
    WeeklyPermission,
    FileShare,
    AuditLog,
    PermissionChange,
    DepartmentRole,
    PermissionLevel,
    AccessScope,
)


class PermissionRepository:
    """Repository for permission and ACL queries"""

    def __init__(self, session: Session):
        self.session = session

    # Weekly Permissions

    def get_accessible_weeklies_optimized(self, user_id: str) -> List[WeeklyReport]:
        """
        Get all weeklies accessible to user with optimized query.
        Includes: owned, department, explicit permissions, manager access
        """
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        query = self.session.query(WeeklyReport).distinct()

        # Subquery 1: Owned by user
        owned = select(WeeklyReport.id).where(WeeklyReport.user_id == user_id)

        # Subquery 2: Manager has access to all
        if self._is_privileged_role(user):
            return self.session.query(WeeklyReport).all()

        # Subquery 3: Department weeklies
        dept_users = select(User.id).where(
            and_(
                User.department == user.department,
                User.id != user_id,
                User.is_active == True,
            )
        )
        dept_weeklies = select(WeeklyReport.id).where(
            WeeklyReport.user_id.in_(dept_users)
        )

        # Subquery 4: Explicitly shared
        explicit_permissions = select(WeeklyPermission.weekly_report_id).where(
            and_(
                WeeklyPermission.user_id == user_id,
                WeeklyPermission.permission_level != PermissionLevel.NONE,
                or_(
                    WeeklyPermission.expires_at.is_(None),
                    WeeklyPermission.expires_at > datetime.now(UTC),
                ),
            )
        )

        # Combine all conditions
        query = self.session.query(WeeklyReport).where(
            or_(
                WeeklyReport.id.in_(owned),
                WeeklyReport.id.in_(dept_weeklies),
                WeeklyReport.id.in_(explicit_permissions),
            )
        )

        return query.all()

    def get_department_weeklies_optimized(self, user_id: str) -> List[WeeklyReport]:
        """Get all weeklies from same department"""
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        return (
            self.session.query(WeeklyReport)
            .join(User, WeeklyReport.user_id == User.id)
            .filter(
                and_(
                    User.department == user.department,
                    WeeklyReport.user_id != user_id,
                )
            )
            .all()
        )

    def get_shared_weeklies_optimized(self, user_id: str) -> List[WeeklyReport]:
        """Get explicitly shared weeklies with permission check"""
        now = datetime.now(UTC)
        return (
            self.session.query(WeeklyReport)
            .join(
                WeeklyPermission,
                WeeklyReport.id == WeeklyPermission.weekly_report_id
            )
            .filter(
                and_(
                    WeeklyPermission.user_id == user_id,
                    WeeklyPermission.permission_level != PermissionLevel.NONE,
                    or_(
                        WeeklyPermission.expires_at.is_(None),
                        WeeklyPermission.expires_at > now,
                    ),
                )
            )
            .all()
        )

    def check_weekly_permission(
        self,
        user_id: str,
        weekly_id: str,
        min_level: PermissionLevel = PermissionLevel.VIEWER
    ) -> bool:
        """Check if user has permission to access weekly report"""
        user = self.session.query(User).filter(User.id == user_id).first()
        weekly = self.session.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()

        if not user or not weekly:
            return False

        # Owner has access
        if weekly.user_id == user_id:
            return True

        # Managers have access to all
        if self._is_privileged_role(user):
            return True

        # Check explicit permission
        perm = self.session.query(WeeklyPermission).filter(
            and_(
                WeeklyPermission.weekly_report_id == weekly_id,
                WeeklyPermission.user_id == user_id,
                WeeklyPermission.permission_level != PermissionLevel.NONE,
                or_(
                    WeeklyPermission.expires_at.is_(None),
                    WeeklyPermission.expires_at > datetime.now(UTC),
                ),
            )
        ).first()

        if perm:
            # Check permission level hierarchy
            level_hierarchy = [PermissionLevel.NONE, PermissionLevel.VIEWER, PermissionLevel.EDITOR, PermissionLevel.OWNER]
            return level_hierarchy.index(perm.permission_level) >= level_hierarchy.index(min_level)

        # Check department access
        weekly_owner = self.session.query(User).filter(User.id == weekly.user_id).first()
        if weekly_owner and weekly_owner.department == user.department:
            return True

        return False

    # Activity Permissions

    def get_accessible_activities_optimized(self, user_id: str) -> List[Activity]:
        """Get all activities accessible to user"""
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # Manager gets all
        if self._is_privileged_role(user):
            return self.session.query(Activity).all()

        # Subquery 1: Owned
        owned = select(Activity.id).where(Activity.user_id == user_id)

        # Subquery 2: Department activities
        dept_users = select(User.id).where(
            and_(
                User.department == user.department,
                User.id != user_id,
                User.is_active == True,
            )
        )
        dept_activities = select(Activity.id).where(
            Activity.user_id.in_(dept_users)
        )

        # Subquery 3: Explicitly shared
        shared_activities = select(ActivityShare.activity_id).where(
            and_(
                ActivityShare.shared_with_user_id == user_id,
                ActivityShare.permission_level != PermissionLevel.NONE,
            )
        )

        return (
            self.session.query(Activity)
            .where(
                or_(
                    Activity.id.in_(owned),
                    Activity.id.in_(dept_activities),
                    Activity.id.in_(shared_activities),
                )
            )
            .all()
        )

    def check_activity_permission(
        self,
        user_id: str,
        activity_id: str,
        min_level: PermissionLevel = PermissionLevel.VIEWER
    ) -> bool:
        """Check if user has permission to access activity"""
        user = self.session.query(User).filter(User.id == user_id).first()
        activity = self.session.query(Activity).filter(Activity.id == activity_id).first()

        if not user or not activity:
            return False

        # Owner
        if activity.user_id == user_id:
            return True

        # Manager
        if self._is_privileged_role(user):
            return True

        # Explicit share
        share = self.session.query(ActivityShare).filter(
            and_(
                ActivityShare.activity_id == activity_id,
                ActivityShare.shared_with_user_id == user_id,
                ActivityShare.permission_level != PermissionLevel.NONE,
            )
        ).first()

        if share:
            level_hierarchy = [PermissionLevel.NONE, PermissionLevel.VIEWER, PermissionLevel.EDITOR, PermissionLevel.OWNER]
            return level_hierarchy.index(share.permission_level) >= level_hierarchy.index(min_level)

        # Department access
        activity_owner = self.session.query(User).filter(User.id == activity.user_id).first()
        if activity_owner and activity_owner.department == user.department:
            return True

        return False

    # Attachment Permissions

    def get_accessible_attachments_optimized(self, user_id: str) -> List[Attachment]:
        """Get all attachments accessible to user"""
        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # Manager gets all
        if self._is_privileged_role(user):
            return self.session.query(Attachment).all()

        # Get accessible activities first
        accessible_activities = self.get_accessible_activities_optimized(user_id)
        activity_ids = [a.id for a in accessible_activities]

        if not activity_ids:
            return []

        return (
            self.session.query(Attachment)
            .filter(Attachment.activity_id.in_(activity_ids))
            .all()
        )

    def check_attachment_permission(
        self,
        user_id: str,
        attachment_id: str,
    ) -> bool:
        """Check if user can access attachment"""
        attachment = self.session.query(Attachment).filter(
            Attachment.id == attachment_id
        ).first()

        if not attachment:
            return False

        # Check activity permission
        return self.check_activity_permission(user_id, attachment.activity_id)

    def get_shared_attachments_optimized(self, user_id: str) -> List[Attachment]:
        """Get attachments shared with user"""
        now = datetime.now(UTC)

        return (
            self.session.query(Attachment)
            .join(FileShare, Attachment.id == FileShare.attachment_id)
            .filter(
                and_(
                    or_(
                        FileShare.shared_with_user_id == user_id,
                        FileShare.shared_with_department == (
                            self.session.query(User.department)
                            .filter(User.id == user_id)
                            .scalar_subquery()
                        ),
                    ),
                    FileShare.permission_level != PermissionLevel.NONE,
                    or_(
                        FileShare.expires_at.is_(None),
                        FileShare.expires_at > now,
                    ),
                )
            )
            .all()
        )

    def can_download_file_optimized(self, user_id: str, attachment_id: str) -> bool:
        """Check if user can download file"""
        user = self.session.query(User).filter(User.id == user_id).first()
        attachment = self.session.query(Attachment).filter(
            Attachment.id == attachment_id
        ).first()

        if not user or not attachment:
            return False

        # Get activity owner
        activity = self.session.query(Activity).filter(
            Activity.id == attachment.activity_id
        ).first()

        if not activity:
            return False

        # Owner can download
        if activity.user_id == user_id:
            return True

        # Manager can download
        if self._is_privileged_role(user):
            return True

        # Check explicit file share
        now = datetime.now(UTC)
        file_share = self.session.query(FileShare).filter(
            and_(
                FileShare.attachment_id == attachment_id,
                or_(
                    FileShare.shared_with_user_id == user_id,
                    FileShare.shared_with_department == user.department,
                ),
                FileShare.permission_level != PermissionLevel.NONE,
                or_(
                    FileShare.expires_at.is_(None),
                    FileShare.expires_at > now,
                ),
            )
        ).first()

        if file_share:
            return True

        # Check department auto-share
        activity_owner = self.session.query(User).filter(
            User.id == activity.user_id
        ).first()

        if activity_owner and activity_owner.department == user.department:
            dept_role = self.session.query(DepartmentRole).filter(
                and_(
                    DepartmentRole.department == activity_owner.department,
                    DepartmentRole.role == activity_owner.role.value,
                )
            ).first()

            if dept_role and dept_role.auto_share_files_with_department:
                return True

        return False

    # Audit & Logging

    def log_permission_check(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        allowed: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log a permission check"""
        audit = AuditLog(
            user_id=user_id,
            action=f"permission_check_{action}",
            resource_type=resource_type,
            resource_id=resource_id,
            status="success" if allowed else "failure",
            ip_address=ip_address,
            user_agent=user_agent,
            changes={"allowed": allowed},
        )
        self.session.add(audit)
        self.session.commit()
        return audit

    def get_user_permission_history(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[PermissionChange]:
        """Get permission changes for a user"""
        return (
            self.session.query(PermissionChange)
            .filter(PermissionChange.target_user_id == user_id)
            .order_by(desc(PermissionChange.created_at))
            .limit(limit)
            .all()
        )

    def get_audit_logs_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs for a specific resource"""
        return (
            self.session.query(AuditLog)
            .filter(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id,
                )
            )
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .all()
        )

    def get_audit_logs_by_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs for a specific user"""
        return (
            self.session.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .all()
        )

    # Role-based Helpers

    def _is_privileged_role(self, user: User) -> bool:
        """Check if user has privileged role"""
        return user.role in MANAGEMENT_ROLES

    def get_department_role(
        self,
        department: str,
        role: str,
    ) -> Optional[DepartmentRole]:
        """Get department role configuration"""
        return (
            self.session.query(DepartmentRole)
            .filter(
                and_(
                    DepartmentRole.department == department,
                    DepartmentRole.role == role,
                )
            )
            .first()
        )

    # Batch Operations

    def bulk_grant_weekly_permission(
        self,
        weekly_id: str,
        user_ids: List[str],
        permission_level: PermissionLevel = PermissionLevel.VIEWER,
        access_scope: AccessScope = AccessScope.PERSONAL,
    ) -> List[WeeklyPermission]:
        """Grant permission to multiple users at once"""
        permissions = []
        for user_id in user_ids:
            existing = self.session.query(WeeklyPermission).filter(
                and_(
                    WeeklyPermission.weekly_report_id == weekly_id,
                    WeeklyPermission.user_id == user_id,
                )
            ).first()

            if existing:
                existing.permission_level = permission_level
                existing.access_scope = access_scope
                permissions.append(existing)
            else:
                perm = WeeklyPermission(
                    weekly_report_id=weekly_id,
                    user_id=user_id,
                    permission_level=permission_level,
                    access_scope=access_scope,
                )
                self.session.add(perm)
                permissions.append(perm)

        self.session.commit()
        return permissions

    def revoke_all_permissions(
        self,
        resource_type: str,
        resource_id: str,
        user_id: str,
    ) -> bool:
        """Revoke all permissions for a user on a resource"""
        if resource_type == "weekly":
            self.session.query(WeeklyPermission).filter(
                and_(
                    WeeklyPermission.weekly_report_id == resource_id,
                    WeeklyPermission.user_id == user_id,
                )
            ).delete()
        elif resource_type == "activity":
            self.session.query(ActivityShare).filter(
                and_(
                    ActivityShare.activity_id == resource_id,
                    ActivityShare.shared_with_user_id == user_id,
                )
            ).delete()
        elif resource_type == "file":
            self.session.query(FileShare).filter(
                and_(
                    FileShare.attachment_id == resource_id,
                    FileShare.shared_with_user_id == user_id,
                )
            ).delete()

        self.session.commit()
        return True
