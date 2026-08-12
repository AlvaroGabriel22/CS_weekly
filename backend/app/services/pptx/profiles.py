"""Layout profile resolution from sector and AI presentation plan."""

from __future__ import annotations

from typing import Any

from app.models import QualitySector
from app.schemas.weekly_content import LayoutProfile, default_layout_for_sector


def resolve_layout_profile(
    presentation_plan: dict[str, Any] | None,
    sector: QualitySector | str,
    activities: list[dict[str, Any]],
) -> LayoutProfile:
    """Pick the deck layout profile from AI plan, with sector-based defaults."""
    plan = presentation_plan or {}
    profile = plan.get("layout_profile")
    valid: tuple[LayoutProfile, ...] = (
        "executive",
        "operational",
        "analytical",
        "field_case",
    )
    if profile in valid:
        return profile  # type: ignore[return-value]

    sector_str = sector.value if isinstance(sector, QualitySector) else str(sector)
    default = default_layout_for_sector(sector_str)

    has_device = any(
        block.get("type") == "device_info"
        for act in activities
        for block in (act.get("blocks") or [])
        if isinstance(block, dict)
    )
    has_measurements = any(
        block.get("type") in ("measurement_table", "generic_table")
        for act in activities
        for block in (act.get("blocks") or [])
        if isinstance(block, dict)
    )
    if sector_str == "FIELD" and (has_device or has_measurements):
        return "field_case"

    has_charts = any(
        block.get("type") == "chart"
        for act in activities
        for block in (act.get("blocks") or [])
        if isinstance(block, dict)
    ) or any(
        block.get("type") == "chart"
        for block in (plan.get("global_blocks") or [])
        if isinstance(block, dict)
    )
    if has_charts:
        return "analytical"

    if len(activities) >= 6:
        return "operational"

    return default


def sidebar_sections(
    presentation_plan: dict[str, Any] | None,
    layout_profile: LayoutProfile,
) -> list[str]:
    """Executive PPT: no sidebar — activities only, full-width."""
    return []
