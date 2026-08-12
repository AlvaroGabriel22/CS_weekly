"""Activity Repository - Specialized queries for Activity model"""
from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, select, or_
from app.models import Activity, ActivityStatus, User, UserRole, MANAGEMENT_ROLES
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[Activity]):
    """Repository for Activity model with specialized queries"""

    def __init__(self, session: Session):
        super().__init__(session, Activity)

    def get_by_week(self, user_id: str, year: int, week: int) -> List[Activity]:
        """Get all activities for a specific week (optimized)"""
        return (
            self.session.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.year == year,
                    Activity.week_number == week,
                )
            )
            .order_by(desc(Activity.activity_date))
            .all()
        )

    def get_by_week_with_permission(
        self,
        user_id: str,
        year: int,
        week: int,
    ) -> List[Activity]:
        """Get activities for a week with permission filter"""
        from app.models.permissions import ActivityShare, PermissionLevel

        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # Managers can see all
        if user.role in MANAGEMENT_ROLES:
            return (
                self.session.query(Activity)
                .filter(
                    and_(
                        Activity.year == year,
                        Activity.week_number == week,
                    )
                )
                .order_by(desc(Activity.activity_date))
                .all()
            )

        from sqlalchemy import select, or_

        # Own activities
        owned = select(Activity.id).where(
            and_(
                Activity.user_id == user_id,
                Activity.year == year,
                Activity.week_number == week,
            )
        )

        # Department activities
        dept_users = select(User.id).where(
            and_(
                User.department == user.department,
                User.id != user_id,
                User.is_active == True,
            )
        )
        dept_activities = select(Activity.id).where(
            and_(
                Activity.user_id.in_(dept_users),
                Activity.year == year,
                Activity.week_number == week,
            )
        )

        # Shared activities
        shared = select(ActivityShare.activity_id).where(
            and_(
                ActivityShare.shared_with_user_id == user_id,
                ActivityShare.permission_level != PermissionLevel.NONE,
            )
        )

        return (
            self.session.query(Activity)
            .filter(
                and_(
                    Activity.year == year,
                    Activity.week_number == week,
                    or_(
                        Activity.id.in_(owned),
                        Activity.id.in_(dept_activities),
                        Activity.id.in_(shared),
                    ),
                )
            )
            .order_by(desc(Activity.activity_date))
            .all()
        )

    def get_by_week_with_attachments(self, user_id: str, year: int, week: int) -> List[Activity]:
        """Get week activities with eager-loaded attachments"""
        return (
            self.session.query(Activity)
            .options(joinedload(Activity.attachments))
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.year == year,
                    Activity.week_number == week,
                )
            )
            .order_by(desc(Activity.activity_date))
            .all()
        )

    def get_by_date_range(
        self, user_id: str, start_date: datetime, end_date: datetime
    ) -> List[Activity]:
        """Get activities within date range"""
        return (
            self.session.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.activity_date >= start_date,
                    Activity.activity_date <= end_date,
                )
            )
            .order_by(desc(Activity.activity_date))
            .all()
        )

    def get_by_status(self, user_id: str, status: ActivityStatus) -> List[Activity]:
        """Get activities by status"""
        return (
            self.session.query(Activity)
            .filter(and_(Activity.user_id == user_id, Activity.status == status))
            .order_by(desc(Activity.created_at))
            .all()
        )

    def get_for_weekly_report(self, user_id: str, year: int, week: int) -> List[Activity]:
        """Get activities marked for inclusion in weekly report"""
        return (
            self.session.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.year == year,
                    Activity.week_number == week,
                    Activity.include_in_weekly == True,
                    Activity.status.in_([
                        ActivityStatus.REGISTERED,
                        ActivityStatus.PROCESSED,
                        ActivityStatus.USED_IN_REPORT,
                    ])
                )
            )
            .order_by(Activity.activity_date)
            .all()
        )

    def get_by_category(self, user_id: str, category: str, year: int, week: int) -> List[Activity]:
        """Get activities by category in a week"""
        return (
            self.session.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.category == category,
                    Activity.year == year,
                    Activity.week_number == week,
                )
            )
            .all()
        )

    def get_by_project(self, user_id: str, project: str, year: int, week: int) -> List[Activity]:
        """Get activities by project in a week"""
        return (
            self.session.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.project == project,
                    Activity.year == year,
                    Activity.week_number == week,
                )
            )
            .all()
        )

    def search(self, user_id: str, query: str, limit: int = 50) -> List[Activity]:
        """Full-text search activities"""
        search_term = f"%{query}%"
        return (
            self.session.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.title.ilike(search_term)
                    | Activity.description.ilike(search_term)
                    | Activity.notes.ilike(search_term),
                )
            )
            .order_by(desc(Activity.created_at))
            .limit(limit)
            .all()
        )

    def get_with_metadata(self, activity_id: str) -> Optional[Activity]:
        """Get activity with metadata eager loaded"""
        return (
            self.session.query(Activity)
            .options(joinedload(Activity.metadata_entry))
            .filter(Activity.id == activity_id)
            .first()
        )

    def get_unprocessed(self, user_id: str) -> List[Activity]:
        """Get unprocessed activities for AI processing"""
        return (
            self.session.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.status == ActivityStatus.REGISTERED,
                )
            )
            .order_by(Activity.created_at)
            .all()
        )

    def update_status_bulk(self, activity_ids: List[str], status: ActivityStatus) -> int:
        """Update status for multiple activities"""
        activities = (
            self.session.query(Activity)
            .filter(Activity.id.in_(activity_ids))
            .all()
        )

        for activity in activities:
            activity.status = status

        self.session.commit()
        return len(activities)

    def count_by_week(self, user_id: str, year: int, week: int) -> int:
        """Count activities in a week"""
        return self.count(
            user_id=user_id,
            year=year,
            week_number=week,
        )

    def count_by_status(self, user_id: str, status: ActivityStatus) -> int:
        """Count activities by status"""
        return self.count(user_id=user_id, status=status)

    def count_for_report(self, user_id: str, year: int, week: int) -> int:
        """Count activities that will be included in report"""
        return (
            self.session.query(Activity)
            .filter(
                and_(
                    Activity.user_id == user_id,
                    Activity.year == year,
                    Activity.week_number == week,
                    Activity.include_in_weekly == True,
                )
            )
            .count()
        )

    def get_weekly_summary(self, user_id: str, year: int, week: int) -> dict:
        """Get activity summary for a week"""
        activities = self.get_by_week(user_id, year, week)

        summary = {
            'total': len(activities),
            'by_status': {},
            'by_category': {},
            'by_project': {},
            'included_in_report': 0,
        }

        for activity in activities:
            # Count by status
            status = activity.status.value
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1

            # Count by category
            if activity.category:
                summary['by_category'][activity.category] = (
                    summary['by_category'].get(activity.category, 0) + 1
                )

            # Count by project
            if activity.project:
                summary['by_project'][activity.project] = (
                    summary['by_project'].get(activity.project, 0) + 1
                )

            # Count included in report
            if activity.include_in_weekly:
                summary['included_in_report'] += 1

        return summary

    def get_recent(self, user_id: str, limit: int = 10) -> List[Activity]:
        """Get recent activities"""
        return (
            self.session.query(Activity)
            .filter(Activity.user_id == user_id)
            .order_by(desc(Activity.created_at))
            .limit(limit)
            .all()
        )
