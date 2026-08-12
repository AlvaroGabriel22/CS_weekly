# Quick Start - Async Processing System

Get up and running with the event system, Redis cache, and Celery in 5 minutes.

## 1. Prerequisites

- Python 3.9+
- Docker (recommended) or Redis installed locally
- PostgreSQL running

## 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## 3. Start Redis

### Option A: Using Docker (Recommended)

```bash
# Start Redis container
docker run -d -p 6379:6379 --name redis-qwi redis:7 redis-server --appendonly yes

# Verify connection
redis-cli ping  # Should return "PONG"
```

### Option B: Local Installation

```bash
# macOS
brew install redis
redis-server

# Linux
sudo apt-get install redis-server
redis-server

# Windows
# Download from: https://github.com/microsoftarchive/redis/releases
```

## 4. Update Environment

Create or update `.env`:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Enable async processing
ENABLE_ASYNC_PROCESSING=true
```

## 5. Update main.py

Add async system initialization to `app/main.py`:

```python
from app.events.integration import initialize_async_system, cleanup_async_system

def create_app() -> FastAPI:
    app = FastAPI(...)
    
    @app.on_event("startup")
    def startup():
        # ... existing startup code ...
        initialize_async_system()
    
    @app.on_event("shutdown")
    def shutdown():
        cleanup_async_system()
    
    return app
```

## 6. Start Services

### Terminal 1: FastAPI Application

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Celery Worker

```bash
cd backend
celery -A app.celery_app worker -l info
```

### Terminal 3 (Optional): Flower Monitoring

```bash
cd backend
celery -A app.celery_app flower --port=5555
# Visit http://localhost:5555
```

## 7. Test It Out

### Create an Activity

```bash
curl -X POST http://localhost:8000/api/activities \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Activity",
    "department": "Quality",
    "user_id": "user-123"
  }'
```

Watch the Celery worker terminal - you should see a task processing!

### Check Cache

```bash
redis-cli

> GET activity:activity-id
> KEYS *
```

### View Event Logs

```python
# In Python shell or script
from app.core.database import SessionLocal
from app.models import AuditLog

db = SessionLocal()
events = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(5).all()

for event in events:
    print(f"{event.event_type}: {event.aggregate_id}")
```

## Using Docker Compose (All-in-One)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: qwi
      POSTGRES_PASSWORD: qwi_secret
      POSTGRES_DB: qwi_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # FastAPI application
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://qwi:qwi_secret@postgres:5432/qwi_db
      REDIS_HOST: redis
      REDIS_PORT: 6379
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  # Celery worker
  celery:
    build: .
    environment:
      DATABASE_URL: postgresql://qwi:qwi_secret@postgres:5432/qwi_db
      REDIS_HOST: redis
      REDIS_PORT: 6379
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      - postgres
      - redis
    command: celery -A app.celery_app worker -l info

  # Flower monitoring
  flower:
    build: .
    ports:
      - "5555:5555"
    environment:
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      - redis
    command: celery -A app.celery_app flower --port 5555

volumes:
  redis_data:
  postgres_data:
```

Start all services:

```bash
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
docker-compose logs -f celery

# Stop all
docker-compose down
```

## Common Tasks

### Trigger AI Processing Task

```python
from app.tasks import process_activity_ai

# Queue task
task = process_activity_ai.delay(
    activity_id="activity-123",
    user_id="user-1",
)

print(f"Task ID: {task.id}")

# Check status
import time
time.sleep(2)
print(f"Status: {task.status}")
print(f"Result: {task.result}")
```

### Generate Weekly Report with PPTX

```python
from app.tasks import generate_pptx_report

# Queue task
task = generate_pptx_report.delay(
    weekly_id="weekly-123",
    user_id="user-1",
    week_number=42,
    year=2024,
)

# Monitor
print(f"Task: {task.id}")
print(f"Status: {task.status}")
```

### Export Activities

```python
from app.tasks import export_activities

# Queue export
task = export_activities.delay(
    user_id="user-1",
    format="csv",
    date_from="2024-01-01",
    date_to="2024-12-31",
)

print(f"Export Task ID: {task.id}")
```

### Clear Cache

```python
from app.cache import get_cache

cache = get_cache()

# Clear specific cache
cache.invalidate_activity_cache("activity-123")
cache.invalidate_user_activities_cache("user-1")

# Clear all caches
cache.flush_all()
```

### Inspect Tasks

```bash
# List active tasks
celery -A app.celery_app inspect active

# List registered tasks
celery -A app.celery_app inspect registered

# Show worker stats
celery -A app.celery_app inspect stats

# Check queue configuration
celery -A app.celery_app inspect active_queues
```

### Shutdown Gracefully

```bash
# Stop Celery gracefully
celery -A app.celery_app control shutdown

# Or in Python
from app.celery_app import celery_app
celery_app.control.shutdown()
```

## Troubleshooting

### Redis Connection Refused

```bash
# Check if Redis is running
redis-cli ping

# If not, start Redis
redis-server

# Or with Docker
docker run -d -p 6379:6379 redis:7
```

### Celery Workers Not Starting

```bash
# Check Python path
python -c "from app.celery_app import celery_app; print(celery_app)"

# Check broker URL
CELERY_BROKER_URL=redis://localhost:6379/1 celery -A app.celery_app worker -l info

# Check logs
celery -A app.celery_app worker -l debug
```

### Tasks Not Processing

```bash
# Verify broker has tasks
redis-cli

> KEYS celery*

# Check for errors in worker logs
# Look for task import errors or exceptions
```

### Cache Not Working

```bash
# Test Redis connection
redis-cli
> PING
> GET test_key

# Check cache initialization
from app.cache import get_cache
cache = get_cache()
print(cache._is_connected())
```

## Next Steps

1. **Review ASYNC_PROCESSING_GUIDE.md** - Full architecture documentation
2. **Review INTEGRATION_STEPS.md** - Detailed integration instructions
3. **Update route handlers** - Add event publishing to your endpoints
4. **Set up monitoring** - Use Flower dashboard to monitor tasks
5. **Configure workers** - Optimize concurrency for your hardware
6. **Add custom tasks** - Create domain-specific task handlers

## Performance Tips

1. **Adjust worker concurrency** based on task type:
   ```bash
   # CPU-bound (AI processing)
   celery -A app.celery_app worker -c 2
   
   # I/O-bound (notifications)
   celery -A app.celery_app worker -c 8
   ```

2. **Set appropriate cache TTL**:
   - User-specific: 30 minutes
   - Resource data: 1 hour
   - Metadata: 24 hours

3. **Monitor with Flower**:
   - http://localhost:5555
   - Watch task execution and performance

4. **Use dedicated queues** for different task types
5. **Implement retry logic** for failed tasks

## Security Considerations

1. **Update Redis password** in production:
   ```bash
   REDIS_PASSWORD=your_secure_password
   ```

2. **Use SSL for Redis** over network:
   ```python
   RedisCache(..., ssl=True)
   ```

3. **Secure Celery broker** with authentication
4. **Audit event logs** for compliance
5. **Set task TTL** to prevent memory leaks

## Resources

- Event Bus & Cache Implementation: `backend/app/events/`, `backend/app/cache/`
- Celery Tasks: `backend/app/tasks/`
- Full Documentation: `ASYNC_PROCESSING_GUIDE.md`
- Integration Guide: `INTEGRATION_STEPS.md`
- Tests: `backend/tests/test_async_system.py`

## Support

For questions or issues:
1. Check the troubleshooting section
2. Review full documentation
3. Check Celery and Redis documentation
4. Review test cases for examples
