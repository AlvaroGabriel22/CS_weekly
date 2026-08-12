"""
Celery Worker Configuration - Settings for running Celery workers.

This file provides configuration for starting and running Celery workers
with optimized settings for different task queues.

Usage:
    # Start all workers (default)
    celery -A app.celery_app worker -l info

    # Start AI task worker
    celery -A app.celery_app worker -Q ai_tasks -l info

    # Start PPTX task worker
    celery -A app.celery_app worker -Q pptx_tasks -l info

    # Start notification worker
    celery -A app.celery_app worker -Q notifications -l info

    # With Flower monitoring
    celery -A app.celery_app flower
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class WorkerConfig:
    """Base worker configuration."""

    # Broker and backend
    BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    # Logging
    LOG_LEVEL: str = os.getenv("CELERY_LOG_LEVEL", "info")

    # Worker settings
    WORKER_CONCURRENCY: int = int(os.getenv("CELERY_CONCURRENCY", "4"))
    WORKER_PREFETCH_MULTIPLIER: int = 1
    WORKER_MAX_TASKS_PER_CHILD: int = 1000

    # Task settings
    TASK_ALWAYS_EAGER: bool = os.getenv("CELERY_ALWAYS_EAGER", "false").lower() == "true"
    TASK_EAGER_PROPAGATES: bool = True

    # Timezone
    TIMEZONE: str = "UTC"

    @classmethod
    def get_worker_args(cls) -> dict:
        """Get worker command-line arguments."""
        return {
            "loglevel": cls.LOG_LEVEL,
            "concurrency": cls.WORKER_CONCURRENCY,
            "prefetch_multiplier": cls.WORKER_PREFETCH_MULTIPLIER,
            "max_tasks_per_child": cls.WORKER_MAX_TASKS_PER_CHILD,
        }


class AIWorkerConfig(WorkerConfig):
    """Configuration for AI task worker."""

    QUEUE: str = "ai_tasks"
    WORKER_CONCURRENCY: int = int(os.getenv("AI_WORKER_CONCURRENCY", "2"))
    DESCRIPTION: str = "AI processing worker (higher resource usage)"


class PPTXWorkerConfig(WorkerConfig):
    """Configuration for PPTX generation worker."""

    QUEUE: str = "pptx_tasks"
    WORKER_CONCURRENCY: int = int(os.getenv("PPTX_WORKER_CONCURRENCY", "2"))
    DESCRIPTION: str = "PPTX generation worker (high memory usage)"


class NotificationWorkerConfig(WorkerConfig):
    """Configuration for notification delivery worker."""

    QUEUE: str = "notifications"
    WORKER_CONCURRENCY: int = int(os.getenv("NOTIFICATION_WORKER_CONCURRENCY", "4"))
    DESCRIPTION: str = "Notification delivery worker (low resource usage)"


class ExportWorkerConfig(WorkerConfig):
    """Configuration for data export worker."""

    QUEUE: str = "exports"
    WORKER_CONCURRENCY: int = int(os.getenv("EXPORT_WORKER_CONCURRENCY", "2"))
    DESCRIPTION: str = "Data export worker"


def get_worker_config(worker_type: str = "all") -> WorkerConfig:
    """
    Get worker configuration by type.

    Args:
        worker_type: Worker type (all, ai, pptx, notifications, exports)

    Returns:
        Worker configuration class
    """
    configs = {
        "ai": AIWorkerConfig,
        "pptx": PPTXWorkerConfig,
        "notifications": NotificationWorkerConfig,
        "exports": ExportWorkerConfig,
    }

    if worker_type == "all":
        return WorkerConfig

    return configs.get(worker_type, WorkerConfig)


def print_worker_info():
    """Print information about available workers."""
    print("\n" + "=" * 60)
    print("Celery Workers Configuration")
    print("=" * 60)

    print("\nBase Worker (all queues):")
    print(f"  Command: celery -A app.celery_app worker -l info")
    print(f"  Queues: default, ai_tasks, pptx_tasks, notifications, exports")
    print(f"  Concurrency: {WorkerConfig.WORKER_CONCURRENCY}")

    print("\nAI Worker (CPU-intensive AI processing):")
    config = AIWorkerConfig()
    print(f"  Command: celery -A app.celery_app worker -Q {config.QUEUE} -l info")
    print(f"  Queue: {config.QUEUE}")
    print(f"  Concurrency: {config.WORKER_CONCURRENCY}")
    print(f"  Note: {config.DESCRIPTION}")

    print("\nPPTX Worker (Memory-intensive PPTX generation):")
    config = PPTXWorkerConfig()
    print(f"  Command: celery -A app.celery_app worker -Q {config.QUEUE} -l info")
    print(f"  Queue: {config.QUEUE}")
    print(f"  Concurrency: {config.WORKER_CONCURRENCY}")
    print(f"  Note: {config.DESCRIPTION}")

    print("\nNotification Worker (Fast notification delivery):")
    config = NotificationWorkerConfig()
    print(f"  Command: celery -A app.celery_app worker -Q {config.QUEUE} -l info")
    print(f"  Queue: {config.QUEUE}")
    print(f"  Concurrency: {config.WORKER_CONCURRENCY}")
    print(f"  Note: {config.DESCRIPTION}")

    print("\nExport Worker (Data export processing):")
    config = ExportWorkerConfig()
    print(f"  Command: celery -A app.celery_app worker -Q {config.QUEUE} -l info")
    print(f"  Queue: {config.QUEUE}")
    print(f"  Concurrency: {config.WORKER_CONCURRENCY}")
    print(f"  Note: {config.DESCRIPTION}")

    print("\nMonitoring:")
    print("  Command: celery -A app.celery_app flower")
    print("  Dashboard: http://localhost:5555")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    print_worker_info()
