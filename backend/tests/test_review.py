"""Revisor da semana (POST /ai/review) — com LLM mockado (sem gemma)."""
import asyncio
import json
import tempfile
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import create_app
from app.core.security import get_password_hash
from app.models import (
    User, UserRole, QualitySector, WritingProfile, Activity, ActivityMetadata,
)
import app.api.routes.ai_features as ai_features
from app.services.llm_service import LLMResponse

_TMP = tempfile.mkdtemp(prefix="qwi_review_")
_engine = create_engine(f"sqlite:///{_TMP}/r.db", connect_args={"check_same_thread": False})
_Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
Base.metadata.create_all(bind=_engine)

# seed: usuário + perfil + atividade com KPI
_s = _Session()
_s.add(User(id="u1", email="r@qwitest.com", employee_id="R1",
            hashed_password=get_password_hash("senha123"), name="Rev",
            role=UserRole.ANALISTA_JR, sector=QualitySector.OQC))
_s.add(WritingProfile(user_id="u1", about_me="Acompanho FPY (~92%) na linha 3."))
_s.add(Activity(id="a1", user_id="u1", title="Auditoria linha 3",
                description="Verificados 12 pontos; FPY em 85%.",
                department="Qualidade", week_number=33, year=2026,
                activity_date=datetime(2026, 8, 11, tzinfo=UTC)))
_s.add(ActivityMetadata(activity_id="a1", related_kpis=["FPY"], line="Linha 3"))
_s.commit(); _s.close()

_APP = create_app()


def _override_get_db():
    db = _Session()
    try:
        yield db
    finally:
        db.close()


_APP.dependency_overrides[get_db] = _override_get_db


class _FakeLLM:
    """Substitui LLMService: devolve JSON fixo do revisor."""
    def __init__(self, *a, **k):
        pass

    async def generate(self, prompt, system=None, images=None, json_mode=False):
        payload = {"suggestions": [
            {"type": "anomaly", "message": "Seu FPY caiu para 85% (costuma ~92%).", "activity_id": "a1"},
            {"type": "gap", "message": "Auditoria sem plano de ação — quer incluir?", "activity_id": "a1"},
            {"type": "invalido", "message": "isto deve ser descartado", "activity_id": "a1"},
            {"type": "highlight", "message": "", "activity_id": "a1"},  # vazio → descartado
        ]}
        return LLMResponse(content=json.dumps(payload), model="fake")


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=_APP), base_url="http://t", timeout=30)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _token():
    async def go():
        async with _client() as c:
            r = await c.post("/api/auth/login", json={"email": "r@qwitest.com", "password": "senha123"})
            return r.json()["access_token"]
    return _run(go())


def test_review_sanitizes_and_anchors(monkeypatch):
    monkeypatch.setattr(ai_features, "LLMService", _FakeLLM)
    tok = _token()

    async def go():
        async with _client() as c:
            return await c.post("/api/ai/review",
                                headers={"Authorization": f"Bearer {tok}"},
                                json={"year": 2026, "week_number": 33, "activity_ids": ["a1"]})
    r = _run(go())
    assert r.status_code == 200
    sugg = r.json()["suggestions"]
    # tipo inválido e mensagem vazia descartados → sobram 2
    assert len(sugg) == 2
    types = {s["type"] for s in sugg}
    assert types == {"anomaly", "gap"}
    assert all(s["activity_id"] == "a1" for s in sugg)
    assert "FPY" in sugg[0]["message"]


def test_review_llm_down_returns_503(monkeypatch):
    class _Down:
        def __init__(self, *a, **k): pass
        async def generate(self, *a, **k):
            raise RuntimeError("ollama down")
    monkeypatch.setattr(ai_features, "LLMService", _Down)
    tok = _token()

    async def go():
        async with _client() as c:
            return await c.post("/api/ai/review",
                                headers={"Authorization": f"Bearer {tok}"},
                                json={"year": 2026, "week_number": 33, "activity_ids": ["a1"]})
    r = _run(go())
    assert r.status_code == 503


def test_review_requires_own_activity(monkeypatch):
    monkeypatch.setattr(ai_features, "LLMService", _FakeLLM)
    tok = _token()

    async def go():
        async with _client() as c:
            return await c.post("/api/ai/review",
                                headers={"Authorization": f"Bearer {tok}"},
                                json={"year": 2026, "week_number": 33, "activity_ids": ["inexistente"]})
    r = _run(go())
    assert r.status_code == 400
