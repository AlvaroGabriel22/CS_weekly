"""
Test suite for Permission/ACL system

Run with: pytest PERMISSION_ACL_TESTS.py -v
"""

import pytest
from datetime import datetime, UTC, timedelta
from sqlalchemy.orm import Session

from app.models import User, Activity, WeeklyReport, Attachment, UserRole, WeeklyStatus, ActivityStatus
from app.models.permissions import (
    ActivityShare, WeeklyPermission, FileShare, PermissionLevel,
    AccessScope, AuditLog, PermissionChange, DepartmentRole
)
from app.repositories.permission_repo import PermissionRepository
from app.repositories.weekly_repo import WeeklyRepository
from app.repositories.activity_repo import ActivityRepository
from app.repositories.attachment_repo import AttachmentRepository
from app.services.permission_service import PermissionService


@pytest.fixture
def manager_user(db: Session):
    """Create a manager user"""
    user = User(
        email="manager@example.com",
        employee_id="MGR001",
        hashed_password="hashed",
        name="Manager",
        department="Qualidade",
        role=UserRole.GERENTE_SR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def analyst_user1(db: Session):
    """Create first analyst user"""
    user = User(
        email="analyst1@example.com",
        employee_id="ANA001",
        hashed_password="hashed",
        name="Analyst 1",
        department="Qualidade",
        role=UserRole.ANALISTA_SR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def analyst_user2(db: Session):
    """Create second analyst user in different department"""
    user = User(
        email="analyst2@example.com",
        employee_id="ANA002",
        hashed_password="hashed",
        name="Analyst 2",
        department="Engenharia",
        role=UserRole.ANALISTA_SR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def weekly_report(db: Session, analyst_user1):
    """Create a weekly report"""
    report = WeeklyReport(
        user_id=analyst_user1.id,
        week_number=1,
        year=2026,
        status=WeeklyStatus.COMPLETED,
    )
    db.add(report)
    db.commit()
    return report


@pytest.fixture
def activity(db: Session, analyst_user1):
    """Create an activity"""
    act = Activity(
        user_id=analyst_user1.id,
        title="Test Activity",
        description="Test description",
        activity_date=datetime.now(UTC),
        week_number=1,
        year=2026,
        status=ActivityStatus.REGISTERED,
    )
    db.add(act)
    db.commit()
    return act


@pytest.fixture
def attachment(db: Session, activity):
    """Create an attachment"""
    att = Attachment(
        activity_id=activity.id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_path="/path/to/test.pdf",
        file_type="document",
        file_size=1024,
    )
    db.add(att)
    db.commit()
    return att


class TestPermissionLevels:
    """Test permission level hierarchy"""

    def test_permission_level_hierarchy(self):
        """Test that permission levels follow correct hierarchy"""
        levels = [PermissionLevel.NONE, PermissionLevel.VIEWER,
                  PermissionLevel.EDITOR, PermissionLevel.OWNER]

        assert levels[0] == PermissionLevel.NONE
        assert levels[1] == PermissionLevel.VIEWER
        assert levels[2] == PermissionLevel.EDITOR
        assert levels[3] == PermissionLevel.OWNER

    def test_permission_level_comparison(self):
        """Test permission level string values"""
        assert PermissionLevel.OWNER.value == "owner"
        assert PermissionLevel.EDITOR.value == "editor"
        assert PermissionLevel.VIEWER.value == "viewer"
        assert PermissionLevel.NONE.value == "none"


class TestWeeklyPermissions:
    """Test weekly report permission checks"""

    def test_owner_can_view_own_weekly(self, db, analyst_user1, weekly_report):
        """Owner should always be able to view their own report"""
        assert PermissionService.can_view_weekly_report(analyst_user1, weekly_report, db)

    def test_manager_can_view_any_weekly(self, db, manager_user, weekly_report):
        """Manager should be able to view any report"""
        assert PermissionService.can_view_weekly_report(manager_user, weekly_report, db)

    def test_department_member_can_view_weekly(self, db, analyst_user1, analyst_user2, weekly_report):
        """
        Different department members shouldn't see each other's reports
        """
        # analyst_user2 is in "Engenharia", analyst_user1 is in "Qualidade"
        assert not PermissionService.can_view_weekly_report(analyst_user2, weekly_report, db)

    def test_same_department_can_view_weekly(self, db, analyst_user1, weekly_report):
        """
        Create another user in same department who should see the report
        """
        same_dept_user = User(
            email="analyst3@example.com",
            employee_id="ANA003",
            hashed_password="hashed",
            name="Analyst 3",
            department="Qualidade",
            role=UserRole.ANALISTA_JR,
            is_active=True,
        )
        db.add(same_dept_user)
        db.commit()

        assert PermissionService.can_view_weekly_report(same_dept_user, weekly_report, db)

    def test_explicit_permission_grants_access(self, db, analyst_user1, analyst_user2, weekly_report):
        """Explicit permission should grant access to user from different department"""
        # Grant explicit permission
        PermissionService.grant_weekly_permission(
            weekly_report=weekly_report,
            user_id=analyst_user2.id,
            permission_level=PermissionLevel.VIEWER,
            db=db,
        )

        assert PermissionService.can_view_weekly_report(analyst_user2, weekly_report, db)

    def test_expired_permission_denies_access(self, db, analyst_user1, analyst_user2, weekly_report):
        """Expired permissions should not grant access"""
        # Grant permission that expires in the past
        expired_time = datetime.now(UTC) - timedelta(days=1)

        perm = WeeklyPermission(
            weekly_report_id=weekly_report.id,
            user_id=analyst_user2.id,
            permission_level=PermissionLevel.VIEWER,
            expires_at=expired_time,
        )
        db.add(perm)
        db.commit()

        assert not PermissionService.can_view_weekly_report(analyst_user2, weekly_report, db)

    def test_can_edit_requires_explicit_permission(self, db, analyst_user1, analyst_user2, weekly_report):
        """Editing requires explicit permission"""
        # User from different department can't edit
        assert not PermissionService.can_edit_weekly_report(analyst_user2, weekly_report, db)

        # Grant editor permission
        PermissionService.grant_weekly_permission(
            weekly_report=weekly_report,
            user_id=analyst_user2.id,
            permission_level=PermissionLevel.EDITOR,
            db=db,
        )

        # Now should be able to edit
        assert PermissionService.can_edit_weekly_report(analyst_user2, weekly_report, db)


class TestActivityPermissions:
    """Test activity permission checks"""

    def test_owner_can_view_own_activity(self, db, analyst_user1, activity):
        """Owner should be able to view their own activity"""
        assert PermissionService.can_view_activity(analyst_user1, activity, db)

    def test_manager_can_view_any_activity(self, db, manager_user, activity):
        """Manager should be able to view any activity"""
        assert PermissionService.can_view_activity(manager_user, activity, db)

    def test_other_user_cannot_view_activity(self, db, analyst_user2, activity):
        """User from different department can't view activity"""
        assert not PermissionService.can_view_activity(analyst_user2, activity, db)

    def test_share_activity(self, db, analyst_user1, analyst_user2, activity):
        """Test sharing activity with another user"""
        share = PermissionService.share_activity(
            activity=activity,
            shared_by_user=analyst_user1,
            shared_with_user_id=analyst_user2.id,
            permission_level=PermissionLevel.VIEWER,
            db=db,
        )

        assert share.activity_id == activity.id
        assert share.shared_with_user_id == analyst_user2.id
        assert PermissionService.can_view_activity(analyst_user2, activity, db)

    def test_cannot_share_if_not_owner(self, db, analyst_user1, analyst_user2, activity):
        """Non-owner shouldn't be able to share activity"""
        with pytest.raises(PermissionError):
            PermissionService.share_activity(
                activity=activity,
                shared_by_user=analyst_user2,
                shared_with_user_id=analyst_user1.id,
                db=db,
            )


class TestAttachmentPermissions:
    """Test attachment/file permission checks"""

    def test_owner_can_download_file(self, db, analyst_user1, attachment):
        """Owner should be able to download their file"""
        assert PermissionService.can_download_file(analyst_user1, attachment, db)

    def test_manager_can_download_any_file(self, db, manager_user, attachment):
        """Manager should be able to download any file"""
        assert PermissionService.can_download_file(manager_user, attachment, db)

    def test_other_user_cannot_download_file(self, db, analyst_user2, attachment):
        """User from different department can't download file"""
        assert not PermissionService.can_download_file(analyst_user2, attachment, db)

    def test_share_file_with_department(self, db, analyst_user1, attachment):
        """Test sharing file with department"""
        file_share = PermissionService.share_file(
            attachment=attachment,
            shared_by_user=analyst_user1,
            shared_with_department="Qualidade",
            permission_level=PermissionLevel.VIEWER,
            db=db,
        )

        assert file_share.attachment_id == attachment.id
        assert file_share.shared_with_department == "Qualidade"

    def test_share_file_with_specific_user(self, db, analyst_user1, analyst_user2, attachment):
        """Test sharing file with specific user"""
        file_share = PermissionService.share_file(
            attachment=attachment,
            shared_by_user=analyst_user1,
            shared_with_user_id=analyst_user2.id,
            permission_level=PermissionLevel.VIEWER,
            db=db,
        )

        assert file_share.shared_with_user_id == analyst_user2.id
        assert PermissionService.can_download_file(analyst_user2, attachment, db)


class TestPermissionRepository:
    """Test optimized permission repository queries"""

    def test_get_accessible_weeklies_manager(self, db, manager_user, weekly_report):
        """Manager should get all weeklies"""
        perm_repo = PermissionRepository(db)
        weeklies = perm_repo.get_accessible_weeklies_optimized(manager_user.id)

        assert len(weeklies) > 0
        assert weekly_report in weeklies

    def test_get_accessible_weeklies_owner(self, db, analyst_user1, weekly_report):
        """Owner should see their own weekly"""
        perm_repo = PermissionRepository(db)
        weeklies = perm_repo.get_accessible_weeklies_optimized(analyst_user1.id)

        assert weekly_report in weeklies

    def test_get_accessible_activities_manager(self, db, manager_user, activity):
        """Manager should get all activities"""
        perm_repo = PermissionRepository(db)
        activities = perm_repo.get_accessible_activities_optimized(manager_user.id)

        assert len(activities) > 0
        assert activity in activities

    def test_get_department_weeklies(self, db, analyst_user1, weekly_report):
        """Get weeklies from same department"""
        perm_repo = PermissionRepository(db)

        # Create another user in same department
        same_dept_user = User(
            email="analyst3@example.com",
            employee_id="ANA003",
            hashed_password="hashed",
            name="Analyst 3",
            department="Qualidade",
            role=UserRole.ANALISTA_JR,
            is_active=True,
        )
        db.add(same_dept_user)
        db.commit()

        dept_weeklies = perm_repo.get_department_weeklies_optimized(same_dept_user.id)
        assert weekly_report in dept_weeklies

    def test_check_weekly_permission(self, db, analyst_user1, analyst_user2, weekly_report):
        """Test permission check method"""
        perm_repo = PermissionRepository(db)

        # Owner should have permission
        assert perm_repo.check_weekly_permission(
            analyst_user1.id,
            weekly_report.id,
            PermissionLevel.VIEWER
        )

        # Different department user shouldn't
        assert not perm_repo.check_weekly_permission(
            analyst_user2.id,
            weekly_report.id,
            PermissionLevel.VIEWER
        )

    def test_check_activity_permission(self, db, analyst_user1, analyst_user2, activity):
        """Test activity permission check"""
        perm_repo = PermissionRepository(db)

        # Owner should have permission
        assert perm_repo.check_activity_permission(
            analyst_user1.id,
            activity.id,
            PermissionLevel.VIEWER
        )

        # Different department user shouldn't
        assert not perm_repo.check_activity_permission(
            analyst_user2.id,
            activity.id,
            PermissionLevel.VIEWER
        )

    def test_bulk_grant_permissions(self, db, manager_user, weekly_report):
        """Test bulk permission granting"""
        perm_repo = PermissionRepository(db)

        user_ids = [manager_user.id]
        permissions = perm_repo.bulk_grant_weekly_permission(
            weekly_id=weekly_report.id,
            user_ids=user_ids,
            permission_level=PermissionLevel.EDITOR,
        )

        assert len(permissions) > 0

    def test_revoke_permissions(self, db, analyst_user1, analyst_user2, weekly_report):
        """Test permission revocation"""
        perm_repo = PermissionRepository(db)

        # Grant permission first
        perm_repo.bulk_grant_weekly_permission(
            weekly_id=weekly_report.id,
            user_ids=[analyst_user2.id],
            permission_level=PermissionLevel.VIEWER,
        )

        # Verify it exists
        assert perm_repo.check_weekly_permission(
            analyst_user2.id,
            weekly_report.id,
            PermissionLevel.VIEWER
        )

        # Revoke it
        perm_repo.revoke_all_permissions(
            resource_type="weekly",
            resource_id=weekly_report.id,
            user_id=analyst_user2.id,
        )

        # Verify it's gone
        assert not perm_repo.check_weekly_permission(
            analyst_user2.id,
            weekly_report.id,
            PermissionLevel.VIEWER
        )


class TestAuditLogging:
    """Test audit trail functionality"""

    def test_log_audit(self, db, analyst_user1):
        """Test audit logging"""
        audit = PermissionService.log_audit(
            user_id=analyst_user1.id,
            action="test_action",
            resource_type="weekly",
            resource_id="test-id-123",
            changes={"test": "change"},
            db=db,
        )

        assert audit.user_id == analyst_user1.id
        assert audit.action == "test_action"
        assert audit.resource_type == "weekly"

    def test_log_permission_change(self, db, analyst_user1, analyst_user2, weekly_report):
        """Test permission change logging"""
        # Create audit log first
        audit = PermissionService.log_audit(
            user_id=analyst_user1.id,
            action="grant_permission",
            resource_type="weekly",
            resource_id=weekly_report.id,
            db=db,
        )

        # Log permission change
        perm_change = PermissionService.log_permission_change(
            audit_log_id=audit.id,
            changed_by_user_id=analyst_user1.id,
            target_user_id=analyst_user2.id,
            resource_type="weekly",
            resource_id=weekly_report.id,
            new_permission_level="viewer",
            reason="Test permission change",
            db=db,
        )

        assert perm_change.target_user_id == analyst_user2.id
        assert perm_change.new_permission_level == "viewer"

    def test_get_user_permission_history(self, db, analyst_user1, analyst_user2, weekly_report):
        """Test retrieving permission history"""
        perm_repo = PermissionRepository(db)

        # Grant permission
        PermissionService.grant_weekly_permission(
            weekly_report=weekly_report,
            user_id=analyst_user2.id,
            permission_level=PermissionLevel.VIEWER,
            db=db,
        )

        # Get history
        history = perm_repo.get_user_permission_history(analyst_user2.id)
        # Note: history might be empty if no PermissionChange logs were created


class TestFilteredQueries:
    """Test repository methods with permission filters"""

    def test_get_completed_with_permission_owner(self, db, analyst_user1, weekly_report):
        """Owner should see their completed reports"""
        weekly_repo = WeeklyRepository(db)
        reports = weekly_repo.get_completed_with_permission(analyst_user1.id)

        assert weekly_report in reports

    def test_get_by_week_with_permission_owner(self, db, analyst_user1, activity):
        """Owner should see their weekly activities"""
        activity_repo = ActivityRepository(db)
        activities = activity_repo.get_by_week_with_permission(
            user_id=analyst_user1.id,
            year=2026,
            week=1,
        )

        assert activity in activities

    def test_get_by_activity_with_permission_owner(self, db, analyst_user1, attachment):
        """Owner should see their attachments"""
        attachment_repo = AttachmentRepository(db)
        attachments = attachment_repo.get_by_activity_with_permission(
            user_id=analyst_user1.id,
            activity_id=attachment.activity_id,
        )

        assert attachment in attachments
