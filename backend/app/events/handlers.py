"""
Event Handlers - Business logic triggered by domain events.

Connects domain events to Celery tasks and other async operations.
"""

import logging
from typing import TYPE_CHECKING

from app.events.types import (
    Event,
    EventType,
    ActivityCreatedEvent,
    WeeklyGeneratedEvent,
    FileSharedEvent,
    PermissionGrantedEvent,
)

if TYPE_CHECKING:
    from app.events.bus import EventBus

logger = logging.getLogger(__name__)


class EventHandlers:
    """Container for event handler functions."""

    @staticmethod
    def on_activity_created(event: ActivityCreatedEvent) -> None:
        """
        Handle activity created event.

        Triggers:
        - AI processing via Celery task
        - Cache invalidation
        - Metadata extraction

        Args:
            event: The activity created event
        """
        logger.info(
            f"Activity created: {event.aggregate_id} | "
            f"title={event.title} | user_id={event.user_id}"
        )

        try:
            from app.tasks import process_activity_ai

            # Queue AI processing task
            task = process_activity_ai.delay(
                activity_id=event.aggregate_id,
                user_id=event.user_id,
                metadata=event.metadata,
            )
            logger.info(f"AI processing task queued: {task.id}")

            # Invalidate related caches
            from app.cache import cache

            cache.invalidate_activity_cache(event.aggregate_id)
            cache.invalidate_user_activities_cache(event.user_id)

        except Exception as e:
            logger.error(f"Error handling activity_created event: {str(e)}", exc_info=True)

    @staticmethod
    def on_activity_updated(event: Event) -> None:
        """
        Handle activity updated event.

        Triggers:
        - Cache invalidation
        - Re-processing if content changed

        Args:
            event: The activity updated event
        """
        logger.info(
            f"Activity updated: {event.aggregate_id} | user_id={event.user_id}"
        )

        try:
            from app.cache import cache

            # Invalidate activity cache
            cache.invalidate_activity_cache(event.aggregate_id)
            cache.invalidate_user_activities_cache(event.user_id)

            # Check if content changed (requires re-processing)
            if event.metadata.get("content_changed", False):
                from app.tasks import process_activity_ai

                task = process_activity_ai.delay(
                    activity_id=event.aggregate_id,
                    user_id=event.user_id,
                    metadata=event.metadata,
                )
                logger.info(f"Re-processing activity: {task.id}")

        except Exception as e:
            logger.error(f"Error handling activity_updated event: {str(e)}", exc_info=True)

    @staticmethod
    def on_weekly_generated(event: WeeklyGeneratedEvent) -> None:
        """
        Handle weekly generated event.

        Triggers:
        - PPTX generation via Celery task
        - Report compilation
        - Distribution

        Args:
            event: The weekly generated event
        """
        logger.info(
            f"Weekly report generated: {event.aggregate_id} | "
            f"week={event.week_number}/{event.year} | user_id={event.user_id}"
        )

        try:
            from app.tasks import generate_pptx_report, send_weekly_notification

            # Queue PPTX generation
            pptx_task = generate_pptx_report.delay(
                weekly_id=event.aggregate_id,
                user_id=event.user_id,
                week_number=event.week_number,
                year=event.year,
            )
            logger.info(f"PPTX generation task queued: {pptx_task.id}")

            # Queue notification
            notify_task = send_weekly_notification.delay(
                weekly_id=event.aggregate_id,
                user_id=event.user_id,
            )
            logger.info(f"Notification task queued: {notify_task.id}")

            # Invalidate cache
            from app.cache import cache

            cache.invalidate_weekly_cache(event.aggregate_id)
            cache.invalidate_user_weekly_cache(event.user_id)

        except Exception as e:
            logger.error(f"Error handling weekly_generated event: {str(e)}", exc_info=True)

    @staticmethod
    def on_file_shared(event: FileSharedEvent) -> None:
        """
        Handle file shared event.

        Triggers:
        - Cache invalidation
        - Permission updates
        - Notifications

        Args:
            event: The file shared event
        """
        logger.info(
            f"File shared: {event.file_id} | "
            f"shared_with={event.shared_with} | user_id={event.user_id}"
        )

        try:
            from app.cache import cache
            from app.tasks import send_share_notification

            # Invalidate permission caches for all users
            cache.invalidate_file_cache(event.file_id)
            for user_id in event.shared_with:
                cache.invalidate_user_permissions_cache(user_id)

            # Send notifications
            for user_id in event.shared_with:
                task = send_share_notification.delay(
                    file_id=event.file_id,
                    file_name=event.file_name,
                    shared_by=event.user_id,
                    shared_with=user_id,
                    permission_level=event.permission_level,
                )
                logger.info(f"Share notification task queued: {task.id}")

        except Exception as e:
            logger.error(f"Error handling file_shared event: {str(e)}", exc_info=True)

    @staticmethod
    def on_permission_granted(event: PermissionGrantedEvent) -> None:
        """
        Handle permission granted event.

        Triggers:
        - Cache invalidation
        - Notification

        Args:
            event: The permission granted event
        """
        logger.info(
            f"Permission granted: {event.resource_id} | "
            f"grantee={event.grantee_id} | level={event.permission_level}"
        )

        try:
            from app.cache import cache

            # Invalidate permission caches
            cache.invalidate_resource_cache(event.resource_id)
            cache.invalidate_user_permissions_cache(event.grantee_id)

            logger.info(f"Permission cache invalidated for {event.grantee_id}")

        except Exception as e:
            logger.error(
                f"Error handling permission_granted event: {str(e)}", exc_info=True
            )


def register_event_handlers(event_bus: "EventBus") -> None:
    """
    Register all event handlers with the event bus.

    Args:
        event_bus: The event bus instance
    """
    logger.info("Registering event handlers...")

    # Activity events
    event_bus.subscribe(EventType.ACTIVITY_CREATED, EventHandlers.on_activity_created)
    event_bus.subscribe(EventType.ACTIVITY_UPDATED, EventHandlers.on_activity_updated)

    # Weekly events
    event_bus.subscribe(EventType.WEEKLY_GENERATED, EventHandlers.on_weekly_generated)

    # File events
    event_bus.subscribe(EventType.FILE_SHARED, EventHandlers.on_file_shared)

    # Permission events
    event_bus.subscribe(EventType.PERMISSION_GRANTED, EventHandlers.on_permission_granted)

    logger.info("Event handlers registered successfully")
