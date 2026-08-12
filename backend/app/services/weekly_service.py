"""Weekly Service - Business logic for weekly report generation"""
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.models import WeeklyReport, WeeklyStatus, Activity
from app.repositories import WeeklyRepository, ActivityRepository
from app.core.dates import calculate_week_number
from app.core.exceptions import QWIException


class WeeklyService:
    """Service for weekly report generation and management"""

    def __init__(self, db: Session):
        self.db = db
        self.weekly_repo = WeeklyRepository(db)
        self.activity_repo = ActivityRepository(db)

    def get_or_create_draft(self, user_id: str, year: int, week: int) -> WeeklyReport:
        """Get existing draft or create new one"""
        if not (1 <= week <= 53):
            raise QWIException('Week must be between 1 and 53')

        return self.weekly_repo.get_or_create_draft(user_id, year, week)

    def get_report(self, report_id: str, user_id: str) -> Optional[WeeklyReport]:
        """Get report with permission check"""
        report = self.weekly_repo.read(report_id)
        if not report:
            return None

        if report.user_id != user_id:
            raise QWIException('Not authorized to view this report')

        return report

    def start_generation(self, report_id: str, user_id: str) -> WeeklyReport:
        """Mark report generation as starting"""
        report = self.get_report(report_id, user_id)
        if not report:
            raise QWIException('Report not found')

        if report.status == WeeklyStatus.COMPLETED:
            raise QWIException('Cannot regenerate completed report')

        return self.weekly_repo.start_generation(report_id)

    def complete_generation(
        self,
        report_id: str,
        user_id: str,
        content: Dict[str, Any],
        pptx_path: str,
        quality_score: Optional[float] = None,
    ) -> WeeklyReport:
        """Mark report as completed"""
        report = self.get_report(report_id, user_id)
        if not report:
            raise QWIException('Report not found')

        # Validate content
        if not content or not isinstance(content, dict):
            raise QWIException('Invalid report content')

        if not pptx_path:
            raise QWIException('PPTX path is required')

        # Update activities to mark as used
        activities = self.activity_repo.get_for_weekly_report(
            user_id, report.year, report.week_number
        )
        for activity in activities:
            self.activity_repo.update(activity.id, {'status': 'used_in_report'})

        # Complete report
        completed = self.weekly_repo.complete_generation(report_id, content, pptx_path)
        if quality_score is not None:
            completed.quality_score = quality_score
            self.db.commit()

        return completed

    def mark_failed(self, report_id: str, user_id: str, error: str = "") -> WeeklyReport:
        """Mark report generation as failed"""
        report = self.get_report(report_id, user_id)
        if not report:
            raise QWIException('Report not found')

        return self.weekly_repo.mark_failed(report_id, error)

    def get_activities_for_report(
        self,
        user_id: str,
        year: int,
        week: int,
    ) -> List[Activity]:
        """Get activities to include in report"""
        return self.activity_repo.get_for_weekly_report(user_id, year, week)

    def get_report_by_week(self, user_id: str, year: int, week: int) -> Optional[WeeklyReport]:
        """Get report for specific week"""
        return self.weekly_repo.get_by_user_week(user_id, year, week)

    def get_completed_reports(self, user_id: str, limit: int = 12) -> List[WeeklyReport]:
        """Get completed reports for dashboard"""
        return self.weekly_repo.get_completed(user_id, limit=limit)

    def get_historical(self, user_id: str, limit: int = 52) -> List[WeeklyReport]:
        """Get historical reports"""
        return self.weekly_repo.get_historical(user_id, limit=limit)

    def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get report statistics"""
        return {
            'completed': self.weekly_repo.count_completed(user_id),
            'in_progress': self.weekly_repo.count_by_status(user_id, WeeklyStatus.GENERATING),
            'quality': self.weekly_repo.get_quality_stats(user_id),
        }
