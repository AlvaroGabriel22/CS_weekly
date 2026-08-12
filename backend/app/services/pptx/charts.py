"""Native chart rendering for QWI presentations."""

from __future__ import annotations

import logging
from typing import Any

from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.util import Inches, Pt

from app.services.pptx.strings import BRAND, FONT, INK, MUTED

logger = logging.getLogger(__name__)

CHART_TYPES = {
    "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
    "bar": XL_CHART_TYPE.BAR_CLUSTERED,
    "line": XL_CHART_TYPE.LINE_MARKERS,
    "pie": XL_CHART_TYPE.PIE,
}


def render_chart(
    slide,
    block: dict[str, Any],
    left: float,
    top: float,
    width: float,
    height: float,
) -> float:
    """Render a chart block; returns height used."""
    chart_type = block.get("chart_type", "column")
    categories = block.get("categories") or []
    series_list = block.get("series") or []
    if not categories or not series_list:
        return 0.0

    xl_type = CHART_TYPES.get(chart_type, XL_CHART_TYPE.COLUMN_CLUSTERED)
    chart_data = CategoryChartData()
    chart_data.categories = categories
    for series in series_list:
        name = series.get("name", "Series")
        values = series.get("values") or []
        if len(values) < len(categories):
            values = values + [0.0] * (len(categories) - len(values))
        chart_data.add_series(name, values[: len(categories)])

    try:
        frame = slide.shapes.add_chart(
            xl_type,
            Inches(left),
            Inches(top),
            Inches(width),
            Inches(height),
            chart_data,
        )
        chart = frame.chart
        chart.has_legend = len(series_list) > 1
        if chart.has_legend:
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
            chart.legend.font.name = FONT
            chart.legend.font.size = Pt(8)

        if chart_type != "pie" and chart.value_axis:
            chart.value_axis.has_major_gridlines = True
            chart.value_axis.tick_labels.font.name = FONT
            chart.value_axis.tick_labels.font.size = Pt(8)
        if chart.category_axis:
            chart.category_axis.tick_labels.font.name = FONT
            chart.category_axis.tick_labels.font.size = Pt(8)

        for series in chart.series:
            series.format.fill.solid()
            series.format.fill.fore_color.rgb = BRAND

        title = block.get("title")
        if title:
            chart.has_title = True
            chart.chart_title.text_frame.text = str(title)
            chart.chart_title.text_frame.paragraphs[0].font.name = FONT
            chart.chart_title.text_frame.paragraphs[0].font.size = Pt(10)
            chart.chart_title.text_frame.paragraphs[0].font.color.rgb = INK

        insight = block.get("insight")
        if insight:
            box = slide.shapes.add_textbox(
                Inches(left),
                Inches(top + height + 0.04),
                Inches(width),
                Inches(0.35),
            )
            para = box.text_frame.paragraphs[0]
            para.text = str(insight)
            para.font.name = FONT
            para.font.size = Pt(9)
            para.font.color.rgb = MUTED
            return height + 0.42

        return height
    except Exception as error:
        logger.warning("Chart render failed: %s", error)
        return 0.0
