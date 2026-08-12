"""Domain Permission Rules - Business logic for permission checks"""
from typing import Optional

from app.domain.entities import (
    UserAggregate,
    ActivityAggregate,
    WeeklyReportAggregate,
    AttachmentAggregate,
    DepartmentAggregate,
)
from app.domain.exceptions import (
    PermissionDenied,
    InsufficientPermissions,
    UnauthorizedAccess,
)
from app.domain.values import (
    UserId,
    ActivityId,
    WeeklyReportId,
    AttachmentId,
    Permission,
)


class PermissionRules:
    """Domain permission rules - pure business logic"""

    # ========================================================================
    # Activity Permission Rules
    # ========================================================================

    @staticmethod
    def can_view_activity(user: UserAggregate, activity: ActivityAggregate) -> bool:
        """Check if user can view an activity"""
        user.assert_is_active()
        try:
            activity.assert_can_view_by(user.user_id)
            return True
        except (PermissionDenied, UnauthorizedAccess):
            return False

    @staticmethod
    def can_edit_activity(user: UserAggregate, activity: ActivityAggregate) -> bool:
        """Check if user can edit an activity"""
        user.assert_is_active()
        try:
            activity.assert_can_be_modified_by(user.user_id)
            return True
        except (PermissionDenied, InsufficientPermissions):
            return False

    @staticmethod
    def can_delete_activity(user: UserAggregate, activity: ActivityAggregate) -> bool:
        """Check if user can delete an activity"""
        # Only owner can delete
        return user.user_id == activity.user_id and user.is_active

    @staticmethod
    def can_share_activity(
        sharing_user: UserAggregate,
        activity: ActivityAggregate,
        target_user: UserAggregate,
    ) -> bool:
        """Check if user can share activity with another user"""
        sharing_user.assert_is_active()
        target_user.assert_is_active()

        try:
            activity.assert_can_share_with(sharing_user.user_id, target_user.user_id)
            return True
        except (PermissionDenied, UnauthorizedAccess):
            return False

    @staticmethod
    def get_accessible_activities(
        user: UserAggregate, all_activities: list[ActivityAggregate]
    ) -> list[ActivityAggregate]:
        """Get all activities accessible by user"""
        user.assert_is_active()
        accessible = []
        for activity in all_activities:
            try:
                activity.assert_can_view_by(user.user_id)
                accessible.append(activity)
            except (PermissionDenied, UnauthorizedAccess):
                continue
        return accessible

    # ========================================================================
    # Weekly Report Permission Rules
    # ========================================================================

    @staticmethod
    def can_view_weekly(user: UserAggregate, weekly: WeeklyReportAggregate) -> bool:
        """Check if user can view a weekly report"""
        user.assert_is_active()
        try:
            weekly.assert_can_view_by(user.user_id)
            return True
        except UnauthorizedAccess:
            return False

    @staticmethod
    def can_edit_weekly(user: UserAggregate, weekly: WeeklyReportAggregate) -> bool:
        """Check if user can edit a weekly report"""
        user.assert_is_active()
        try:
            weekly.assert_can_edit_by(user.user_id)
            return True
        except (PermissionDenied, InsufficientPermissions):
            return False

    @staticmethod
    def can_generate_weekly(user: UserAggregate, weekly: WeeklyReportAggregate) -> bool:
        """Check if user can generate a weekly report"""
        # Only owner can generate their weekly
        return (
            user.user_id == weekly.user_id
            and user.is_active
            and weekly.status.value != "generating"
        )

    @staticmethod
    def can_delete_weekly(user: UserAggregate, weekly: WeeklyReportAggregate) -> bool:
        """Check if user can delete a weekly report"""
        # Only owner can delete
        return user.user_id == weekly.user_id and user.is_active

    @staticmethod
    def can_share_weekly(
        sharing_user: UserAggregate,
        weekly: WeeklyReportAggregate,
        target_user: UserAggregate,
    ) -> bool:
        """Check if user can share weekly with another user"""
        sharing_user.assert_is_active()
        target_user.assert_is_active()

        try:
            weekly.assert_can_share_by(sharing_user.user_id)
            return True
        except PermissionDenied:
            return False

    @staticmethod
    def get_accessible_weeklys(
        user: UserAggregate, all_weeklys: list[WeeklyReportAggregate]
    ) -> list[WeeklyReportAggregate]:
        """Get all weekly reports accessible by user"""
        user.assert_is_active()
        accessible = []
        for weekly in all_weeklys:
            try:
                weekly.assert_can_view_by(user.user_id)
                accessible.append(weekly)
            except UnauthorizedAccess:
                continue
        return accessible

    # ========================================================================
    # Attachment/File Permission Rules
    # ========================================================================

    @staticmethod
    def can_view_attachment(user: UserAggregate, attachment: AttachmentAggregate) -> bool:
        """Check if user can view an attachment"""
        user.assert_is_active()
        try:
            attachment.assert_can_view_by(user.user_id)
            return True
        except UnauthorizedAccess:
            return False

    @staticmethod
    def can_download_attachment(
        user: UserAggregate, attachment: AttachmentAggregate
    ) -> bool:
        """Check if user can download an attachment"""
        user.assert_is_active()
        try:
            attachment.assert_can_download_by(user.user_id)
            return True
        except UnauthorizedAccess:
            return False

    @staticmethod
    def can_delete_attachment(user: UserAggregate, attachment: AttachmentAggregate) -> bool:
        """Check if user can delete an attachment"""
        # Only owner can delete
        return user.user_id == attachment.user_id and user.is_active

    @staticmethod
    def can_share_attachment(
        sharing_user: UserAggregate,
        attachment: AttachmentAggregate,
        target_user: UserAggregate,
    ) -> bool:
        """Check if user can share attachment with another user"""
        sharing_user.assert_is_active()
        target_user.assert_is_active()

        try:
            attachment.assert_can_share_by(sharing_user.user_id)
            return True
        except PermissionDenied:
            return False

    @staticmethod
    def get_accessible_attachments(
        user: UserAggregate, all_attachments: list[AttachmentAggregate]
    ) -> list[AttachmentAggregate]:
        """Get all attachments accessible by user"""
        user.assert_is_active()
        accessible = []
        for attachment in all_attachments:
            try:
                attachment.assert_can_view_by(user.user_id)
                accessible.append(attachment)
            except UnauthorizedAccess:
                continue
        return accessible

    # ========================================================================
    # Department Permission Rules
    # ========================================================================

    @staticmethod
    def can_view_department(user: UserAggregate, department: DepartmentAggregate) -> bool:
        """Check if user can view a department"""
        user.assert_is_active()
        return department.has_user(user.user_id) or user.is_admin

    @staticmethod
    def can_manage_department(user: UserAggregate, department: DepartmentAggregate) -> bool:
        """Check if user can manage a department"""
        user.assert_is_active()
        # Only admins can manage departments (would be expanded with department admin roles)
        return user.is_admin

    @staticmethod
    def can_add_user_to_department(
        managing_user: UserAggregate, department: DepartmentAggregate
    ) -> bool:
        """Check if user can add users to a department"""
        managing_user.assert_is_active()
        return managing_user.is_admin

    @staticmethod
    def get_user_departments(
        user: UserAggregate, all_departments: list[DepartmentAggregate]
    ) -> list[DepartmentAggregate]:
        """Get all departments a user belongs to"""
        user.assert_is_active()
        if user.is_admin:
            return all_departments
        return [d for d in all_departments if d.has_user(user.user_id)]

    # ========================================================================
    # Cross-Aggregate Permission Rules
    # ========================================================================

    @staticmethod
    def can_include_activity_in_weekly(
        user: UserAggregate,
        activity: ActivityAggregate,
        weekly: WeeklyReportAggregate,
    ) -> bool:
        """Check if user can include activity in weekly report"""
        user.assert_is_active()

        # Must be able to view activity
        if not PermissionRules.can_view_activity(user, activity):
            return False

        # Must be able to edit weekly
        if not PermissionRules.can_edit_weekly(user, weekly):
            return False

        # Activity must be from same week
        return (
            activity.week_number == weekly.week_number
            and activity.year == weekly.year
        )

    @staticmethod
    def can_add_attachment_to_activity(
        user: UserAggregate, activity: ActivityAggregate
    ) -> bool:
        """Check if user can add attachments to an activity"""
        user.assert_is_active()
        return PermissionRules.can_edit_activity(user, activity)

    # ========================================================================
    # Bulk Permission Checks
    # ========================================================================

    @staticmethod
    def filter_activities_by_permission(
        user: UserAggregate,
        activities: list[ActivityAggregate],
        permission: Permission = Permission.VIEWER,
    ) -> list[ActivityAggregate]:
        """Filter activities by user's permission level"""
        user.assert_is_active()
        filtered = []

        for activity in activities:
            if activity.user_id == user.user_id:
                # Owner has full access
                filtered.append(activity)
            elif str(user.user_id) in activity.shares:
                # Check if user's permission meets minimum requirement
                user_permission = activity.shares[str(user.user_id)]
                if PermissionRules._compare_permissions(user_permission, permission) >= 0:
                    filtered.append(activity)

        return filtered

    @staticmethod
    def filter_weeklys_by_permission(
        user: UserAggregate,
        weeklys: list[WeeklyReportAggregate],
        permission: Permission = Permission.VIEWER,
    ) -> list[WeeklyReportAggregate]:
        """Filter weeklys by user's permission level"""
        user.assert_is_active()
        filtered = []

        for weekly in weeklys:
            if weekly.user_id == user.user_id:
                # Owner has full access
                filtered.append(weekly)
            elif str(user.user_id) in weekly.permissions:
                # Check if user's permission meets minimum requirement
                perm_grant = weekly.permissions[str(user.user_id)]
                if perm_grant.is_valid():
                    if (
                        PermissionRules._compare_permissions(
                            perm_grant.permission_level, permission
                        )
                        >= 0
                    ):
                        filtered.append(weekly)

        return filtered

    # ========================================================================
    # Helper Methods
    # ========================================================================

    @staticmethod
    def _compare_permissions(user_perm: Permission, required_perm: Permission) -> int:
        """
        Compare two permissions.
        Returns: 1 if user_perm >= required_perm, 0 if equal, -1 if less
        """
        hierarchy = {
            Permission.OWNER: 3,
            Permission.EDITOR: 2,
            Permission.VIEWER: 1,
            Permission.NONE: 0,
        }
        user_level = hierarchy.get(user_perm, -1)
        required_level = hierarchy.get(required_perm, -1)

        if user_level > required_level:
            return 1
        elif user_level == required_level:
            return 0
        else:
            return -1
