"""Perfil de conhecimento do usuário — o que a IA APRENDE sobre ele.

Alimentado de forma determinística (sem LLM) a cada weekly gerado, a partir dos
metadados que o sistema já extrai das atividades: KPIs acompanhados
(`related_kpis`) e entidades recorrentes (linha, fornecedor, processo, produto,
tipo de defeito). Com decaimento temporal (semanas recentes pesam mais).

O que o usuário DECLARA (WritingProfile.about_me) tem precedência sobre isto e é
combinado na hora de montar o card / o contexto do Revisor. Itens que o usuário
descarta no card entram em `ignored` e não voltam.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import UserKnowledgeProfile

logger = logging.getLogger(__name__)

ALPHA = 0.35  # peso da semana nova (decaimento das anteriores)
ENTITY_FIELDS = ("line", "supplier", "process", "product", "defect_type")
TOP_KPIS = 12
TOP_ENTITIES = 8


def _extract(activities) -> tuple[Counter, dict[str, Counter]]:
    """KPIs e entidades observados nesta leva de atividades."""
    kpis: Counter = Counter()
    entities: dict[str, Counter] = {f: Counter() for f in ENTITY_FIELDS}
    for act in activities:
        meta = getattr(act, "metadata_entry", None)
        if not meta:
            continue
        for kpi in (meta.related_kpis or []):
            name = str(kpi).strip()
            if name:
                kpis[name] += 1
        for field in ENTITY_FIELDS:
            value = getattr(meta, field, None)
            if value and str(value).strip():
                entities[field][str(value).strip()] += 1
    return kpis, entities


def _merge(old: dict, new: Counter, alpha: float, cap: int) -> dict:
    """EMA: decai o antigo, soma o novo normalizado. Poda para não crescer."""
    merged = {k: round(v * (1 - alpha), 3) for k, v in (old or {}).items()}
    total = sum(new.values()) or 1
    for key, value in new.items():
        merged[key] = round(merged.get(key, 0.0) + alpha * value / total * 10, 3)
    return dict(sorted(merged.items(), key=lambda kv: -kv[1])[:cap])


def learn_from_activities(db: Session, user_id: str, activities) -> None:
    """Atualiza o perfil de conhecimento com as atividades de um weekly.

    Nunca derruba a geração: qualquer erro é só logado.
    """
    try:
        kpis, entities = _extract(activities)
        if not kpis and not any(entities.values()):
            return  # nada aprendível ainda (metadados não extraídos)

        row = (
            db.query(UserKnowledgeProfile)
            .filter(UserKnowledgeProfile.user_id == user_id)
            .first()
        )
        if row is None:
            row = UserKnowledgeProfile(user_id=user_id, knowledge={}, ignored={}, sample_count=0)
            db.add(row)

        knowledge = dict(row.knowledge or {})
        knowledge["kpis"] = _merge(knowledge.get("kpis", {}), kpis, ALPHA, TOP_KPIS)
        ent_out = dict(knowledge.get("entities", {}))
        for field in ENTITY_FIELDS:
            ent_out[field] = _merge(ent_out.get(field, {}), entities[field], ALPHA, TOP_ENTITIES)
        knowledge["entities"] = ent_out

        row.knowledge = knowledge
        row.sample_count = (row.sample_count or 0) + 1
        row.updated_at = datetime.now(UTC)
        logger.info("Conhecimento aprendido | user=%s | amostras=%d", user_id, row.sample_count)
    except Exception as error:
        logger.warning("Falha ao aprender perfil de conhecimento | user=%s | %s", user_id, error)


# ─────────────────────────── card / contexto ────────────────────────────────

def build_card(db: Session, user_id: str, about_me: str, personal_prompt: str) -> dict:
    """Dados do card "O que a IA sabe sobre você": declarado vs aprendido."""
    row = (
        db.query(UserKnowledgeProfile)
        .filter(UserKnowledgeProfile.user_id == user_id)
        .first()
    )
    knowledge = (row.knowledge if row else None) or {}
    ignored = (row.ignored if row else None) or {}
    ignored_kpis = set(ignored.get("kpis", []))
    ignored_ent = ignored.get("entities", {})

    learned_kpis = [
        k for k in sorted(knowledge.get("kpis", {}), key=lambda k: -knowledge["kpis"][k])
        if k not in ignored_kpis
    ]
    learned_entities: dict[str, list[str]] = {}
    for field, values in (knowledge.get("entities", {}) or {}).items():
        skip = set(ignored_ent.get(field, []))
        items = [v for v in sorted(values, key=lambda v: -values[v]) if v not in skip]
        if items:
            learned_entities[field] = items

    return {
        "declared": {
            "about_me": about_me or "",
            "personal_prompt": personal_prompt or "",
        },
        "learned": {
            "kpis": learned_kpis,
            "entities": learned_entities,
        },
        "sample_count": row.sample_count if row else 0,
    }


def ignore_item(db: Session, user_id: str, kind: str, value: str, entity_field: str | None = None) -> None:
    """Usuário descarta um item aprendido ('na verdade não acompanho isso')."""
    row = (
        db.query(UserKnowledgeProfile)
        .filter(UserKnowledgeProfile.user_id == user_id)
        .first()
    )
    if row is None:
        row = UserKnowledgeProfile(user_id=user_id, knowledge={}, ignored={}, sample_count=0)
        db.add(row)
    ignored = dict(row.ignored or {})
    if kind == "kpi":
        kpis = list(ignored.get("kpis", []))
        if value not in kpis:
            kpis.append(value)
        ignored["kpis"] = kpis
    elif kind == "entity" and entity_field:
        ent = dict(ignored.get("entities", {}))
        vals = list(ent.get(entity_field, []))
        if value not in vals:
            vals.append(value)
        ent[entity_field] = vals
        ignored["entities"] = ent
    row.ignored = ignored
    row.updated_at = datetime.now(UTC)
    db.commit()


def knowledge_context(db: Session, user_id: str, about_me: str) -> str:
    """Bloco de contexto do usuário para o prompt do Revisor (Fase 2).

    Combina o declarado (precedência) com o aprendido, em texto curto.
    """
    card = build_card(db, user_id, about_me, "")
    parts: list[str] = []
    if card["declared"]["about_me"].strip():
        parts.append("O usuário informou sobre si: " + card["declared"]["about_me"].strip())
    kpis = card["learned"]["kpis"]
    if kpis:
        parts.append("KPIs que costuma acompanhar: " + ", ".join(kpis[:10]) + ".")
    ent = card["learned"]["entities"]
    flat = [v for values in ent.values() for v in values[:4]]
    if flat:
        parts.append("Contexto recorrente: " + ", ".join(flat[:12]) + ".")
    return "\n".join(parts)
