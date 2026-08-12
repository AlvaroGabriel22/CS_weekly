import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import QWIException
from app.core.security import get_password_hash, verify_password
from app.models import MANAGEMENT_ROLES, User, WritingProfile
from app.schemas.user import UserResponse, UserUpdate, WritingProfileResponse, WritingProfileUpdate

router = APIRouter(prefix="/users", tags=["Users"])

PHOTO_DIR = Path("uploads/photos")
PHOTO_MAX_BYTES = 5 * 1024 * 1024
PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def can_view_user_weeklys(viewer: User, owner: User) -> bool:
    """Regra de acesso a weeklys de outra pessoa.

    - Próprio usuário e admins: sempre.
    - Cargos de gestão (MANAGEMENT_ROLES): todos os departamentos.
    - Demais: apenas colegas do MESMO departamento.
    """
    if viewer.id == owner.id or viewer.is_admin:
        return True
    if viewer.role in MANAGEMENT_ROLES:
        return True
    return viewer.department == owner.department


def _field_error(field: str, message: str, hint: str) -> HTTPException:
    """Erro 400 apontando o campo culpado (mesmo contrato do /auth/register)."""
    return HTTPException(
        status_code=400,
        detail={"field": field, "message": message, "hint": hint},
    )


class OrgUserResponse(BaseModel):
    id: str
    name: str
    role: str
    sector: str
    department: str
    photo_url: str | None
    viewer_can_access: bool


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6)
    new_password_confirm: str = Field(min_length=6)


@router.get("/org", response_model=list[OrgUserResponse])
def get_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Todos os usuários ativos, para o organograma de departamentos."""
    users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    return [
        OrgUserResponse(
            id=u.id,
            name=u.name,
            role=u.role.value,
            sector=u.sector.value,
            department=u.department,
            photo_url=u.photo_url,
            viewer_can_access=can_view_user_weeklys(current_user, u),
        )
        for u in users
    ]


@router.put("/me/password", response_model=UserResponse)
def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise _field_error(
            "current_password",
            "Senha atual incorreta.",
            "Digite a senha que você usa hoje para entrar no sistema.",
        )
    if data.new_password != data.new_password_confirm:
        raise _field_error(
            "new_password_confirm",
            "As senhas não conferem.",
            "Digite a mesma senha nova nos dois campos.",
        )
    if data.new_password == data.current_password:
        raise _field_error(
            "new_password",
            "A nova senha é igual à atual.",
            "Escolha uma senha diferente da que você já usa.",
        )

    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/photo", response_model=UserResponse)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in PHOTO_TYPES:
        raise _field_error(
            "photo",
            "Formato de imagem não suportado.",
            "Envie uma foto JPG, PNG ou WEBP.",
        )

    content = await file.read()
    if len(content) > PHOTO_MAX_BYTES:
        raise _field_error(
            "photo",
            "Imagem muito grande (máx. 5 MB).",
            "Reduza a resolução ou escolha outra foto.",
        )

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)

    # Nome novo a cada upload (evita cache velho no navegador); remove o anterior
    if current_user.photo_url:
        old = Path(current_user.photo_url.lstrip("/"))
        if old.is_file() and old.parent == PHOTO_DIR:
            old.unlink(missing_ok=True)

    filename = f"{current_user.id}-{uuid.uuid4().hex[:8]}{PHOTO_TYPES[file.content_type]}"
    (PHOTO_DIR / filename).write_bytes(content)

    current_user.photo_url = f"/uploads/photos/{filename}"
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/writing-profile", response_model=WritingProfileResponse)
def get_writing_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(WritingProfile).filter(WritingProfile.user_id == current_user.id).first()
    if not profile:
        raise QWIException("Writing profile not found", 404)
    return profile


@router.patch("/writing-profile", response_model=WritingProfileResponse)
def update_writing_profile(
    data: WritingProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(WritingProfile).filter(WritingProfile.user_id == current_user.id).first()
    if not profile:
        raise QWIException("Writing profile not found", 404)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


# ── Layout fixado do editor de montagem (PPT) ──────────────────────────────

class SlideLayoutRequest(BaseModel):
    layout: dict


class SlideLayoutResponse(BaseModel):
    layout: dict | None


@router.get("/me/slide-layout", response_model=SlideLayoutResponse)
def get_slide_layout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import SlideLayoutPref

    pref = db.query(SlideLayoutPref).filter(SlideLayoutPref.user_id == current_user.id).first()
    return SlideLayoutResponse(layout=pref.layout if pref else None)


@router.put("/me/slide-layout", response_model=SlideLayoutResponse)
def save_slide_layout(
    data: SlideLayoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import SlideLayoutPref

    pref = db.query(SlideLayoutPref).filter(SlideLayoutPref.user_id == current_user.id).first()
    if pref:
        pref.layout = data.layout
    else:
        pref = SlideLayoutPref(user_id=current_user.id, layout=data.layout)
        db.add(pref)
    db.commit()
    return SlideLayoutResponse(layout=pref.layout)
