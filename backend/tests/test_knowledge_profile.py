"""Perfil de conhecimento do usuário (o que a IA aprende + card + ignorar)."""
import tempfile
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import User, UserRole, QualitySector, WritingProfile
from app.services import knowledge_profile as kp


@pytest.fixture()
def db():
    tmp = tempfile.mkdtemp(prefix="qwi_kp_")
    engine = create_engine(f"sqlite:///{tmp}/kp.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    u = User(id="u1", email="k@qwitest.com", employee_id="K1",
             hashed_password="x", name="K", role=UserRole.ANALISTA_JR,
             sector=QualitySector.OQC)
    session.add(u)
    session.add(WritingProfile(user_id="u1", about_me="Acompanho FPY e scrap na linha 3."))
    session.commit()
    yield session
    session.close()


def _activity(kpis, line=None, process=None):
    meta = SimpleNamespace(related_kpis=kpis, line=line, supplier=None,
                           process=process, product=None, defect_type=None)
    return SimpleNamespace(metadata_entry=meta, attachments=[])


def test_learns_kpis_and_entities(db):
    acts = [
        _activity(["FPY", "PPM"], line="Linha 3", process="Solda"),
        _activity(["FPY"], line="Linha 3"),
    ]
    kp.learn_from_activities(db, "u1", acts)
    db.commit()
    card = kp.build_card(db, "u1", about_me="Acompanho FPY e scrap na linha 3.", personal_prompt="")
    assert "FPY" in card["learned"]["kpis"]
    assert "PPM" in card["learned"]["kpis"]
    assert "Linha 3" in card["learned"]["entities"].get("line", [])
    assert card["sample_count"] == 1
    # declarado presente (precedência é combinada no contexto)
    assert "FPY" in card["declared"]["about_me"]


def test_ignore_removes_learned_item(db):
    kp.learn_from_activities(db, "u1", [_activity(["FPY", "OEE"])])
    db.commit()
    assert "OEE" in kp.build_card(db, "u1", "", "")["learned"]["kpis"]
    kp.ignore_item(db, "u1", "kpi", "OEE")
    assert "OEE" not in kp.build_card(db, "u1", "", "")["learned"]["kpis"]
    assert "FPY" in kp.build_card(db, "u1", "", "")["learned"]["kpis"]


def test_context_combines_declared_and_learned(db):
    kp.learn_from_activities(db, "u1", [_activity(["FPY"], line="Linha 3")])
    db.commit()
    ctx = kp.knowledge_context(db, "u1", about_me="Acompanho FPY e scrap na linha 3.")
    assert "informou sobre si" in ctx.lower() or "FPY" in ctx
    assert "FPY" in ctx


def test_no_metadata_is_safe(db):
    # atividade sem metadata_entry não quebra nem cria ruído
    kp.learn_from_activities(db, "u1", [SimpleNamespace(metadata_entry=None, attachments=[])])
    db.commit()
    card = kp.build_card(db, "u1", "", "")
    assert card["learned"]["kpis"] == []
