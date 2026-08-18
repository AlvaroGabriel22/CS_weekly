import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import NotFoundError, QWIException
from app.core.config import get_settings
from app.core.activity_directives import activity_requests_image_analysis
from app.models import Attachment, ImageUsage, User
from app.schemas.activity import (
    ActivityCreate,
    ActivityListResponse,
    ActivityResponse,
    ActivityUpdate,
    AttachmentUpdate,
)
from app.services.business import ActivityService, FileService
from app.core.background import submit_background
from app.services.ai_processor import (
    process_activity_in_background,
    process_attachment_in_background,
)

# Extensões aceitas em anexos de atividade. Planilhas e imagens têm extração
# dedicada; documentos (pdf/doc/docx/txt) viram texto; apresentações são
# armazenadas. Espelha FileService.ALLOWED_EXTENSIONS (QA-021).
ALLOWED_ATTACHMENT_EXTS = {
    ".xlsx", ".xls", ".csv", ".jpg", ".jpeg", ".png",
    ".pdf", ".doc", ".docx", ".txt", ".pptx", ".ppt",
}
# Assinaturas (magic bytes) para validar imagens declaradas (QA-043).
_IMAGE_MAGIC = {
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
}

router = APIRouter(prefix="/activities", tags=["Activities"])
settings = get_settings()


@router.post("", response_model=ActivityResponse, status_code=201)
def create_activity(
    data: ActivityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ActivityService(db)
    activity = service.create(current_user, data.model_dump())
    # Enriquecimento de IA fora do request path, com concorrência limitada,
    # para não esgotar o pool de conexões (QA-046).
    submit_background(process_activity_in_background, activity.id)
    return _load_activity(db, activity.id)


@router.get("", response_model=ActivityListResponse)
def list_activities(
    week_number: int | None = Query(None),
    year: int | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    timezone: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ActivityService(db)
    activities, total = service.list_activities(
        current_user.id,
        week_number=week_number,
        year=year,
        start_date=start_date,
        end_date=end_date,
        timezone=timezone,
        page=page,
        page_size=page_size,
    )
    return ActivityListResponse(
        items=[_serialize_activity(a) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _load_activity(db, activity_id, current_user.id)


@router.patch("/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: str,
    data: ActivityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ActivityService(db)
    activity = service.get_by_id(activity_id, current_user.id)
    service.update(activity, data.model_dump(exclude_unset=True))
    return _load_activity(db, activity.id)


@router.delete("/{activity_id}", status_code=204)
def delete_activity(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ActivityService(db)
    activity = service.get_by_id(activity_id, current_user.id)
    service.delete(activity)


@router.post("/{activity_id}/attachments", response_model=ActivityResponse)
async def upload_attachment(
    activity_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ActivityService(db)
    activity = service.get_by_id(activity_id, current_user.id)

    content = await file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise QWIException(
            f"Arquivo excede o limite de {settings.MAX_UPLOAD_SIZE_MB} MB",
            413,
        )
    if len(content) == 0:
        raise QWIException("Arquivo vazio. Selecione um arquivo válido.", 422)
    original = file.filename or "file"
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else "bin"
    dot_ext = f".{ext}"
    if dot_ext not in ALLOWED_ATTACHMENT_EXTS:
        raise QWIException(
            "Tipo de arquivo não suportado. Use xlsx, xls, csv, jpg, jpeg, png, "
            "pdf, doc, docx, txt, ppt ou pptx.",
            422,
        )
    # Imagem declarada precisa ter os bytes de imagem (evita png de texto — QA-043).
    if dot_ext in _IMAGE_MAGIC and not any(
        content.startswith(sig) for sig in _IMAGE_MAGIC[dot_ext]
    ):
        raise QWIException(
            "O arquivo não é uma imagem válida (conteúdo não corresponde à extensão).",
            422,
        )
    stored = f"{uuid.uuid4().hex[:12]}.{ext}"

    file_service = FileService(db)

    is_image = file_service.get_file_type(original) == "image"
    image_usage = ImageUsage.INSERT_REPORT if is_image else None
    analyze_images = activity_requests_image_analysis(activity)

    attachment = await file_service.save_attachment(
        activity,
        stored_filename=stored,
        original_filename=original,
        content=content,
        mime_type=file.content_type,
        image_usage=image_usage,
        manual_caption=None,
        include_in_weekly=True,
    )
    if not is_image or analyze_images:
        submit_background(process_attachment_in_background, attachment.id)

    return _load_activity(db, activity.id)


@router.patch("/{activity_id}/attachments/{attachment_id}", response_model=ActivityResponse)
def update_attachment(
    activity_id: str,
    attachment_id: str,
    data: AttachmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ActivityService(db)
    service.get_by_id(activity_id, current_user.id)

    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.activity_id == activity_id)
        .first()
    )
    if not attachment:
        raise NotFoundError("Anexo")

    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None or isinstance(value, bool):
            setattr(attachment, key, value)

    db.commit()
    return _load_activity(db, activity_id)


@router.delete("/{activity_id}/attachments/{attachment_id}", response_model=ActivityResponse)
def delete_attachment(
    activity_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ActivityService(db)
    service.get_by_id(activity_id, current_user.id)

    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.activity_id == activity_id)
        .first()
    )
    if not attachment:
        raise NotFoundError("Anexo")

    file_path = Path(attachment.file_path)
    if file_path.exists():
        file_path.unlink()

    db.delete(attachment)
    db.commit()
    return _load_activity(db, activity_id)


def _load_activity(db: Session, activity_id: str, user_id: str | None = None) -> ActivityResponse:
    from app.models import Activity

    query = (
        db.query(Activity)
        .options(joinedload(Activity.metadata_entry), joinedload(Activity.attachments))
        .filter(Activity.id == activity_id)
    )
    if user_id:
        query = query.filter(Activity.user_id == user_id)
    activity = query.first()
    if not activity:
        raise QWIException("Atividade não encontrada", 404)
    return _serialize_activity(activity)


def _serialize_activity(activity) -> ActivityResponse:
    return ActivityResponse.model_validate(activity)


@router.get("/attachments/{attachment_id}/file")
def get_attachment_file(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve o arquivo do anexo.

    Acesso: o DONO da atividade e colegas que podem ver os weeklys do dono
    (mesma regra do organograma) — necessário para a pré-visualização do PPT.
    """
    from app.api.routes.users import can_view_user_weeklys

    attachment = (
        db.query(Attachment)
        .options(joinedload(Attachment.activity))
        .filter(Attachment.id == attachment_id)
        .first()
    )
    if not attachment:
        raise NotFoundError("Anexo")
    owner = db.query(User).filter(User.id == attachment.activity.user_id).first()
    if not owner or not can_view_user_weeklys(current_user, owner, db):
        raise NotFoundError("Anexo")
    path = Path(attachment.file_path)
    if not path.exists():
        raise NotFoundError("Arquivo do anexo")
    return FileResponse(
        path=str(path),
        media_type=attachment.mime_type or "application/octet-stream",
        filename=attachment.original_filename,
    )
