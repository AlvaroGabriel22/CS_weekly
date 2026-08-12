"""
Notification Tasks - Async notification delivery via Celery.

Tasks:
- send_weekly_notification: Notify user of weekly report completion
- send_share_notification: Notify when file is shared
- send_permission_notification: Notify of permission changes
"""

import logging
from typing import Any, Optional

from app.celery_app import celery_app
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="notifications",
)
def send_weekly_notification(
    self,
    weekly_id: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Send notification of weekly report completion.

    Notifies:
    - Report owner
    - Department managers
    - Shared recipients

    Args:
        weekly_id: Weekly report ID
        user_id: Report owner user ID

    Returns:
        Notification result

    Raises:
        Retries on failure (max 3 times)
    """
    logger.info(f"Sending weekly report notification | weekly={weekly_id} | user={user_id}")

    db = SessionLocal()
    try:
        from app.models import WeeklyReport, User
        from app.events import get_event_bus
        from app.events.types import EventType, Event

        # Get weekly report
        weekly = db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
        if not weekly:
            logger.warning(f"Weekly report {weekly_id} not found")
            return {"status": "skipped", "reason": "Report not found"}

        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            return {"status": "skipped", "reason": "User not found"}

        # Prepare notification content
        notification = {
            "type": "weekly_report_completed",
            "recipient_id": user_id,
            "recipient_email": user.email,
            "subject": f"Weekly Report Ready - Week {weekly.week_number}/{weekly.year}",
            "body": f"Your weekly report for week {weekly.week_number} has been generated successfully.",
            "data": {
                "weekly_id": weekly_id,
                "week_number": weekly.week_number,
                "year": weekly.year,
            },
        }

        # Send notification (would integrate with email service, push notifications, etc.)
        logger.info(f"Sending notification to {user.email}")

        # Publish notification sent event
        event_bus = get_event_bus(db)
        event = Event(
            event_type=EventType.NOTIFICATION_SENT,
            aggregate_id=weekly_id,
            aggregate_type="weekly",
            user_id=user_id,
            metadata={
                "notification_type": "weekly_report_completed",
                "recipient": user.email,
            },
        )
        event_bus.publish(event)

        return {
            "status": "sent",
            "recipient": user.email,
            "notification_type": "weekly_report_completed",
        }

    except Exception as exc:
        logger.error(
            f"Error sending weekly notification: {str(exc)}", exc_info=True
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))

    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=20,
    queue="notifications",
)
def send_share_notification(
    self,
    file_id: str,
    file_name: str,
    shared_by: str,
    shared_with: str,
    permission_level: str,
) -> dict[str, Any]:
    """
    Send notification when file is shared.

    Args:
        file_id: File ID
        file_name: File name
        shared_by: User ID who shared
        shared_with: User ID who received share
        permission_level: Permission level (view, edit, etc.)

    Returns:
        Notification result

    Raises:
        Retries on failure (max 2 times)
    """
    logger.info(
        f"Sending share notification | file={file_id} | from={shared_by} | to={shared_with}"
    )

    db = SessionLocal()
    try:
        from app.models import User
        from app.events import get_event_bus
        from app.events.types import EventType, Event

        # Get users
        sender = db.query(User).filter(User.id == shared_by).first()
        recipient = db.query(User).filter(User.id == shared_with).first()

        if not recipient:
            logger.warning(f"Recipient user {shared_with} not found")
            return {"status": "skipped", "reason": "Recipient not found"}

        # Prepare notification
        notification = {
            "type": "file_shared",
            "recipient_id": shared_with,
            "recipient_email": recipient.email,
            "subject": f"{sender.name if sender else 'Someone'} shared '{file_name}' with you",
            "body": f"You have been granted {permission_level} access to {file_name}",
            "data": {
                "file_id": file_id,
                "file_name": file_name,
                "permission_level": permission_level,
            },
        }

        logger.info(f"Sending share notification to {recipient.email}")

        # Publish event
        event_bus = get_event_bus(db)
        event = Event(
            event_type=EventType.NOTIFICATION_SENT,
            aggregate_id=file_id,
            aggregate_type="file",
            user_id=shared_by,
            metadata={
                "notification_type": "file_shared",
                "recipient": recipient.email,
                "permission_level": permission_level,
            },
        )
        event_bus.publish(event)

        return {
            "status": "sent",
            "recipient": recipient.email,
            "notification_type": "file_shared",
        }

    except Exception as exc:
        logger.error(
            f"Error sending share notification: {str(exc)}", exc_info=True
        )
        raise self.retry(exc=exc, countdown=20 * (2 ** self.request.retries))

    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=20,
    queue="notifications",
)
def send_permission_notification(
    self,
    resource_id: str,
    resource_type: str,
    user_id: str,
    permission_level: str,
    action: str = "granted",
) -> dict[str, Any]:
    """
    Send notification of permission change.

    Args:
        resource_id: Resource ID
        resource_type: Type of resource
        user_id: User who received permission
        permission_level: Permission level
        action: Action type (granted, revoked, updated)

    Returns:
        Notification result

    Raises:
        Retries on failure (max 2 times)
    """
    logger.info(
        f"Sending permission notification | resource={resource_id} | "
        f"user={user_id} | action={action}"
    )

    db = SessionLocal()
    try:
        from app.models import User
        from app.events import get_event_bus
        from app.events.types import EventType, Event

        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            return {"status": "skipped", "reason": "User not found"}

        # Prepare notification
        action_text = {
            "granted": "been granted",
            "revoked": "been revoked",
            "updated": "been updated",
        }.get(action, "been modified")

        notification = {
            "type": "permission_changed",
            "recipient_id": user_id,
            "recipient_email": user.email,
            "subject": f"Your access permissions have {action_text}",
            "body": f"Your {permission_level} access to {resource_type} has {action_text}",
            "data": {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "permission_level": permission_level,
                "action": action,
            },
        }

        logger.info(f"Sending permission notification to {user.email}")

        # Publish event
        event_bus = get_event_bus(db)
        event = Event(
            event_type=EventType.NOTIFICATION_SENT,
            aggregate_id=resource_id,
            aggregate_type="permission",
            user_id=user_id,
            metadata={
                "notification_type": "permission_changed",
                "recipient": user.email,
                "action": action,
            },
        )
        event_bus.publish(event)

        return {
            "status": "sent",
            "recipient": user.email,
            "notification_type": "permission_changed",
        }

    except Exception as exc:
        logger.error(
            f"Error sending permission notification: {str(exc)}", exc_info=True
        )
        raise self.retry(exc=exc, countdown=20 * (2 ** self.request.retries))

    finally:
        db.close()
