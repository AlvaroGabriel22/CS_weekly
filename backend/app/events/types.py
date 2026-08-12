"""
Event Type Definitions - Domain events for the Quality Weekly Intelligence system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import pytz


class EventType(str, Enum):
    """All event types in the system."""

    ACTIVITY_CREATED = "activity.created"
    ACTIVITY_UPDATED = "activity.updated"
    ACTIVITY_DELETED = "activity.deleted"
    WEEKLY_GENERATED = "weekly.generated"
    WEEKLY_PUBLISHED = "weekly.published"
    FILE_SHARED = "file.shared"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_REVOKED = "permission.revoked"
    PROCESSING_STARTED = "processing.started"
    PROCESSING_COMPLETED = "processing.completed"
    PROCESSING_FAILED = "processing.failed"
    EXPORT_INITIATED = "export.initiated"
    EXPORT_COMPLETED = "export.completed"
    NOTIFICATION_SENT = "notification.sent"


@dataclass
class Event:
    """Base event class for all domain events."""

    event_type: EventType
    aggregate_id: str  # ID of the entity that triggered the event
    aggregate_type: str  # Type of entity (activity, weekly, user, etc.)
    timestamp: datetime = field(default_factory=lambda: datetime.now(pytz.UTC))
    event_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "metadata": self.metadata,
        }


@dataclass
class ActivityCreatedEvent(Event):
    """Event triggered when an activity is created."""

    title: str = ""
    department: str = ""
    activity_date: Optional[datetime] = None

    def __post_init__(self):
        if self.event_type == EventType(0):  # Default value guard
            self.event_type = EventType.ACTIVITY_CREATED
        if not self.aggregate_type:
            self.aggregate_type = "activity"


@dataclass
class ActivityUpdatedEvent(Event):
    """Event triggered when an activity is updated."""

    title: Optional[str] = None
    changes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.event_type == EventType(0):
            self.event_type = EventType.ACTIVITY_UPDATED
        if not self.aggregate_type:
            self.aggregate_type = "activity"


@dataclass
class WeeklyGeneratedEvent(Event):
    """Event triggered when a weekly report is generated."""

    week_number: int = 0
    year: int = 0
    total_activities: int = 0
    report_url: Optional[str] = None

    def __post_init__(self):
        if self.event_type == EventType(0):
            self.event_type = EventType.WEEKLY_GENERATED
        if not self.aggregate_type:
            self.aggregate_type = "weekly"


@dataclass
class FileSharedEvent(Event):
    """Event triggered when a file is shared."""

    file_id: str = ""
    file_name: str = ""
    shared_with: list[str] = field(default_factory=list)
    permission_level: str = "view"

    def __post_init__(self):
        if self.event_type == EventType(0):
            self.event_type = EventType.FILE_SHARED
        if not self.aggregate_type:
            self.aggregate_type = "file"


@dataclass
class PermissionGrantedEvent(Event):
    """Event triggered when permission is granted."""

    resource_type: str = ""
    resource_id: str = ""
    grantee_id: str = ""
    permission_level: str = "view"

    def __post_init__(self):
        if self.event_type == EventType(0):
            self.event_type = EventType.PERMISSION_GRANTED
        if not self.aggregate_type:
            self.aggregate_type = "permission"


@dataclass
class ProcessingStartedEvent(Event):
    """Event triggered when processing starts."""

    processing_type: str = ""  # ai_analysis, pptx_generation, export, etc.
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.event_type == EventType(0):
            self.event_type = EventType.PROCESSING_STARTED
        if not self.aggregate_type:
            self.aggregate_type = "processing"


@dataclass
class ProcessingCompletedEvent(Event):
    """Event triggered when processing completes."""

    processing_type: str = ""
    duration_seconds: float = 0.0
    result: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.event_type == EventType(0):
            self.event_type = EventType.PROCESSING_COMPLETED
        if not self.aggregate_type:
            self.aggregate_type = "processing"
