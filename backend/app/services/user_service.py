"""User Service - Business logic for user management"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import User, UserRole, QualitySector, WritingProfile, Language, WritingTone, ObjectivityLevel, TechnicalLevel
from app.repositories import UserRepository
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import QWIException


class UserService:
    """Service for user management with business rules"""

    # Email validation
    MIN_PASSWORD_LENGTH = 6
    MAX_NAME_LENGTH = 255
    MAX_EMAIL_LENGTH = 255

    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def create_user(
        self,
        email: str,
        employee_id: str,
        password: str,
        name: str,
        role: UserRole,
        sector: QualitySector = QualitySector.CSI,
        department: str = "Qualidade",
    ) -> User:
        """Create new user with business validation"""

        # Validate email
        email = email.lower().strip()
        if not email or len(email) > self.MAX_EMAIL_LENGTH:
            raise QWIException('Invalid email address')

        if self.repo.email_exists(email):
            raise QWIException('Email already registered')

        # Validate employee ID
        employee_id = employee_id.strip()
        if not employee_id:
            raise QWIException('Employee ID is required')

        if self.repo.employee_id_exists(employee_id):
            raise QWIException('Employee ID already exists')

        # Validate name
        name = name.strip()
        if not name or len(name) > self.MAX_NAME_LENGTH:
            raise QWIException('Invalid name')

        # Validate password
        if len(password) < self.MIN_PASSWORD_LENGTH:
            raise QWIException(f'Password must be at least {self.MIN_PASSWORD_LENGTH} characters')

        # Hash password
        hashed_password = get_password_hash(password)

        # Create user
        user = self.repo.create({
            'email': email,
            'employee_id': employee_id,
            'hashed_password': hashed_password,
            'name': name,
            'role': role,
            'sector': sector,
            'department': department,
            'is_active': True,
        })

        # Create default writing profile
        self._create_default_profile(user.id)

        return user

    def _create_default_profile(self, user_id: str) -> WritingProfile:
        """Create default writing profile for user"""

        profile = WritingProfile(
            user_id=user_id,
            default_language=Language.PT,
            writing_tone=WritingTone.SPECIALIST,
            objectivity=ObjectivityLevel.HIGH,
            technical_level=TechnicalLevel.MEDIUM,
            auto_conclusions=True,
            auto_next_steps=True,
            auto_impact=True,
            auto_describe_images=True,
            auto_explain_charts=True,
        )
        self.db.add(profile)
        self.db.commit()
        return profile

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email/password"""

        email = email.lower().strip()

        user = self.repo.get_by_email(email)
        if not user:
            return None

        if not user.is_active:
            raise QWIException('User account is deactivated')

        if not verify_password(password, user.hashed_password):
            return None

        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""

        return self.repo.read(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""

        return self.repo.get_by_email(email.lower().strip())

    def update_profile(
        self,
        user_id: str,
        **updates
    ) -> User:
        """Update user profile"""

        user = self.repo.read(user_id)
        if not user:
            raise QWIException('User not found')

        # Validate updates
        if 'email' in updates:
            email = updates['email'].lower().strip()
            if email != user.email and self.repo.email_exists(email):
                raise QWIException('Email already in use')
            updates['email'] = email

        if 'name' in updates:
            name = updates['name'].strip()
            if not name or len(name) > self.MAX_NAME_LENGTH:
                raise QWIException('Invalid name')
            updates['name'] = name

        if 'photo_url' in updates:
            # Validate URL format (basic)
            url = updates['photo_url']
            if url and not url.startswith(('http://', 'https://')):
                raise QWIException('Invalid photo URL')

        # Only allow updating specific fields
        allowed_fields = {'name', 'photo_url', 'sector', 'department'}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        return self.repo.update(user_id, filtered_updates)

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change user password"""

        user = self.repo.read(user_id)
        if not user:
            raise QWIException('User not found')

        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise QWIException('Current password is incorrect')

        # Validate new password
        if len(new_password) < self.MIN_PASSWORD_LENGTH:
            raise QWIException(f'Password must be at least {self.MIN_PASSWORD_LENGTH} characters')

        if current_password == new_password:
            raise QWIException('New password must be different from current password')

        # Update password
        hashed = get_password_hash(new_password)
        self.repo.update(user_id, {'hashed_password': hashed})

        return True

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""

        return self.repo.soft_delete(user_id)

    def activate_user(self, user_id: str) -> Optional[User]:
        """Activate user account"""

        return self.repo.activate(user_id)

    def update_writing_profile(
        self,
        user_id: str,
        default_language: Optional[Language] = None,
        default_template_id: Optional[str] = None,
        writing_tone: Optional[WritingTone] = None,
        objectivity: Optional[ObjectivityLevel] = None,
        technical_level: Optional[TechnicalLevel] = None,
        auto_conclusions: Optional[bool] = None,
        auto_next_steps: Optional[bool] = None,
        auto_impact: Optional[bool] = None,
        auto_describe_images: Optional[bool] = None,
        auto_explain_charts: Optional[bool] = None,
        personal_prompt: Optional[str] = None,
    ) -> WritingProfile:
        """Update user's writing profile"""

        user = self.repo.read(user_id)
        if not user:
            raise QWIException('User not found')

        profile = user.writing_profile
        if not profile:
            raise QWIException('Writing profile not found')

        # Update only provided fields
        if default_language is not None:
            profile.default_language = default_language

        if default_template_id is not None:
            profile.default_template_id = default_template_id

        if writing_tone is not None:
            profile.writing_tone = writing_tone

        if objectivity is not None:
            profile.objectivity = objectivity

        if technical_level is not None:
            profile.technical_level = technical_level

        if auto_conclusions is not None:
            profile.auto_conclusions = auto_conclusions

        if auto_next_steps is not None:
            profile.auto_next_steps = auto_next_steps

        if auto_impact is not None:
            profile.auto_impact = auto_impact

        if auto_describe_images is not None:
            profile.auto_describe_images = auto_describe_images

        if auto_explain_charts is not None:
            profile.auto_explain_charts = auto_explain_charts

        if personal_prompt is not None:
            profile.personal_prompt = personal_prompt

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_by_role(self, role: UserRole) -> List[User]:
        """Get all users with specific role"""

        return self.repo.get_by_role(role)

    def get_by_sector(self, sector: QualitySector) -> List[User]:
        """Get all users in specific sector"""

        return self.repo.get_by_sector(sector)

    def get_active_users(self) -> List[User]:
        """Get all active users"""

        return self.repo.get_active_users()

    def search_users(self, query: str) -> List[User]:
        """Search users by name"""

        if not query or len(query) < 2:
            raise QWIException('Search query must be at least 2 characters')

        return self.repo.search_by_name(query)

    def get_statistics(self) -> dict:
        """Get user statistics"""

        return {
            'active': self.repo.count_active(),
            'total': self.repo.count(),
            'by_role': {
                role.value: self.repo.count_by_role(role)
                for role in UserRole
            },
            'by_sector': {
                sector.value: self.repo.count_by_sector(sector)
                for sector in QualitySector
            },
        }
