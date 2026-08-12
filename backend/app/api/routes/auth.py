from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import create_user_with_profile, get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import QualitySector, User, UserRole
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _field_error(field: str, message: str, hint: str) -> HTTPException:
    """Erro 400 apontando o campo culpado, para o formulário destacar a caixa certa."""
    return HTTPException(
        status_code=400,
        detail={"field": field, "message": message, "hint": hint},
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if data.password != data.password_confirm:
        raise _field_error(
            "password_confirm",
            "As senhas não conferem.",
            "Digite a mesma senha nos dois campos.",
        )

    existing_email = db.query(User).filter(User.email == data.email).first()
    if existing_email:
        raise _field_error(
            "email",
            "Este email já está cadastrado.",
            "Use outro email ou entre com a conta existente.",
        )

    existing_id = db.query(User).filter(User.employee_id == data.employee_id).first()
    if existing_id:
        raise _field_error(
            "employee_id",
            "Esta matrícula já está cadastrada.",
            "Confira o número; se estiver certo, procure o administrador.",
        )

    user = create_user_with_profile(
        db,
        data.email,
        data.employee_id,
        data.password,
        data.name,
        data.role,
        sector=data.sector,
    )
    return user


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id})
    return Token(access_token=token)


class PasswordResetRequest(BaseModel):
    """Recuperação de senha verificada pela MATRÍCULA (sem envio de email)."""
    email: EmailStr
    employee_id: str = Field(min_length=1, max_length=50)
    new_password: str = Field(min_length=6, max_length=128)
    new_password_confirm: str


@router.post("/reset-password", response_model=UserResponse)
def reset_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    if data.new_password != data.new_password_confirm:
        raise _field_error(
            "new_password_confirm",
            "As senhas não conferem.",
            "Digite a mesma senha nos dois campos.",
        )

    user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    # Resposta única para email inexistente OU matrícula errada:
    # não revela qual dos dois falhou (evita enumeração de contas).
    if (
        not user
        or not user.is_active
        or user.employee_id.strip().lower() != data.employee_id.strip().lower()
    ):
        raise _field_error(
            "employee_id",
            "Email e matrícula não conferem.",
            "Confira os dois dados; se persistir, procure o administrador.",
        )

    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/roles")
def get_available_roles():
    return {
        "roles": [{"value": role.value, "label": role.value} for role in UserRole]
    }


@router.get("/sectors")
def get_available_sectors():
    return {
        "sectors": [{"value": s.value, "label": s.value} for s in QualitySector]
    }
