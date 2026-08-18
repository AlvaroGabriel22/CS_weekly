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
        # SQLite (deploy padrão do QWI, ver DEPLOY_WINDOWS.md).
        is_memory = ":memory:" in settings.DATABASE_URL or settings.DATABASE_URL.endswith("sqlite://")
        engine_kwargs = {
            "connect_args": {"check_same_thread": False, "timeout": 30},
            "echo": settings.DEBUG,
        }
        if not is_memory:
            # Só SQLite em arquivo usa QueuePool. Pool maior + timeout para
            # suportar as tarefas de IA em background sem esgotar conexões
            # (QA-046). SQLite :memory: (testes) usa SingletonThreadPool e não
            # aceita esses parâmetros.
            engine_kwargs.update(
                pool_size=20, max_overflow=40, pool_timeout=30, pool_pre_ping=True
            )
        engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """PRAGMAs de concorrência do SQLite.

            WAL deixa leituras e escritas coexistirem (leitor não bloqueia
            escritor e vice-versa); busy_timeout faz uma escrita esperar em vez
            de falhar na hora sob contenção. Juntos, sustentam a IA em
            background + o tráfego web sem os 500 de 'database is locked'.
            """
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA synchronous=NORMAL")
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
