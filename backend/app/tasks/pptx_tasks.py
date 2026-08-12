"""
PPTX Generation Tasks - Async report generation via Celery.

Tasks:
- generate_pptx_report: Generate PPTX for a single weekly report
- generate_pptx_batch: Generate multiple reports in parallel
"""

import logging
from typing import Any, Optional
from pathlib import Path

from app.celery_app import celery_app
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="pptx_tasks",
)
def generate_pptx_report(
    self,
    weekly_id: str,
    user_id: str,
    week_number: int,
    year: int,
) -> dict[str, Any]:
    """
    Generate PPTX report for weekly data.

    Performs:
    - Compile activities and metrics
    - Create presentation slides
    - Generate charts and visualizations
    - Save file to storage

    Args:
        weekly_id: Weekly report ID
        user_id: User ID (owner)
        week_number: ISO week number
        year: Year

    Returns:
        Generation result with file info

    Raises:
        Retries on failure (max 2 times)
    """
    logger.info(
        f"Generating PPTX report {weekly_id} | week={week_number}/{year} | user={user_id}"
    )

    db = SessionLocal()
    try:
        from app.events import get_event_bus
        from app.events.types import ProcessingStartedEvent, ProcessingCompletedEvent
        from app.models import WeeklyReport
        from time import time

        start_time = time()

        # Publish processing started event
        event_bus = get_event_bus(db)
        start_event = ProcessingStartedEvent(
            aggregate_id=weekly_id,
            processing_type="pptx_generation",
            user_id=user_id,
            metadata={
                "week": week_number,
                "year": year,
            },
        )
        event_bus.publish(start_event)

        # Get weekly report
        weekly = db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
        if not weekly:
            raise ValueError(f"Weekly report {weekly_id} not found")

        # Generate PPTX
        from app.services.pptx_service import PPTXService

        pptx_service = PPTXService(db)
        pptx_path = pptx_service.generate_weekly_presentation(weekly)

        duration = time() - start_time

        # Update cache
        from app.cache import cache

        cache_data = {
            "id": weekly_id,
            "pptx_path": str(pptx_path),
            "generated_at": start_time,
            "file_size": Path(pptx_path).stat().st_size,
        }
        cache.set_weekly_report(weekly_id, cache_data, ttl=7200)

        # Publish completion event
        completion_event = ProcessingCompletedEvent(
            aggregate_id=weekly_id,
            processing_type="pptx_generation",
            duration_seconds=duration,
            user_id=user_id,
            result={
                "file_path": str(pptx_path),
                "file_size": Path(pptx_path).stat().st_size,
            },
        )
        event_bus.publish(completion_event)

        logger.info(
            f"PPTX report {weekly_id} generated successfully | "
            f"path={pptx_path} | duration={duration:.2f}s"
        )

        return {
            "weekly_id": weekly_id,
            "status": "success",
            "file_path": str(pptx_path),
            "duration": duration,
        }

    except Exception as exc:
        logger.error(
            f"Error generating PPTX report {weekly_id}: {str(exc)}", exc_info=True
        )

        # Publish failure event
        try:
            from app.events import get_event_bus
            from app.events.types import EventType, Event

            event_bus = get_event_bus(db)
            failure_event = Event(
                event_type=EventType.PROCESSING_FAILED,
                aggregate_id=weekly_id,
                aggregate_type="weekly",
                user_id=user_id,
                metadata={"error": str(exc)},
            )
            event_bus.publish(failure_event)
        except Exception as e:
            logger.error(f"Failed to publish failure event: {str(e)}")

        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()


@celery_app.task(
    bind=True,
    default_retry_delay=120,
    queue="pptx_tasks",
)
def generate_pptx_batch(
    self,
    weekly_ids: list[str],
    user_id: str,
) -> dict[str, Any]:
    """
    Generate multiple PPTX reports in parallel.

    Uses Celery chord to generate reports in parallel
    and wait for all to complete.

    Args:
        weekly_ids: List of weekly report IDs
        user_id: User ID (owner)

    Returns:
        Batch generation result

    Raises:
        Retries on failure
    """
    logger.info(
        f"Batch generating {len(weekly_ids)} PPTX reports | user={user_id}"
    )

    try:
        from celery import group

        # Get week/year data for each report
        db = SessionLocal()
        try:
            from app.models import WeeklyReport

            reports = (
                db.query(WeeklyReport)
                .filter(WeeklyReport.id.in_(weekly_ids))
                .all()
            )

            # Create task group for parallel generation
            tasks = group([
                generate_pptx_report.s(
                    weekly_id=report.id,
                    user_id=user_id,
                    week_number=report.week_number,
                    year=report.year,
                )
                for report in reports
            ])

            # Execute all tasks
            result = tasks.apply_async()

            logger.info(
                f"Batch PPTX generation started | "
                f"group_id={result.id} | count={len(weekly_ids)}"
            )

            return {
                "status": "queued",
                "group_id": result.id,
                "count": len(weekly_ids),
            }

        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Error in batch PPTX generation: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=120)
