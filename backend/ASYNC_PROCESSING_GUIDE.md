# Async Processing System - Event Bus, Redis Cache & Celery

Comprehensive guide for the async processing architecture.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│                    (HTTP Endpoints)                          │
└────────┬────────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────┐
         │                                 │
    ┌────▼─────┐                   ┌──────▼───────┐
    │ Event Bus │                   │ Event        │
    │ (Publish) │                   │ Handlers     │
    └────┬─────┘                    └──────┬───────┘
         │                                 │
    ┌────▼──────────────────────────────────▼──────┐
    │        Celery Task Queue                      │
    │  (process_activity_ai, generate_pptx, etc.)  │
    └────┬──────────────────────────────────┬──────┘
         │                                  │
    ┌────▼────────────────────────────┐   │
    │  Redis Broker & Result Backend  │   │
    │  (Task queueing, state storage) │   │
    └──────────────────────────────────┘   │
         │                                  │
         ├──────────────────────────────────┤
         │                                  │
    ┌────▼──────────┐             ┌────────▼──────┐
    │ Celery Worker │             │ Redis Cache   │
    │ (Task Exec.)  │             │ (Caching)     │
    └───────────────┘             └───────────────┘
         │
    ┌────▼──────────────────────────────┐
    │  Database (PostgreSQL)            │
    │  - Activities, Weekly, Users      │
    │  - Permissions, Audit Logs        │
    └───────────────────────────────────┘
```

## Components

### 1. Event Bus System (`backend/app/events/`)

Pub/Sub pattern for domain events with automatic handler triggering.

**Files:**
- `events/__init__.py` - Module exports
- `events/types.py` - Event type definitions
- `events/bus.py` - EventBus class implementation
- `events/handlers.py` - Event handler functions

**Key Classes:**
- `Event` - Base event class
- `EventBus` - Publish/subscribe manager
- `EventHandlers` - Static handler functions
- Event Types: ActivityCreatedEvent, WeeklyGeneratedEvent, etc.

**Features:**
- Synchronous and asynchronous handler support
- Automatic audit logging to database
- Error handling and retry logic
- Event metadata preservation

### 2. Redis Cache (`backend/app/cache/`)

High-level caching interface with TTL and domain-specific methods.

**Files:**
- `cache/__init__.py` - Module exports
- `cache/redis_client.py` - RedisCache class

**Key Methods:**
- `get(key)` / `set(key, value, ttl)`
- `get_activity()` / `set_activity()`
- `get_weekly_report()` / `set_weekly_report()`
- `get_user_activities()` / `invalidate_user_activities_cache()`
- `set_session()` / `get_session()`

**Features:**
- JSON serialization for complex types
- Automatic TTL management
- Pattern-based cache invalidation
- Session storage support

### 3. Celery Task Queue (`backend/app/celery_app.py`)

Distributed task processing with multiple queues.

**Task Queues:**
- `default` - General tasks
- `ai_tasks` - AI processing (2 workers, CPU-intensive)
- `pptx_tasks` - Report generation (2 workers, memory-intensive)
- `notifications` - Notification delivery (4 workers, fast)
- `exports` - Data export (2 workers)

**Features:**
- Automatic retry with exponential backoff
- Task routing by type
- Result persistence
- Worker prefetching control

### 4. Task Implementations (`backend/app/tasks/`)

**AI Tasks** (`ai_tasks.py`):
- `process_activity_ai` - Enrich activity with AI insights
- `analyze_attachment` - Process uploaded files

**PPTX Tasks** (`pptx_tasks.py`):
- `generate_pptx_report` - Generate single report
- `generate_pptx_batch` - Batch generate reports

**Notification Tasks** (`notification_tasks.py`):
- `send_weekly_notification` - Weekly completion notification
- `send_share_notification` - File sharing notification
- `send_permission_notification` - Permission change notification

**Export Tasks** (`export_tasks.py`):
- `export_activities` - Export to CSV/Excel/JSON
- `export_weekly_report` - Export weekly report

## Event Flow Example: Activity Creation

```python
# 1. HTTP Request Handler (FastAPI)
@router.post("/activities")
def create_activity(data: ActivitySchema):
    activity = Activity(...)
    db.add(activity)
    db.commit()
    
    # 2. Publish Event
    event_bus = get_event_bus(db)
    event = ActivityCreatedEvent(
        aggregate_id=activity.id,
        title=activity.title,
        user_id=current_user.id,
    )
    event_bus.publish(event)  # Non-blocking
    
    # 3. Return immediately to client
    return {"status": "created", "id": activity.id}

# 4. Event Handler (triggered automatically)
def on_activity_created(event: ActivityCreatedEvent):
    # Queue AI processing task
    process_activity_ai.delay(
        activity_id=event.aggregate_id,
        user_id=event.user_id,
    )
    
    # Invalidate cache
    cache.invalidate_user_activities_cache(event.user_id)

# 5. Celery Worker processes task asynchronously
@celery_app.task
def process_activity_ai(activity_id, user_id):
    # AI processing
    insights = ai_service.analyze_activity(activity_id)
    
    # Update database
    activity.metadata_entry.insights = insights
    db.commit()
    
    # Cache result
    cache.set_activity(activity_id, {...})
    
    # Publish completion event
    event_bus.publish(ProcessingCompletedEvent(...))
```

## Integration with FastAPI

### Setup in main.py

```python
from fastapi import FastAPI
from app.events import get_event_bus, register_event_handlers
from app.cache import get_cache
from app.celery_app import celery_app

app = FastAPI()

@app.on_event("startup")
def startup_events():
    # Initialize event bus with database session
    db = SessionLocal()
    event_bus = get_event_bus(db)
    
    # Register all event handlers
    register_event_handlers(event_bus)
    
    # Initialize cache
    cache = get_cache(
        host="localhost",
        port=6379,
        db=0,
    )
    
    logger.info("Event bus and cache initialized")

@app.on_event("shutdown")
def shutdown_events():
    # Cleanup if needed
    pass
```

### Using Events in Endpoints

```python
from app.events import get_event_bus, ActivityCreatedEvent

@router.post("/activities")
async def create_activity(data: ActivitySchema, db: Session = Depends(get_db)):
    activity = Activity(**data.dict())
    db.add(activity)
    db.commit()
    
    # Publish event
    event_bus = get_event_bus(db)
    event = ActivityCreatedEvent(
        aggregate_id=activity.id,
        title=activity.title,
        user_id=data.user_id,
    )
    event_bus.publish(event)
    
    return activity
```

### Using Cache in Endpoints

```python
from app.cache import get_cache

@router.get("/activities/{activity_id}")
def get_activity(activity_id: str, db: Session = Depends(get_db)):
    cache = get_cache()
    
    # Try cache first
    cached = cache.get_activity(activity_id)
    if cached:
        return cached
    
    # Query database
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    
    # Cache result
    cache.set_activity(activity_id, activity.to_dict(), ttl=3600)
    
    return activity
```

## Configuration

### Environment Variables

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Worker Configuration
CELERY_CONCURRENCY=4
AI_WORKER_CONCURRENCY=2
PPTX_WORKER_CONCURRENCY=2
NOTIFICATION_WORKER_CONCURRENCY=4
EXPORT_WORKER_CONCURRENCY=2

# Logging
CELERY_LOG_LEVEL=info
```

### Requirements

Ensure `requirements.txt` contains:

```
redis==5.0.1
celery==5.3.4
flower==2.0.1  # Optional monitoring
```

## Running the System

### 1. Start Redis

```bash
# Docker
docker run -d -p 6379:6379 redis:7

# Or local installation
redis-server
```

### 2. Start FastAPI Application

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start Celery Workers

```bash
# Start all workers
celery -A app.celery_app worker -l info

# Or start specialized workers
celery -A app.celery_app worker -Q ai_tasks -l info
celery -A app.celery_app worker -Q pptx_tasks -l info
celery -A app.celery_app worker -Q notifications -l info
celery -A app.celery_app worker -Q exports -l info
```

### 4. Monitor with Flower (Optional)

```bash
celery -A app.celery_app flower --port=5555
# Visit http://localhost:5555
```

## Monitoring & Debugging

### Check Task Status

```python
from app.celery_app import celery_app

# Get task result
result = celery_app.AsyncResult(task_id)
print(result.status)  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
print(result.result)  # Task result or exception
```

### View Event Logs

```python
from app.models import AuditLog
from app.core.database import SessionLocal

db = SessionLocal()
logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()

for log in logs:
    print(f"{log.timestamp}: {log.event_type} - {log.aggregate_id}")
```

### Monitor Redis

```bash
redis-cli

# Check memory usage
info memory

# View keys
keys *

# Monitor operations
monitor
```

## Best Practices

### 1. Event Naming

Use domain-driven event names:
- `activity.created` (past tense, specific)
- Not `CreateActivity` (imperative)
- Not `ActivityCreate` (generic)

### 2. Task Idempotency

Tasks should be safe to retry:

```python
@celery_app.task
def process_activity(activity_id):
    # Check if already processed
    if is_already_processed(activity_id):
        return {"status": "already_processed"}
    
    # Do work
    # ...
    
    # Mark as processed
    mark_as_processed(activity_id)
```

### 3. Cache Keys

Use consistent, hierarchical keys:

```python
# Good
f"activity:{activity_id}"
f"user:{user_id}:activities"
f"weekly:{weekly_id}:metadata"

# Avoid
f"activity-{activity_id}"
f"activities_by_user_{user_id}"
```

### 4. Error Handling

Always catch and log errors:

```python
@celery_app.task
def my_task():
    try:
        # Do work
        pass
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        # Publish failure event
        raise
```

### 5. TTL Management

Set appropriate TTL for different cache types:

```python
# Short-lived: User-specific data
cache.set_user_activities(user_id, data, ttl=1800)  # 30 min

# Medium-lived: Resource data
cache.set_activity(activity_id, data, ttl=3600)  # 1 hour

# Long-lived: Metadata
cache.set_file(file_id, data, ttl=86400)  # 24 hours

# Session: User session
cache.set_session(session_id, data, ttl=86400)  # 24 hours
```

## Troubleshooting

### Tasks Not Processing

1. Check Redis connection:
   ```bash
   redis-cli ping  # Should return "PONG"
   ```

2. Check Celery worker running:
   ```bash
   celery -A app.celery_app inspect active
   ```

3. Check task queue:
   ```bash
   celery -A app.celery_app inspect active_queues
   ```

### Cache Not Working

1. Check Redis:
   ```bash
   redis-cli
   > ping
   > get activity:test_id
   ```

2. Check cache connection in logs

### Event Handlers Not Triggered

1. Verify event handlers registered:
   ```python
   event_bus.get_handlers_for_event(EventType.ACTIVITY_CREATED)
   ```

2. Check for exceptions in handler:
   ```python
   # Add try-catch and logging in handler
   ```

## Performance Tuning

### Redis Connection Pooling

```python
from redis import ConnectionPool

pool = ConnectionPool.from_url("redis://localhost:6379/0")
redis_client = redis.Redis(connection_pool=pool)
```

### Celery Worker Concurrency

Adjust based on task type:

```bash
# CPU-bound tasks (AI processing)
celery -A app.celery_app worker -Q ai_tasks -c 2

# I/O-bound tasks (notifications)
celery -A app.celery_app worker -Q notifications -c 8

# Mixed
celery -A app.celery_app worker -c 4
```

### Batch Operations

Use Celery chord for parallel execution:

```python
from celery import chord

# Process multiple items in parallel
callback = process_batch_result.s()
header = [process_item.s(item) for item in items]

result = chord(header)(callback)
```

## Testing

### Mock Event Bus

```python
from app.events import EventBus, reset_event_bus
from unittest.mock import Mock

def test_activity_created():
    reset_event_bus()
    event_bus = EventBus()
    
    # Mock handler
    handler = Mock()
    event_bus.subscribe(EventType.ACTIVITY_CREATED, handler)
    
    # Publish event
    event = ActivityCreatedEvent(
        aggregate_id="test",
        title="Test Activity",
    )
    event_bus.publish(event)
    
    # Verify
    handler.assert_called_once()
```

### Mock Celery Tasks

```python
@pytest.fixture
def celery_config():
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
        "task_always_eager": True,
    }
```

## Next Steps

1. Integrate event handlers into existing route handlers
2. Add cache warming on application startup
3. Implement monitoring dashboard with Flower
4. Set up log aggregation (ELK stack, CloudWatch)
5. Add performance monitoring (APM, New Relic)
6. Implement rate limiting for task queue
7. Add task retry strategies based on error type

## Support & Resources

- Celery Documentation: https://docs.celeryproject.io
- Redis Documentation: https://redis.io/docs
- FastAPI Documentation: https://fastapi.tiangolo.com
