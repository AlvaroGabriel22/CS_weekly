import asyncio
import logging

from sqlalchemy.orm import joinedload

from app.core.database import SessionLocal
from app.models import Activity, Attachment
from app.services.business import ActivityService, FileService

logger = logging.getLogger(__name__)


def process_activity_in_background(activity_id: str) -> None:
    """Run activity enrichment after the HTTP response has been sent."""
    database = SessionLocal()
    try:
        activity = (
            database.query(Activity)
            .options(joinedload(Activity.metadata_entry))
            .filter(Activity.id == activity_id)
            .first()
        )
        if activity:
            asyncio.run(
                ActivityService(database).process_activity_metadata(activity)
            )
    except Exception:
        logger.exception(
            "Background activity processing failed | activity_id=%s",
            activity_id,
        )
    finally:
        database.close()


def process_attachment_in_background(attachment_id: str) -> None:
    """Analyze an uploaded attachment without delaying the employee."""
    database = SessionLocal()
    try:
        attachment = (
            database.query(Attachment)
            .options(joinedload(Attachment.activity))
            .filter(Attachment.id == attachment_id)
            .first()
        )
        if attachment:
            asyncio.run(FileService(database).process_attachment(attachment))
    except Exception:
        logger.exception(
            "Background attachment processing failed | attachment_id=%s",
            attachment_id,
        )
    finally:
        database.close()
