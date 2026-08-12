"""
Event Bus - Central publish/subscribe pattern implementation.

Manages event publishing, handler registration, and async processing
with audit logging for all events.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional

import pytz
from sqlalchemy.orm import Session

from app.events.types import Event, EventType

logger = logging.getLogger(__name__)

# Global event bus instance
_event_bus: Optional["EventBus"] = None


class EventBus:
    """
    Publish-Subscribe event bus for domain events.

    Features:
    - Event publishing with async handler support
    - Handler registration per event type
    - Event audit logging to database
    - Graceful error handling with logging
    """

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the event bus.

        Args:
            db_session: Optional SQLAlchemy session for audit logging
        """
        self.db_session = db_session
        self.handlers: dict[EventType, list[Callable]] = {}
        self.async_handlers: dict[EventType, list[Callable[[Event], Coroutine]]] = {}

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
    ) -> None:
        """
        Register a synchronous event handler.

        Args:
            event_type: The event type to subscribe to
            handler: Callable that processes the event
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.debug(f"Handler subscribed to {event_type.value}: {handler.__name__}")

    def subscribe_async(
        self,
        event_type: EventType,
        handler: Callable[[Event], Coroutine],
    ) -> None:
        """
        Register an asynchronous event handler.

        Args:
            event_type: The event type to subscribe to
            handler: Async callable that processes the event
        """
        if event_type not in self.async_handlers:
            self.async_handlers[event_type] = []
        self.async_handlers[event_type].append(handler)
        logger.debug(f"Async handler subscribed to {event_type.value}: {handler.__name__}")

    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None],
    ) -> None:
        """
        Unregister a synchronous event handler.

        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove
        """
        if event_type in self.handlers:
            self.handlers[event_type] = [
                h for h in self.handlers[event_type] if h != handler
            ]

    def unsubscribe_async(
        self,
        event_type: EventType,
        handler: Callable[[Event], Coroutine],
    ) -> None:
        """
        Unregister an asynchronous event handler.

        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove
        """
        if event_type in self.async_handlers:
            self.async_handlers[event_type] = [
                h for h in self.async_handlers[event_type] if h != handler
            ]

    def publish(self, event: Event) -> None:
        """
        Publish an event to all registered handlers.

        Calls synchronous handlers immediately and queues
        asynchronous handlers for event loop execution.

        Args:
            event: The event to publish
        """
        logger.info(
            f"Publishing event: {event.event_type.value} | "
            f"aggregate_id={event.aggregate_id} | user_id={event.user_id}"
        )

        # Log event to audit trail
        self._log_event(event)

        # Call synchronous handlers
        if event.event_type in self.handlers:
            for handler in self.handlers[event.event_type]:
                try:
                    handler(event)
                    logger.debug(f"Handler {handler.__name__} executed successfully")
                except Exception as e:
                    logger.error(
                        f"Error in handler {handler.__name__}: {str(e)}",
                        exc_info=True,
                    )

        # Queue async handlers if event loop is running
        if event.event_type in self.async_handlers:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    for handler in self.async_handlers[event.event_type]:
                        asyncio.create_task(self._run_async_handler(handler, event))
                else:
                    # Run async handlers sequentially
                    asyncio.run(
                        self._run_async_handlers(
                            self.async_handlers[event.event_type], event
                        )
                    )
            except RuntimeError:
                # No event loop, create one for async handlers
                asyncio.run(
                    self._run_async_handlers(
                        self.async_handlers[event.event_type], event
                    )
                )

    async def publish_async(self, event: Event) -> None:
        """
        Publish an event asynchronously to all registered handlers.

        Args:
            event: The event to publish
        """
        logger.info(
            f"Publishing async event: {event.event_type.value} | "
            f"aggregate_id={event.aggregate_id} | user_id={event.user_id}"
        )

        # Log event to audit trail
        self._log_event(event)

        # Call synchronous handlers
        if event.event_type in self.handlers:
            for handler in self.handlers[event.event_type]:
                try:
                    handler(event)
                    logger.debug(f"Handler {handler.__name__} executed successfully")
                except Exception as e:
                    logger.error(
                        f"Error in handler {handler.__name__}: {str(e)}",
                        exc_info=True,
                    )

        # Call async handlers
        if event.event_type in self.async_handlers:
            await self._run_async_handlers(
                self.async_handlers[event.event_type], event
            )

    async def _run_async_handler(
        self, handler: Callable[[Event], Coroutine], event: Event
    ) -> None:
        """Run a single async handler with error handling."""
        try:
            await handler(event)
            logger.debug(f"Async handler {handler.__name__} executed successfully")
        except Exception as e:
            logger.error(
                f"Error in async handler {handler.__name__}: {str(e)}",
                exc_info=True,
            )

    async def _run_async_handlers(
        self, handlers: list[Callable[[Event], Coroutine]], event: Event
    ) -> None:
        """Run multiple async handlers concurrently."""
        tasks = [handler(event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(
                    f"Error in async handler {handler.__name__}: {str(result)}",
                    exc_info=True,
                )

    def _log_event(self, event: Event) -> None:
        """
        Log event to audit trail in database.

        Args:
            event: The event to log
        """
        if not self.db_session:
            return

        try:
            from app.models import AuditLog

            audit_log = AuditLog(
                event_type=event.event_type.value,
                aggregate_id=event.aggregate_id,
                aggregate_type=event.aggregate_type,
                user_id=event.user_id,
                event_data=event.to_dict(),
                timestamp=event.timestamp,
            )
            self.db_session.add(audit_log)
            self.db_session.commit()
        except Exception as e:
            logger.error(f"Failed to log event to audit trail: {str(e)}", exc_info=True)

    def get_handlers_for_event(self, event_type: EventType) -> dict[str, list]:
        """
        Get all handlers registered for an event type.

        Args:
            event_type: The event type to query

        Returns:
            Dictionary with sync and async handlers
        """
        return {
            "sync": self.handlers.get(event_type, []),
            "async": self.async_handlers.get(event_type, []),
        }

    def clear_handlers(self) -> None:
        """Clear all registered handlers."""
        self.handlers.clear()
        self.async_handlers.clear()
        logger.info("All event handlers cleared")


def get_event_bus(db_session: Optional[Session] = None) -> EventBus:
    """
    Get or create the global event bus instance.

    Args:
        db_session: Optional SQLAlchemy session for audit logging

    Returns:
        The event bus instance
    """
    global _event_bus

    if _event_bus is None:
        _event_bus = EventBus(db_session)

    return _event_bus


def reset_event_bus() -> None:
    """Reset the global event bus instance (for testing)."""
    global _event_bus
    _event_bus = None
