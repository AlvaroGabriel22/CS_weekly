# Integration Steps - Event System, Redis Cache & Celery

Step-by-step guide to integrate the new async processing system into the existing FastAPI application.

## Prerequisites

### 1. Update requirements.txt

Add these packages (already listed):

```
redis==5.0.1
celery==5.3.4
flower==2.0.1  # Optional: for monitoring
pytz==2024.1   # For timezone handling
```

Install:
```bash
pip install -r requirements.txt
```

### 2. Update Environment Configuration

Add to `.env`:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Leave empty for local development

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Worker Configuration (adjust based on hardware)
CELERY_CONCURRENCY=4
AI_WORKER_CONCURRENCY=2
PPTX_WORKER_CONCURRENCY=2
NOTIFICATION_WORKER_CONCURRENCY=4
EXPORT_WORKER_CONCURRENCY=2

# Celery Logging
CELERY_LOG_LEVEL=info
```

### 3. Update app/core/config.py

Add Redis and Celery configuration:

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ... existing configuration ...

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_TTL: int = 3600  # Default cache TTL in seconds

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Worker Configuration
    CELERY_CONCURRENCY: int = 4
    AI_WORKER_CONCURRENCY: int = 2
    PPTX_WORKER_CONCURRENCY: int = 2
    NOTIFICATION_WORKER_CONCURRENCY: int = 4
    EXPORT_WORKER_CONCURRENCY: int = 2
    CELERY_LOG_LEVEL: str = "info"

    # Async Processing
    ENABLE_ASYNC_PROCESSING: bool = True
    TASK_TIME_LIMIT: int = 30 * 60  # 30 minutes


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## Integration Steps

### Step 1: Update app/main.py

Import the integration helpers:

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import activities, auth, users, weekly, pptx
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.exceptions import QWIException
from app.core.logging import setup_logging
from app.core.migrations import run_migrations
from app.models import Template, Language
from app.core.database import SessionLocal

# NEW: Import async system
from app.events.integration import (
    initialize_async_system,
    cleanup_async_system,
)

settings = get_settings()
setup_logging()


def seed_default_template():
    # ... existing code ...
    pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Quality Weekly Intelligence - AI-powered corporate weekly report platform",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(QWIException)
    async def qwi_exception_handler(request: Request, exc: QWIException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(activities.router, prefix="/api")
    app.include_router(weekly.router, prefix="/api")
    app.include_router(pptx.router)

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)
        run_migrations()
        seed_default_template()

        # NEW: Initialize async processing system
        if settings.ENABLE_ASYNC_PROCESSING:
            try:
                initialize_async_system(
                    redis_host=settings.REDIS_HOST,
                    redis_port=settings.REDIS_PORT,
                    redis_db=settings.REDIS_DB,
                    redis_password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                )
            except Exception as e:
                logger.warning(f"Async processing system initialization failed: {e}")
                logger.warning("Application will run without async features")

    @app.on_event("shutdown")
    def on_shutdown():
        # NEW: Cleanup async system
        if settings.ENABLE_ASYNC_PROCESSING:
            cleanup_async_system()

    @app.get("/api/health")
    def health():
        return {"status": "healthy", "version": settings.APP_VERSION}

    return app


app = create_app()
```

### Step 2: Update Route Handlers

Example: Integrating with activity creation endpoint

**In app/api/routes/activities.py:**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas import ActivitySchema, ActivityResponse
from app.core.database import get_db
from app.models import Activity
from app.services import ActivityService

# NEW: Import event system
from app.events import get_event_bus, ActivityCreatedEvent
from app.cache import get_cache

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.post("/", response_model=ActivityResponse)
def create_activity(
    activity_data: ActivitySchema,
    db: Session = Depends(get_db),
):
    """Create a new activity with async AI processing."""

    # Create activity
    activity = Activity(**activity_data.dict())
    db.add(activity)
    db.commit()
    db.refresh(activity)

    # NEW: Publish event (triggers AI processing via Celery)
    try:
        event_bus = get_event_bus(db)
        event = ActivityCreatedEvent(
            aggregate_id=activity.id,
            title=activity.title,
            department=activity.department,
            user_id=activity_data.user_id,
        )
        event_bus.publish(event)
    except Exception as e:
        logger.warning(f"Failed to publish activity created event: {e}")
        # Continue - don't fail the request

    return ActivityResponse.from_orm(activity)


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: str,
    db: Session = Depends(get_db),
):
    """Get activity with cache support."""

    # NEW: Try cache first
    cache = get_cache()
    cached = cache.get_activity(activity_id)
    if cached:
        logger.info(f"Activity cache hit: {activity_id}")
        return cached

    # Query database
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # NEW: Cache the result
    try:
        cache.set_activity(activity_id, activity.dict(), ttl=3600)
    except Exception as e:
        logger.warning(f"Failed to cache activity: {e}")

    return ActivityResponse.from_orm(activity)


@router.get("/user/{user_id}")
def get_user_activities(
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get all activities for a user with cache support."""

    # NEW: Try cache first
    cache = get_cache()
    cached = cache.get_user_activities(user_id)
    if cached:
        logger.info(f"User activities cache hit: {user_id}")
        return cached

    # Query database
    activities = db.query(Activity).filter(Activity.owner_id == user_id).all()

    # NEW: Cache the result
    try:
        cache.set_user_activities(user_id, [a.dict() for a in activities], ttl=1800)
    except Exception as e:
        logger.warning(f"Failed to cache user activities: {e}")

    return [ActivityResponse.from_orm(a) for a in activities]
```

### Step 3: Update Weekly Report Routes

**In app/api/routes/weekly.py:**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas import WeeklyReportSchema, WeeklyReportResponse
from app.core.database import get_db
from app.models import WeeklyReport
from app.services import WeeklyService

# NEW: Import event system
from app.events import get_event_bus, WeeklyGeneratedEvent
from app.cache import get_cache

router = APIRouter(prefix="/api/weekly", tags=["weekly"])


@router.post("/", response_model=WeeklyReportResponse)
def create_weekly_report(
    report_data: WeeklyReportSchema,
    db: Session = Depends(get_db),
):
    """Create weekly report with async PPTX generation and notifications."""

    # Create report
    weekly = WeeklyReport(**report_data.dict())
    db.add(weekly)
    db.commit()
    db.refresh(weekly)

    # NEW: Publish event (triggers PPTX generation)
    try:
        event_bus = get_event_bus(db)
        event = WeeklyGeneratedEvent(
            aggregate_id=weekly.id,
            week_number=weekly.week_number,
            year=weekly.year,
            total_activities=len(weekly.activities),
            user_id=weekly.owner_id,
        )
        event_bus.publish(event)
    except Exception as e:
        logger.warning(f"Failed to publish weekly generated event: {e}")

    return WeeklyReportResponse.from_orm(weekly)


@router.get("/{weekly_id}", response_model=WeeklyReportResponse)
def get_weekly_report(
    weekly_id: str,
    db: Session = Depends(get_db),
):
    """Get weekly report with cache support."""

    # NEW: Try cache first
    cache = get_cache()
    cached = cache.get_weekly_report(weekly_id)
    if cached:
        logger.info(f"Weekly report cache hit: {weekly_id}")
        return cached

    # Query database
    weekly = db.query(WeeklyReport).filter(WeeklyReport.id == weekly_id).first()
    if not weekly:
        raise HTTPException(status_code=404, detail="Weekly report not found")

    # NEW: Cache the result
    try:
        cache.set_weekly_report(weekly_id, weekly.dict(), ttl=3600)
    except Exception as e:
        logger.warning(f"Failed to cache weekly report: {e}")

    return WeeklyReportResponse.from_orm(weekly)
```

### Step 4: Update Permission Routes

**In app/api/routes/permissions.py (if exists) or add to a new permissions endpoint:**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# NEW: Import event system
from app.events import get_event_bus, PermissionGrantedEvent
from app.cache import get_cache

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


@router.post("/grant")
def grant_permission(
    resource_id: str,
    resource_type: str,
    user_id: str,
    permission_level: str = "view",
    db: Session = Depends(get_db),
):
    """Grant permission to a resource."""

    # Grant permission logic
    # ... your existing code ...

    # NEW: Publish permission granted event
    try:
        event_bus = get_event_bus(db)
        event = PermissionGrantedEvent(
            aggregate_id=resource_id,
            resource_id=resource_id,
            resource_type=resource_type,
            grantee_id=user_id,
            permission_level=permission_level,
            user_id=current_user.id,  # Who granted the permission
        )
        event_bus.publish(event)
    except Exception as e:
        logger.warning(f"Failed to publish permission granted event: {e}")

    return {"status": "success"}
```

### Step 5: Add Task Status Endpoint

**Add to app/api/routes/tasks.py (create if doesn't exist):**

```python
from fastapi import APIRouter, HTTPException
from app.celery_app import celery_app

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}/status")
def get_task_status(task_id: str):
    """Get status of a Celery task."""

    result = celery_app.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str):
    """Cancel a Celery task."""

    celery_app.control.revoke(task_id, terminate=True)

    return {"status": "cancelled", "task_id": task_id}
```

## Step 6: Database Migrations

The system uses `AuditLog` model for event logging. Ensure your database has this table:

```python
# If not already in your models, add:
from sqlalchemy import Column, String, DateTime, JSON
from app.core.database import Base
import pytz

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    event_type = Column(String, index=True)
    aggregate_id = Column(String, index=True)
    aggregate_type = Column(String)
    user_id = Column(String, nullable=True)
    event_data = Column(JSON)
    timestamp = Column(DateTime, default=lambda: datetime.now(pytz.UTC), index=True)

    __table_args__ = (
        Index("idx_event_type_timestamp", "event_type", "timestamp"),
        Index("idx_aggregate_id", "aggregate_id"),
    )
```

Run migrations:

```bash
cd backend
alembic revision --autogenerate -m "Add audit log table"
alembic upgrade head
```

## Testing the Integration

### 1. Test Redis Connection

```bash
# In Python shell
from app.cache import get_cache

cache = get_cache()
cache.set("test_key", {"test": "value"})
value = cache.get("test_key")
print(value)  # Should print: {"test": "value"}
```

### 2. Test Event Bus

```python
from app.events import get_event_bus, ActivityCreatedEvent, EventHandlers
from app.core.database import SessionLocal

db = SessionLocal()
event_bus = get_event_bus(db)

# Register handlers
from app.events.handlers import register_event_handlers
register_event_handlers(event_bus)

# Publish event
event = ActivityCreatedEvent(
    aggregate_id="test-123",
    title="Test Activity",
    user_id="user-1",
)
event_bus.publish(event)

# Check audit log
from app.models import AuditLog
logs = db.query(AuditLog).filter(AuditLog.aggregate_id == "test-123").all()
print(f"Logged events: {len(logs)}")
```

### 3. Test Celery Task

```bash
# Start Celery worker in another terminal
celery -A app.celery_app worker -l info

# Then in Python:
from app.tasks import process_activity_ai

# Queue a task
task = process_activity_ai.delay(
    activity_id="test-activity-123",
    user_id="user-1",
)

print(f"Task ID: {task.id}")
print(f"Task Status: {task.status}")

# Check result
import time
time.sleep(5)  # Wait for task to complete
print(f"Result: {task.result}")
```

### 4. Test API Endpoint

```bash
# Create activity (should publish event and queue AI task)
curl -X POST http://localhost:8000/api/activities \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Activity",
    "department": "Quality",
    "user_id": "user-123"
  }'

# Check if activity was cached
curl http://localhost:8000/api/activities/activity-id
```

## Monitoring

### 1. Check Celery Workers

```bash
# List active tasks
celery -A app.celery_app inspect active

# List registered tasks
celery -A app.celery_app inspect registered

# Check worker stats
celery -A app.celery_app inspect stats
```

### 2. Check Redis

```bash
redis-cli

# Check memory usage
> INFO memory

# View keys
> KEYS *

# Check specific key
> GET activity:test-id
```

### 3. Check Audit Logs

```python
from app.core.database import SessionLocal
from app.models import AuditLog

db = SessionLocal()
recent_events = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(20).all()

for event in recent_events:
    print(f"{event.timestamp}: {event.event_type} - {event.aggregate_id}")
```

## Troubleshooting

### Events not triggering tasks

1. Check Redis is running: `redis-cli ping`
2. Check Celery worker is running: `celery -A app.celery_app inspect active`
3. Check handler registration: Print handlers after initialization
4. Check logs for errors

### Cache not working

1. Check Redis connection: `redis-cli`
2. Verify cache is being initialized in startup event
3. Check TTL values are appropriate

### Celery tasks failing

1. Check task logs in worker terminal
2. Check task in Redis queue: `celery -A app.celery_app inspect active`
3. Check for task dependency issues (imports, etc.)

## Next Steps

1. Customize event handlers for your business logic
2. Add more task types as needed
3. Implement monitoring dashboard with Flower
4. Add rate limiting for task queues
5. Set up log aggregation and alerts
6. Performance tuning based on monitoring data

## Support

For issues or questions, refer to:
- ASYNC_PROCESSING_GUIDE.md - Detailed architecture guide
- Celery docs: https://docs.celeryproject.io
- Redis docs: https://redis.io/docs
