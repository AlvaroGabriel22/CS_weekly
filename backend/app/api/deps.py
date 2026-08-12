from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.models import User, WritingProfile, QualitySector, UserRole, MANAGEMENT_ROLES
from app.repositories.permission_repo import PermissionRepository
from app.services.permission_service import PermissionService

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = (
        db.query(User)
        .options(joinedload(User.writing_profile))
        .filter(User.id == payload["sub"])
        .first()
    )
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
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


def get_permission_repo(db: Session = Depends(get_db)) -> PermissionRepository:
    """Dependency for permission repository"""
    return PermissionRepository(db)


async def get_user_context(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get user context with permission info"""
    perm_repo = PermissionRepository(db)

    # Get IP address
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    # Get accessible resources
    accessible_weeklies = perm_repo.get_accessible_weeklies_optimized(current_user.id)
    accessible_activities = perm_repo.get_accessible_activities_optimized(current_user.id)
    shared_attachments = perm_repo.get_shared_attachments_optimized(current_user.id)

    return {
        "user": current_user,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "is_manager": current_user.role in MANAGEMENT_ROLES,
        "accessible_weeklies": [w.id for w in accessible_weeklies],
        "accessible_activities": [a.id for a in accessible_activities],
        "shared_attachments": [a.id for a in shared_attachments],
        "department": current_user.department,
    }


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
