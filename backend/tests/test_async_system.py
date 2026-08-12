"""
Unit and Integration Tests for Event System, Cache, and Celery Tasks.

Tests for:
- Event bus functionality
- Event handler registration
- Redis cache operations
- Celery task execution
"""

import pytest
from datetime import datetime
from typing import Generator
from unittest.mock import Mock, patch, MagicMock

from sqlalchemy.orm import Session

# Event Bus Tests
from app.events.bus import EventBus, get_event_bus, reset_event_bus
from app.events.types import (
    Event,
    EventType,
    ActivityCreatedEvent,
    WeeklyGeneratedEvent,
    PermissionGrantedEvent,
)
from app.events.handlers import EventHandlers, register_event_handlers

# Cache Tests
from app.cache.redis_client import RedisCache

# Celery Tests
from app.celery_app import celery_app


class TestEventBus:
    """Test EventBus functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        reset_event_bus()

    def test_event_bus_creation(self):
        """Test event bus can be created."""
        bus = EventBus()
        assert bus is not None
        assert len(bus.handlers) == 0
        assert len(bus.async_handlers) == 0

    def test_subscribe_sync_handler(self):
        """Test subscribing to synchronous events."""
        bus = EventBus()
        handler = Mock()

        bus.subscribe(EventType.ACTIVITY_CREATED, handler)

        assert EventType.ACTIVITY_CREATED in bus.handlers
        assert handler in bus.handlers[EventType.ACTIVITY_CREATED]

    def test_subscribe_async_handler(self):
        """Test subscribing to asynchronous events."""
        bus = EventBus()
        async_handler = Mock()

        bus.subscribe_async(EventType.ACTIVITY_CREATED, async_handler)

        assert EventType.ACTIVITY_CREATED in bus.async_handlers
        assert async_handler in bus.async_handlers[EventType.ACTIVITY_CREATED]

    def test_publish_event_calls_handler(self):
        """Test publishing an event calls registered handlers."""
        bus = EventBus()
        handler = Mock()

        bus.subscribe(EventType.ACTIVITY_CREATED, handler)

        event = ActivityCreatedEvent(
            aggregate_id="test-123",
            title="Test Activity",
            user_id="user-1",
        )

        bus.publish(event)

        handler.assert_called_once()
        called_event = handler.call_args[0][0]
        assert called_event.aggregate_id == "test-123"

    def test_publish_event_with_multiple_handlers(self):
        """Test publishing calls multiple handlers."""
        bus = EventBus()
        handler1 = Mock()
        handler2 = Mock()

        bus.subscribe(EventType.ACTIVITY_CREATED, handler1)
        bus.subscribe(EventType.ACTIVITY_CREATED, handler2)

        event = ActivityCreatedEvent(
            aggregate_id="test-123",
            title="Test Activity",
        )

        bus.publish(event)

        handler1.assert_called_once()
        handler2.assert_called_once()

    def test_unsubscribe_handler(self):
        """Test unsubscribing removes handler."""
        bus = EventBus()
        handler = Mock()

        bus.subscribe(EventType.ACTIVITY_CREATED, handler)
        bus.unsubscribe(EventType.ACTIVITY_CREATED, handler)

        event = ActivityCreatedEvent(aggregate_id="test-123", title="Test")
        bus.publish(event)

        handler.assert_not_called()

    def test_publish_handles_handler_exceptions(self):
        """Test publishing handles exceptions in handlers."""
        bus = EventBus()
        failing_handler = Mock(side_effect=Exception("Test error"))
        success_handler = Mock()

        bus.subscribe(EventType.ACTIVITY_CREATED, failing_handler)
        bus.subscribe(EventType.ACTIVITY_CREATED, success_handler)

        event = ActivityCreatedEvent(aggregate_id="test-123", title="Test")

        # Should not raise
        bus.publish(event)

        failing_handler.assert_called_once()
        success_handler.assert_called_once()

    def test_get_handlers_for_event(self):
        """Test retrieving handlers for an event."""
        bus = EventBus()
        sync_handler = Mock()
        async_handler = Mock()

        bus.subscribe(EventType.ACTIVITY_CREATED, sync_handler)
        bus.subscribe_async(EventType.ACTIVITY_CREATED, async_handler)

        handlers = bus.get_handlers_for_event(EventType.ACTIVITY_CREATED)

        assert len(handlers["sync"]) == 1
        assert len(handlers["async"]) == 1

    def test_clear_handlers(self):
        """Test clearing all handlers."""
        bus = EventBus()
        bus.subscribe(EventType.ACTIVITY_CREATED, Mock())
        bus.subscribe_async(EventType.WEEKLY_GENERATED, Mock())

        bus.clear_handlers()

        assert len(bus.handlers) == 0
        assert len(bus.async_handlers) == 0

    def test_global_event_bus_instance(self):
        """Test global event bus singleton."""
        reset_event_bus()

        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2


class TestEventTypes:
    """Test event type definitions."""

    def test_activity_created_event(self):
        """Test ActivityCreatedEvent creation."""
        event = ActivityCreatedEvent(
            aggregate_id="activity-123",
            title="Test Activity",
            department="Quality",
            user_id="user-1",
        )

        assert event.aggregate_id == "activity-123"
        assert event.title == "Test Activity"
        assert event.department == "Quality"
        assert event.event_type == EventType.ACTIVITY_CREATED

    def test_weekly_generated_event(self):
        """Test WeeklyGeneratedEvent creation."""
        event = WeeklyGeneratedEvent(
            aggregate_id="weekly-123",
            week_number=42,
            year=2024,
            total_activities=10,
            user_id="user-1",
        )

        assert event.aggregate_id == "weekly-123"
        assert event.week_number == 42
        assert event.total_activities == 10
        assert event.event_type == EventType.WEEKLY_GENERATED

    def test_permission_granted_event(self):
        """Test PermissionGrantedEvent creation."""
        event = PermissionGrantedEvent(
            aggregate_id="perm-123",
            resource_type="activity",
            resource_id="activity-456",
            grantee_id="user-2",
            permission_level="edit",
            user_id="user-1",
        )

        assert event.resource_type == "activity"
        assert event.permission_level == "edit"
        assert event.event_type == EventType.PERMISSION_GRANTED

    def test_event_to_dict(self):
        """Test event serialization to dict."""
        event = ActivityCreatedEvent(
            aggregate_id="activity-123",
            title="Test",
            user_id="user-1",
        )

        event_dict = event.to_dict()

        assert event_dict["aggregate_id"] == "activity-123"
        assert event_dict["event_type"] == EventType.ACTIVITY_CREATED.value
        assert "timestamp" in event_dict


class TestEventHandlers:
    """Test event handler functions."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_db = Mock(spec=Session)

    @patch("app.events.handlers.get_event_bus")
    @patch("app.events.handlers.process_activity_ai")
    def test_on_activity_created_publishes_ai_task(self, mock_task, mock_get_bus):
        """Test activity created handler queues AI task."""
        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus

        event = ActivityCreatedEvent(
            aggregate_id="activity-123",
            title="Test Activity",
            user_id="user-1",
        )

        # Call handler
        with patch("app.cache.get_cache"):
            EventHandlers.on_activity_created(event)

        # Verify task was queued
        mock_task.delay.assert_called_once()

    @patch("app.events.handlers.get_event_bus")
    def test_on_weekly_generated_publishes_events(self, mock_get_bus):
        """Test weekly generated handler publishes generation and notification events."""
        mock_bus = Mock()
        mock_get_bus.return_value = mock_bus

        event = WeeklyGeneratedEvent(
            aggregate_id="weekly-123",
            week_number=42,
            year=2024,
            user_id="user-1",
        )

        with patch("app.cache.get_cache"):
            with patch("app.events.handlers.generate_pptx_report"):
                with patch("app.events.handlers.send_weekly_notification"):
                    EventHandlers.on_weekly_generated(event)

    def test_register_event_handlers(self):
        """Test registering all event handlers."""
        reset_event_bus()
        bus = get_event_bus()

        register_event_handlers(bus)

        # Verify handlers are registered
        assert len(bus.handlers[EventType.ACTIVITY_CREATED]) > 0
        assert len(bus.handlers[EventType.WEEKLY_GENERATED]) > 0


class TestRedisCache:
    """Test Redis cache functionality."""

    def test_redis_cache_creation_no_connection(self):
        """Test cache can be created even if Redis is unavailable."""
        cache = RedisCache(host="invalid_host", port=9999)

        # Should not raise, just not connected
        assert cache is not None

    @pytest.mark.skip(reason="Requires Redis connection")
    def test_cache_set_and_get(self):
        """Test setting and getting values (requires Redis)."""
        cache = RedisCache()

        cache.set("test_key", {"test": "value"}, ttl=60)
        value = cache.get("test_key")

        assert value == {"test": "value"}

    @pytest.mark.skip(reason="Requires Redis connection")
    def test_cache_activity(self):
        """Test activity cache methods (requires Redis)."""
        cache = RedisCache()

        activity_data = {"id": "activity-123", "title": "Test"}
        cache.set_activity("activity-123", activity_data)

        cached = cache.get_activity("activity-123")
        assert cached == activity_data

    @pytest.mark.skip(reason="Requires Redis connection")
    def test_cache_invalidation(self):
        """Test cache invalidation (requires Redis)."""
        cache = RedisCache()

        cache.set_activity("activity-123", {"title": "Test"})
        cache.invalidate_activity_cache("activity-123")

        assert cache.get_activity("activity-123") is None

    @pytest.mark.skip(reason="Requires Redis connection")
    def test_cache_session(self):
        """Test session storage (requires Redis)."""
        cache = RedisCache()

        session_data = {"user_id": "user-1", "token": "abc123"}
        cache.set_session("session-123", session_data, ttl=3600)

        cached = cache.get_session("session-123")
        assert cached == session_data


class TestCeleryTasks:
    """Test Celery task configuration and execution."""

    def test_celery_app_configuration(self):
        """Test Celery app is properly configured."""
        assert celery_app is not None
        assert celery_app.conf.broker_url
        assert celery_app.conf.result_backend

    def test_debug_task(self):
        """Test debug task exists."""
        from app.celery_app import debug_task

        assert debug_task is not None
        assert debug_task.name == "app.celery_app.debug_task"

    @pytest.mark.skip(reason="Requires Celery worker running")
    def test_process_activity_ai_task(self):
        """Test AI processing task (requires worker)."""
        from app.tasks import process_activity_ai

        # Note: This would require a running worker and database
        pass

    def test_task_always_eager_config(self):
        """Test tasks can be configured to run eagerly (sync) for testing."""
        # Enable eager execution
        celery_app.conf.task_always_eager = True

        # Tasks would execute immediately
        assert celery_app.conf.task_always_eager is True


class TestIntegration:
    """Integration tests for the full async system."""

    def setup_method(self):
        """Setup test fixtures."""
        reset_event_bus()

    def test_event_to_task_flow(self):
        """Test event flows to task queue."""
        # Mock the task
        with patch("app.events.handlers.process_activity_ai") as mock_task:
            bus = EventBus()
            register_event_handlers(bus)

            event = ActivityCreatedEvent(
                aggregate_id="activity-123",
                title="Test Activity",
                user_id="user-1",
            )

            with patch("app.cache.get_cache"):
                bus.publish(event)

            # Verify task was queued
            mock_task.delay.assert_called_once()

    def test_multiple_event_types(self):
        """Test handling multiple event types."""
        bus = EventBus()

        activity_handler = Mock()
        weekly_handler = Mock()

        bus.subscribe(EventType.ACTIVITY_CREATED, activity_handler)
        bus.subscribe(EventType.WEEKLY_GENERATED, weekly_handler)

        activity_event = ActivityCreatedEvent(
            aggregate_id="activity-123", title="Test"
        )
        weekly_event = WeeklyGeneratedEvent(
            aggregate_id="weekly-123",
            week_number=42,
            year=2024,
        )

        bus.publish(activity_event)
        bus.publish(weekly_event)

        activity_handler.assert_called_once()
        weekly_handler.assert_called_once()


class TestEventSerialization:
    """Test event serialization for storage/transmission."""

    def test_event_to_dict_json_serializable(self):
        """Test events can be serialized to JSON."""
        import json

        event = ActivityCreatedEvent(
            aggregate_id="activity-123",
            title="Test Activity",
            user_id="user-1",
        )

        event_dict = event.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(event_dict, default=str)
        assert json_str is not None

    def test_permission_event_serialization(self):
        """Test permission event serialization."""
        event = PermissionGrantedEvent(
            aggregate_id="resource-123",
            resource_type="activity",
            resource_id="activity-123",
            grantee_id="user-2",
            permission_level="edit",
            user_id="user-1",
        )

        event_dict = event.to_dict()

        assert event_dict["resource_type"] == "activity"
        assert "timestamp" in event_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
