"""Weekly Report Repository - Specialized queries for WeeklyReport model"""
from typing import Optional, List
from datetime import datetime, UTC
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, or_, select
from app.models import WeeklyReport, WeeklyStatus, User, UserRole, MANAGEMENT_ROLES
from app.repositories.base import BaseRepository


class WeeklyRepository(BaseRepository[WeeklyReport]):
    """Repository for WeeklyReport model with specialized queries"""

    def __init__(self, session: Session):
        super().__init__(session, WeeklyReport)

    def get_or_create_draft(self, user_id: str, year: int, week: int) -> WeeklyReport:
        """Get existing draft or create new one"""
        existing = self.get_by_user_week(user_id, year, week)

        if existing and existing.status == WeeklyStatus.DRAFT:
            return existing

        # Create new draft
        report = self.create({
            'user_id': user_id,
            'year': year,
            'week_number': week,
            'status': WeeklyStatus.DRAFT,
        })
        return report

    def get_by_user_week(self, user_id: str, year: int, week: int) -> Optional[WeeklyReport]:
        """Get report for specific user/year/week (UNIQUE constraint)"""
        return (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.user_id == user_id,
                    WeeklyReport.year == year,
                    WeeklyReport.week_number == week,
                )
            )
            .first()
        )

    def get_with_template(self, report_id: str) -> Optional[WeeklyReport]:
        """Get report with template eager loaded"""
        return (
            self.session.query(WeeklyReport)
            .options(joinedload(WeeklyReport.template))
            .filter(WeeklyReport.id == report_id)
            .first()
        )

    def get_by_status(self, user_id: str, status: WeeklyStatus) -> List[WeeklyReport]:
        """Get reports by status"""
        return (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.user_id == user_id,
                    WeeklyReport.status == status,
                )
            )
            .order_by(desc(WeeklyReport.created_at))
            .all()
        )

    def get_completed(self, user_id: str, limit: int = 10) -> List[WeeklyReport]:
        """Get completed reports for a user"""
        return (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.user_id == user_id,
                    WeeklyReport.status == WeeklyStatus.COMPLETED,
                )
            )
            .order_by(desc(WeeklyReport.year), desc(WeeklyReport.week_number))
            .limit(limit)
            .all()
        )

    def get_completed_with_permission(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[WeeklyReport]:
        """Get completed reports accessible to user (with permission filter)"""
        from app.models.permissions import WeeklyPermission, PermissionLevel

        user = self.session.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # Managers can see all
        if user.role in MANAGEMENT_ROLES:
            return (
                self.session.query(WeeklyReport)
                .filter(WeeklyReport.status == WeeklyStatus.COMPLETED)
                .order_by(desc(WeeklyReport.year), desc(WeeklyReport.week_number))
                .limit(limit)
                .all()
            )

        # Get accessible weeklies (owned, department, shared)
        now = datetime.now(UTC)

        # Own weeklies
        owned = select(WeeklyReport.id).where(WeeklyReport.user_id == user_id)

        # Department weeklies
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

        # Shared weeklies
        shared = select(WeeklyPermission.weekly_report_id).where(
            and_(
                WeeklyPermission.user_id == user_id,
                WeeklyPermission.permission_level != PermissionLevel.NONE,
                or_(
                    WeeklyPermission.expires_at.is_(None),
                    WeeklyPermission.expires_at > now,
                ),
            )
        )

        return (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.status == WeeklyStatus.COMPLETED,
                    or_(
                        WeeklyReport.id.in_(owned),
                        WeeklyReport.id.in_(dept_weeklies),
                        WeeklyReport.id.in_(shared),
                    ),
                )
            )
            .order_by(desc(WeeklyReport.year), desc(WeeklyReport.week_number))
            .limit(limit)
            .all()
        )

    def get_in_progress(self, user_id: str) -> List[WeeklyReport]:
        """Get reports currently being generated"""
        return (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.user_id == user_id,
                    WeeklyReport.status == WeeklyStatus.GENERATING,
                )
            )
            .all()
        )

    def get_failed(self, user_id: str) -> List[WeeklyReport]:
        """Get failed reports"""
        return (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.user_id == user_id,
                    WeeklyReport.status == WeeklyStatus.FAILED,
                )
            )
            .order_by(desc(WeeklyReport.created_at))
            .all()
        )

    def get_by_year(self, user_id: str, year: int) -> List[WeeklyReport]:
        """Get all reports for a year"""
        return (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.user_id == user_id,
                    WeeklyReport.year == year,
                )
            )
            .order_by(WeeklyReport.week_number)
            .all()
        )

    def get_by_template(self, template_id: str) -> List[WeeklyReport]:
        """Get reports using specific template"""
        return (
            self.session.query(WeeklyReport)
            .filter(WeeklyReport.template_id == template_id)
            .all()
        )

    def get_historical(self, user_id: str, limit: int = 12) -> List[WeeklyReport]:
        """Get recent completed reports (for dashboard)"""
        return (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.user_id == user_id,
                    WeeklyReport.status == WeeklyStatus.COMPLETED,
                )
            )
            .order_by(desc(WeeklyReport.year), desc(WeeklyReport.week_number))
            .limit(limit)
            .all()
        )

    def start_generation(self, report_id: str) -> Optional[WeeklyReport]:
        """Mark report as generating"""
        report = self.read(report_id)
        if report:
            report.status = WeeklyStatus.GENERATING
            self.session.commit()
            self.session.refresh(report)
        return report

    def complete_generation(self, report_id: str, content: dict, pptx_path: str) -> Optional[WeeklyReport]:
        """Mark report as completed and save content"""
        report = self.read(report_id)
        if report:
            report.status = WeeklyStatus.COMPLETED
            report.content = content
            report.pptx_path = pptx_path
            report.generated_at = datetime.now()
            self.session.commit()
            self.session.refresh(report)
        return report

    def mark_failed(self, report_id: str, error: str = "") -> Optional[WeeklyReport]:
        """Mark report generation as failed"""
        report = self.read(report_id)
        if report:
            report.status = WeeklyStatus.FAILED
            if error and hasattr(report, 'ai_summary'):
                report.ai_summary = f"Error: {error}"
            self.session.commit()
            self.session.refresh(report)
        return report

    def exists_for_week(self, user_id: str, year: int, week: int) -> bool:
        """Check if report exists for specific week"""
        return (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.user_id == user_id,
                    WeeklyReport.year == year,
                    WeeklyReport.week_number == week,
                )
            )
            .first()
            is not None
        )

    def count_completed(self, user_id: str) -> int:
        """Count completed reports"""
        return self.count(user_id=user_id, status=WeeklyStatus.COMPLETED)

    def count_by_status(self, user_id: str, status: WeeklyStatus) -> int:
        """Count reports by status"""
        return self.count(user_id=user_id, status=status)

    def get_latest(self, user_id: str) -> Optional[WeeklyReport]:
        """Get latest (most recent) report"""
        return (
            self.session.query(WeeklyReport)
            .filter(WeeklyReport.user_id == user_id)
            .order_by(desc(WeeklyReport.year), desc(WeeklyReport.week_number))
            .first()
        )

    def get_quality_stats(self, user_id: str, limit: int = 52) -> dict:
        """Get quality score statistics"""
        reports = (
            self.session.query(WeeklyReport)
            .filter(
                and_(
                    WeeklyReport.user_id == user_id,
                    WeeklyReport.status == WeeklyStatus.COMPLETED,
                )
            )
            .order_by(desc(WeeklyReport.year), desc(WeeklyReport.week_number))
            .limit(limit)
            .all()
        )

        scores = [r.quality_score for r in reports if r.quality_score is not None]

        if not scores:
            return {
                'average': 0,
                'min': 0,
                'max': 0,
                'count': 0,
            }

        return {
            'average': sum(scores) / len(scores),
            'min': min(scores),
            'max': max(scores),
            'count': len(scores),
        }
