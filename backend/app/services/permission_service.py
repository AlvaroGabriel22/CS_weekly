"""Permission and ACL service for QWI"""
from datetime import datetime, UTC, timedelta
from typing import Optional
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import User, UserRole, Activity, WeeklyReport, Attachment, MANAGEMENT_ROLES
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


class PermissionService:
    """Service for managing permissions and ACLs"""

    ADMIN_ROLES = {"Gerente Sr", "Gerente PL", "Gerente Jr", "Chefe"}
    SUPERVISOR_ROLES = {"Supervisor", "Chefe"}

    @staticmethod
    def can_view_weekly_report(user: User, weekly_report: WeeklyReport, db: Session) -> bool:
        """
        Check if user can view a weekly report based on ACL rules:
        - User owns the report (owner)
        - User has explicit permission
        - User is manager/chief (can see all)
        - User is in same department
        """
        # Owners always have access
        if weekly_report.user_id == user.id:
            return True

        # Admins/Managers have access to all weeklys
        if PermissionService._is_privileged_role(user):
            return True

        # Check explicit permissions
        permission = db.query(WeeklyPermission).filter(
            and_(
                WeeklyPermission.weekly_report_id == weekly_report.id,
                WeeklyPermission.user_id == user.id,
            )
        ).first()

        if permission:
            # Check if permission expired
            if permission.expires_at and permission.expires_at < datetime.now(UTC):
                return False
            return permission.permission_level != PermissionLevel.NONE

        # Check department-level access
        report_owner = db.query(User).filter(User.id == weekly_report.user_id).first()
        if report_owner and report_owner.department == user.department:
            return True

        return False

    @staticmethod
    def can_edit_weekly_report(user: User, weekly_report: WeeklyReport, db: Session) -> bool:
        """
        Check if user can edit a weekly report:
        - User owns the report
        - User is manager/chief with explicit edit permission
        """
        # Owners can edit
        if weekly_report.user_id == user.id:
            return True

        # Check explicit edit permission
        permission = db.query(WeeklyPermission).filter(
            and_(
                WeeklyPermission.weekly_report_id == weekly_report.id,
                WeeklyPermission.user_id == user.id,
                WeeklyPermission.permission_level.in_([PermissionLevel.EDITOR, PermissionLevel.OWNER]),
            )
        ).first()

        if permission:
            if permission.expires_at and permission.expires_at < datetime.now(UTC):
                return False
            return True

        return False

    @staticmethod
    def can_view_activity(user: User, activity: Activity, db: Session) -> bool:
        """
        Check if user can view an activity:
        - User owns it
        - User is manager/chief
        - User has explicit share permission
        - User is in same department
        """
        # Owner can view
        if activity.user_id == user.id:
            return True

        # Admins can view all
        if PermissionService._is_privileged_role(user):
            return True

        # Check explicit share
        share = db.query(ActivityShare).filter(
            and_(
                ActivityShare.activity_id == activity.id,
                ActivityShare.shared_with_user_id == user.id,
            )
        ).first()

        if share and share.permission_level != PermissionLevel.NONE:
            return True

        # Check department access
        activity_owner = db.query(User).filter(User.id == activity.user_id).first()
        if activity_owner and activity_owner.department == user.department:
            return True

        return False

    @staticmethod
    def can_share_activity(user: User, activity: Activity, db: Session) -> bool:
        """Check if user can share an activity"""
        # Owner can share
        if activity.user_id == user.id:
            return True

        # Check role permissions in department_roles
        dept_role = db.query(DepartmentRole).filter(
            and_(
                DepartmentRole.department == user.department,
                DepartmentRole.role == user.role.value,
            )
        ).first()

        if dept_role and dept_role.can_share_activities:
            return True

        return False

    @staticmethod
    def share_activity(
        activity: Activity,
        shared_by_user: User,
        shared_with_user_id: str,
        permission_level: PermissionLevel = PermissionLevel.VIEWER,
        db: Session = None,
    ) -> ActivityShare:
        """Share an activity with another user"""
        # Verify sharer has permission
        if not PermissionService.can_share_activity(shared_by_user, activity, db):
            raise PermissionError(f"User {shared_by_user.id} cannot share activities")

        # Check if already shared
        existing = db.query(ActivityShare).filter(
            and_(
                ActivityShare.activity_id == activity.id,
                ActivityShare.shared_with_user_id == shared_with_user_id,
            )
        ).first()

        if existing:
            existing.permission_level = permission_level
            existing.updated_at = datetime.now(UTC)
        else:
            existing = ActivityShare(
                activity_id=activity.id,
                shared_by_user_id=shared_by_user.id,
                shared_with_user_id=shared_with_user_id,
                permission_level=permission_level,
            )
            db.add(existing)

        db.commit()
        return existing

    @staticmethod
    def grant_weekly_permission(
        weekly_report: WeeklyReport,
        user_id: str,
        permission_level: PermissionLevel = PermissionLevel.VIEWER,
        access_scope: AccessScope = AccessScope.PERSONAL,
        expires_in_days: Optional[int] = None,
        granted_by_user: Optional[User] = None,
        db: Session = None,
    ) -> WeeklyPermission:
        """Grant permission to access a weekly report"""
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        # Check if permission exists
        existing = db.query(WeeklyPermission).filter(
            and_(
                WeeklyPermission.weekly_report_id == weekly_report.id,
                WeeklyPermission.user_id == user_id,
            )
        ).first()

        if existing:
            existing.permission_level = permission_level
            existing.access_scope = access_scope
            existing.expires_at = expires_at
            existing.updated_at = datetime.now(UTC)
        else:
            existing = WeeklyPermission(
                weekly_report_id=weekly_report.id,
                user_id=user_id,
                permission_level=permission_level,
                access_scope=access_scope,
                expires_at=expires_at,
            )
            db.add(existing)

        db.commit()
        return existing

    @staticmethod
    def auto_grant_department_weekly_access(weekly_report: WeeklyReport, db: Session) -> list[WeeklyPermission]:
        """
        Automatically grant weekly access to all department members.
        Department members can view each other's weeklys.
        """
        report_owner = db.query(User).filter(User.id == weekly_report.user_id).first()
        if not report_owner:
            return []

        # Get all active users in same department (excluding owner)
        dept_users = db.query(User).filter(
            and_(
                User.department == report_owner.department,
                User.id != weekly_report.user_id,
                User.is_active == True,
            )
        ).all()

        permissions = []
        for user in dept_users:
            permission = PermissionService.grant_weekly_permission(
                weekly_report,
                user.id,
                permission_level=PermissionLevel.VIEWER,
                access_scope=AccessScope.DEPARTMENT,
                db=db,
            )
            permissions.append(permission)

        return permissions

    @staticmethod
    def auto_grant_manager_access(weekly_report: WeeklyReport, db: Session) -> list[WeeklyPermission]:
        """
        Automatically grant access to all managers/chiefs.
        Managers have access to ALL weeklys in the organization.
        """
        # Get all active managers/chiefs
        managers = db.query(User).filter(
            and_(
                User.is_active == True,
                User.role.in_(MANAGEMENT_ROLES),
            )
        ).all()

        permissions = []
        for manager in managers:
            permission = PermissionService.grant_weekly_permission(
                weekly_report,
                manager.id,
                permission_level=PermissionLevel.VIEWER,
                access_scope=AccessScope.ORGANIZATION,
                db=db,
            )
            permissions.append(permission)

        return permissions

    @staticmethod
    def share_file(
        attachment: Attachment,
        shared_by_user: User,
        shared_with_department: Optional[str] = None,
        shared_with_user_id: Optional[str] = None,
        permission_level: PermissionLevel = PermissionLevel.VIEWER,
        expires_in_days: Optional[int] = None,
        db: Session = None,
    ) -> FileShare:
        """Share a file with department or specific user"""
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        file_share = FileShare(
            attachment_id=attachment.id,
            shared_by_user_id=shared_by_user.id,
            shared_with_department=shared_with_department,
            shared_with_user_id=shared_with_user_id,
            permission_level=permission_level,
            access_scope=AccessScope.DEPARTMENT if shared_with_department else AccessScope.PERSONAL,
            expires_at=expires_at,
        )
        db.add(file_share)
        db.commit()
        return file_share

    @staticmethod
    def can_download_file(user: User, attachment: Attachment, db: Session) -> bool:
        """
        Check if user can download/view a file:
        - User owns the activity containing the file
        - User is manager
        - User has explicit file share
        - File is auto-shared with department
        """
        # Get activity owner
        activity = db.query(Activity).filter(Activity.id == attachment.activity_id).first()
        if not activity:
            return False

        # Owner can download
        if activity.user_id == user.id:
            return True

        # Managers can download all files
        if PermissionService._is_privileged_role(user):
            return True

        # Check explicit file share
        file_share = db.query(FileShare).filter(
            and_(
                FileShare.attachment_id == attachment.id,
                or_(
                    FileShare.shared_with_user_id == user.id,
                    FileShare.shared_with_department == user.department,
                ),
            )
        ).first()

        if file_share:
            if file_share.expires_at and file_share.expires_at < datetime.now(UTC):
                return False
            return file_share.permission_level != PermissionLevel.NONE

        # Check department auto-share
        activity_owner = db.query(User).filter(User.id == activity.user_id).first()
        if activity_owner and activity_owner.department == user.department:
            dept_role = db.query(DepartmentRole).filter(
                and_(
                    DepartmentRole.department == activity_owner.department,
                    DepartmentRole.role == activity_owner.role.value,
                )
            ).first()
            if dept_role and dept_role.auto_share_files_with_department:
                return True

        return False

    @staticmethod
    def log_audit(
        user_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: str,
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        db: Session = None,
    ) -> AuditLog:
        """Log an action for audit trail"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
        )
        db.add(audit_log)
        db.commit()
        return audit_log

    @staticmethod
    def log_permission_change(
        audit_log_id: str,
        target_user_id: str,
        resource_type: str,
        resource_id: str,
        changed_by_user_id: Optional[str] = None,
        old_permission_level: Optional[str] = None,
        new_permission_level: Optional[str] = None,
        old_access_scope: Optional[str] = None,
        new_access_scope: Optional[str] = None,
        reason: Optional[str] = None,
        db: Session = None,
    ) -> PermissionChange:
        """Log a permission change for compliance"""
        perm_change = PermissionChange(
            audit_log_id=audit_log_id,
            changed_by_user_id=changed_by_user_id,
            target_user_id=target_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            old_permission_level=old_permission_level,
            new_permission_level=new_permission_level,
            old_access_scope=old_access_scope,
            new_access_scope=new_access_scope,
            reason=reason,
        )
        db.add(perm_change)
        db.commit()
        return perm_change

    @staticmethod
    def _is_privileged_role(user: User) -> bool:
        """Check if user has a privileged role (manager/chief/supervisor)"""
        return user.role in MANAGEMENT_ROLES

    @staticmethod
    def get_accessible_weeklies(user: User, db: Session) -> list[WeeklyReport]:
        """Get all weeklies accessible to user"""
        # Start with owned weeklies
        owned = db.query(WeeklyReport).filter(WeeklyReport.user_id == user.id).all()

        # If manager, add all weeklies
        if PermissionService._is_privileged_role(user):
            all_weeklies = db.query(WeeklyReport).all()
            return list(set(owned + all_weeklies))

        # Add department weeklies
        dept_weeklies = db.query(WeeklyReport).join(User).filter(
            and_(
                User.department == user.department,
                WeeklyReport.user_id != user.id,
            )
        ).all()

        # Add explicitly shared weeklies
        shared_weeklies = db.query(WeeklyReport).join(WeeklyPermission).filter(
            and_(
                WeeklyPermission.user_id == user.id,
                WeeklyPermission.permission_level != PermissionLevel.NONE,
            )
        ).all()

        return list(set(owned + dept_weeklies + shared_weeklies))

    @staticmethod
    def get_accessible_activities(user: User, db: Session) -> list[Activity]:
        """Get all activities accessible to user"""
        # Own activities
        owned = db.query(Activity).filter(Activity.user_id == user.id).all()

        # Manager activities
        if PermissionService._is_privileged_role(user):
            all_activities = db.query(Activity).all()
            return list(set(owned + all_activities))

        # Department activities
        dept_activities = db.query(Activity).join(User).filter(
            and_(
                User.department == user.department,
                Activity.user_id != user.id,
            )
        ).all()

        # Shared activities
        shared_activities = db.query(Activity).join(ActivityShare).filter(
            and_(
                ActivityShare.shared_with_user_id == user.id,
                ActivityShare.permission_level != PermissionLevel.NONE,
            )
        ).all()

        return list(set(owned + dept_activities + shared_activities))

    @staticmethod
    def check_permission(
        user: User,
        resource_id: str,
        action: str,
        resource_type: str = "weekly",
        db: Session = None,
    ) -> bool:
        """
        Unified permission check method

        Actions: view, edit, delete, share
        Resource types: weekly, activity, file
        """
        if resource_type == "weekly":
            if action == "view":
                return PermissionService.can_view_weekly_report(user, db.query(WeeklyReport).filter(WeeklyReport.id == resource_id).first(), db)
            elif action == "edit":
                return PermissionService.can_edit_weekly_report(user, db.query(WeeklyReport).filter(WeeklyReport.id == resource_id).first(), db)
        elif resource_type == "activity":
            if action == "view":
                return PermissionService.can_view_activity(user, db.query(Activity).filter(Activity.id == resource_id).first(), db)
            elif action == "share":
                return PermissionService.can_share_activity(user, db.query(Activity).filter(Activity.id == resource_id).first(), db)
        elif resource_type == "file":
            if action == "download":
                return PermissionService.can_download_file(user, db.query(Attachment).filter(Attachment.id == resource_id).first(), db)

        return False

    @staticmethod
    def get_accessible_weeklies_paginated(
        user: User,
        db: Session,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[WeeklyReport], int]:
        """Get accessible weeklies with pagination"""
        # Start with owned weeklies
        owned_query = db.query(WeeklyReport).filter(WeeklyReport.user_id == user.id)

        # If manager, get all
        if PermissionService._is_privileged_role(user):
            query = db.query(WeeklyReport)
        else:
            # Build combined query
            from sqlalchemy import union

            dept_query = db.query(WeeklyReport).join(User).filter(
                and_(
                    User.department == user.department,
                    WeeklyReport.user_id != user.id,
                )
            )

            shared_query = db.query(WeeklyReport).join(WeeklyPermission).filter(
                and_(
                    WeeklyPermission.user_id == user.id,
                    WeeklyPermission.permission_level != PermissionLevel.NONE,
                )
            )

            query = owned_query.union(dept_query).union(shared_query)

        total = query.count()
        items = query.order_by(db.query(WeeklyReport).desc(WeeklyReport.created_at)).offset(skip).limit(limit).all()

        return items, total
