import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.api.routes.users import can_view_user_weeklys
from app.core.database import get_db
from app.core.exceptions import NotFoundError, QWIException
from app.models import Template, User, WeeklyReport
from app.schemas.weekly import (
    DashboardStats,
    TemplateCreate,
    TemplateResponse,
    WeeklyGenerateRequest,
    WeeklyReportResponse,
)
from app.services.business import WeeklyService
from app.services.pptx_service import PptxService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Weekly Reports"])


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WeeklyService(db)
    return service.get_dashboard_stats(current_user)


@router.post("/weekly/generate", response_model=WeeklyReportResponse)
async def generate_weekly(
    data: WeeklyGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WeeklyService(db)
    report = await service.generate_weekly(
        current_user,
        activity_ids=data.activity_ids,
        start_date=data.start_date,
        end_date=data.end_date,
        week_number=data.week_number,
        year=data.year,
        template_id=data.template_id,
        language=data.language,
        timezone=data.timezone,
        layout=data.layout,
        layout_source=data.layout_source,
        pptx_template_id=data.pptx_template_id,
    )
    return _serialize_report(report, db)


@router.get("/weekly", response_model=list[WeeklyReportResponse])
def list_weekly_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WeeklyService(db)
    reports, _ = service.list_reports(current_user.id, page=page, page_size=page_size)
    return [_serialize_report(r, db) for r in reports]


class WeeklySummaryResponse(BaseModel):
    """Resumo de um weekly para listagens (área de colegas/departamentos)."""
    id: str
    week_number: int
    year: int
    status: str
    title: str | None
    version: int
    generated_at: str | None
    has_pptx: bool


def _get_report_for_viewer(report_id: str, current_user: User, db: Session) -> WeeklyReport:
    """Busca um weekly aplicando a regra de acesso (dono, gestão, mesmo depto)."""
    report = db.query(WeeklyReport).filter(WeeklyReport.id == report_id).first()
    if not report:
        raise NotFoundError("Weekly não encontrado")

    owner = db.query(User).filter(User.id == report.user_id).first()
    if owner is None or not can_view_user_weeklys(current_user, owner, db):
        raise QWIException("Você não tem acesso a este weekly.", 403)
    return report


@router.get("/weekly/user/{user_id}", response_model=list[WeeklySummaryResponse])
def list_user_weeklys(
    user_id: str,
    year: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Weeklys publicados por um usuário, respeitando a regra de acesso."""
    owner = db.query(User).filter(User.id == user_id).first()
    if not owner:
        raise NotFoundError("Usuário não encontrado")
    if not can_view_user_weeklys(current_user, owner, db):
        raise QWIException(
            "Você não tem acesso aos weeklys deste usuário. "
            "Apenas colegas do mesmo departamento ou cargos de gestão podem visualizar.",
            403,
        )

    query = db.query(WeeklyReport).filter(WeeklyReport.user_id == user_id)
    if year:
        query = query.filter(WeeklyReport.year == year)
    reports = query.order_by(
        WeeklyReport.year.desc(), WeeklyReport.week_number.desc(), WeeklyReport.version.desc()
    ).all()

    return [
        WeeklySummaryResponse(
            id=r.id,
            week_number=r.week_number,
            year=r.year,
            status=r.status.value,
            title=r.title,
            version=r.version,
            generated_at=r.generated_at.isoformat() if r.generated_at else None,
            has_pptx=bool(r.pptx_path),
        )
        for r in reports
    ]


@router.get("/weekly/{report_id}", response_model=WeeklyReportResponse)
def get_weekly_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = _get_report_for_viewer(report_id, current_user, db)
    return _serialize_report(report, db)


@router.get("/weekly/{report_id}/download")
def download_weekly_pptx(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = _get_report_for_viewer(report_id, current_user, db)

    if not report.pptx_path or not Path(report.pptx_path).exists():
        raise QWIException("Arquivo PowerPoint não encontrado. Gere o relatório novamente.", 404)

    filename = f"Weekly_S{report.week_number}_{report.year}_v{report.version}.pptx"
    return FileResponse(
        path=report.pptx_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.get("/templates", response_model=list[TemplateResponse])
def list_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    templates = db.query(Template).filter(Template.is_active == True).all()  # noqa: E712
    return templates


@router.post("/templates", response_model=TemplateResponse, status_code=201)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = Template(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.post("/templates/{template_id}/upload", response_model=TemplateResponse)
async def upload_template_pptx(
    template_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise NotFoundError("Template")

    if not file.filename or not file.filename.lower().endswith((".pptx", ".ppt")):
        raise QWIException("Apenas arquivos PowerPoint (.pptx) são aceitos", 422)

    content = await file.read()
    pptx_service = PptxService()
    file_path = pptx_service.save_template_file(template_id, content, file.filename)

    try:
        slides_config = pptx_service.analyze_template(file_path)
    except Exception as e:
        raise QWIException(f"Erro ao analisar template PPT: {e}", 422)

    template.file_path = file_path
    template.slides_config = slides_config
    db.commit()
    db.refresh(template)
    return template


def _serialize_report(report, db: Session) -> WeeklyReportResponse:
    from app.schemas.weekly import CoverageMetrics, ConfidenceSlide, TemplateResponse

    data = WeeklyReportResponse.model_validate(report)
    if isinstance(report.content, dict):
        data.ai_degraded = bool(report.content.get("ai_degraded"))
    if report.coverage:
        data.coverage = CoverageMetrics(**report.coverage)
    if report.confidence_index:
        data.confidence_index = [ConfidenceSlide(**c) for c in report.confidence_index]
    if report.template_id:
        template = db.query(Template).filter(Template.id == report.template_id).first()
        if template:
            data.template = TemplateResponse.model_validate(template)
    return data


# ── Envio do weekly por e-mail ─────────────────────────────────────────────

class SendEmailRequest(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=50)
    subject: str = Field(min_length=1, max_length=300)
    # Corpo opcional: sem texto, o e-mail vai só com o anexo e uma linha padrão.
    body: str = Field(default="", max_length=10000)


@router.post("/weekly/{report_id}/send-email")
def send_weekly_email(
    report_id: str,
    data: SendEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envia o PPTX do weekly por e-mail (somente o DONO do relatório)."""
    from app.services.email_service import EmailService

    report = (
        db.query(WeeklyReport)
        .filter(WeeklyReport.id == report_id, WeeklyReport.user_id == current_user.id)
        .first()
    )
    if not report:
        raise NotFoundError("Weekly Report")
    if not report.pptx_path or not Path(report.pptx_path).exists():
        raise QWIException("Este weekly não possui arquivo PPTX para enviar.", 400)

    service = EmailService()
    if not service.is_configured():
        raise QWIException(
            "Envio de e-mail ainda não configurado (SMTP). Avise o administrador.",
            503,
        )
    try:
        service.send(
            to=[r.strip() for r in data.recipients if r.strip()],
            subject=data.subject.strip(),
            body=data.body.strip()
            or f"Weekly W{report.week_number}/{report.year} em anexo.",
            attachment_path=report.pptx_path,
            attachment_name=f"Weekly_W{report.week_number}_{report.year}_v{report.version}.pptx",
            reply_to=current_user.email,
        )
    except Exception as error:
        # Loga o detalhe técnico, mas devolve mensagem PT genérica (não expõe
        # o erro interno ao usuário — QA-045).
        import logging
        logging.getLogger(__name__).warning("Falha SMTP no envio: %s", error)
        raise QWIException(
            "Não foi possível enviar o e-mail. Verifique a configuração do "
            "servidor de e-mail (SMTP) com o administrador.",
            502,
        )
    return {"sent": True, "recipients": len(data.recipients)}


@router.delete("/weekly/{report_id}", status_code=204)
def delete_weekly(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exclui permanentemente um weekly do histórico (dono ou admin).

    Remove a linha e o arquivo .pptx do disco. Sem senha — a confirmação é
    feita no frontend.
    """
    report = db.query(WeeklyReport).filter(WeeklyReport.id == report_id).first()
    if not report:
        raise NotFoundError("Weekly")
    if report.user_id != current_user.id and not current_user.is_admin:
        raise QWIException("Você só pode excluir os seus próprios weeklys.", 403)

    pptx_path = report.pptx_path
    db.delete(report)
    db.commit()
    if pptx_path:
        try:
            p = Path(pptx_path)
            if p.exists():
                p.unlink()
        except Exception:
            logger.warning("Falha ao remover PPTX do weekly %s", report_id)
