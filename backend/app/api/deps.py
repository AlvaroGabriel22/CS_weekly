from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.models import User, WritingProfile, QualitySector, UserRole, MANAGEMENT_ROLES

# auto_error=False: sem header não levanta 403 automático — devolvemos 401
# explícito para "não autenticado", que é o que o frontend usa para redirecionar
# ao login (QA-040).
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    user = (
        db.query(User)
        .options(joinedload(User.writing_profile))
        .filter(User.id == payload["sub"])
        .first()
    )
    if not user or not user.is_active:
        raise UnauthorizedError("Usuário não encontrado ou inativo")
    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency for endpoints requiring admin/manager role"""
    if current_user.role not in MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin/Manager role required"
        )
    return current_user


def require_root(current_user: User = Depends(get_current_user)) -> User:
    """Dependency para ações exclusivas do usuário root/admin (is_admin).

    Ex.: fechar/responder FAQ, gerir a lista de quem recebe os e-mails do FAQ.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ação restrita ao administrador do sistema.",
        )
    return current_user


def create_user_with_profile(
    db: Session,
    email: str,
    employee_id: str,
    password: str,
    name: str,
    role: UserRole,
    sector: QualitySector = QualitySector.CSI,
) -> User:
    from app.core.security import get_password_hash

    # Normaliza o e-mail (o login busca com lower(); sem isso, "A@x" e "a@x"
    # coexistiriam e o login cairia numa conta arbitrária — QA-005).
    email = email.lower().strip()

    user = User(
        email=email,
        employee_id=employee_id,
        hashed_password=get_password_hash(password),
        name=name,
        role=role,
        sector=sector,
    )
    db.add(user)
    db.flush()

    profile = WritingProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user
