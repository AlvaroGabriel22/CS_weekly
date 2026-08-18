"""FAQ / report de bugs interno.

- Qualquer usuário abre uma solicitação (título + descrição curta) e ela fica
  visível para todos (para não abrirem a mesma).
- Ao abrir, um e-mail é enviado (best-effort) aos usuários que o admin definiu.
- Só o usuário root/admin (is_admin) fecha e responde.
"""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_root
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError, QWIException
from app.models import BugReport, BugStatus, FaqNotifyUser, User

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/faq", tags=["FAQ"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class BugCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=3, max_length=4000)


class BugResolve(BaseModel):
    response: str | None = Field(default=None, max_length=4000)
    close: bool = True


class BugResponse(BaseModel):
    id: str
    title: str
    description: str
    author_name: str
    status: str
    admin_response: str | None
    is_mine: bool
    created_at: datetime
    closed_at: datetime | None


class NotifyUserRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=50)


class NotifyUserResponse(BaseModel):
    id: str          # id da linha faq_notify_users
    user_id: str
    name: str
    employee_id: str
    email: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _serialize(report: BugReport, current_user: User) -> BugResponse:
    return BugResponse(
        id=report.id,
        title=report.title,
        description=report.description,
        author_name=report.author_name,
        status=report.status.value if hasattr(report.status, "value") else str(report.status),
        admin_response=report.admin_response,
        is_mine=report.user_id == current_user.id,
        created_at=report.created_at,
        closed_at=report.closed_at,
    )


def _notify_recipients(db: Session) -> list[str]:
    """E-mails dos usuários marcados pelo admin para receber o FAQ; se a lista
    estiver vazia, cai para todos os admins."""
    rows = (
        db.query(User.email)
        .join(FaqNotifyUser, FaqNotifyUser.user_id == User.id)
        .filter(User.is_active == True)  # noqa: E712
        .all()
    )
    emails = [r[0] for r in rows]
    if not emails:
        emails = [
            r[0] for r in db.query(User.email).filter(
                User.is_admin == True, User.is_active == True  # noqa: E712
            ).all()
        ]
    return emails


def _send_faq_email(db: Session, report: BugReport, author: User) -> None:
    """Envia (best-effort) o aviso de nova solicitação. Nunca derruba o POST."""
    from app.services.email_service import EmailService

    service = EmailService()
    if not service.is_configured():
        return
    recipients = _notify_recipients(db)
    if not recipients:
        return
    try:
        service.send(
            to=recipients,
            subject=f"[QWI FAQ] Nova solicitação: {report.title}",
            body=(
                f"Uma nova solicitação foi aberta no FAQ do QWI.\n\n"
                f"Autor: {author.name} ({author.sector.value})\n"
                f"Título: {report.title}\n\n"
                f"Descrição:\n{report.description}\n\n"
                f"Acesse o sistema para responder e fechar a solicitação."
            ),
            reply_to=author.email,
        )
    except Exception as error:
        logger.warning("Falha ao enviar e-mail do FAQ: %s", error)


# ── Endpoints (usuário comum) ────────────────────────────────────────────────

@router.get("", response_model=list[BugResponse])
def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Todas as solicitações (abertas e fechadas), visíveis a todos os usuários."""
    reports = db.query(BugReport).order_by(BugReport.created_at.desc()).all()
    return [_serialize(r, current_user) for r in reports]


@router.post("", response_model=BugResponse, status_code=201)
def create_report(
    data: BugCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Abre uma solicitação e avisa os administradores por e-mail (best-effort)."""
    report = BugReport(
        user_id=current_user.id,
        author_name=current_user.name,
        title=data.title.strip(),
        description=data.description.strip(),
        status=BugStatus.OPEN,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    _send_faq_email(db, report, current_user)
    return _serialize(report, current_user)


# ── Endpoints (somente root/admin) ───────────────────────────────────────────

@router.put("/{report_id}", response_model=BugResponse)
def resolve_report(
    report_id: str,
    data: BugResolve,
    current_user: User = Depends(require_root),
    db: Session = Depends(get_db),
):
    """Fecha e/ou responde uma solicitação (exclusivo do admin/root)."""
    report = db.query(BugReport).filter(BugReport.id == report_id).first()
    if not report:
        raise NotFoundError("Solicitação")
    if data.response is not None:
        report.admin_response = data.response.strip() or None
    if data.close:
        report.status = BugStatus.CLOSED
        report.closed_by = current_user.id
        report.closed_at = datetime.now(UTC)
    db.commit()
    db.refresh(report)
    return _serialize(report, current_user)


@router.get("/notify-users", response_model=list[NotifyUserResponse])
def list_notify_users(
    current_user: User = Depends(require_root),
    db: Session = Depends(get_db),
):
    """Usuários que recebem por e-mail as novas solicitações do FAQ."""
    rows = (
        db.query(FaqNotifyUser, User)
        .join(User, User.id == FaqNotifyUser.user_id)
        .order_by(User.name)
        .all()
    )
    return [
        NotifyUserResponse(
            id=row.FaqNotifyUser.id, user_id=u.id, name=u.name,
            employee_id=u.employee_id, email=u.email,
        )
        for row in rows for u in [row.User]
    ]


@router.post("/notify-users", response_model=list[NotifyUserResponse])
def add_notify_user(
    data: NotifyUserRequest,
    current_user: User = Depends(require_root),
    db: Session = Depends(get_db),
):
    """Adiciona um usuário (pela matrícula) à lista de avisos do FAQ."""
    from fastapi import HTTPException
    target = db.query(User).filter(User.employee_id == data.employee_id.strip()).first()
    if not target:
        raise HTTPException(400, detail={
            "field": "employee_id", "message": "Matrícula não encontrada.",
            "hint": "Confira o número com o colega.",
        })
    exists = db.query(FaqNotifyUser).filter(FaqNotifyUser.user_id == target.id).first()
    if not exists:
        db.add(FaqNotifyUser(user_id=target.id))
        db.commit()
    return list_notify_users(current_user, db)


@router.delete("/notify-users/{user_id}", response_model=list[NotifyUserResponse])
def remove_notify_user(
    user_id: str,
    current_user: User = Depends(require_root),
    db: Session = Depends(get_db),
):
    """Remove um usuário da lista de avisos do FAQ."""
    row = db.query(FaqNotifyUser).filter(FaqNotifyUser.user_id == user_id).first()
    if row:
        db.delete(row)
        db.commit()
    return list_notify_users(current_user, db)
