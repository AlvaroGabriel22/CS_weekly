"""Recursos de IA do QWI — opcionais, o usuário usa se quiser.

1. Copiloto do gestor  — POST/GET /ai/department-rollup
   Sintetiza os weeklys + atividades de um setor numa visão executiva da
   semana. Restrito à gestão (MANAGEMENT_ROLES). Cacheado por setor+semana.

2. Deck em um clique   — POST /ai/deck-draft
   Gera um DeckLayout completo (contrato do editor WYSIWYG) a partir das
   atividades da semana, anexos, elementos fixados e histórico de decks.
   SEMPRE devolve um deck utilizável: se o LLM falhar ou responder fora do
   contrato, cai numa montagem determinística (source="fallback").

Ambos passam pelo provedor global de LLM (Ollama local por padrão; API
OpenAI-compatível via .env, com fila de N req/min e fallback automático).
"""

import base64
import json
import logging
import time as time_mod
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.dates import get_week_boundaries
from app.models import (
    Activity,
    DepartmentRollup,
    MANAGEMENT_ROLES,
    QualitySector,
    SlideLayoutPref,
    User,
    UserStyleProfile,
    WeeklyReport,
    WeeklyStatus,
)
from app.services.llm_service import LLMService, QUALITY_DEPT_CONTEXT
from app.services.style_learning import (
    apply_profile_style,
    compact_layout,
    style_rules_text,
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/ai", tags=["AI"])

BRAND = "#0C379C"
DARK = "#1F2937"
GRAY = "#6B7280"

# Espelho de FONT_FAMILIES do frontend (slideLayout.ts) — manter em sincronia.
ALLOWED_FONTS = {
    "Calibri", "Arial", "Verdana", "Tahoma",
    "Trebuchet MS", "Georgia", "Times New Roman", "Courier New",
}


# ── util ─────────────────────────────────────────────────────────────────────

def _parse_json_object(raw: str) -> dict | None:
    """Extrai o primeiro objeto JSON da resposta (tolerante a cercas/prosa)."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _str_list(value, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            text = item.get("text") or item.get("value") or ""
            if str(text).strip():
                out.append(str(text).strip())
        if len(out) >= limit:
            break
    return out


def _layout_texts(layout: dict | None) -> list[str]:
    """Textos visíveis de um DeckLayout salvo (para resumir weeklys prontos)."""
    if not isinstance(layout, dict):
        return []
    texts: list[str] = []
    for slide in layout.get("slides", []):
        if not isinstance(slide, dict):
            continue
        for el in slide.get("elements", []):
            if isinstance(el, dict) and el.get("type") == "text" and el.get("text"):
                texts.append(str(el["text"]))
    return texts


def _require_management(user: User) -> None:
    if not (user.is_admin or user.role in MANAGEMENT_ROLES):
        raise HTTPException(403, detail="Recurso disponível apenas para a gestão.")


# ═════════════════════════════════ 1. COPILOTO DO GESTOR ════════════════════

ROLLUP_SYSTEM = (
    f"{QUALITY_DEPT_CONTEXT} "
    "Você é o copiloto de um gestor da Qualidade. Escreva em português do "
    "Brasil, tom executivo, frases curtas e factuais — apenas com base nos "
    "dados fornecidos, sem inventar números. Responda APENAS com JSON no "
    "formato: {\"summary\": \"parágrafo executivo\", \"highlights\": [\"...\"], "
    "\"kpis\": [\"...\"], \"risks\": [\"...\"], "
    "\"by_person\": [{\"name\": \"...\", \"headline\": \"1 frase sobre a semana da pessoa\"}], "
    "\"next_steps\": [\"...\"]}"
)


class RollupRequest(BaseModel):
    sector: str
    year: int = Field(ge=2020, le=2100)
    week_number: int = Field(ge=1, le=53)
    force: bool = False


def _sector_or_400(sector: str) -> QualitySector:
    try:
        return QualitySector(sector)
    except ValueError:
        raise HTTPException(400, detail="Setor inválido.")


def _collect_sector_week(db: Session, sector: QualitySector, year: int, week: int):
    """Pessoas do setor + weekly/atividades da semana de cada uma."""
    users = (
        db.query(User)
        .filter(User.sector == sector, User.is_active.is_(True))
        .order_by(User.name)
        .all()
    )
    dossier = []
    for person in users:
        report = (
            db.query(WeeklyReport)
            .filter(
                WeeklyReport.user_id == person.id,
                WeeklyReport.year == year,
                WeeklyReport.week_number == week,
                WeeklyReport.status == WeeklyStatus.COMPLETED,
            )
            .order_by(WeeklyReport.version.desc())
            .first()
        )
        activities = (
            db.query(Activity)
            .options(joinedload(Activity.attachments))
            .filter(
                Activity.user_id == person.id,
                Activity.year == year,
                Activity.week_number == week,
            )
            .all()
        )
        entry = {
            "name": person.name,
            "role": person.role.value,
            "has_weekly": report is not None,
            "weekly_texts": _layout_texts((report.content or {}).get("layout")) if report else [],
            "weekly_summary": (report.ai_summary or "")[:500] if report else "",
            "activities": [
                {
                    "title": a.title,
                    "description": (a.description or "")[:300],
                    "status": a.status.value,
                    "tables": [
                        {
                            "columns": att.kpi_data["table"]["columns"],
                            "rows": att.kpi_data["table"]["rows"][:10],
                        }
                        for att in a.attachments
                        if isinstance(att.kpi_data, dict) and att.kpi_data.get("table")
                    ],
                }
                for a in activities
            ],
        }
        dossier.append(entry)
    return users, dossier


def _sanitize_rollup(data: dict | None, users: list[User], dossier: list[dict]) -> dict:
    """Normaliza a resposta do LLM; by_person é reconciliado com a lista REAL."""
    data = data or {}
    headline_by_name: dict[str, str] = {}
    for item in data.get("by_person") or []:
        if isinstance(item, dict) and item.get("name"):
            headline_by_name[str(item["name"]).strip().lower()] = str(
                item.get("headline") or ""
            ).strip()

    has_weekly = {d["name"]: d["has_weekly"] for d in dossier}
    n_acts = {d["name"]: len(d["activities"]) for d in dossier}
    by_person = []
    for person in users:
        headline = headline_by_name.get(person.name.strip().lower(), "")
        if not headline:
            headline = (
                f"{n_acts.get(person.name, 0)} atividades registradas"
                if n_acts.get(person.name)
                else "Sem registros na semana"
            )
        by_person.append({
            "name": person.name,
            "role": person.role.value,
            "has_weekly": bool(has_weekly.get(person.name)),
            "headline": headline[:200],
        })

    summary = str(data.get("summary") or "").strip()
    return {
        "summary": summary[:2000],
        "highlights": _str_list(data.get("highlights")),
        "kpis": _str_list(data.get("kpis")),
        "risks": _str_list(data.get("risks")),
        "by_person": by_person,
        "next_steps": _str_list(data.get("next_steps")),
    }


@router.get("/department-rollup")
def get_department_rollup(
    sector: str = Query(...),
    year: int = Query(...),
    week_number: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_management(current_user)
    sector_enum = _sector_or_400(sector)
    cached = (
        db.query(DepartmentRollup)
        .filter(
            DepartmentRollup.sector == sector_enum.value,
            DepartmentRollup.year == year,
            DepartmentRollup.week_number == week_number,
        )
        .first()
    )
    if not cached:
        return {"content": None}
    return {
        "content": cached.content,
        "model": cached.model,
        "generated_at": cached.generated_at.isoformat(),
    }


@router.post("/department-rollup")
async def generate_department_rollup(
    data: RollupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_management(current_user)
    sector_enum = _sector_or_400(data.sector)

    existing = (
        db.query(DepartmentRollup)
        .filter(
            DepartmentRollup.sector == sector_enum.value,
            DepartmentRollup.year == data.year,
            DepartmentRollup.week_number == data.week_number,
        )
        .first()
    )
    if existing and not data.force:
        return {
            "content": existing.content,
            "model": existing.model,
            "generated_at": existing.generated_at.isoformat(),
            "cached": True,
        }

    users, dossier = _collect_sector_week(db, sector_enum, data.year, data.week_number)
    if not users:
        raise HTTPException(404, detail="Nenhuma pessoa ativa neste setor.")

    monday, sunday = get_week_boundaries(data.year, data.week_number)
    prompt = (
        f"Semana W{data.week_number}/{data.year} "
        f"({monday.strftime('%d/%m')}–{sunday.strftime('%d/%m')}), "
        f"setor {sector_enum.value}. Gere o resumo executivo do departamento a "
        f"partir do dossiê:\n{json.dumps(dossier, ensure_ascii=False)}"
    )

    service = LLMService()
    started = time_mod.monotonic()
    parsed: dict | None = None
    model_name = None
    try:
        response = await service.generate(prompt, ROLLUP_SYSTEM, json_mode=True)
        model_name = response.model
        parsed = _parse_json_object(response.content)
        if parsed is None:  # segunda tentativa resolve a maioria dos desvios
            retry = await service.generate(prompt, ROLLUP_SYSTEM, json_mode=True)
            parsed = _parse_json_object(retry.content)
    except Exception as error:
        logger.warning("Rollup: LLM falhou | %s", error)

    if parsed is None:
        raise HTTPException(503, detail="IA indisponível no momento. Tente novamente.")

    content = _sanitize_rollup(parsed, users, dossier)
    duration_ms = int((time_mod.monotonic() - started) * 1000)

    if existing:
        existing.content = content
        existing.model = model_name
        existing.generated_by = current_user.id
        existing.generated_at = datetime.now(UTC)
    else:
        db.add(DepartmentRollup(
            sector=sector_enum.value,
            year=data.year,
            week_number=data.week_number,
            content=content,
            model=model_name,
            generated_by=current_user.id,
        ))
    db.commit()
    logger.info(
        "Rollup gerado | sector=%s W%d/%d | %dms", sector_enum.value,
        data.week_number, data.year, duration_ms,
    )
    return {"content": content, "model": model_name, "duration_ms": duration_ms, "cached": False}


# ═════════════════════════════════ 2. DECK EM UM CLIQUE ═════════════════════

DECK_SYSTEM = (
    f"{QUALITY_DEPT_CONTEXT} "
    "Você é um designer de apresentações executivas. Monte um deck 16:9 "
    "seguindo EXATAMENTE este contrato JSON:\n"
    '{"slides": [{"id": "s1", "kind": "cover"|"custom", "elements": [\n'
    '  {"id": "e1", "type": "text", "x": 0.06, "y": 0.1, "w": 0.5, "h": 0.1,\n'
    '   "text": "...", "font_size": 24, "bold": true, "align": "left", "color": "#0C379C"},\n'
    '  {"id": "e2", "type": "table", "attachment_id": "<id fornecido>", "x": .., "y": .., "w": .., "h": .., "font_size": 11},\n'
    '  {"id": "e3", "type": "image", "attachment_id": "<id fornecido>", "x": .., "y": .., "w": .., "h": ..}\n'
    "]}]}\n"
    "Regras: coordenadas são frações 0–1 da página; elementos NÃO podem se "
    "sobrepor; use SOMENTE attachment_ids fornecidos no dossiê; primeiro slide "
    "é a capa (kind=cover) com o título e o subtítulo dados; um slide por "
    "atividade (título 24pt bold na cor #0C379C no topo, descrição 14pt, "
    "tabelas/imagens ao lado ou abaixo); máximo 10 slides; textos em português. "
    "Responda APENAS com o JSON."
)


class DeckDraftRequest(BaseModel):
    year: int = Field(ge=2020, le=2100)
    week_number: int = Field(ge=1, le=53)
    activity_ids: list[str] = Field(min_length=1, max_length=100)
    # Weekly do histórico para usar como modelo NESTA geração. None = usa o
    # template ativo do usuário; use_template=False = gerar sem modelo.
    template_report_id: str | None = None
    # PPT enviado pelo usuário (aba Templates) usado como modelo NESTA geração.
    # Tem prioridade sobre template_report_id quando informado.
    template_pptx_id: str | None = None
    use_template: bool = True


def _deck_labels(user: User, year: int, week: int) -> tuple[str, str]:
    monday, sunday = get_week_boundaries(year, week)
    return (
        f"Weekly W{week}",
        f"{monday.strftime('%d/%m')} – {sunday.strftime('%d/%m/%Y')} · {user.name}",
    )


def _text_el(eid, x, y, w, h, text, size=14, bold=False, color=DARK, align="left"):
    return {
        "id": eid, "type": "text", "x": x, "y": y, "w": w, "h": h,
        "text": text, "font_size": size, "bold": bold, "align": align, "color": color,
    }


def _deterministic_deck(
    activities: list[Activity], title: str, subtitle: str, pinned: list[dict]
) -> dict:
    """Montagem sem IA — garante que o botão SEMPRE entrega um deck editável."""
    slides = [{
        "id": "s-cover", "kind": "cover",
        "elements": [
            _text_el("c-title", 0.06, 0.32, 0.88, 0.16, title, 40, True, BRAND),
            _text_el("c-sub", 0.06, 0.5, 0.88, 0.08, subtitle, 18, False, GRAY),
            *[{**p, "id": f"pin-{i}"} for i, p in enumerate(pinned) if p.get("pinned")],
        ],
    }]
    for idx, activity in enumerate(activities):
        tables = [a for a in activity.attachments if isinstance(a.kpi_data, dict) and a.kpi_data.get("table")]
        images = [
            a for a in activity.attachments
            if a.file_type == "image" or (a.mime_type or "").startswith("image/")
        ]
        elements = [
            _text_el(f"a{idx}-t", 0.06, 0.06, 0.88, 0.11, activity.title, 24, True, BRAND),
        ]
        body_w = 0.5 if (tables or images) else 0.88
        if activity.description:
            elements.append(_text_el(f"a{idx}-d", 0.06, 0.2, body_w, 0.65, activity.description, 14))
        if tables:
            elements.append({
                "id": f"a{idx}-tbl", "type": "table",
                "attachment_id": tables[0].id,
                "x": 0.6 if activity.description else 0.06, "y": 0.2,
                "w": 0.34 if activity.description else 0.6, "h": 0.35,
                "font_size": 11, "color": BRAND,
            })
        for j, image in enumerate(images[:2]):
            elements.append({
                "id": f"a{idx}-img{j}", "type": "image", "attachment_id": image.id,
                "x": 0.6, "y": 0.2 + (0.37 if tables else 0.0) + j * 0.37,
                "w": 0.34, "h": 0.33, "font_size": 14,
            })
        slides.append({"id": f"s-a{idx}", "kind": "custom", "elements": elements})
    return {"slides": slides}


def _template_deck(
    template: dict,
    activities: list[Activity],
    title: str,
    subtitle: str,
) -> dict:
    """Deck determinístico que CLONA a estrutura do weekly-modelo do usuário.

    Capa: a do template, com título/subtítulo da semana atual. Conteúdo: o
    primeiro slide de conteúdo do template vira molde — cada atividade nova é
    encaixada nele (título no lugar do título, descrição no maior bloco de
    texto, tabela/imagem nos mesmos retângulos). Formas e textos decorativos
    são mantidos como estão. Não depende do LLM: fidelidade garantida.
    """
    import copy

    t_slides = template.get("slides") or []
    cover_src = next((s for s in t_slides if s.get("kind") == "cover"), None)
    molds = [s for s in t_slides if s.get("kind") != "cover" and s.get("elements")]

    def texts_by_size(slide: dict) -> list[dict]:
        return sorted(
            [e for e in slide.get("elements", []) if e.get("type") == "text"],
            key=lambda e: -(e.get("font_size") or 0),
        )

    slides: list[dict] = []
    # capa do template com os rótulos da semana nova
    if cover_src:
        cover = copy.deepcopy(cover_src)
        cover["id"] = "s-cover"
        ordered = texts_by_size(cover)
        if ordered:
            ordered[0]["text"] = title
        if len(ordered) > 1:
            ordered[1]["text"] = subtitle
        for i, el in enumerate(cover.get("elements", [])):
            el["id"] = f"c-{i}"
        slides.append(cover)
    else:
        slides.append({
            "id": "s-cover", "kind": "cover",
            "elements": [
                _text_el("c-title", 0.06, 0.32, 0.88, 0.16, title, 40, True, BRAND),
                _text_el("c-sub", 0.06, 0.5, 0.88, 0.08, subtitle, 18, False, GRAY),
            ],
        })

    if not molds:
        base = _deterministic_deck(activities, title, subtitle, [])
        slides.extend(base["slides"][1:])
        return {"slides": slides}

    for idx, activity in enumerate(activities):
        mold = copy.deepcopy(molds[min(idx, len(molds) - 1)])
        mold["id"] = f"s-a{idx}"
        mold["kind"] = "custom"
        tables = [a for a in activity.attachments
                  if isinstance(a.kpi_data, dict) and a.kpi_data.get("table")]
        images = [a for a in activity.attachments
                  if a.file_type == "image" or (a.mime_type or "").startswith("image/")]

        ordered = texts_by_size(mold)
        if ordered:
            ordered[0]["text"] = activity.title
        if len(ordered) > 1 and activity.description:
            # maior bloco (área) entre os não-título recebe a descrição
            body = max(ordered[1:], key=lambda e: (e.get("w") or 0) * (e.get("h") or 0))
            body["text"] = activity.description

        kept = []
        for i, el in enumerate(mold.get("elements", [])):
            el["id"] = f"a{idx}-{i}"
            el.pop("pinned", None)
            if el.get("type") == "table":
                if tables:
                    el["attachment_id"] = tables.pop(0).id
                else:
                    continue  # atividade sem tabela: remove o slot
            elif el.get("type") == "image":
                if images:
                    el["attachment_id"] = images.pop(0).id
                else:
                    continue
            kept.append(el)
        mold["elements"] = kept
        slides.append(mold)

    return {"slides": slides}


def _sanitize_deck(
    data: dict | None,
    allowed_attachments: dict[str, str],
    title: str,
    subtitle: str,
) -> dict | None:
    """Valida/normaliza o layout do LLM. None = irrecuperável (usar fallback)."""
    if not isinstance(data, dict):
        return None
    raw_slides = data.get("slides")
    if not isinstance(raw_slides, list) or not raw_slides:
        return None

    slides = []
    seen_ids: set[str] = set()
    for s_idx, slide in enumerate(raw_slides[:12]):
        if not isinstance(slide, dict):
            continue
        elements = []
        for e_idx, el in enumerate((slide.get("elements") or [])[:25]):
            if not isinstance(el, dict):
                continue
            etype = el.get("type")
            if etype not in {"text", "image", "table", "shape"}:
                continue
            if etype in {"image", "table"}:
                att_id = str(el.get("attachment_id") or "")
                if att_id not in allowed_attachments:
                    continue
                if etype == "table" and allowed_attachments[att_id] != "table":
                    continue
                if etype == "image" and allowed_attachments[att_id] != "image":
                    continue
            if etype == "text" and not str(el.get("text") or "").strip():
                continue

            def num(key, default, lo=0.0, hi=1.0):
                try:
                    return min(max(float(el.get(key, default)), lo), hi)
                except (TypeError, ValueError):
                    return default

            x = num("x", 0.06)
            y = num("y", 0.1)
            w = num("w", 0.4, 0.02)
            h = num("h", 0.1, 0.02)
            w = min(w, 1.0 - x)
            h = min(h, 1.0 - y)
            eid = str(el.get("id") or f"el-{s_idx}-{e_idx}")
            while eid in seen_ids:
                eid += "x"
            seen_ids.add(eid)
            clean = {
                "id": eid, "type": etype, "x": round(x, 4), "y": round(y, 4),
                "w": round(w, 4), "h": round(h, 4),
                "font_size": min(max(int(el.get("font_size") or 14), 8), 60),
            }
            if etype == "text":
                clean["text"] = str(el.get("text"))[:2000]
                clean["bold"] = bool(el.get("bold"))
                clean["italic"] = bool(el.get("italic"))
                if el.get("font_family") in ALLOWED_FONTS:
                    clean["font_family"] = el["font_family"]
                if el.get("align") in {"left", "center", "right"}:
                    clean["align"] = el["align"]
                color = str(el.get("color") or DARK)
                clean["color"] = color if color.startswith("#") and len(color) == 7 else DARK
            if etype in {"image", "table"}:
                clean["attachment_id"] = str(el["attachment_id"])
                if etype == "table":
                    clean["color"] = BRAND
            if etype == "shape":
                if el.get("shape") not in {"rect", "line", "ellipse"}:
                    continue
                clean["shape"] = el["shape"]
                clean["color"] = str(el.get("color") or BRAND)
                clean["fill"] = el.get("fill") if isinstance(el.get("fill"), str) else None
                clean["stroke_width"] = min(max(int(el.get("stroke_width") or 2), 1), 12)
            elements.append(clean)
        if elements:
            slides.append({
                "id": str(slide.get("id") or f"s-{s_idx}"),
                "kind": "cover" if slide.get("kind") == "cover" else "custom",
                "elements": elements,
            })

    if not slides:
        return None
    # capa garantida: se o LLM não fez, injeta uma padrão na frente
    if slides[0]["kind"] != "cover":
        slides.insert(0, {
            "id": "s-cover", "kind": "cover",
            "elements": [
                _text_el("c-title", 0.06, 0.32, 0.88, 0.16, title, 40, True, BRAND),
                _text_el("c-sub", 0.06, 0.5, 0.88, 0.08, subtitle, 18, False, GRAY),
            ],
        })
    return {"slides": slides}


def _collect_deck_images(activities: list[Activity], limit: int = 4) -> list[str]:
    """Imagens (base64) para o modelo multimodal — só quando a API externa
    está ativa; o gemma local não usa visão aqui."""
    if settings.LLM_PROVIDER != "openai_compat":
        return []
    images: list[str] = []
    for activity in activities:
        for att in activity.attachments:
            is_image = att.file_type == "image" or (att.mime_type or "").startswith("image/")
            if not is_image:
                continue
            path = Path(att.file_path)
            if path.exists() and path.stat().st_size < 4_000_000:
                images.append(base64.b64encode(path.read_bytes()).decode())
            if len(images) >= limit:
                return images
    return images


@router.post("/deck-draft")
async def generate_deck_draft(
    data: DeckDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    activities = (
        db.query(Activity)
        .options(joinedload(Activity.attachments))
        .filter(Activity.id.in_(data.activity_ids), Activity.user_id == current_user.id)
        .all()
    )
    if not activities:
        raise HTTPException(400, detail="Nenhuma atividade válida selecionada.")
    activities.sort(key=lambda a: a.activity_date or datetime.min)

    title, subtitle = _deck_labels(current_user, data.year, data.week_number)

    pref = db.query(SlideLayoutPref).filter(SlideLayoutPref.user_id == current_user.id).first()
    pinned = (pref.layout or {}).get("pinned", []) if pref else []

    # dicionário de anexos permitidos: id → tipo ("table"/"image")
    allowed: dict[str, str] = {}
    dossier = []
    for activity in activities:
        atts = []
        for att in activity.attachments:
            if isinstance(att.kpi_data, dict) and att.kpi_data.get("table"):
                allowed[att.id] = "table"
                table = att.kpi_data["table"]
                atts.append({
                    "attachment_id": att.id, "kind": "table",
                    "columns": table["columns"], "sample_rows": table["rows"][:5],
                })
            elif att.file_type == "image" or (att.mime_type or "").startswith("image/"):
                allowed[att.id] = "image"
                atts.append({
                    "attachment_id": att.id, "kind": "image",
                    "caption": att.ai_caption or att.manual_caption or att.original_filename,
                })
        dossier.append({
            "title": activity.title,
            "description": (activity.description or "")[:500],
            "date": activity.activity_date.strftime("%d/%m") if activity.activity_date else "",
            "attachments": atts,
        })

    # ── padrão pessoal: template ativo + perfil de estilo aprendido ─────────
    profile_row = (
        db.query(UserStyleProfile)
        .filter(UserStyleProfile.user_id == current_user.id)
        .first()
    )
    profile = (profile_row.profile if profile_row else None) or {}
    sample_count = profile_row.sample_count if profile_row else 0

    template_layout: dict | None = None
    # PPT enviado pelo usuário → clonagem determinística (máxima fidelidade,
    # instantânea, sem depender do LLM interpretar o modelo).
    clone_only = False
    if data.use_template:
        if data.template_pptx_id:
            # Modelo é um PPT enviado pelo usuário (já convertido no upload).
            from app.models import PptxTemplate

            pptx_tpl = (
                db.query(PptxTemplate)
                .filter(
                    PptxTemplate.id == data.template_pptx_id,
                    PptxTemplate.user_id == current_user.id,
                )
                .first()
            )
            if pptx_tpl and isinstance(pptx_tpl.layout, dict) and pptx_tpl.layout.get("slides"):
                template_layout = pptx_tpl.layout
                clone_only = True
        if template_layout is None:
            template_id = data.template_report_id or (
                profile_row.template_report_id if profile_row else None
            )
            if template_id:
                template_report = (
                    db.query(WeeklyReport)
                    .filter(
                        WeeklyReport.id == template_id,
                        WeeklyReport.user_id == current_user.id,
                    )
                    .first()
                )
                candidate = ((template_report.content or {}).get("layout")
                             if template_report else None)
                if isinstance(candidate, dict) and candidate.get("slides"):
                    template_layout = candidate

    style_block = ""
    if template_layout:
        style_block = (
            "MODELO DO USUÁRIO — siga EXATAMENTE esta estrutura de slides "
            "(mesmas posições, fontes, cores e ordem de elementos), apenas "
            "substituindo os conteúdos pelos da semana atual:\n"
            f"{json.dumps(compact_layout(template_layout), ensure_ascii=False)}\n"
        )
    if profile:
        style_block += style_rules_text(profile) + "\n"

    prompt = (
        f"Capa: título \"{title}\", subtítulo \"{subtitle}\".\n"
        f"Dossiê da semana (uma entrada por atividade):\n"
        f"{json.dumps(dossier, ensure_ascii=False)}\n"
        + style_block
        + "Gere o deck agora."
    )

    service = LLMService()
    started = time_mod.monotonic()
    layout = None
    model_name = None
    # Modelo de PPT enviado: clona direto, sem chamar o LLM (fidelidade máxima).
    if not clone_only:
        try:
            images = _collect_deck_images(activities)
            response = await service.generate(
                prompt, DECK_SYSTEM, images=images or None, json_mode=True
            )
            model_name = response.model
            layout = _sanitize_deck(_parse_json_object(response.content), allowed, title, subtitle)
            if layout is None:
                retry = await service.generate(prompt, DECK_SYSTEM, json_mode=True)
                layout = _sanitize_deck(_parse_json_object(retry.content), allowed, title, subtitle)
        except Exception as error:
            logger.warning("Deck-draft: LLM falhou | %s", error)

    source = "ai"
    supplemented = 0
    if layout is None:
        if template_layout:
            layout = _template_deck(template_layout, activities, title, subtitle)
            source = "template"
        else:
            layout = _deterministic_deck(activities, title, subtitle, pinned)
            source = "fallback"
    else:
        # Modelos fracos às vezes entregam só a capa: completa com slides
        # determinísticos das atividades que a IA deixou de fora.
        covered_atts = {
            el.get("attachment_id")
            for s in layout["slides"]
            for el in s["elements"]
            if el.get("attachment_id")
        }
        covered_text = " ".join(
            str(el.get("text") or "").lower()
            for s in layout["slides"]
            if s["kind"] != "cover"
            for el in s["elements"]
        )
        missing = [
            a for a in activities
            if a.title.lower()[:40] not in covered_text
            and not any(att.id in covered_atts for att in a.attachments)
        ]
        if missing:
            extra = (
                _template_deck(template_layout, missing, title, subtitle)
                if template_layout
                else _deterministic_deck(missing, title, subtitle, [])
            )
            layout["slides"].extend(extra["slides"][1:])  # sem a capa duplicada
            supplemented = len(extra["slides"]) - 1

    if source == "ai":
        # O LLM às vezes monta o slide da atividade só com os anexos: garante
        # o título dela no topo do slide que contém seus attachments.
        att_owner = {att.id: a for a in activities for att in a.attachments}
        for slide in layout["slides"]:
            if slide["kind"] == "cover":
                continue
            has_text = any(el["type"] == "text" for el in slide["elements"])
            if has_text:
                continue
            owner = next(
                (att_owner[el["attachment_id"]] for el in slide["elements"]
                 if el.get("attachment_id") in att_owner),
                None,
            )
            if owner:
                top = min((el["y"] for el in slide["elements"]), default=1.0)
                slide["elements"].insert(0, _text_el(
                    f"{slide['id']}-title", 0.06, max(0.02, min(0.06, top - 0.12)),
                    0.88, 0.1, owner.title, 24, True, BRAND,
                ))

    # Garantia final do padrão pessoal: aplica fonte/tamanhos/cores do perfil
    # mesmo quando o LLM ignora as instruções de estilo.
    if source == "ai" and profile:
        layout = apply_profile_style(layout, profile, sample_count)

    duration_ms = int((time_mod.monotonic() - started) * 1000)
    logger.info(
        "Deck-draft | user=%s W%d/%d | source=%s | template=%s | perfil=%d amostras "
        "| %d slides (%d complementados) | %dms",
        current_user.id, data.week_number, data.year, source,
        bool(template_layout), sample_count,
        len(layout["slides"]), supplemented, duration_ms,
    )
    return {
        "layout": layout,
        "source": source,
        "model": model_name,
        "duration_ms": duration_ms,
        "supplemented_slides": supplemented,
        "used_template": bool(template_layout),
        "style_samples": sample_count,
    }


# ══════════════ 2b. PERFIL DE ESTILO + TEMPLATE DO "MONTAR COM IA" ══════════

def _style_response(row: UserStyleProfile | None, db: Session) -> dict:
    template = None
    if row and row.template_report_id:
        report = (
            db.query(WeeklyReport)
            .filter(WeeklyReport.id == row.template_report_id)
            .first()
        )
        if report:
            template = {
                "report_id": report.id,
                "week_number": report.week_number,
                "year": report.year,
                "version": report.version,
            }
    profile = (row.profile if row else None) or {}
    return {
        "sample_count": row.sample_count if row else 0,
        "template": template,
        "profile_summary": {
            "font": max(profile["fonts"], key=profile["fonts"].get)
            if profile.get("fonts") else None,
            "title_size": profile.get("title_size"),
            "body_size": profile.get("body_size"),
            "content_slides": profile.get("content_slides"),
        } if profile else None,
    }


@router.get("/style")
def get_style_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Estado do aprendizado do usuário: amostras, template ativo e resumo."""
    row = (
        db.query(UserStyleProfile)
        .filter(UserStyleProfile.user_id == current_user.id)
        .first()
    )
    return _style_response(row, db)


# ── "O que a IA sabe sobre você" (perfil de conhecimento) ────────────────────

@router.get("/knowledge")
def get_knowledge(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Card do perfil: o que o usuário DECLAROU vs. o que a IA APRENDEU."""
    from app.services.knowledge_profile import build_card

    wp = current_user.writing_profile
    return build_card(
        db, current_user.id,
        about_me=getattr(wp, "about_me", "") or "",
        personal_prompt=getattr(wp, "personal_prompt", "") or "",
    )


class IgnoreKnowledgeRequest(BaseModel):
    kind: str  # "kpi" | "entity"
    value: str
    entity_field: str | None = None


@router.post("/knowledge/ignore")
def ignore_knowledge(
    data: IgnoreKnowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Usuário descarta um item aprendido ('na verdade não acompanho isso')."""
    from app.services.knowledge_profile import build_card, ignore_item

    ignore_item(db, current_user.id, data.kind, data.value.strip(), data.entity_field)
    wp = current_user.writing_profile
    return build_card(
        db, current_user.id,
        about_me=getattr(wp, "about_me", "") or "",
        personal_prompt=getattr(wp, "personal_prompt", "") or "",
    )


# ── Revisor da semana (sugestões ancoradas no perfil do usuário) ─────────────

REVIEW_SYSTEM = (
    f"{QUALITY_DEPT_CONTEXT} "
    "Você é o assistente pessoal deste analista e CONHECE o trabalho dele "
    "(KPIs e padrões são dados abaixo). Revise as atividades da semana e "
    "aponte, nos termos DELE, apenas o que estiver ANCORADO nos dados "
    "apresentados. Categorias:\n"
    "- highlight: 1 a 3 resultados mais relevantes para destacar (com base nos "
    "KPIs dele).\n"
    "- gap: algo que costuma constar e está faltando (ex.: auditoria sem o KPI, "
    "NC sem plano de ação).\n"
    "- anomaly: um KPI fora da faixa típica dele.\n"
    "- inconsistency: número no texto que não bate com a tabela, contradição.\n"
    "REGRAS ABSOLUTAS: NÃO reescreva nem resuma o texto do usuário. NÃO invente "
    "KPIs, números ou fatos que não estejam nos dados. Seja específico e cite a "
    "atividade. No máximo 6 itens; se não houver nada notável, devolva poucos ou "
    "nenhum. Escreva em português, tom de colega que conhece o trabalho dele.\n"
    'Responda APENAS com JSON: {"suggestions": [{"type": "highlight|gap|anomaly|'
    'inconsistency", "message": "...", "activity_id": "<id ou vazio>"}]}'
)

_REVIEW_TYPES = {"highlight", "gap", "anomaly", "inconsistency"}


def _week_dossier(activities: list[Activity]) -> list[dict]:
    dossier = []
    for a in activities:
        meta = getattr(a, "metadata_entry", None)
        dossier.append({
            "activity_id": a.id,
            "title": a.title,
            "description": (a.description or "")[:400],
            "kpis": (meta.related_kpis or []) if meta else [],
            "line": (meta.line if meta else None),
            "tables": [
                {
                    "columns": att.kpi_data["table"]["columns"],
                    "rows": att.kpi_data["table"]["rows"][:8],
                }
                for att in a.attachments
                if isinstance(att.kpi_data, dict) and att.kpi_data.get("table")
            ],
        })
    return dossier


class ReviewRequest(BaseModel):
    year: int = Field(ge=2020, le=2100)
    week_number: int = Field(ge=1, le=53)
    activity_ids: list[str] = Field(min_length=1, max_length=100)


@router.post("/review")
async def review_week(
    data: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A IA revisa a semana e sugere destaques/lacunas/anomalias, ancorada no
    perfil do usuário. Não altera nada — é conselho. 503 se a IA estiver fora."""
    from app.services.knowledge_profile import knowledge_context

    activities = (
        db.query(Activity)
        .options(joinedload(Activity.attachments), joinedload(Activity.metadata_entry))
        .filter(Activity.id.in_(data.activity_ids), Activity.user_id == current_user.id)
        .all()
    )
    if not activities:
        raise HTTPException(400, detail="Nenhuma atividade válida selecionada.")

    valid_ids = {a.id for a in activities}
    wp = current_user.writing_profile
    context = knowledge_context(db, current_user.id, getattr(wp, "about_me", "") or "")

    prompt = (
        (f"Perfil do usuário:\n{context}\n\n" if context.strip() else "")
        + "Atividades da semana (uma por entrada):\n"
        + json.dumps(_week_dossier(activities), ensure_ascii=False)
        + "\nRevise agora."
    )

    service = LLMService()
    started = time_mod.monotonic()
    parsed = None
    model_name = None
    try:
        images = _collect_deck_images(activities)  # multimodal só no openai_compat
        response = await service.generate(
            prompt, REVIEW_SYSTEM, images=images or None, json_mode=True
        )
        model_name = response.model
        parsed = _parse_json_object(response.content)
        if parsed is None:
            retry = await service.generate(prompt, REVIEW_SYSTEM, json_mode=True)
            parsed = _parse_json_object(retry.content)
    except Exception as error:
        logger.warning("Review: LLM indisponível | %s", error)
        raise HTTPException(
            503,
            detail="A revisão por IA está indisponível agora. Tente novamente em instantes.",
        )

    suggestions = []
    for item in (parsed or {}).get("suggestions", [])[:8]:
        if not isinstance(item, dict):
            continue
        stype = str(item.get("type", "")).strip().lower()
        message = str(item.get("message", "")).strip()
        if stype not in _REVIEW_TYPES or not message:
            continue
        aid = str(item.get("activity_id") or "").strip()
        suggestions.append({
            "type": stype,
            "message": message[:600],
            "activity_id": aid if aid in valid_ids else None,
        })

    duration_ms = int((time_mod.monotonic() - started) * 1000)
    logger.info(
        "Review | user=%s W%d/%d | %d sugestões | %dms",
        current_user.id, data.week_number, data.year, len(suggestions), duration_ms,
    )
    return {"suggestions": suggestions, "model": model_name, "duration_ms": duration_ms}


class SetTemplateRequest(BaseModel):
    report_id: str | None = None  # None remove o modelo ativo


@router.put("/template")
def set_ai_template(
    data: SetTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Define (ou remove) o weekly do histórico usado como modelo da IA."""
    if data.report_id is not None:
        report = (
            db.query(WeeklyReport)
            .filter(
                WeeklyReport.id == data.report_id,
                WeeklyReport.user_id == current_user.id,
            )
            .first()
        )
        if report is None:
            raise HTTPException(404, detail="Weekly não encontrado.")
        layout = (report.content or {}).get("layout")
        if not (isinstance(layout, dict) and layout.get("slides")):
            raise HTTPException(
                400,
                detail={
                    "field": "report_id",
                    "message": "Este weekly não tem montagem salva.",
                    "hint": "Escolha um weekly montado no editor (com layout).",
                },
            )

    row = (
        db.query(UserStyleProfile)
        .filter(UserStyleProfile.user_id == current_user.id)
        .first()
    )
    if row is None:
        row = UserStyleProfile(user_id=current_user.id, profile={}, sample_count=0)
        db.add(row)
    row.template_report_id = data.report_id
    row.updated_at = datetime.now(UTC)
    db.commit()
    logger.info(
        "Template da IA %s | user=%s | report=%s",
        "definido" if data.report_id else "removido",
        current_user.id, data.report_id,
    )
    return _style_response(row, db)


# ═════════════════════════ 3. SUGESTÃO DE E-MAIL DO WEEKLY ══════════════════

EMAIL_LANG_NAMES = {"pt": "português do Brasil", "en": "inglês", "ko": "coreano"}

EMAIL_SYSTEM = (
    f"{QUALITY_DEPT_CONTEXT} "
    "Você redige e-mails corporativos curtos e profissionais para envio do "
    "relatório semanal (weekly) em anexo. Responda APENAS com JSON no formato "
    '{"subject": "assunto conciso", "body": "corpo do e-mail com saudação, '
    '1 parágrafo de contexto citando os destaques da semana e despedida"}. '
    "Sem markdown; quebras de linha com \\n."
)


class EmailSuggestionRequest(BaseModel):
    report_id: str
    language: str = Field(default="pt", pattern="^(pt|en|ko)$")


@router.post("/email-suggestion")
async def suggest_email(
    data: EmailSuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sugere assunto + corpo do e-mail a partir do conteúdo do weekly."""
    report = (
        db.query(WeeklyReport)
        .filter(WeeklyReport.id == data.report_id, WeeklyReport.user_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(404, detail="Weekly não encontrado.")

    texts = _layout_texts((report.content or {}).get("layout"))
    prompt = (
        f"Escreva em {EMAIL_LANG_NAMES[data.language]}. "
        f"Weekly W{report.week_number}/{report.year} de {current_user.name} "
        f"(setor {current_user.sector.value}). Conteúdo dos slides:\n"
        + "\n".join(f"- {t}" for t in texts[:40])
    )

    service = LLMService()
    parsed: dict | None = None
    try:
        response = await service.generate(prompt, EMAIL_SYSTEM, json_mode=True)
        parsed = _parse_json_object(response.content)
        if parsed is None:
            retry = await service.generate(prompt, EMAIL_SYSTEM, json_mode=True)
            parsed = _parse_json_object(retry.content)
    except Exception as error:
        logger.warning("Sugestão de e-mail: LLM falhou | %s", error)

    if not parsed or not str(parsed.get("subject") or "").strip():
        raise HTTPException(503, detail="IA indisponível no momento. Tente novamente.")
    return {
        "subject": str(parsed.get("subject"))[:300].strip(),
        "body": str(parsed.get("body") or "")[:5000].strip(),
    }
