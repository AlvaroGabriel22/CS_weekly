"""
Event System Integration - Setup helpers for FastAPI application.

This module provides helper functions to initialize the event system,
cache, and register handlers when the FastAPI application starts.

Usage in main.py:

    from app.events.integration import initialize_async_system, cleanup_async_system

    app = FastAPI()

    @app.on_event("startup")
    def startup():
        initialize_async_system()

    @app.on_event("shutdown")
    def shutdown():
        cleanup_async_system()
"""

import logging
from typing import Optional

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def initialize_async_system(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
) -> None:
    """
    Initialize the async processing system.

    Sets up:
    1. Redis cache connection
    2. Event bus with database session
    3. Event handler registration
    4. Celery app verification

    Args:
        redis_host: Redis host address
        redis_port: Redis port
        redis_db: Redis database number
        redis_password: Redis password (optional)
    """
    logger.info("Initializing async processing system...")

    try:
        # 1. Initialize Redis cache
        from app.cache import get_cache

        cache = get_cache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            default_ttl=3600,
        )
        logger.info("✓ Redis cache initialized")

        # 2. Initialize event bus
        from app.events import get_event_bus
        from app.events.handlers import register_event_handlers

        db = SessionLocal()
        event_bus = get_event_bus(db)
        logger.info("✓ Event bus initialized")

        # 3. Register event handlers
        register_event_handlers(event_bus)
        logger.info("✓ Event handlers registered")

        # 4. Verify Celery connection
        from app.celery_app import celery_app

        celery_app.connection()
        logger.info("✓ Celery app verified")

        logger.info("Async processing system initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize async system: {str(e)}", exc_info=True)
        raise


def cleanup_async_system() -> None:
    """
    Cleanup async system resources.

    Closes connections and clears handlers.
    """
    logger.info("Cleaning up async processing system...")

    try:
        # Clear event handlers
        from app.events import reset_event_bus

        reset_event_bus()
        logger.info("✓ Event handlers cleared")

        # Note: Cache and Celery clients stay open for graceful shutdown
        logger.info("Async processing system cleaned up")

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}", exc_info=True)


# Middleware for adding event bus to request state
class EventBusMiddleware:
    """
    Middleware to make event bus available in request context.

    Usage in main.py:

        app.add_middleware(EventBusMiddleware)

    Then in route handlers:

        @router.post("/activities")
        def create_activity(request: Request):
            event_bus = request.state.event_bus
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from app.events import get_event_bus
            from app.core.database import SessionLocal

            db = SessionLocal()
            scope["state"]["event_bus"] = get_event_bus(db)
            scope["state"]["db"] = db

            async def send_wrapper(message):
                if message["type"] == "http.disconnect":
                    db.close()
                await send(message)

            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


# Dependency for getting event bus in route handlers
def get_event_bus_from_db():
    """
    FastAPI dependency for getting event bus.

    Usage:

        @router.post("/activities")
        def create_activity(
            data: ActivitySchema,
            event_bus: EventBus = Depends(get_event_bus_from_db)
        ):
            # Use event_bus
    """
    from app.events import get_event_bus
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        return get_event_bus(db)
    finally:
        # Note: Don't close db here as it might be needed for other operations
        # Close in finally of the request handler or use the middleware
        pass


def publish_event(event) -> None:
    """
    Publish an event to the event bus.

    Convenience function for use in sync contexts.

    Args:
        event: The event to publish
    """
    from app.events import get_event_bus
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        event_bus = get_event_bus(db)
        event_bus.publish(event)
    finally:
        db.close()


async def publish_event_async(event) -> None:
    """
    Publish an event to the event bus asynchronously.

    Args:
        event: The event to publish
    """
    from app.events import get_event_bus
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        event_bus = get_event_bus(db)
        await event_bus.publish_async(event)
    finally:
        db.close()


# Example configuration update for main.py
EXAMPLE_MAIN_PY_UPDATE = """
# Add to main.py imports:
from app.events.integration import (
    initialize_async_system,
    cleanup_async_system,
    get_event_bus_from_db,
)

# Add to create_app() function:

def create_app() -> FastAPI:
    app = FastAPI(...)

    # ... existing middleware and routes ...

    @app.on_event("startup")
    def startup():
        # ... existing startup code ...

        # Initialize async processing system
        initialize_async_system(
            redis_host=settings.REDIS_HOST,
            redis_port=settings.REDIS_PORT,
            redis_db=0,
        )

    @app.on_event("shutdown")
    def shutdown():
        # Cleanup async system
        cleanup_async_system()

    return app

# Example usage in route handler:

@router.post("/activities")
async def create_activity(
    data: ActivitySchema,
    db: Session = Depends(get_db),
    event_bus: EventBus = Depends(get_event_bus_from_db),
):
    activity = Activity(**data.dict())
    db.add(activity)
    db.commit()

    # Publish event (non-blocking)
    event = ActivityCreatedEvent(
        aggregate_id=activity.id,
        title=activity.title,
        user_id=data.user_id,
    )
    event_bus.publish(event)

    return activity
"""
