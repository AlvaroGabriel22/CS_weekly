"""Integration tests for Services"""
import pytest
from datetime import datetime, UTC
from app.models import ActivityStatus, WeeklyStatus, UserRole, QualitySector
from app.services import (
    ActivityService,
    UserService,
    WeeklyService,
    FileService,
)
from app.core.exceptions import QWIException


@pytest.mark.integration
class TestActivityService:
    def test_create_activity(self, db, test_user):
        service = ActivityService(db)
        activity = service.create_activity(
            test_user.id,
            'Test Activity',
            'Description',
        )
        assert activity.id is not None
        assert activity.title == 'Test Activity'
        assert activity.user_id == test_user.id

    def test_create_activity_validation(self, db, test_user):
        service = ActivityService(db)
        with pytest.raises(QWIException):
            service.create_activity(test_user.id, '')

    def test_update_activity(self, db, test_activity):
        service = ActivityService(db)
        updated = service.update_activity(
            test_activity.id,
            test_activity.user_id,
            title='Updated Title',
        )
        assert updated.title == 'Updated Title'

    def test_delete_activity(self, db, test_activity):
        service = ActivityService(db)
        result = service.delete_activity(test_activity.id, test_activity.user_id)
        assert result is True

    def test_mark_for_report(self, db, test_activity):
        service = ActivityService(db)
        updated = service.mark_for_report(test_activity.id, test_activity.user_id, True)
        assert updated.include_in_weekly is True


@pytest.mark.integration
class TestUserService:
    def test_create_user(self, db):
        service = UserService(db)
        user = service.create_user(
            'test@example.com',
            'EMP-999',
            'password123',
            'Test User',
            UserRole.ANALISTA_SR,
        )
        assert user.id is not None
        assert user.email == 'test@example.com'

    def test_create_user_email_exists(self, db, test_user):
        service = UserService(db)
        with pytest.raises(QWIException):
            service.create_user(
                test_user.email,
                'EMP-NEW',
                'password123',
                'Another',
                UserRole.ANALISTA_JR,
            )

    def test_authenticate(self, db, test_user, test_user_data):
        service = UserService(db)
        user = service.authenticate(test_user.email, test_user_data['password'])
        assert user is not None
        assert user.id == test_user.id

    def test_authenticate_wrong_password(self, db, test_user):
        service = UserService(db)
        user = service.authenticate(test_user.email, 'wrongpassword')
        assert user is None

    def test_change_password(self, db, test_user, test_user_data):
        service = UserService(db)
        result = service.change_password(
            test_user.id,
            test_user_data['password'],
            'newpassword123',
        )
        assert result is True


@pytest.mark.integration
class TestWeeklyService:
    def test_get_or_create_draft(self, db, test_user):
        service = WeeklyService(db)
        report = service.get_or_create_draft(test_user.id, 2026, 32)
        assert report.status == WeeklyStatus.DRAFT
        assert report.week_number == 32

    def test_start_generation(self, db, test_user):
        service = WeeklyService(db)
        report = service.get_or_create_draft(test_user.id, 2026, 33)
        started = service.start_generation(report.id, test_user.id)
        assert started.status == WeeklyStatus.GENERATING

    def test_complete_generation(self, db, test_user):
        service = WeeklyService(db)
        report = service.get_or_create_draft(test_user.id, 2026, 34)
        completed = service.complete_generation(
            report.id,
            test_user.id,
            {'summary': 'test'},
            '/path/to/file.pptx',
        )
        assert completed.status == WeeklyStatus.COMPLETED


@pytest.mark.integration
class TestFileService:
    def test_upload_file(self, db, test_activity):
        service = FileService(db)
        content = b'Test content'
        attachment = service.upload_file(
            test_activity.id,
            content,
            'test.pdf',
            'application/pdf',
        )
        assert attachment.id is not None
        assert attachment.original_filename == 'test.pdf'
        assert attachment.file_type == 'document'

    def test_upload_invalid_type(self, db, test_activity):
        service = FileService(db)
        with pytest.raises(QWIException):
            service.upload_file(
                test_activity.id,
                b'content',
                'test.exe',
                'application/x-msdownload',
            )

    def test_delete_file(self, db, test_activity):
        service = FileService(db)
        attachment = service.upload_file(
            test_activity.id,
            b'content',
            'test.pdf',
            'application/pdf',
        )
        result = service.delete_file(attachment.id)
        assert result is True
