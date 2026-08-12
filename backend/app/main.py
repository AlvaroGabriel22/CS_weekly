from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import activities, auth, users, weekly, pptx
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

    # Arquivos enviados (fotos de perfil etc.) servidos estaticamente
    uploads_dir = Path("uploads")
    (uploads_dir / "photos").mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)
        run_migrations()
        seed_default_template()

    @app.get("/api/health")
    def health():
        return {"status": "healthy", "version": settings.APP_VERSION}

    return app


app = create_app()
