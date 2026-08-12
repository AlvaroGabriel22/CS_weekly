"""Seed data generators for users"""
from datetime import datetime, UTC
from app.models import User, WritingProfile, UserRole, QualitySector, Language, WritingTone, ObjectivityLevel, TechnicalLevel
from app.core.security import get_password_hash


def create_test_users() -> list[dict]:
    """Generate test user data"""
    return [
        {
            'email': 'gerente.sr@example.com',
            'employee_id': 'EMP-001',
            'password': 'Test123456!',
            'name': 'João Gerente Sr',
            'role': UserRole.GERENTE_SR,
            'sector': QualitySector.QA,
        },
        {
            'email': 'analista.sr@example.com',
            'employee_id': 'EMP-002',
            'password': 'Test123456!',
            'name': 'Maria Analista Sr',
            'role': UserRole.ANALISTA_SR,
            'sector': QualitySector.CSI,
        },
        {
            'email': 'auditor.pl@example.com',
            'employee_id': 'EMP-003',
            'password': 'Test123456!',
            'name': 'Pedro Auditor PL',
            'role': UserRole.AUDITOR_PL,
            'sector': QualitySector.OQC,
        },
        {
            'email': 'analista.eng.sr@example.com',
            'employee_id': 'EMP-004',
            'password': 'Test123456!',
            'name': 'Ana Analista Eng Sr',
            'role': UserRole.ANALISTA_ENG_SR,
            'sector': QualitySector.IQC,
        },
        {
            'email': 'chefe@example.com',
            'employee_id': 'EMP-005',
            'password': 'Test123456!',
            'name': 'Carlos Chefe',
            'role': UserRole.CHEFE,
            'sector': QualitySector.QM,
        },
    ]


def seed_users(session) -> list[User]:
    """Create and persist test users"""
    users = []
    for user_data in create_test_users():
        user = User(
            email=user_data['email'],
            employee_id=user_data['employee_id'],
            hashed_password=get_password_hash(user_data['password']),
            name=user_data['name'],
            role=user_data['role'],
            sector=user_data['sector'],
            department='Qualidade',
            is_active=True,
        )
        session.add(user)
        session.flush()

        # Create default writing profile
        profile = WritingProfile(
            user_id=user.id,
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
        session.add(profile)

        users.append(user)

    session.commit()
    return users
