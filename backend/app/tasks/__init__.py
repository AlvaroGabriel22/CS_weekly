"""
Celery Tasks - Async job processing for Quality Weekly Intelligence.

Provides task definitions for:
- AI processing of activities
- PPTX report generation
- Notification delivery
- Data export
"""

from app.tasks.ai_tasks import process_activity_ai, analyze_attachment
from app.tasks.pptx_tasks import generate_pptx_report, generate_pptx_batch
from app.tasks.notification_tasks import (
    send_weekly_notification,
    send_share_notification,
    send_permission_notification,
)
from app.tasks.export_tasks import export_activities, export_weekly_report

__all__ = [
    # AI tasks
    "process_activity_ai",
    "analyze_attachment",
    # PPTX tasks
    "generate_pptx_report",
    "generate_pptx_batch",
    # Notification tasks
    "send_weekly_notification",
    "send_share_notification",
    "send_permission_notification",
    # Export tasks
    "export_activities",
    "export_weekly_report",
]
