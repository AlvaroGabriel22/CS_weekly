"""
Event Bus System - Publish/Subscribe pattern for domain events.

Provides event publishing, subscription, and async processing with
audit logging for tracking all events in the system.
"""

from app.events.bus import EventBus, get_event_bus
from app.events.types import (
    Event,
    EventType,
    ActivityCreatedEvent,
    ActivityUpdatedEvent,
    WeeklyGeneratedEvent,
    FileSharedEvent,
    PermissionGrantedEvent,
    ProcessingStartedEvent,
    ProcessingCompletedEvent,
)

__all__ = [
    "EventBus",
    "get_event_bus",
    "Event",
    "EventType",
    "ActivityCreatedEvent",
    "ActivityUpdatedEvent",
    "WeeklyGeneratedEvent",
    "FileSharedEvent",
    "PermissionGrantedEvent",
    "ProcessingStartedEvent",
    "ProcessingCompletedEvent",
]
