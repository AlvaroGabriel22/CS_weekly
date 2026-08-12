"""Activity Service - Business logic for activities"""
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.models import Activity, ActivityStatus, ActivityMetadata
from app.repositories import ActivityRepository
from app.core.dates import calculate_week_number
from app.core.exceptions import QWIException


class ActivityService:
    """Service for activity management with business rules"""

    # Constants
    MAX_ACTIVITIES_PER_WEEK = 50
    MAX_DESCRIPTION_LENGTH = 5000
    MAX_TITLE_LENGTH = 500

    def __init__(self, db: Session):
        self.db = db
        self.repo = ActivityRepository(db)

    def create_activity(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        activity_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        project: Optional[str] = None,
        category: Optional[str] = None,
        department: Optional[str] = None,
    ) -> Activity:
        """Create a new activity with business validation"""

        # Validate input
        if not title or not title.strip():
            raise QWIException('Title is required')

        if len(title) > self.MAX_TITLE_LENGTH:
            raise QWIException(f'Title must be <= {self.MAX_TITLE_LENGTH} chars')

        if description and len(description) > self.MAX_DESCRIPTION_LENGTH:
            raise QWIException(f'Description must be <= {self.MAX_DESCRIPTION_LENGTH} chars')

        # Set default date to now
        if activity_date is None:
            activity_date = datetime.now(UTC)

        # Validate date not in future
        if activity_date > datetime.now(UTC):
            raise QWIException('Activity date cannot be in future')

        # Calculate week info
        week_num, year = calculate_week_number(activity_date)

        # Check quota
        count = self.repo.count_by_week(user_id, year, week_num)
        if count >= self.MAX_ACTIVITIES_PER_WEEK:
            raise QWIException(
                f'Maximum {self.MAX_ACTIVITIES_PER_WEEK} activities per week exceeded'
            )

        # Create activity
        activity = self.repo.create({
            'user_id': user_id,
            'title': title.strip(),
            'description': description.strip() if description else None,
            'activity_date': activity_date,
            'tags': tags or [],
            'project': project,
            'category': category,
            'department': department,
            'week_number': week_num,
            'year': year,
            'status': ActivityStatus.REGISTERED,
            'include_in_weekly': True,
        })

        return activity

    def update_activity(
        self,
        activity_id: str,
        user_id: str,
        **updates
    ) -> Activity:
        """Update activity with permission check"""

        # Get current activity
        activity = self.repo.read(activity_id)
        if not activity:
            raise QWIException('Activity not found')

        # Check ownership
        if activity.user_id != user_id:
            raise QWIException('Not authorized to update this activity')

        # Validate updates
        if 'title' in updates:
            title = updates['title']
            if not title or not title.strip():
                raise QWIException('Title cannot be empty')
            if len(title) > self.MAX_TITLE_LENGTH:
                raise QWIException(f'Title must be <= {self.MAX_TITLE_LENGTH} chars')
            updates['title'] = title.strip()

        if 'description' in updates and updates['description']:
            desc = updates['description']
            if len(desc) > self.MAX_DESCRIPTION_LENGTH:
                raise QWIException(f'Description must be <= {self.MAX_DESCRIPTION_LENGTH} chars')
            updates['description'] = desc.strip()

        # Recalculate week if activity_date changed
        if 'activity_date' in updates:
            new_date = updates['activity_date']
            if new_date > datetime.now(UTC):
                raise QWIException('Activity date cannot be in future')

            week_num, year = calculate_week_number(new_date)
            updates['week_number'] = week_num
            updates['year'] = year

            # Check new week quota
            current_count = self.repo.count_by_week(user_id, year, week_num)
            if current_count >= self.MAX_ACTIVITIES_PER_WEEK:
                raise QWIException(f'Week {week_num}/{year} has max activities')

        # Update
        updated = self.repo.update(activity_id, updates)
        return updated

    def delete_activity(self, activity_id: str, user_id: str) -> bool:
        """Delete activity with permission check"""

        activity = self.repo.read(activity_id)
        if not activity:
            raise QWIException('Activity not found')

        if activity.user_id != user_id:
            raise QWIException('Not authorized to delete this activity')

        # Cascade delete metadata and attachments (handled by DB)
        return self.repo.delete(activity_id)

    def get_activity(self, activity_id: str, user_id: str) -> Optional[Activity]:
        """Get activity with permission check"""

        activity = self.repo.read(activity_id)
        if not activity:
            return None

        if activity.user_id != user_id:
            raise QWIException('Not authorized to view this activity')

        return activity

    def get_week_activities(
        self,
        user_id: str,
        year: int,
        week: int,
        include_attachments: bool = False,
    ) -> List[Activity]:
        """Get all activities for a specific week"""

        if not (1 <= week <= 53):
            raise QWIException('Week must be between 1 and 53')

        if include_attachments:
            return self.repo.get_by_week_with_attachments(user_id, year, week)
        else:
            return self.repo.get_by_week(user_id, year, week)

    def get_week_summary(self, user_id: str, year: int, week: int) -> Dict[str, Any]:
        """Get detailed summary of week activities"""

        if not (1 <= week <= 53):
            raise QWIException('Week must be between 1 and 53')

        summary = self.repo.get_weekly_summary(user_id, year, week)

        # Enrich with report status
        from app.repositories import WeeklyRepository
        weekly_repo = WeeklyRepository(self.db)
        report = weekly_repo.get_by_user_week(user_id, year, week)

        summary['report_generated'] = report is not None
        if report:
            summary['report_status'] = report.status.value
            summary['report_id'] = report.id

        return summary

    def mark_for_report(self, activity_id: str, user_id: str, include: bool = True) -> Activity:
        """Mark activity for inclusion in weekly report"""

        activity = self.get_activity(activity_id, user_id)
        if not activity:
            raise QWIException('Activity not found')

        return self.repo.update(activity_id, {'include_in_weekly': include})

    def change_status(
        self,
        activity_id: str,
        user_id: str,
        new_status: ActivityStatus,
    ) -> Activity:
        """Change activity status"""

        activity = self.get_activity(activity_id, user_id)
        if not activity:
            raise QWIException('Activity not found')

        # Validate status transition
        current = activity.status
        if current == ActivityStatus.USED_IN_REPORT:
            raise QWIException('Cannot modify activity already used in report')

        return self.repo.update(activity_id, {'status': new_status})

    def search_activities(
        self,
        user_id: str,
        query: str,
        limit: int = 50,
    ) -> List[Activity]:
        """Search user's activities by text"""

        if not query or not query.strip():
            raise QWIException('Search query cannot be empty')

        if len(query) < 2:
            raise QWIException('Search query must be at least 2 characters')

        return self.repo.search(user_id, query, limit=limit)

    def get_unprocessed(self, user_id: str) -> List[Activity]:
        """Get activities awaiting AI processing"""

        return self.repo.get_unprocessed(user_id)

    def mark_processed(self, activity_id: str) -> Activity:
        """Mark activity as AI-processed"""

        activity = self.repo.read(activity_id)
        if not activity:
            raise QWIException('Activity not found')

        return self.repo.update(activity_id, {'status': ActivityStatus.PROCESSED})

    def create_metadata(
        self,
        activity_id: str,
        project: Optional[str] = None,
        supplier: Optional[str] = None,
        line: Optional[str] = None,
        process: Optional[str] = None,
        product: Optional[str] = None,
        category: Optional[str] = None,
        activity_type: Optional[str] = None,
        defect_type: Optional[str] = None,
        related_kpis: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        technical_summary: Optional[str] = None,
    ) -> ActivityMetadata:
        """Create or update activity metadata"""

        # Check if metadata exists
        activity = self.repo.read(activity_id)
        if not activity:
            raise QWIException('Activity not found')

        # Ensure lists
        related_kpis = related_kpis or []
        keywords = keywords or []

        if activity.metadata_entry:
            # Update existing
            metadata = activity.metadata_entry
            metadata.project = project
            metadata.supplier = supplier
            metadata.line = line
            metadata.process = process
            metadata.product = product
            metadata.category = category
            metadata.activity_type = activity_type
            metadata.defect_type = defect_type
            metadata.related_kpis = related_kpis
            metadata.keywords = keywords
            metadata.technical_summary = technical_summary
            metadata.processed_at = datetime.now(UTC)
        else:
            # Create new
            metadata = ActivityMetadata(
                activity_id=activity_id,
                project=project,
                supplier=supplier,
                line=line,
                process=process,
                product=product,
                category=category,
                activity_type=activity_type,
                defect_type=defect_type,
                related_kpis=related_kpis,
                keywords=keywords,
                technical_summary=technical_summary,
                processed_at=datetime.now(UTC),
            )
            self.db.add(metadata)

        self.db.commit()
        self.db.refresh(metadata)
        return metadata

    def get_statistics(self, user_id: str, year: int, week: int) -> Dict[str, Any]:
        """Get activity statistics for period"""

        activities = self.repo.get_by_week(user_id, year, week)

        return {
            'total': len(activities),
            'by_status': {
                status.value: sum(1 for a in activities if a.status == status)
                for status in ActivityStatus
            },
            'for_report': sum(1 for a in activities if a.include_in_weekly),
            'with_attachments': sum(1 for a in activities if a.attachments),
            'with_metadata': sum(1 for a in activities if a.metadata_entry),
        }

    def bulk_mark_for_report(
        self,
        activity_ids: List[str],
        user_id: str,
        include: bool = True,
    ) -> int:
        """Bulk mark activities for report inclusion"""

        if not activity_ids:
            raise QWIException('No activities specified')

        # Verify ownership of all activities
        for activity_id in activity_ids:
            activity = self.repo.read(activity_id)
            if not activity or activity.user_id != user_id:
                raise QWIException(f'Not authorized for activity {activity_id}')

        # Bulk update
        count = 0
        for activity_id in activity_ids:
            self.repo.update(activity_id, {'include_in_weekly': include})
            count += 1

        return count
