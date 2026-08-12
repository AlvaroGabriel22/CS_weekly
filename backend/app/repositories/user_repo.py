"""User Repository - Specialized queries for User model"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import User, UserRole, QualitySector, WritingProfile
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with specialized queries"""

    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.session.query(User).filter(User.email == email).first()

    def get_by_employee_id(self, employee_id: str) -> Optional[User]:
        """Get user by employee ID"""
        return self.session.query(User).filter(User.employee_id == employee_id).first()

    def get_active_users(self, skip: int = 0, limit: int = 50) -> List[User]:
        """Get all active users"""
        return (
            self.session.query(User)
            .filter(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_role(self, role: UserRole, skip: int = 0, limit: int = 50) -> List[User]:
        """Get users by role"""
        return (
            self.session.query(User)
            .filter(User.role == role)
            .filter(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_sector(self, sector: QualitySector, skip: int = 0, limit: int = 50) -> List[User]:
        """Get users by sector"""
        return (
            self.session.query(User)
            .filter(User.sector == sector)
            .filter(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_department(self, department: str, skip: int = 0, limit: int = 50) -> List[User]:
        """Get users by department"""
        return (
            self.session.query(User)
            .filter(User.department == department)
            .filter(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_admins(self) -> List[User]:
        """Get all admin users"""
        return (
            self.session.query(User)
            .filter(User.is_admin == True)
            .filter(User.is_active == True)
            .all()
        )

    def get_with_profile(self, user_id: str) -> Optional[User]:
        """Get user with writing profile eager loaded"""
        return (
            self.session.query(User)
            .filter(User.id == user_id)
            .filter(User.is_active == True)
            .first()
        )

    def search_by_name(self, name: str, skip: int = 0, limit: int = 50) -> List[User]:
        """Search users by name (case-insensitive)"""
        return (
            self.session.query(User)
            .filter(User.name.ilike(f"%{name}%"))
            .filter(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return self.exists(email=email)

    def employee_id_exists(self, employee_id: str) -> bool:
        """Check if employee ID already exists"""
        return self.exists(employee_id=employee_id)

    def deactivate(self, user_id: str) -> bool:
        """Deactivate a user"""
        return self.soft_delete(user_id)

    def activate(self, user_id: str) -> Optional[User]:
        """Activate a user"""
        user = self.read(user_id)
        if user:
            user.is_active = True
            self.session.commit()
            self.session.refresh(user)
        return user

    def count_active(self) -> int:
        """Count active users"""
        return self.count(is_active=True)

    def count_by_role(self, role: UserRole) -> int:
        """Count users by role"""
        return self.count(role=role, is_active=True)

    def count_by_sector(self, sector: QualitySector) -> int:
        """Count users by sector"""
        return self.count(sector=sector, is_active=True)
