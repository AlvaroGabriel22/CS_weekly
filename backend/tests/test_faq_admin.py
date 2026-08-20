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
    # cadastro é pelo E-MAIL da pessoa (era pela matrícula)
    lst = c.post("/api/faq/notify-users", headers=H(ctx["root"]),
                 json={"email": "faq_a@qwitest.com"}).json()
    assert any(u["email"] == "faq_a@qwitest.com" for u in lst)


def test_notify_users_email_desconhecido_da_erro_de_campo(ctx):
    c = ctx["c"]
    bad = c.post("/api/faq/notify-users", headers=H(ctx["root"]),
                 json={"email": "ninguem@qwitest.com"})
    assert bad.status_code == 400
    assert bad.json()["detail"]["field"] == "email"


def test_notify_users_email_nao_diferencia_maiusculas(ctx):
    """O cadastro grava em minúsculas; digitar com maiúscula não pode falhar."""
    c = ctx["c"]
    lst = c.post("/api/faq/notify-users", headers=H(ctx["root"]),
                 json={"email": "FAQ_B@QWITEST.COM"})
    assert lst.status_code == 200
    assert any(u["email"] == "faq_b@qwitest.com" for u in lst.json())


def test_notify_users_recusa_texto_que_nao_e_email(ctx):
    c = ctx["c"]
    assert c.post("/api/faq/notify-users", headers=H(ctx["root"]),
                  json={"email": "FAQA"}).status_code == 422


# ── conta root: teste, não conteúdo da equipe ────────────────────────────────

def test_solicitacao_aberta_pela_root_nao_e_publica(ctx):
    """A root usa o FAQ para RESPONDER; o que ela abre é teste dela."""
    c = ctx["c"]
    rid = c.post("/api/faq", headers=H(ctx["root"]),
                 json={"title": "Teste do admin", "description": "Verificando o fluxo."})
    assert rid.status_code == 201
    fid = rid.json()["id"]

    for token in (ctx["ua"], ctx["ub"]):
        visiveis = c.get("/api/faq", headers=H(token)).json()
        assert all(x["id"] != fid for x in visiveis)
        assert all(x["title"] != "Teste do admin" for x in visiveis)

    # ...mas a própria root continua vendo a dela.
    assert any(x["id"] == fid for x in c.get("/api/faq", headers=H(ctx["root"])).json())


def test_resposta_da_root_continua_publica(ctx):
    """O oposto do teste acima: responder é justamente o papel da conta."""
    c = ctx["c"]
    fid = c.post("/api/faq", headers=H(ctx["ua"]),
                 json={"title": "Dúvida real", "description": "Como faço X?"}).json()["id"]
    c.put(f"/api/faq/{fid}", headers=H(ctx["root"]),
          json={"response": "Faça assim.", "close": True})

    visiveis = c.get("/api/faq", headers=H(ctx["ub"])).json()
    alvo = next(x for x in visiveis if x["id"] == fid)
    assert alvo["admin_response"] == "Faça assim."


def test_weekly_da_root_nao_aparece_para_usuario_real(ctx):
    """Nada criado na conta de teste pode chegar a quem usa o sistema."""
    c = ctx["c"]
    manual = {"slides": [{"id": "s0", "kind": "cover", "elements": [
        {"id": "t", "type": "text", "x": 0.1, "y": 0.3, "w": 0.8, "h": 0.15,
         "text": "Teste do admin", "font_size": 40}]}]}
    aid = c.post("/api/activities", headers=H(ctx["root"]),
                 json={"title": "ativ do admin", "include_in_weekly": True}).json()["id"]
    gerado = c.post("/api/weekly/generate", headers=H(ctx["root"]),
                    json={"activity_ids": [aid], "week_number": 31, "year": 2026,
                          "layout": manual, "layout_source": "manual"})
    assert gerado.status_code == 200
    rid = gerado.json()["id"]

    root_id = c.get("/api/users/profile", headers=H(ctx["root"])).json()["id"]
    # Colega do mesmo setor da root (CSI) e cargo de gestão não bastam.
    gestor = _register_login(c, "gestor_csi@qwitest.com", "GCSI", sector="CSI")
    for token in (ctx["ua"], gestor):
        assert c.get(f"/api/weekly/{rid}", headers=H(token)).status_code == 403
        assert c.get(f"/api/weekly/{rid}/download", headers=H(token)).status_code == 403
        assert c.get(f"/api/weekly/user/{root_id}", headers=H(token)).status_code == 403

    # A própria root continua com acesso ao que criou.
    assert c.get(f"/api/weekly/{rid}", headers=H(ctx["root"])).status_code == 200


def test_root_nao_pode_ser_escolhida_para_compartilhar(ctx):
    """Listar a root numa tela de compartilhamento exporia a conta de teste."""
    c = ctx["c"]
    r = c.post("/api/users/me/access-grants", headers=H(ctx["ua"]),
               json={"employee_id": "ROOT"})
    assert r.status_code == 400


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


def test_resumo_do_gestor_ignora_a_conta_root(ctx):
    """O gestor lê o resumo como trabalho da equipe — teste do admin não entra.

    Exercita o coletor direto: é ele que monta o dossiê que vai ao LLM, e é
    onde a conta root entrava por ter setor e estar ativa como qualquer um.
    """
    from app.api.routes.ai_features import _collect_sector_week
    from app.models import QualitySector

    c = ctx["c"]
    membro = _register_login(c, "csi_membro@qwitest.com", "CSIM", sector="CSI")
    c.post("/api/activities", headers=H(membro),
           json={"title": "Atividade real da equipe", "include_in_weekly": True})
    c.post("/api/activities", headers=H(ctx["root"]),
           json={"title": "Atividade de teste do admin", "include_in_weekly": True})

    from app.services.business import get_week_info
    semana, ano = get_week_info()

    db = _TestSession()
    try:
        usuarios, dossie = _collect_sector_week(db, QualitySector.CSI, ano, semana)
    finally:
        db.close()

    assert all(u.is_admin is False for u in usuarios)
    assert all(entrada["name"] != "Administrador" for entrada in dossie)
    titulos = [a["title"] for entrada in dossie for a in entrada["activities"]]
    assert "Atividade de teste do admin" not in titulos
    assert "Atividade real da equipe" in titulos
