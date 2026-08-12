"""
Celery Configuration - Async task processing for Quality Weekly Intelligence.

Configures Celery for distributed task processing with Redis broker,
result backend, and worker settings.
"""

import logging
from typing import Optional

from celery import Celery

logger = logging.getLogger(__name__)


class CeleryConfig:
    """Celery configuration class."""

    # Broker settings
    broker_url: str = "redis://localhost:6379/1"
    result_backend: str = "redis://localhost:6379/2"

    # Task settings
    task_serializer: str = "json"
    accept_content: list = ["json"]
    result_serializer: str = "json"
    timezone: str = "UTC"
    enable_utc: bool = True

    # Task execution settings
    task_track_started: bool = True
    task_time_limit: int = 30 * 60  # 30 minutes
    task_soft_time_limit: int = 25 * 60  # 25 minutes

    # Result backend settings
    result_expires: int = 3600  # 1 hour
    result_persistent: bool = True

    # Worker settings
    worker_prefetch_multiplier: int = 1
    worker_max_tasks_per_child: int = 1000

    # Retry settings
    task_acks_late: bool = True
    task_reject_on_worker_lost: bool = True

    # Queue settings
    task_default_queue: str = "default"
    task_queues: dict = {
        "default": {"routing_key": "default"},
        "ai_tasks": {"routing_key": "ai.*"},
        "pptx_tasks": {"routing_key": "pptx.*"},
        "notifications": {"routing_key": "notifications.*"},
        "exports": {"routing_key": "exports.*"},
    }

    # Route tasks to appropriate queues
    task_routes: dict = {
        "app.tasks.ai_tasks.*": {"queue": "ai_tasks"},
        "app.tasks.pptx_tasks.*": {"queue": "pptx_tasks"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.export_tasks.*": {"queue": "exports"},
    }


def create_celery_app(config_class: Optional[type] = None) -> Celery:
    """
    Create and configure Celery application.

    Args:
        config_class: Optional custom config class

    Returns:
        Configured Celery application
    """
    celery_app = Celery("quality_weekly_intelligence")

    # Use provided config or default
    config = config_class or CeleryConfig

    celery_app.config_from_object(config)

    # Auto-discover tasks from app.tasks
    celery_app.autodiscover_tasks(["app.tasks"])

    logger.info("Celery app created and configured")
    return celery_app


# Create the Celery app instance
celery_app = create_celery_app()


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    logger.info(f"Request: {self.request!r}")
