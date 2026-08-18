from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import activities, ai_features, auth, faq, translate, users, weekly
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.exceptions import QWIException
from app.core.logging import setup_logging
from app.core.migrations import run_migrations
from app.models import Template
from app.core.database import SessionLocal
from app.models import Language

settings = get_settings()
setup_logging()


def seed_default_template():
    db = SessionLocal()
    try:
        if db.query(Template).count() == 0:
            template = Template(
                name="Quality Weekly - Standard",
                department="Quality",
                language=Language.PT,
                description="Default corporate weekly report template",
                slides_config={
                    "slides": [
                        {"number": 1, "title": "Cover", "fields": ["title", "week", "department", "author"]},
                        {"number": 2, "title": "Executive Summary", "fields": ["summary", "highlights"]},
                        {"number": 3, "title": "Activities", "fields": ["activities_list", "achievements"]},
                        {"number": 4, "title": "KPIs & Metrics", "fields": ["kpis", "trends", "charts"]},
                        {"number": 5, "title": "Issues & Actions", "fields": ["issues", "actions", "next_steps"]},
                        {"number": 6, "title": "Conclusions", "fields": ["conclusions", "impact"]},
                    ]
                },
            )
            db.add(template)
            db.commit()
    finally:
        db.close()


def seed_root_user():
    """Cria o usuário root/admin no 1º startup, se ainda não existir.

    É usuário de testes + administração: is_admin=True, NÃO aparece no
    organograma, gerencia o FAQ. Credenciais vêm do .env (ROOT_*).
    """
    from app.models import User, UserRole, QualitySector
    from app.core.security import get_password_hash

    db = SessionLocal()
    try:
        email = settings.ROOT_EMAIL.lower().strip()
        exists = db.query(User).filter(
            (User.is_admin == True) | (User.email == email)  # noqa: E712
        ).first()
        if exists:
            return
        root = User(
            email=email,
            employee_id=settings.ROOT_EMPLOYEE_ID,
            hashed_password=get_password_hash(settings.ROOT_PASSWORD),
            name=settings.ROOT_NAME,
            role=UserRole.GERENTE_SR,
            sector=QualitySector.CSI,
            is_admin=True,
            is_active=True,
        )
        db.add(root)
        db.commit()
        import logging
        logging.getLogger(__name__).info("Usuário root/admin criado: %s", email)
    finally:
        db.close()


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
    app.include_router(translate.router, prefix="/api")
    app.include_router(ai_features.router, prefix="/api")
    app.include_router(faq.router, prefix="/api")

    # Arquivos enviados (fotos de perfil etc.) servidos estaticamente
    uploads_dir = Path("uploads")
    (uploads_dir / "photos").mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)
        run_migrations()
        seed_default_template()
        seed_root_user()
        # Limpeza de PPTX antigos por (usuário, semana) — evita crescimento
        # indefinido de uploads/reports (QA-010).
        from app.services.retention import cleanup_old_reports
        cleanup_old_reports()

    @app.on_event("shutdown")
    def on_shutdown():
        from app.core.background import shutdown_background
        shutdown_background()

    @app.get("/api/health")
    def health(deep: bool = False):
        """Liveness simples; `?deep=1` também testa uma conexão do banco, para
        refletir a saúde real do pool (QA-047)."""
        if deep:
            from sqlalchemy import text
            from app.core.database import SessionLocal
            db = SessionLocal()
            try:
                db.execute(text("SELECT 1"))
            except Exception:
                return JSONResponse(
                    status_code=503,
                    content={"status": "degraded", "db": "unavailable",
                             "version": settings.APP_VERSION},
                )
            finally:
                db.close()
        return {"status": "healthy", "version": settings.APP_VERSION}

    return app


app = create_app()
