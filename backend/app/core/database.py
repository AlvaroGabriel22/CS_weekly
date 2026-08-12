"""PostgreSQL database connection configuration"""
from collections.abc import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings

settings = get_settings()


def create_db_engine():
    """Create database engine with PostgreSQL optimizations"""
    if settings.DATABASE_URL.startswith("postgresql://") or settings.DATABASE_URL.startswith("postgresql+psycopg2://"):
        # PostgreSQL configuration with connection pooling
        engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={
                "application_name": "qwi_backend",
                "connect_timeout": 10,
            },
        )

        @event.listens_for(engine, "connect")
        def set_postgres_config(dbapi_conn, connection_record):
            """Configure PostgreSQL connection settings"""
            cursor = dbapi_conn.cursor()
            # Set timezone to UTC for all connections
            cursor.execute("SET timezone TO 'UTC'")
            # Enable check constraints
            cursor.execute("SET check_function_bodies = off")
            cursor.close()

    else:
        # Fallback for SQLite (for testing/development)
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """Configure SQLite for development"""
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy base class for models"""
    pass


def get_db() -> Generator[Session, None, None]:
    """Database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create all tables)"""
    Base.metadata.create_all(bind=engine)


async def close_db():
    """Close database connection pool"""
    await engine.dispose()
