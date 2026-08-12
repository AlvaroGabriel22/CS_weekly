"""Post-process AI text to remove obvious LLM phrasing for executive reports."""

from __future__ import annotations

import re
from typing import Any

# Patterns to strip or simplify (PT and EN)
_FORBIDDEN_PHRASES = (
    r"\bindica\s+que\b",
    r"\bsugere\s+que\b",
    r"\bdemonstra\s+que\b",
    r"\bdemonstra\s+um\s+avanço\b",
    r"\bvale\s+ressaltar\b",
    r"\bem\s+conclusão\b",
    r"\bno\s+geral\b",
    r"\bimportante\s+destacar\b",
    r"\bit\s+is\s+worth\s+noting\b",
    r"\bindicates\s+that\b",
    r"\bsuggests\s+that\b",
    r"\bdemonstrates\s+that\b",
    r"\bin\s+conclusion\b",
    r"\boverall\b,",
)

_MAX_NARRATIVE_CHARS = 280
_MAX_FACT_CHARS = 120


def sanitize_executive_text(text: str) -> str:
    if not text:
        return ""
    result = text.strip()
    for pattern in _FORBIDDEN_PHRASES:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    result = re.sub(r"\s{2,}", " ", result)
    result = re.sub(r"\.\s*\.", ".", result)
    return result.strip(" ,.;")


def truncate_narrative(text: str, max_chars: int = _MAX_NARRATIVE_CHARS) -> str:
    cleaned = sanitize_executive_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[: max_chars - 1].rsplit(" ", 1)[0]
    return cut.rstrip(".,;") + "…"


def sanitize_string_list(items: list[Any], max_items: int = 4) -> list[str]:
    result = []
    for item in items[:max_items]:
        if not item:
            continue
        text = sanitize_executive_text(str(item))
        if len(text) > _MAX_FACT_CHARS:
            text = text[: _MAX_FACT_CHARS - 1].rsplit(" ", 1)[0] + "…"
        if text:
            result.append(text)
    return result


def sanitize_weekly_content(data: dict[str, Any]) -> dict[str, Any]:
    """Apply executive tone cleanup to structured weekly content."""
    payload = dict(data)

    for key in ("summary", "narrative"):
        if payload.get(key):
            payload[key] = sanitize_executive_text(str(payload[key]))

    for key in ("highlights", "conclusions", "next_steps", "kpis"):
        if isinstance(payload.get(key), list):
            payload[key] = sanitize_string_list(payload[key])

    activities = []
    for item in payload.get("activities") or []:
        if not isinstance(item, dict):
            continue
        act = dict(item)
        mode = act.get("content_mode", "compress")
        narrative = act.get("narrative") or ""
        if mode == "compress":
            act["narrative"] = truncate_narrative(narrative)
        else:
            act["narrative"] = sanitize_executive_text(narrative)
        act["impact"] = sanitize_executive_text(str(act.get("impact") or ""))
        act["facts"] = sanitize_string_list(act.get("facts") or [], max_items=4)
        act["actions"] = sanitize_string_list(act.get("actions") or [], max_items=4)
        if act.get("title"):
            act["title"] = sanitize_executive_text(str(act["title"]))
        activities.append(act)
    payload["activities"] = activities

    plan = payload.get("presentation_plan")
    if isinstance(plan, dict):
        plan = dict(plan)
        plan["sidebar"] = []
        payload["presentation_plan"] = plan

    return payload
