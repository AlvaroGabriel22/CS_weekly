"""Validated schema for AI-generated weekly report content and PPT blocks."""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

LayoutProfile = Literal["executive", "operational", "analytical", "field_case"]
ContentMode = Literal["transcribe", "compress"]
ChartType = Literal["column", "bar", "line", "pie"]
BlockType = Literal[
    "device_info",
    "measurement_table",
    "generic_table",
    "countermeasure_table",
    "chart",
    "image_row",
    "text",
    "highlight",
]


class ChartSeries(BaseModel):
    name: str = "Series"
    values: list[float] = Field(default_factory=list)


class ChartBlock(BaseModel):
    type: Literal["chart"] = "chart"
    title: str = ""
    chart_type: ChartType = "column"
    categories: list[str] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)
    insight: str | None = None


class DeviceInfoBlock(BaseModel):
    type: Literal["device_info"] = "device_info"
    title: str | None = None
    fields: dict[str, str] = Field(default_factory=dict)


class MeasurementTableBlock(BaseModel):
    type: Literal["measurement_table"] = "measurement_table"
    title: str = "Medições"
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class GenericTableBlock(BaseModel):
    type: Literal["generic_table"] = "generic_table"
    title: str = ""
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class CountermeasureRow(BaseModel):
    action: str
    owner: str = ""
    status: str = ""
    due: str = ""


class CountermeasureBlock(BaseModel):
    type: Literal["countermeasure_table"] = "countermeasure_table"
    title: str = "Contramedidas"
    rows: list[CountermeasureRow] = Field(default_factory=list)


class ImageRef(BaseModel):
    attachment_id: str | None = None
    path: str | None = None
    caption: str | None = None


class ImageRowBlock(BaseModel):
    type: Literal["image_row"] = "image_row"
    title: str | None = None
    images: list[ImageRef] = Field(default_factory=list)


class TextBlock(BaseModel):
    type: Literal["text", "highlight"] = "text"
    text: str = ""
    size: int | None = None
    bold: bool = False


class KpiTableRow(BaseModel):
    kpi: str
    result: str = ""
    trend: str = ""


class ActivityReport(BaseModel):
    source: int
    title: str
    date: str = ""
    sector: str | None = None
    activity_kind: str | None = None
    content_mode: ContentMode = "compress"
    narrative: str = ""
    impact: str = ""
    facts: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    images: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("source", mode="before")
    @classmethod
    def coerce_source(cls, value: Any) -> int:
        return int(value)


class PresentationPlan(BaseModel):
    layout_profile: LayoutProfile = "executive"
    sidebar: list[str] = Field(default_factory=list)
    global_blocks: list[dict[str, Any]] = Field(default_factory=list)


class WeeklyContent(BaseModel):
    summary: str = ""
    highlights: list[str] = Field(default_factory=list)
    activities: list[ActivityReport] = Field(default_factory=list)
    kpis: list[str] = Field(default_factory=list)
    kpi_table: list[KpiTableRow] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    archetype: str = "executivo"
    narrative: str = ""
    presentation_plan: PresentationPlan = Field(default_factory=PresentationPlan)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def parse_visual_block(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort validation of a single visual block; returns dict or None."""
    block_type = raw.get("type")
    if not block_type:
        return None
    validators: dict[str, type[BaseModel]] = {
        "chart": ChartBlock,
        "device_info": DeviceInfoBlock,
        "measurement_table": MeasurementTableBlock,
        "generic_table": GenericTableBlock,
        "countermeasure_table": CountermeasureBlock,
        "image_row": ImageRowBlock,
        "text": TextBlock,
        "highlight": TextBlock,
    }
    model = validators.get(block_type)
    if not model:
        return None
    try:
        if block_type == "highlight":
            raw = {**raw, "type": "highlight"}
        return model.model_validate(raw).model_dump(mode="json")
    except Exception as error:
        logger.debug("Invalid visual block discarded: %s", error)
        return None


def parse_weekly_content(data: dict[str, Any]) -> WeeklyContent:
    """Validate AI output; sanitize blocks and coerce types."""
    payload = dict(data)
    if "presentation_plan" not in payload or not isinstance(
        payload.get("presentation_plan"), dict
    ):
        payload["presentation_plan"] = {}

    activities = []
    for item in payload.get("activities") or []:
        if not isinstance(item, dict):
            continue
        blocks = []
        for block in item.get("blocks") or []:
            if isinstance(block, dict):
                parsed = parse_visual_block(block)
                if parsed:
                    blocks.append(parsed)
        item = {**item, "blocks": blocks}
        try:
            activities.append(ActivityReport.model_validate(item))
        except Exception as error:
            logger.warning("Skipping invalid activity entry: %s", error)
    payload["activities"] = activities

    global_blocks = []
    plan = payload.get("presentation_plan") or {}
    for block in plan.get("global_blocks") or []:
        if isinstance(block, dict):
            parsed = parse_visual_block(block)
            if parsed:
                global_blocks.append(parsed)
    plan["global_blocks"] = global_blocks
    payload["presentation_plan"] = plan

    kpi_rows = []
    for row in payload.get("kpi_table") or []:
        if isinstance(row, dict) and row.get("kpi"):
            try:
                kpi_rows.append(KpiTableRow.model_validate(row))
            except Exception:
                pass
    payload["kpi_table"] = kpi_rows

    return WeeklyContent.model_validate(payload)


def weekly_content_to_legacy_dict(content: WeeklyContent) -> dict[str, Any]:
    """Dict compatible with PptxService and stored report JSON."""
    data = content.to_dict()
    data["kpi_table"] = [row.model_dump() for row in content.kpi_table]
    data["activities"] = [
        {
            **act.model_dump(),
            "blocks": act.blocks,
        }
        for act in content.activities
    ]
    return data


def default_layout_for_sector(sector: str) -> LayoutProfile:
    mapping: dict[str, LayoutProfile] = {
        "FIELD": "field_case",
        "IQC": "analytical",
        "OQC": "analytical",
        "QM": "executive",
        "QA": "operational",
        "CSI": "executive",
    }
    return mapping.get(sector.upper(), "executive")
