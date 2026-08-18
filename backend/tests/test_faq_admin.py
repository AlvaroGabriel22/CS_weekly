"""FAQ, usuário root/admin e exclusão de weekly.

Sobe o app com um banco SQLite temporário isolado e exercita os fluxos via
httpx.ASGITransport (o TestClient do Starlette é incompatível com o httpx do
venv). Nenhum banco de dev/produção é tocado.
"""
import os
import tempfile

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Engine dedicado ao teste (decoplado do engine global/.env).
_TMP = tempfile.mkdtemp(prefix="qwi_faq_test_")
os.environ["UPLOAD_DIR"] = f"{_TMP}/uploads"

from app.core.database import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models import User, UserRole, QualitySector  # noqa: E402

_test_engine = create_engine(
    f"sqlite:///{_TMP}/faq.db", connect_args={"check_same_thread": False}
)
_TestSession = sessionmaker(bind=_test_engine, autocommit=False, autoflush=False)
Base.metadata.create_all(bind=_test_engine)

# Seed do root direto na sessão de teste.
_s = _TestSession()
_s.add(User(
    email="admin@qwitest.com", employee_id="ROOT",
    hashed_password=get_password_hash("root-senha-teste"),
    name="Administrador", role=UserRole.GERENTE_SR,
    sector=QualitySector.CSI, is_admin=True, is_active=True,
))
_s.commit()
_s.close()

_APP = create_app()


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


_APP.dependency_overrides[get_db] = _override_get_db


import asyncio  # noqa: E402


class SyncClient:
    """Fachada síncrona sobre httpx.AsyncClient+ASGITransport (sem TestClient,
    que é incompatível com o httpx do venv, e sem pytest-asyncio)."""

    def __init__(self):
        self._c = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_APP),
            base_url="http://test", timeout=30,
        )

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def get(self, url, **kw):
        return self._run(self._c.get(url, **kw))

    def post(self, url, **kw):
        return self._run(self._c.post(url, **kw))

    def put(self, url, **kw):
        return self._run(self._c.put(url, **kw))

    def delete(self, url, **kw):
        return self._run(self._c.delete(url, **kw))


def client() -> "SyncClient":
    return SyncClient()


def _register_login(c, email, emp, sector="OQC"):
    c.post("/api/auth/register", json={
        "name": f"User {emp}", "email": email, "password": "senha123",
        "password_confirm": "senha123", "employee_id": emp,
        "role": "Analista Jr", "sector": sector,
    })
    r = c.post("/api/auth/login", json={"email": email, "password": "senha123"})
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def ctx():
    c = client()
    root = c.post("/api/auth/login", json={
        "email": "admin@qwitest.com", "password": "root-senha-teste"}).json()["access_token"]
    ua = _register_login(c, "faq_a@qwitest.com", "FAQA")
    ub = _register_login(c, "faq_b@qwitest.com", "FAQB", sector="IQC")
    return {"c": c, "root": root, "ua": ua, "ub": ub}


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_root_is_admin_and_hidden_from_org(ctx):
    c = ctx["c"]
    prof = c.get("/api/users/profile", headers=H(ctx["root"])).json()
    assert prof["is_admin"] is True
    org = c.get("/api/users/org", headers=H(ctx["ua"])).json()
    assert all(u["name"] != "Administrador" for u in org)


def test_faq_create_visible_and_permissions(ctx):
    c = ctx["c"]
    r = c.post("/api/faq", headers=H(ctx["ua"]),
               json={"title": "Erro no botão", "description": "Não responde ao clique."})
    assert r.status_code == 201
    fid = r.json()["id"]
    # visível para outro usuário
    lst = c.get("/api/faq", headers=H(ctx["ub"])).json()
    assert any(x["id"] == fid for x in lst)
    # usuário comum NÃO fecha/responde
    assert c.put(f"/api/faq/{fid}", headers=H(ctx["ub"]),
                 json={"response": "x", "close": True}).status_code == 403
    # root fecha e responde
    resolved = c.put(f"/api/faq/{fid}", headers=H(ctx["root"]),
                     json={"response": "Corrigido.", "close": True}).json()
    assert resolved["status"] == "closed"
    assert resolved["admin_response"] == "Corrigido."


def test_faq_validation(ctx):
    c = ctx["c"]
    # título muito curto -> 422
    assert c.post("/api/faq", headers=H(ctx["ua"]),
                  json={"title": "x", "description": "y"}).status_code == 422


def test_notify_users_admin_only(ctx):
    c = ctx["c"]
    assert c.get("/api/faq/notify-users", headers=H(ctx["ua"])).status_code == 403
    assert c.get("/api/faq/notify-users", headers=H(ctx["root"])).status_code == 200
    # adiciona por matrícula
    lst = c.post("/api/faq/notify-users", headers=H(ctx["root"]),
                 json={"employee_id": "FAQA"}).json()
    assert any(u["employee_id"] == "FAQA" for u in lst)
    # matrícula inexistente -> 400 field error
    bad = c.post("/api/faq/notify-users", headers=H(ctx["root"]),
                 json={"employee_id": "NAOEXISTE"})
    assert bad.status_code == 400
    assert bad.json()["detail"]["field"] == "employee_id"


def test_delete_weekly_owner_and_permissions(ctx):
    c = ctx["c"]
    manual = {"slides": [{"id": "s0", "kind": "cover", "elements": [
        {"id": "t", "type": "text", "x": 0.1, "y": 0.3, "w": 0.8, "h": 0.15,
         "text": "W", "font_size": 40}]}]}
    aid = c.post("/api/activities", headers=H(ctx["ua"]),
                 json={"title": "ativ", "include_in_weekly": True}).json()["id"]
    g = c.post("/api/weekly/generate", headers=H(ctx["ua"]),
               json={"activity_ids": [aid], "week_number": 30, "year": 2026,
                     "layout": manual, "layout_source": "manual"})
    rid = g.json()["id"]
    # outro usuário (não dono, não admin) -> 403
    assert c.delete(f"/api/weekly/{rid}", headers=H(ctx["ub"])).status_code == 403
    # dono -> 204
    assert c.delete(f"/api/weekly/{rid}", headers=H(ctx["ua"])).status_code == 204
    # sumiu
    assert c.get(f"/api/weekly/{rid}", headers=H(ctx["ua"])).status_code == 404
