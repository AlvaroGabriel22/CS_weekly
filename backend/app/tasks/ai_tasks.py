"""
AI Processing Tasks - Async activity enrichment and analysis via Celery.

Tasks:
- process_activity_ai: Enrich activity with AI-generated insights
- analyze_attachment: Process uploaded attachments
"""

import logging
from typing import Any, Optional

from app.celery_app import celery_app
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ai_tasks",
)
def process_activity_ai(
    self,
    activity_id: str,
    user_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Process activity with AI for enrichment.

    Performs:
    - Extract key insights from activity content
    - Generate summary
    - Identify related activities
    - Update metadata

    Args:
        activity_id: Activity ID to process
        user_id: User ID (for context)
        metadata: Additional metadata

    Returns:
        Processing result with insights

    Raises:
        Retries on failure (max 3 times)
    """
    logger.info(f"Processing activity {activity_id} with AI | user={user_id}")

    db = SessionLocal()
    try:
        from app.events import get_event_bus
        from app.events.types import ProcessingStartedEvent, ProcessingCompletedEvent
        from app.models import Activity

        # Publish processing started event
        event_bus = get_event_bus(db)
        start_event = ProcessingStartedEvent(
            aggregate_id=activity_id,
            processing_type="ai_analysis",
            user_id=user_id,
            metadata=metadata or {},
        )
        event_bus.publish(start_event)

        # Get activity from database
        activity = db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            logger.error(f"Activity {activity_id} not found")
            raise ValueError(f"Activity {activity_id} not found")

        # Process activity with AI
        from app.services.ai_service import AIService
        from time import time

        start_time = time()

        ai_service = AIService(db)
        insights = await ai_service.analyze_activity_async(activity)

        duration = time() - start_time

        # Update activity metadata with insights
        if activity.metadata_entry:
            activity.metadata_entry.insights = insights.get("insights", {})
            activity.metadata_entry.summary = insights.get("summary")
            activity.metadata_entry.keywords = insights.get("keywords", [])
            db.commit()

        # Update cache
        from app.cache import cache

        cache_data = {
            "id": activity.id,
            "title": activity.title,
            "insights": insights,
        }
        cache.set_activity(activity_id, cache_data, ttl=3600)

        # Publish processing completed event
        completion_event = ProcessingCompletedEvent(
            aggregate_id=activity_id,
            processing_type="ai_analysis",
            duration_seconds=duration,
            user_id=user_id,
            result=insights,
        )
        event_bus.publish(completion_event)

        logger.info(
            f"Activity {activity_id} processed successfully | duration={duration:.2f}s"
        )

        return {
            "activity_id": activity_id,
            "status": "success",
            "duration": duration,
            "insights": insights,
        }

    except Exception as exc:
        logger.error(f"Error processing activity {activity_id}: {str(exc)}", exc_info=True)

        # Publish processing failed event
        try:
            from app.events import get_event_bus
            from app.events.types import EventType

            event_bus = get_event_bus(db)
            # Create a generic event for failure
            from app.events.types import Event

            failure_event = Event(
                event_type=EventType.PROCESSING_FAILED,
                aggregate_id=activity_id,
                aggregate_type="activity",
                user_id=user_id,
                metadata={"error": str(exc)},
            )
            event_bus.publish(failure_event)
        except Exception as e:
            logger.error(f"Failed to publish processing failed event: {str(e)}")

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="ai_tasks",
)
def analyze_attachment(
    self,
    attachment_id: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Analyze uploaded attachment.

    Performs:
    - Extract text from file
    - Classify content
    - Generate preview
    - Link to activity

    Args:
        attachment_id: Attachment ID to analyze
        user_id: User ID (for context)

    Returns:
        Analysis result

    Raises:
        Retries on failure (max 2 times)
    """
    logger.info(f"Analyzing attachment {attachment_id} | user={user_id}")

    db = SessionLocal()
    try:
        from app.events import get_event_bus
        from app.events.types import ProcessingStartedEvent, ProcessingCompletedEvent
        from app.models import Attachment
        from time import time

        start_time = time()

        # Publish processing started event
        event_bus = get_event_bus(db)
        start_event = ProcessingStartedEvent(
            aggregate_id=attachment_id,
            processing_type="attachment_analysis",
            user_id=user_id,
        )
        event_bus.publish(start_event)

        # Get attachment
        attachment = (
            db.query(Attachment).filter(Attachment.id == attachment_id).first()
        )
        if not attachment:
            raise ValueError(f"Attachment {attachment_id} not found")

        # Analyze attachment
        from app.services.file_service import FileService

        file_service = FileService(db)
        analysis = file_service.analyze_attachment(attachment)

        duration = time() - start_time

        # Update cache
        from app.cache import cache

        cache_data = {
            "id": attachment.id,
            "file_name": attachment.file_name,
            "analysis": analysis,
        }
        cache.set_file(attachment_id, cache_data, ttl=3600)

        # Publish completion event
        completion_event = ProcessingCompletedEvent(
            aggregate_id=attachment_id,
            processing_type="attachment_analysis",
            duration_seconds=duration,
            user_id=user_id,
            result=analysis,
        )
        event_bus.publish(completion_event)

        logger.info(f"Attachment {attachment_id} analyzed | duration={duration:.2f}s")

        return {
            "attachment_id": attachment_id,
            "status": "success",
            "duration": duration,
            "analysis": analysis,
        }

    except Exception as exc:
        logger.error(
            f"Error analyzing attachment {attachment_id}: {str(exc)}", exc_info=True
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))

    finally:
        db.close()
