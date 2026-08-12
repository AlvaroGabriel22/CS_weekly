"""Attachment Repository - Specialized queries for Attachment model"""
from typing import Optional, List
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, select, or_
from app.models import Attachment, ImageUsage
from app.repositories.base import BaseRepository


class AttachmentRepository(BaseRepository[Attachment]):
    """Repository for Attachment model with specialized queries"""

    def __init__(self, session: Session):
        super().__init__(session, Attachment)

    def get_by_activity(self, activity_id: str) -> List[Attachment]:
        """Get all attachments for an activity"""
        return (
            self.session.query(Attachment)
            .filter(Attachment.activity_id == activity_id)
            .order_by(Attachment.created_at)
            .all()
        )

    def get_by_activity_with_permission(
        self,
        user_id: str,
        activity_id: str,
    ) -> List[Attachment]:
        """Get attachments for an activity with permission check"""
        from app.models import Activity, User, UserRole, MANAGEMENT_ROLES
        from app.models.permissions import ActivityShare, FileShare, PermissionLevel

        user = self.session.query(User).filter(User.id == user_id).first()
        activity = self.session.query(Activity).filter(Activity.id == activity_id).first()

        if not user or not activity:
            return []

        # Owner can access
        if activity.user_id == user_id:
            return (
                self.session.query(Attachment)
                .filter(Attachment.activity_id == activity_id)
                .order_by(Attachment.created_at)
                .all()
            )

        # Managers can access all
        if user.role in MANAGEMENT_ROLES:
            return (
                self.session.query(Attachment)
                .filter(Attachment.activity_id == activity_id)
                .order_by(Attachment.created_at)
                .all()
            )

        # Check activity permission
        activity_owner = self.session.query(User).filter(User.id == activity.user_id).first()
        has_department_access = activity_owner and activity_owner.department == user.department

        has_share_access = self.session.query(ActivityShare).filter(
            and_(
                ActivityShare.activity_id == activity_id,
                ActivityShare.shared_with_user_id == user_id,
                ActivityShare.permission_level != PermissionLevel.NONE,
            )
        ).first()

        if not has_department_access and not has_share_access:
            return []

        # Return all attachments if user has access to the activity
        return (
            self.session.query(Attachment)
            .filter(Attachment.activity_id == activity_id)
            .order_by(Attachment.created_at)
            .all()
        )

    def get_by_activity_for_report(self, activity_id: str) -> List[Attachment]:
        """Get attachments marked for inclusion in report"""
        return (
            self.session.query(Attachment)
            .filter(
                and_(
                    Attachment.activity_id == activity_id,
                    Attachment.include_in_weekly == True,
                )
            )
            .order_by(Attachment.created_at)
            .all()
        )

    def get_by_type(self, activity_id: str, file_type: str) -> List[Attachment]:
        """Get attachments by file type"""
        return (
            self.session.query(Attachment)
            .filter(
                and_(
                    Attachment.activity_id == activity_id,
                    Attachment.file_type == file_type,
                )
            )
            .all()
        )

    def get_images(self, activity_id: str) -> List[Attachment]:
        """Get image attachments only"""
        return (
            self.session.query(Attachment)
            .filter(
                and_(
                    Attachment.activity_id == activity_id,
                    Attachment.file_type == 'image',
                )
            )
            .all()
        )

    def get_images_for_report(self, activity_id: str) -> List[Attachment]:
        """Get images to include in report"""
        return (
            self.session.query(Attachment)
            .filter(
                and_(
                    Attachment.activity_id == activity_id,
                    Attachment.file_type == 'image',
                    Attachment.include_in_weekly == True,
                    Attachment.image_usage.in_([
                        ImageUsage.INSERT_REPORT,
                        ImageUsage.AI_EVIDENCE,
                    ]),
                )
            )
            .all()
        )

    def get_by_usage(self, activity_id: str, usage: ImageUsage) -> List[Attachment]:
        """Get attachments by image usage"""
        return (
            self.session.query(Attachment)
            .filter(
                and_(
                    Attachment.activity_id == activity_id,
                    Attachment.image_usage == usage,
                )
            )
            .all()
        )

    def get_needing_ai_analysis(self, limit: int = 50) -> List[Attachment]:
        """Get attachments without AI analysis"""
        return (
            self.session.query(Attachment)
            .filter(
                and_(
                    Attachment.file_type.in_(['image', 'document']),
                    Attachment.ai_analysis == None,
                )
            )
            .order_by(Attachment.created_at)
            .limit(limit)
            .all()
        )

    def get_needing_captions(self, limit: int = 50) -> List[Attachment]:
        """Get images without AI captions"""
        return (
            self.session.query(Attachment)
            .filter(
                and_(
                    Attachment.file_type == 'image',
                    Attachment.ai_caption == None,
                )
            )
            .order_by(Attachment.created_at)
            .limit(limit)
            .all()
        )

    def get_with_kpi_data(self, activity_id: str) -> List[Attachment]:
        """Get attachments with extracted KPI data"""
        return (
            self.session.query(Attachment)
            .filter(
                and_(
                    Attachment.activity_id == activity_id,
                    Attachment.kpi_data != None,
                )
            )
            .all()
        )

    def update_ai_analysis(self, attachment_id: str, analysis: dict) -> Optional[Attachment]:
        """Update AI analysis for attachment"""
        attachment = self.read(attachment_id)
        if attachment:
            attachment.ai_analysis = analysis
            self.session.commit()
            self.session.refresh(attachment)
        return attachment

    def update_ai_caption(self, attachment_id: str, caption: str) -> Optional[Attachment]:
        """Update AI-generated caption"""
        attachment = self.read(attachment_id)
        if attachment:
            attachment.ai_caption = caption
            self.session.commit()
            self.session.refresh(attachment)
        return attachment

    def update_kpi_data(self, attachment_id: str, kpi_data: dict) -> Optional[Attachment]:
        """Update extracted KPI data"""
        attachment = self.read(attachment_id)
        if attachment:
            attachment.kpi_data = kpi_data
            self.session.commit()
            self.session.refresh(attachment)
        return attachment

    def get_total_size_for_activity(self, activity_id: str) -> int:
        """Get total file size for an activity"""
        attachments = self.get_by_activity(activity_id)
        return sum(a.file_size for a in attachments)

    def count_by_type(self, activity_id: str) -> dict:
        """Count attachments by file type"""
        attachments = self.get_by_activity(activity_id)
        counts = {}
        for attachment in attachments:
            file_type = attachment.file_type
            counts[file_type] = counts.get(file_type, 0) + 1
        return counts

    def get_recent(self, user_id: str, limit: int = 20) -> List[Attachment]:
        """Get recent attachments for a user (via activity relationship)"""
        return (
            self.session.query(Attachment)
            .join(Attachment.activity)
            .filter(Attachment.activity.has(user_id=user_id))
            .order_by(desc(Attachment.created_at))
            .limit(limit)
            .all()
        )

    def get_old_unprocessed(self, days: int = 7) -> List[Attachment]:
        """Get unprocessed attachments older than N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        return (
            self.session.query(Attachment)
            .filter(
                and_(
                    Attachment.ai_analysis == None,
                    Attachment.created_at < cutoff_date,
                )
            )
            .all()
        )

    def cleanup_orphaned(self) -> int:
        """Delete attachments whose activity was deleted"""
        # Note: With CASCADE delete, this shouldn't happen
        # But kept for safety/data integrity checks
        return 0

    def count_total_size(self, activity_id: str) -> int:
        """Get total storage used for activity"""
        total = self.session.query(
            self.session.query(
                self.session.func.sum(Attachment.file_size)
            )
            .filter(Attachment.activity_id == activity_id)
            .scalar()
        )
        return total or 0
