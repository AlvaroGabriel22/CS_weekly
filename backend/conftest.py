import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from datetime import datetime

# Usar SQLite em memória para testes
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Import após definir a URL de teste
os.environ['DATABASE_URL'] = SQLALCHEMY_DATABASE_URL

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash


@pytest.fixture(scope='session')
def engine():
    """Cria engine SQLite em memória para toda a sessão de testes"""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={'check_same_thread': False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(engine):
    """Cria nova sessão de BD para cada teste"""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """FastAPI test client com BD mockada"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Dados de usuário para testes"""
    return {
        'email': 'test@example.com',
        'employee_id': 'EMP-00001',
        'password': 'test123456',
        'password_confirm': 'test123456',
        'name': 'Test User',
        'role': 'ANALISTA_SR',
        'sector': 'CSI',
    }


@pytest.fixture
def test_user(db, test_user_data):
    """Cria usuário de teste no BD"""
    from app.models import User, UserRole

    user = User(
        email=test_user_data['email'],
        employee_id=test_user_data['employee_id'],
        hashed_password=get_password_hash(test_user_data['password']),
        name=test_user_data['name'],
        role=UserRole.ANALISTA_SR,
        sector='CSI',
        department='Qualidade',
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user_data):
    """Headers com token JWT de usuário autenticado"""
    # Registrar usuário
    response = client.post(
        '/auth/register',
        json=test_user_data,
    )
    assert response.status_code == 201

    # Fazer login
    login_response = client.post(
        '/auth/login',
        json={
            'email': test_user_data['email'],
            'password': test_user_data['password'],
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def test_activity_data():
    """Dados de atividade para testes"""
    return {
        'title': 'Test Activity',
        'description': 'Test description',
        'activity_date': datetime.now().isoformat(),
        'tags': ['test', 'automation'],
    }


@pytest.fixture
def test_activity(db, test_user, test_activity_data):
    """Cria atividade de teste no BD"""
    from app.models import Activity
    from app.core.dates import calculate_week_number

    activity_date = datetime.fromisoformat(test_activity_data['activity_date'])
    week_num, year = calculate_week_number(activity_date)

    activity = Activity(
        user_id=test_user.id,
        title=test_activity_data['title'],
        description=test_activity_data['description'],
        activity_date=activity_date,
        tags=test_activity_data['tags'],
        week_number=week_num,
        year=year,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@pytest.fixture
def async_client(client):
    """Async test client (if needed for async endpoints)"""
    return client
