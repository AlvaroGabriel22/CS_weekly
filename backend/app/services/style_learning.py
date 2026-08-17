"""Aprendizado do padrão de montagem de PPT por usuário.

O "aprendizado" NÃO treina o modelo: cada PPT gerado com layout alimenta um
perfil estatístico individual (fontes, tamanhos, cores, estrutura dos slides,
estilo de escrita). O deck em um clique injeta esse perfil no prompt e o
pós-processamento aplica os defaults do usuário mesmo quando o LLM ignora as
instruções — assim o padrão vale tanto para o gemma local quanto para a API
OpenAI-compatível.

Decaimento temporal: montagens novas entram com peso `alpha` (manual > IA),
então o perfil acompanha mudanças de estilo em vez de congelar no passado.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import UserStyleProfile

logger = logging.getLogger(__name__)

# Peso da observação nova no EMA (manual pesa mais que rascunho da IA).
ALPHA_BY_SOURCE = {"manual": 0.35, "ai": 0.12}


# ─────────────────────────── extração de estatísticas ────────────────────────

def _slide_texts(slide: dict) -> list[dict]:
    return [e for e in slide.get("elements", []) if e.get("type") == "text"]


def _title_of(slide: dict) -> dict | None:
    """Heurística: o texto de maior fonte do slide é o título."""
    texts = _slide_texts(slide)
    return max(texts, key=lambda e: e.get("font_size") or 0) if texts else None


def extract_style(layout: dict) -> dict | None:
    """Estatísticas determinísticas de UM layout (uma montagem)."""
    slides = layout.get("slides") if isinstance(layout, dict) else None
    if not isinstance(slides, list) or not slides:
        return None
    content = [s for s in slides if s.get("kind") != "cover"] or slides

    fonts: Counter = Counter()
    title_colors: Counter = Counter()
    structures: Counter = Counter()
    aligns: Counter = Counter()
    shapes: Counter = Counter()
    title_sizes: list[int] = []
    body_sizes: list[int] = []
    title_words: list[int] = []
    body_lens: list[int] = []
    bold_titles = 0
    bullets = 0
    elements_per_slide: list[int] = []

    for slide in content:
        elements = slide.get("elements", [])
        elements_per_slide.append(len(elements))
        structures[",".join(e.get("type", "?") for e in elements[:8])] += 1
        title = _title_of(slide)
        for el in elements:
            if el.get("type") == "shape":
                shapes[el.get("shape") or "rect"] += 1
            if el.get("type") != "text":
                continue
            fonts[el.get("font_family") or "Calibri"] += 1
            if el.get("align"):
                aligns[el["align"]] += 1
            text = str(el.get("text") or "")
            size = int(el.get("font_size") or 14)
            if el is title:
                title_sizes.append(size)
                title_words.append(len(text.split()))
                title_colors[el.get("color") or "#0C379C"] += 1
                bold_titles += 1 if el.get("bold") else 0
            else:
                body_sizes.append(size)
                body_lens.append(len(text))
                if "•" in text or "\n-" in text or text.startswith("- "):
                    bullets += 1

    def avg(values: list, default: float) -> float:
        return round(sum(values) / len(values), 2) if values else default

    return {
        "fonts": dict(fonts),
        "title_colors": dict(title_colors),
        "structures": dict(structures.most_common(6)),
        "aligns": dict(aligns),
        "shapes": dict(shapes),
        "title_size": avg(title_sizes, 24),
        "body_size": avg(body_sizes, 14),
        "title_words": avg(title_words, 4),
        "body_len": avg(body_lens, 150),
        "bold_title_ratio": round(bold_titles / max(len(content), 1), 2),
        "bullet_ratio": round(bullets / max(len(body_lens), 1), 2) if body_lens else 0.0,
        "elements_per_slide": avg(elements_per_slide, 3),
        "content_slides": len(content),
    }


# ────────────────────────────── merge com decaimento ─────────────────────────

def _merge_counter(old: dict, new: dict, alpha: float) -> dict:
    merged: dict[str, float] = {k: round(v * (1 - alpha), 3) for k, v in (old or {}).items()}
    total_new = sum(new.values()) or 1
    for key, value in new.items():
        merged[key] = round(merged.get(key, 0.0) + alpha * value / total_new * 10, 3)
    # poda ruído para o JSON não crescer sem limite
    return dict(sorted(merged.items(), key=lambda kv: -kv[1])[:8])


def merge_profiles(old: dict | None, new: dict, alpha: float) -> dict:
    if not old:
        return new
    merged = dict(old)
    for key in ("fonts", "title_colors", "structures", "aligns", "shapes"):
        merged[key] = _merge_counter(old.get(key) or {}, new.get(key) or {}, alpha)
    for key in (
        "title_size", "body_size", "title_words", "body_len",
        "bold_title_ratio", "bullet_ratio", "elements_per_slide", "content_slides",
    ):
        old_v = float(old.get(key) or 0)
        merged[key] = round(old_v * (1 - alpha) + float(new.get(key) or 0) * alpha, 2)
    return merged


def learn_from_layout(db: Session, user_id: str, layout: dict, source: str = "manual") -> None:
    """Atualiza o perfil do usuário com uma montagem recém-gerada.

    Nunca falha a geração do PPT: qualquer erro só é logado.
    """
    try:
        observed = extract_style(layout)
        if not observed:
            return
        alpha = ALPHA_BY_SOURCE.get(source, 0.2)
        row = db.query(UserStyleProfile).filter(UserStyleProfile.user_id == user_id).first()
        if row is None:
            row = UserStyleProfile(user_id=user_id, profile=observed, sample_count=1)
            db.add(row)
        else:
            row.profile = merge_profiles(row.profile or {}, observed, alpha)
            row.sample_count = (row.sample_count or 0) + 1
            row.updated_at = datetime.now(UTC)
        logger.info(
            "Estilo aprendido | user=%s | source=%s | amostras=%d",
            user_id, source, row.sample_count,
        )
    except Exception as error:  # aprendizado jamais derruba a geração
        logger.warning("Falha ao aprender estilo | user=%s | %s", user_id, error)


# ─────────────────────────── uso na geração de decks ─────────────────────────

def dominant(counter: dict | None, default: str) -> str:
    if not counter:
        return default
    return max(counter.items(), key=lambda kv: kv[1])[0]


def style_rules_text(profile: dict) -> str:
    """Regras legíveis para o prompt do deck-draft (layout + escrita)."""
    font = dominant(profile.get("fonts"), "Calibri")
    color = dominant(profile.get("title_colors"), "#0C379C")
    structure = dominant(profile.get("structures"), "")
    lines = [
        "PADRÃO PESSOAL deste usuário (imite fielmente):",
        f"- Fonte preferida: {font}; títulos ~{int(profile.get('title_size') or 24)}pt"
        f" na cor {color}; corpo ~{int(profile.get('body_size') or 14)}pt.",
        f"- ~{round(profile.get('elements_per_slide') or 3)} elementos por slide;"
        f" ~{round(profile.get('content_slides') or 3)} slides de conteúdo por deck.",
    ]
    if structure:
        lines.append(f"- Estrutura típica de slide (ordem dos elementos): {structure}.")
    if (profile.get("bold_title_ratio") or 0) >= 0.5:
        lines.append("- Títulos em negrito.")
    lines.append(
        f"- Escrita: títulos com ~{round(profile.get('title_words') or 4)} palavras;"
        f" blocos de texto com ~{int(profile.get('body_len') or 150)} caracteres"
        + ("; usa bullets (• item por linha)." if (profile.get("bullet_ratio") or 0) >= 0.3
           else "; texto corrido, sem bullets.")
    )
    return "\n".join(lines)


def apply_profile_style(layout: dict, profile: dict, sample_count: int) -> dict:
    """Força os defaults do usuário no layout gerado (garantia pós-LLM).

    Aplica fonte dominante em textos sem fonte definida e, com >=2 amostras,
    aproxima os tamanhos de título/corpo do padrão pessoal.
    """
    if not profile:
        return layout
    font = dominant(profile.get("fonts"), "")
    title_size = int(profile.get("title_size") or 0)
    body_size = int(profile.get("body_size") or 0)
    title_color = dominant(profile.get("title_colors"), "")
    confident = sample_count >= 2

    for slide in layout.get("slides", []):
        if slide.get("kind") == "cover":
            continue
        texts = [e for e in slide.get("elements", []) if e.get("type") == "text"]
        title = max(texts, key=lambda e: e.get("font_size") or 0) if texts else None
        for el in texts:
            if font and not el.get("font_family"):
                el["font_family"] = font
            if not confident:
                continue
            if el is title:
                if title_size:
                    el["font_size"] = title_size
                if title_color:
                    el["color"] = title_color
            elif body_size:
                el["font_size"] = body_size
    return layout


def compact_layout(layout: dict, max_slides: int = 8) -> dict:
    """Versão compacta de um layout para caber no prompt como template."""
    slides = []
    for slide in (layout.get("slides") or [])[:max_slides]:
        elements = []
        for el in (slide.get("elements") or [])[:12]:
            item = {
                "type": el.get("type"),
                "x": round(float(el.get("x") or 0), 2),
                "y": round(float(el.get("y") or 0), 2),
                "w": round(float(el.get("w") or 0), 2),
                "h": round(float(el.get("h") or 0), 2),
                "font_size": el.get("font_size"),
            }
            if el.get("type") == "text":
                item["text"] = str(el.get("text") or "")[:80]
                for key in ("bold", "font_family", "color", "align"):
                    if el.get(key):
                        item[key] = el[key]
            if el.get("type") == "shape":
                item["shape"] = el.get("shape")
                item["color"] = el.get("color")
                if el.get("fill"):
                    item["fill"] = el["fill"]
            elements.append(item)
        slides.append({"kind": slide.get("kind"), "elements": elements})
    return {"slides": slides}
