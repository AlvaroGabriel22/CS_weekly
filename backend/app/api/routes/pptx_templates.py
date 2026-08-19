"""Modelos de PPT enviados pelo usuário (aba Templates dos Relatórios).

O usuário sobe um weekly antigo (.pptx) que vira MODELO para a IA. No upload o
arquivo é convertido para o DeckLayout interno (esqueleto). Máx. 2 por usuário;
para trocar, remove um e adiciona outro.
"""
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError, QWIException
from app.models import PptxTemplate, User, generate_uuid
from app.services.pptx_import import SLOTS, PptxImportError, import_pptx_to_layout

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/pptx-templates", tags=["PPTX Templates"])

MAX_PER_USER = 2


class PptxTemplateResponse(BaseModel):
    id: str
    name: str
    slides_count: int
    created_at: datetime
    # False = o registro existe mas o .pptx sumiu do disco. A geração por
    # mutação precisa do arquivo original, então isso tem que ser visível.
    available: bool = True


def template_file(template: PptxTemplate) -> Path:
    """Caminho do .pptx do modelo. Erro claro se o arquivo não estiver lá."""
    path = Path(template.file_path or "")
    if not template.file_path or not path.exists():
        raise QWIException(
            f"O arquivo do modelo “{template.name}” não está mais disponível. "
            "Envie o .pptx novamente na aba Templates.",
            409,
        )
    return path


def _serialize(t: PptxTemplate) -> PptxTemplateResponse:
    slides = t.layout.get("slides", []) if isinstance(t.layout, dict) else []
    return PptxTemplateResponse(
        id=t.id, name=t.name, slides_count=len(slides), created_at=t.created_at,
        available=bool(t.file_path) and Path(t.file_path).exists(),
    )


@router.get("", response_model=list[PptxTemplateResponse])
def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PptxTemplate)
        .filter(PptxTemplate.user_id == current_user.id)
        .order_by(PptxTemplate.created_at.desc())
        .all()
    )
    return [_serialize(t) for t in rows]


@router.post("", response_model=PptxTemplateResponse, status_code=201)
async def upload_template(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.query(PptxTemplate).filter(PptxTemplate.user_id == current_user.id).count()
    if count >= MAX_PER_USER:
        raise QWIException(
            f"Limite de {MAX_PER_USER} modelos de PPT. Remova um antes de adicionar outro.",
            409,
        )

    original = file.filename or "modelo.pptx"
    if not original.lower().endswith(".pptx"):
        raise QWIException("Envie um arquivo .pptx (PowerPoint).", 422)

    content = await file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) == 0:
        raise QWIException("Arquivo vazio. Selecione um .pptx válido.", 422)
    if len(content) > max_size:
        raise QWIException(f"Arquivo excede o limite de {settings.MAX_UPLOAD_SIZE_MB} MB.", 413)

    # Grava o arquivo num diretório dedicado.
    # O id é gerado AQUI: o default da coluna só é aplicado no INSERT, então
    # `template.id` ainda seria None ao montar o caminho — e todos os modelos
    # do usuário virariam o mesmo arquivo "None.pptx", um sobrescrevendo o
    # outro (e apagar um levaria junto o arquivo do outro).
    template_id = generate_uuid()
    template = PptxTemplate(
        id=template_id,
        user_id=current_user.id,
        name=Path(original).stem[:255] or "Modelo",
        file_path="",  # preenchido abaixo
        layout={},
    )
    dest_dir = Path(settings.UPLOAD_DIR) / "pptx_templates" / current_user.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{template_id}.pptx"
    try:
        dest.write_bytes(content)
    except Exception as error:
        logger.warning("Falha ao salvar o PPT do modelo: %s", error)
        raise QWIException("Não foi possível salvar o arquivo. Tente novamente.", 500)

    # Converte para o layout interno.
    try:
        layout = import_pptx_to_layout(str(dest))
    except PptxImportError as error:
        dest.unlink(missing_ok=True)  # não deixa arquivo órfão
        raise QWIException(str(error), 422)
    except Exception as error:
        dest.unlink(missing_ok=True)
        logger.exception("Erro inesperado ao converter o PPT do modelo")
        raise QWIException(
            "Não conseguimos interpretar este PPT. Tente um arquivo mais simples "
            "(caixas de texto, tabelas e imagens).",
            422,
        )

    template.file_path = str(dest)
    template.layout = layout
    db.add(template)
    db.commit()
    db.refresh(template)
    logger.info(
        "Modelo de PPT importado | user=%s | slides=%d",
        current_user.id, len(layout.get("slides", [])),
    )
    return _serialize(template)


class TemplateLayoutResponse(PptxTemplateResponse):
    layout: dict


class SlotsRequest(BaseModel):
    """Marcação de slots: {slide_id: {element_id: slot}}."""
    slots: dict[str, dict[str, str]]


def _load(db: Session, template_id: str, user: User) -> PptxTemplate:
    template = (
        db.query(PptxTemplate)
        .filter(PptxTemplate.id == template_id, PptxTemplate.user_id == user.id)
        .first()
    )
    if not template:
        raise NotFoundError("Modelo")
    return template


def _needs_reimport(layout: dict) -> bool:
    """Layout antigo: importado antes dos slots/âncoras existirem."""
    slides = layout.get("slides") if isinstance(layout, dict) else None
    if not isinstance(slides, list) or not slides:
        return False
    for slide in slides:
        for element in slide.get("elements") or []:
            if "slot" not in element or "src_shape_id" not in element:
                return True
    return False


@router.get("/{template_id}", response_model=TemplateLayoutResponse)
def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Modelo com o layout completo — usado na tela de marcação de slots.

    Modelos enviados antes dos slots existirem são reimportados do .pptx aqui,
    uma única vez: sem a âncora (slide + shape_id) o exportador por mutação não
    consegue achar o shape correspondente no arquivo.
    """
    template = _load(db, template_id, current_user)
    layout = template.layout if isinstance(template.layout, dict) else {}

    if _needs_reimport(layout) and template.file_path and Path(template.file_path).exists():
        try:
            template.layout = import_pptx_to_layout(template.file_path)
            flag_modified(template, "layout")
            db.commit()
            db.refresh(template)
            layout = template.layout
            logger.info("Modelo reimportado para ganhar slots | template=%s", template_id)
        except Exception as error:  # arquivo problemático não pode travar a tela
            logger.warning("Falha ao reimportar o modelo %s: %s", template_id, error)

    base = _serialize(template)
    return TemplateLayoutResponse(**base.model_dump(), layout=layout)


@router.patch("/{template_id}/slots", response_model=TemplateLayoutResponse)
def update_slots(
    template_id: str,
    data: SlotsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Salva o papel de cada elemento do modelo.

    Só o campo `slot` é alterado: geometria, fonte e cor vêm do .pptx original
    e não são editáveis aqui — na geração por mutação quem manda é o arquivo.
    """
    template = _load(db, template_id, current_user)
    layout = template.layout if isinstance(template.layout, dict) else {}
    slides = layout.get("slides")
    if not isinstance(slides, list) or not slides:
        raise QWIException("Este modelo não tem slides para marcar.", 409)

    invalidos = sorted({
        slot for por_slide in data.slots.values()
        for slot in por_slide.values() if slot not in SLOTS
    })
    if invalidos:
        raise QWIException(f"Tipo de slot desconhecido: {', '.join(invalidos)}.", 422)

    aplicados = 0
    for slide in slides:
        marcacao = data.slots.get(str(slide.get("id")))
        if not marcacao:
            continue
        for element in slide.get("elements") or []:
            novo = marcacao.get(str(element.get("id")))
            if novo:
                element["slot"] = novo
                aplicados += 1

    # SQLAlchemy não detecta mutação dentro de um JSON: reatribui.
    template.layout = {**layout, "slides": slides}
    flag_modified(template, "layout")
    db.commit()
    db.refresh(template)
    logger.info("Slots do modelo atualizados | template=%s | elementos=%d",
                template_id, aplicados)
    base = _serialize(template)
    return TemplateLayoutResponse(**base.model_dump(), layout=template.layout)


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = (
        db.query(PptxTemplate)
        .filter(PptxTemplate.id == template_id, PptxTemplate.user_id == current_user.id)
        .first()
    )
    if not template:
        raise NotFoundError("Modelo")
    file_path = template.file_path
    db.delete(template)
    db.commit()
    if file_path:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            logger.warning("Falha ao remover arquivo do modelo %s", template_id)
