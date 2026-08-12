"""Domain Entities - Business logic and rules encapsulated in aggregates"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.exceptions import (
    PermissionDenied,
    InsufficientPermissions,
    CannotShareWithSelf,
    CannotModifyActivity,
    InvalidActivityStatus,
    ActivityNotFound,
    UserNotActive,
    UserNotInDepartment,
    PermissionExpired,
    UnauthorizedAccess,
)
from app.domain.values import (
    UserId,
    ActivityId,
    WeeklyReportId,
    DepartmentId,
    AttachmentId,
    Permission,
    Role,
    Sector,
    ActivityStatus,
    WeeklyStatus,
    AccessScope,
    WritingProfile,
    UserPreferences,
    FileMetadata,
    ActivityMetadata,
    ImageInfo,
    PermissionGrant,
    Language,
)


# ============================================================================
# User Aggregate Root
# ============================================================================

@dataclass
class UserAggregate:
    """User aggregate with permissions, preferences, and identity"""

    user_id: UserId
    email: str
    employee_id: str
    name: str
    department: str
    role: Role
    sector: Sector
    is_active: bool
    is_admin: bool
    preferences: UserPreferences
    photo_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def assert_is_active(self) -> None:
        """Ensure user is active"""
        if not self.is_active:
            raise UserNotActive(str(self.user_id))

    def is_in_department(self, department_name: str) -> bool:
        """Check if user is in the given department"""
        return self.department.lower() == department_name.lower()

    def assert_in_department(self, department_name: str) -> None:
        """Ensure user is in the given department"""
        if not self.is_in_department(department_name):
            raise UserNotInDepartment(str(self.user_id), department_name)

    def has_higher_or_equal_role(self, other_role: Role) -> bool:
        """Check if this user has a higher or equal organizational role"""
        role_hierarchy = {
            Role.GERENTE_SR: 10,
            Role.GERENTE_PL: 9,
            Role.GERENTE_JR: 8,
            Role.CHEFE: 7,
            Role.SUPERVISOR: 7,
            Role.ANALISTA_ENG_SR: 6,
            Role.ANALISTA_ENG_PL: 5,
            Role.ANALISTA_ENG_JR: 4,
            Role.ANALISTA_SR: 3,
            Role.ANALISTA_PL: 2,
            Role.ANALISTA_JR: 1,
            Role.AUDITOR_SR: 6,
            Role.AUDITOR_PL: 5,
            Role.AUDITOR_JR: 4,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(other_role, 0)

    def can_manage_users(self) -> bool:
        """Check if user can manage other users (typically managers and above)"""
        return self.is_admin or self.has_higher_or_equal_role(Role.GERENTE_JR)


# ============================================================================
# Activity Aggregate Root
# ============================================================================

@dataclass
class ActivityAggregate:
    """Activity aggregate with business logic and sharing rules"""

    activity_id: ActivityId
    user_id: UserId
    title: str
    department: str
    activity_date: datetime
    status: ActivityStatus
    week_number: int
    year: int
    description: Optional[str] = None
    project: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    notes: Optional[str] = None
    include_in_weekly: bool = True
    metadata: Optional[ActivityMetadata] = None
    attachments: dict[str, AttachmentId] = field(default_factory=dict)
    shares: dict[str, Permission] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def assert_can_be_modified_by(self, user_id: UserId) -> None:
        """Verify user can modify this activity"""
        if self.user_id != user_id and user_id not in self.shares:
            raise PermissionDenied(
                str(user_id), "modify", f"activity {self.activity_id}"
            )

        # Only EDITOR or OWNER permissions can modify
        if user_id in self.shares:
            permission = self.shares[user_id]
            if permission not in [Permission.EDITOR, Permission.OWNER]:
                raise InsufficientPermissions(
                    str(user_id), permission.value, Permission.EDITOR.value
                )

    def assert_can_view_by(self, user_id: UserId) -> None:
        """Verify user can view this activity"""
        is_owner = self.user_id == user_id
        is_shared = user_id in self.shares
        is_shared_and_valid = is_shared and self.shares[user_id] != Permission.NONE

        if not (is_owner or is_shared_and_valid):
            raise UnauthorizedAccess(str(user_id), str(self.activity_id), "activity")

    def can_be_shared_with(self, target_user_id: UserId) -> bool:
        """Check if activity can be shared with a user"""
        return target_user_id != self.user_id

    def assert_can_share_with(self, by_user_id: UserId, target_user_id: UserId) -> None:
        """Verify user can share this activity"""
        # Only owner can share
        if self.user_id != by_user_id:
            raise PermissionDenied(str(by_user_id), "share", f"activity {self.activity_id}")

        # Cannot share with self
        if target_user_id == by_user_id:
            raise CannotShareWithSelf(str(by_user_id), str(self.activity_id))

    def share_with(
        self, target_user_id: UserId, permission: Permission, by_user_id: UserId
    ) -> None:
        """Share activity with another user"""
        self.assert_can_share_with(by_user_id, target_user_id)
        self.shares[str(target_user_id)] = permission
        self.updated_at = datetime.utcnow()

    def revoke_share(self, target_user_id: UserId, by_user_id: UserId) -> None:
        """Revoke activity share from a user"""
        # Only owner can revoke
        if self.user_id != by_user_id:
            raise PermissionDenied(str(by_user_id), "revoke share", f"activity {self.activity_id}")

        if str(target_user_id) in self.shares:
            del self.shares[str(target_user_id)]
            self.updated_at = datetime.utcnow()

    def add_attachment(self, attachment_id: AttachmentId) -> None:
        """Add an attachment to this activity"""
        self.attachments[str(attachment_id)] = attachment_id
        self.updated_at = datetime.utcnow()

    def remove_attachment(self, attachment_id: AttachmentId) -> None:
        """Remove an attachment from this activity"""
        if str(attachment_id) in self.attachments:
            del self.attachments[str(attachment_id)]
            self.updated_at = datetime.utcnow()

    def can_transition_to(self, new_status: ActivityStatus) -> bool:
        """Check if activity can transition to a new status"""
        transitions = {
            ActivityStatus.DRAFT: [ActivityStatus.REGISTERED],
            ActivityStatus.REGISTERED: [ActivityStatus.PROCESSED, ActivityStatus.DRAFT],
            ActivityStatus.PROCESSED: [ActivityStatus.USED_IN_REPORT],
            ActivityStatus.USED_IN_REPORT: [ActivityStatus.PROCESSED],
        }
        return new_status in transitions.get(self.status, [])

    def transition_to(self, new_status: ActivityStatus) -> None:
        """Transition activity to a new status"""
        if not self.can_transition_to(new_status):
            raise InvalidActivityStatus(
                str(self.activity_id), self.status.value, new_status.value
            )
        self.status = new_status
        self.updated_at = datetime.utcnow()


# ============================================================================
# Weekly Report Aggregate Root
# ============================================================================

@dataclass
class WeeklyReportAggregate:
    """Weekly report aggregate with permissions and sharing rules"""

    weekly_id: WeeklyReportId
    user_id: UserId
    week_number: int
    year: int
    status: WeeklyStatus
    content: Optional[dict] = None
    pptx_path: Optional[str] = None
    prompt_used: Optional[str] = None
    ai_summary: Optional[str] = None
    template_id: Optional[str] = None
    language: Language = Language.PT
    title: Optional[str] = None
    version: int = 1
    coverage: Optional[dict] = None
    confidence_index: Optional[list] = None
    quality_score: Optional[float] = None
    generated_at: Optional[datetime] = None
    permissions: dict[str, PermissionGrant] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def assert_can_view_by(self, user_id: UserId) -> None:
        """Verify user can view this weekly report"""
        is_owner = self.user_id == user_id
        if is_owner:
            return

        # Check if user has permission
        if str(user_id) not in self.permissions:
            raise UnauthorizedAccess(str(user_id), str(self.weekly_id), "weekly_report")

        permission_grant = self.permissions[str(user_id)]
        if not permission_grant.can_view():
            raise UnauthorizedAccess(str(user_id), str(self.weekly_id), "weekly_report")

    def assert_can_edit_by(self, user_id: UserId) -> None:
        """Verify user can edit this weekly report"""
        is_owner = self.user_id == user_id
        if is_owner:
            return

        # Check if user has editor/owner permission
        if str(user_id) not in self.permissions:
            raise PermissionDenied(str(user_id), "edit", f"weekly {self.weekly_id}")

        permission_grant = self.permissions[str(user_id)]
        if not permission_grant.can_edit():
            raise InsufficientPermissions(
                str(user_id),
                permission_grant.permission_level.value,
                Permission.EDITOR.value,
            )

    def assert_can_share_by(self, user_id: UserId) -> None:
        """Verify user can share this weekly report"""
        is_owner = self.user_id == user_id
        if not is_owner:
            if str(user_id) in self.permissions:
                permission_grant = self.permissions[str(user_id)]
                if not permission_grant.can_share():
                    raise PermissionDenied(
                        str(user_id), "share", f"weekly {self.weekly_id}"
                    )
            else:
                raise PermissionDenied(
                    str(user_id), "share", f"weekly {self.weekly_id}"
                )

    def grant_permission(
        self,
        to_user_id: UserId,
        permission: Permission,
        access_scope: AccessScope,
        expires_at: Optional[datetime] = None,
        by_user_id: Optional[UserId] = None,
    ) -> None:
        """Grant permission to a user"""
        # Owner can always grant permissions
        if by_user_id and self.user_id != by_user_id:
            self.assert_can_share_by(by_user_id)

        # Cannot share with self
        if to_user_id == self.user_id:
            raise CannotShareWithSelf(str(self.user_id), str(self.weekly_id))

        grant = PermissionGrant(
            permission_level=permission, access_scope=access_scope, expires_at=expires_at
        )
        self.permissions[str(to_user_id)] = grant
        self.updated_at = datetime.utcnow()

    def revoke_permission(self, from_user_id: UserId, by_user_id: UserId) -> None:
        """Revoke permission from a user"""
        # Only owner can revoke
        if self.user_id != by_user_id:
            raise PermissionDenied(str(by_user_id), "revoke permission", f"weekly {self.weekly_id}")

        if str(from_user_id) in self.permissions:
            del self.permissions[str(from_user_id)]
            self.updated_at = datetime.utcnow()

    def can_transition_to(self, new_status: WeeklyStatus) -> bool:
        """Check if weekly can transition to a new status"""
        transitions = {
            WeeklyStatus.DRAFT: [WeeklyStatus.GENERATING],
            WeeklyStatus.GENERATING: [WeeklyStatus.COMPLETED, WeeklyStatus.FAILED],
            WeeklyStatus.COMPLETED: [WeeklyStatus.GENERATING],
            WeeklyStatus.FAILED: [WeeklyStatus.GENERATING],
        }
        return new_status in transitions.get(self.status, [])

    def transition_to(self, new_status: WeeklyStatus) -> None:
        """Transition weekly to a new status"""
        if not self.can_transition_to(new_status):
            raise InvalidActivityStatus(
                str(self.weekly_id), self.status.value, new_status.value
            )
        self.status = new_status
        self.updated_at = datetime.utcnow()

    def get_accessible_by(self, user_id: UserId) -> bool:
        """Check if accessible by a user"""
        try:
            self.assert_can_view_by(user_id)
            return True
        except UnauthorizedAccess:
            return False


# ============================================================================
# Department Aggregate Root
# ============================================================================

@dataclass
class DepartmentAggregate:
    """Department aggregate managing users, resources, and policies"""

    department_id: DepartmentId
    name: str
    description: Optional[str] = None
    user_ids: set[str] = field(default_factory=set)
    shared_resources: dict[str, list[Permission]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_user(self, user_id: UserId) -> None:
        """Add a user to the department"""
        self.user_ids.add(str(user_id))
        self.updated_at = datetime.utcnow()

    def remove_user(self, user_id: UserId) -> None:
        """Remove a user from the department"""
        if str(user_id) in self.user_ids:
            self.user_ids.discard(str(user_id))
            self.updated_at = datetime.utcnow()

    def has_user(self, user_id: UserId) -> bool:
        """Check if user is in department"""
        return str(user_id) in self.user_ids

    def share_resource(self, resource_id: str, permission: Permission) -> None:
        """Share a resource with the entire department"""
        if resource_id not in self.shared_resources:
            self.shared_resources[resource_id] = []
        if permission not in self.shared_resources[resource_id]:
            self.shared_resources[resource_id].append(permission)
        self.updated_at = datetime.utcnow()

    def user_count(self) -> int:
        """Get number of users in department"""
        return len(self.user_ids)


# ============================================================================
# Attachment Aggregate
# ============================================================================

@dataclass
class AttachmentAggregate:
    """File attachment aggregate with sharing and access rules"""

    attachment_id: AttachmentId
    activity_id: ActivityId
    user_id: UserId
    metadata: FileMetadata
    image_info: Optional[ImageInfo] = None
    shares: dict[str, Permission] = field(default_factory=dict)
    department_shares: dict[str, Permission] = field(default_factory=dict)
    include_in_weekly: bool = True
    download_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def assert_can_view_by(self, user_id: UserId) -> None:
        """Verify user can view this attachment"""
        is_owner = self.user_id == user_id
        is_shared = str(user_id) in self.shares

        if not (is_owner or is_shared):
            raise UnauthorizedAccess(str(user_id), str(self.attachment_id), "attachment")

    def assert_can_download_by(self, user_id: UserId) -> None:
        """Verify user can download this attachment"""
        self.assert_can_view_by(user_id)
        # Access check passed, can download

    def assert_can_share_by(self, user_id: UserId) -> None:
        """Verify user can share this attachment"""
        # Only owner can share
        if self.user_id != user_id:
            raise PermissionDenied(str(user_id), "share", f"attachment {self.attachment_id}")

    def share_with_user(
        self, target_user_id: UserId, permission: Permission, by_user_id: UserId
    ) -> None:
        """Share file with another user"""
        self.assert_can_share_by(by_user_id)

        if target_user_id == by_user_id:
            raise CannotShareWithSelf(str(by_user_id), str(self.attachment_id))

        self.shares[str(target_user_id)] = permission
        self.updated_at = datetime.utcnow()

    def share_with_department(
        self, department_name: str, permission: Permission, by_user_id: UserId
    ) -> None:
        """Share file with an entire department"""
        self.assert_can_share_by(by_user_id)
        self.department_shares[department_name] = permission
        self.updated_at = datetime.utcnow()

    def revoke_user_share(self, target_user_id: UserId, by_user_id: UserId) -> None:
        """Revoke share from a user"""
        self.assert_can_share_by(by_user_id)

        if str(target_user_id) in self.shares:
            del self.shares[str(target_user_id)]
            self.updated_at = datetime.utcnow()

    def revoke_department_share(
        self, department_name: str, by_user_id: UserId
    ) -> None:
        """Revoke share from a department"""
        self.assert_can_share_by(by_user_id)

        if department_name in self.department_shares:
            del self.department_shares[department_name]
            self.updated_at = datetime.utcnow()

    def record_download(self) -> None:
        """Record a download"""
        self.download_count += 1
        self.updated_at = datetime.utcnow()
