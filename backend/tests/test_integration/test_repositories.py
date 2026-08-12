"""Integration tests for Repository pattern"""
import pytest
from datetime import datetime, UTC
from app.models import UserRole, ActivityStatus, WeeklyStatus
from app.repositories import (
    UserRepository,
    ActivityRepository,
    WeeklyRepository,
    AttachmentRepository,
)
from app.core.dates import calculate_week_number


@pytest.mark.integration
class TestUserRepository:
    """Test UserRepository methods"""

    def test_create_and_read_user(self, db):
        """Test creating and reading a user"""
        repo = UserRepository(db)

        # Create
        user = repo.create({
            'email': 'test@example.com',
            'employee_id': 'EMP-001',
            'hashed_password': 'hashed_pwd',
            'name': 'Test User',
            'role': UserRole.ANALISTA_SR,
            'sector': 'CSI',
        })

        assert user.id is not None
        assert user.email == 'test@example.com'

        # Read
        fetched = repo.read(user.id)
        assert fetched.id == user.id
        assert fetched.email == 'test@example.com'

    def test_get_by_email(self, db, test_user):
        """Test getting user by email"""
        repo = UserRepository(db)

        user = repo.get_by_email(test_user.email)
        assert user is not None
        assert user.id == test_user.id

    def test_get_by_employee_id(self, db, test_user):
        """Test getting user by employee_id"""
        repo = UserRepository(db)

        user = repo.get_by_employee_id(test_user.employee_id)
        assert user is not None
        assert user.id == test_user.id

    def test_email_exists(self, db, test_user):
        """Test email existence check"""
        repo = UserRepository(db)

        assert repo.email_exists(test_user.email) is True
        assert repo.email_exists('nonexistent@example.com') is False

    def test_employee_id_exists(self, db, test_user):
        """Test employee_id existence check"""
        repo = UserRepository(db)

        assert repo.employee_id_exists(test_user.employee_id) is True
        assert repo.employee_id_exists('EMP-NONEXISTENT') is False

    def test_get_active_users(self, db, test_user):
        """Test getting active users"""
        repo = UserRepository(db)

        users = repo.get_active_users()
        assert len(users) > 0
        assert test_user in users

    def test_soft_delete(self, db, test_user):
        """Test soft delete via is_active"""
        repo = UserRepository(db)

        # Deactivate
        assert repo.soft_delete(test_user.id) is True

        # Check deactivated
        user = repo.read(test_user.id)
        assert user.is_active is False


@pytest.mark.integration
class TestActivityRepository:
    """Test ActivityRepository methods"""

    def test_create_and_read_activity(self, db, test_user, test_activity_data):
        """Test creating and reading an activity"""
        repo = ActivityRepository(db)

        # Create
        activity_data = test_activity_data.copy()
        activity_data['user_id'] = test_user.id

        activity = repo.create(activity_data)
        assert activity.id is not None
        assert activity.title == activity_data['title']

        # Read
        fetched = repo.read(activity.id)
        assert fetched.id == activity.id

    def test_get_by_week(self, db, test_activity):
        """Test getting activities by week"""
        repo = ActivityRepository(db)

        activities = repo.get_by_week(
            test_activity.user_id,
            test_activity.year,
            test_activity.week_number,
        )

        assert len(activities) > 0
        assert test_activity in activities

    def test_get_by_status(self, db, test_user):
        """Test getting activities by status"""
        repo = ActivityRepository(db)

        # Create activity with specific status
        week_num, year = calculate_week_number(datetime.now(UTC))
        activity = repo.create({
            'user_id': test_user.id,
            'title': 'Test Activity',
            'activity_date': datetime.now(UTC),
            'status': ActivityStatus.DRAFT,
            'week_number': week_num,
            'year': year,
        })

        # Fetch by status
        activities = repo.get_by_status(test_user.id, ActivityStatus.DRAFT)
        assert activity in activities

    def test_search(self, db, test_activity):
        """Test searching activities"""
        repo = ActivityRepository(db)

        # Search by title
        results = repo.search(test_activity.user_id, test_activity.title[:5])
        assert len(results) > 0
        assert test_activity in results

    def test_count_by_week(self, db, test_activity):
        """Test counting activities in a week"""
        repo = ActivityRepository(db)

        count = repo.count_by_week(
            test_activity.user_id,
            test_activity.year,
            test_activity.week_number,
        )

        assert count > 0

    def test_get_weekly_summary(self, db, test_activity):
        """Test getting weekly summary"""
        repo = ActivityRepository(db)

        summary = repo.get_weekly_summary(
            test_activity.user_id,
            test_activity.year,
            test_activity.week_number,
        )

        assert summary['total'] > 0
        assert 'by_status' in summary
        assert 'by_category' in summary


@pytest.mark.integration
class TestWeeklyRepository:
    """Test WeeklyRepository methods"""

    def test_get_or_create_draft(self, db, test_user):
        """Test getting or creating draft report"""
        repo = WeeklyRepository(db)

        report = repo.get_or_create_draft(test_user.id, 2026, 32)
        assert report.status == WeeklyStatus.DRAFT
        assert report.user_id == test_user.id
        assert report.year == 2026
        assert report.week_number == 32

    def test_get_by_user_week(self, db, test_user):
        """Test getting report by user/week"""
        repo = WeeklyRepository(db)

        # Create
        report = repo.create({
            'user_id': test_user.id,
            'year': 2026,
            'week_number': 33,
            'status': WeeklyStatus.DRAFT,
        })

        # Fetch
        fetched = repo.get_by_user_week(test_user.id, 2026, 33)
        assert fetched.id == report.id

    def test_unique_constraint(self, db, test_user):
        """Test that only one report per week exists (UNIQUE constraint)"""
        repo = WeeklyRepository(db)

        # Create first report
        report1 = repo.get_or_create_draft(test_user.id, 2026, 34)

        # Get same report again
        report2 = repo.get_or_create_draft(test_user.id, 2026, 34)

        # Should be same report
        assert report1.id == report2.id

    def test_start_generation(self, db, test_user):
        """Test marking report as generating"""
        repo = WeeklyRepository(db)

        report = repo.get_or_create_draft(test_user.id, 2026, 35)
        updated = repo.start_generation(report.id)

        assert updated.status == WeeklyStatus.GENERATING

    def test_complete_generation(self, db, test_user):
        """Test completing report generation"""
        repo = WeeklyRepository(db)

        report = repo.get_or_create_draft(test_user.id, 2026, 36)
        content = {'summary': 'Test summary'}
        pptx_path = '/path/to/report.pptx'

        completed = repo.complete_generation(report.id, content, pptx_path)

        assert completed.status == WeeklyStatus.COMPLETED
        assert completed.content == content
        assert completed.pptx_path == pptx_path

    def test_mark_failed(self, db, test_user):
        """Test marking report as failed"""
        repo = WeeklyRepository(db)

        report = repo.get_or_create_draft(test_user.id, 2026, 37)
        failed = repo.mark_failed(report.id, 'Error: Connection timeout')

        assert failed.status == WeeklyStatus.FAILED

    def test_exists_for_week(self, db, test_user):
        """Test checking if report exists for week"""
        repo = WeeklyRepository(db)

        repo.get_or_create_draft(test_user.id, 2026, 38)

        assert repo.exists_for_week(test_user.id, 2026, 38) is True
        assert repo.exists_for_week(test_user.id, 2026, 99) is False

    def test_get_completed(self, db, test_user):
        """Test getting completed reports"""
        repo = WeeklyRepository(db)

        # Create and complete a report
        report = repo.get_or_create_draft(test_user.id, 2026, 39)
        repo.complete_generation(report.id, {}, '/path/to/file.pptx')

        # Get completed
        completed = repo.get_completed(test_user.id)
        assert report in completed


@pytest.mark.integration
class TestAttachmentRepository:
    """Test AttachmentRepository methods"""

    def test_create_attachment(self, db, test_activity):
        """Test creating attachment"""
        repo = AttachmentRepository(db)

        attachment = repo.create({
            'activity_id': test_activity.id,
            'filename': 'file_uuid.pdf',
            'original_filename': 'document.pdf',
            'file_path': '/uploads/file_uuid.pdf',
            'file_type': 'document',
            'file_size': 1024000,
            'mime_type': 'application/pdf',
        })

        assert attachment.id is not None
        assert attachment.filename == 'file_uuid.pdf'

    def test_get_by_activity(self, db, test_activity):
        """Test getting attachments by activity"""
        repo = AttachmentRepository(db)

        # Create attachments
        repo.create({
            'activity_id': test_activity.id,
            'filename': 'file1.pdf',
            'original_filename': 'doc1.pdf',
            'file_path': '/uploads/file1.pdf',
            'file_type': 'document',
            'file_size': 1000,
            'mime_type': 'application/pdf',
        })

        repo.create({
            'activity_id': test_activity.id,
            'filename': 'file2.jpg',
            'original_filename': 'image.jpg',
            'file_path': '/uploads/file2.jpg',
            'file_type': 'image',
            'file_size': 2000,
            'mime_type': 'image/jpeg',
        })

        # Fetch
        attachments = repo.get_by_activity(test_activity.id)
        assert len(attachments) >= 2

    def test_get_by_type(self, db, test_activity):
        """Test getting attachments by file type"""
        repo = AttachmentRepository(db)

        # Create image
        repo.create({
            'activity_id': test_activity.id,
            'filename': 'image.jpg',
            'original_filename': 'photo.jpg',
            'file_path': '/uploads/image.jpg',
            'file_type': 'image',
            'file_size': 3000,
            'mime_type': 'image/jpeg',
        })

        # Get images
        images = repo.get_by_type(test_activity.id, 'image')
        assert len(images) > 0
        assert all(a.file_type == 'image' for a in images)

    def test_count_by_type(self, db, test_activity):
        """Test counting by file type"""
        repo = AttachmentRepository(db)

        repo.create({
            'activity_id': test_activity.id,
            'filename': 'file.pdf',
            'original_filename': 'doc.pdf',
            'file_path': '/uploads/file.pdf',
            'file_type': 'document',
            'file_size': 1000,
        })

        counts = repo.count_by_type(test_activity.id)
        assert 'document' in counts
        assert counts['document'] >= 1
