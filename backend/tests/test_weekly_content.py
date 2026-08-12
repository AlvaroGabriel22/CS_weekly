from app.schemas.weekly_content import parse_weekly_content, default_layout_for_sector


def test_parse_weekly_content_validates_blocks():
    raw = {
        "summary": "Semana crítica no FIELD.",
        "highlights": ["Falha recorrente A20"],
        "activities": [
            {
                "source": 1,
                "title": "FIELD: A20 failure",
                "date": "08/07",
                "narrative": "Evidência indica NC material.",
                "blocks": [
                    {
                        "type": "device_info",
                        "fields": {"Modelo": "A20", "Serial": "SN123"},
                    },
                    {
                        "type": "measurement_table",
                        "title": "Medições",
                        "columns": ["Parâmetro", "Valor", "Limite"],
                        "rows": [["Torque", "0.4 Nm", "0.5 Nm"]],
                    },
                    {"type": "not_supported", "data": "x"},
                ],
            }
        ],
        "kpi_table": [{"kpi": "FPY", "result": "97%", "trend": "▼ Piorou"}],
        "presentation_plan": {
            "layout_profile": "field_case",
            "sidebar": ["synthesis", "highlights"],
            "global_blocks": [
                {
                    "type": "chart",
                    "title": "Defeitos",
                    "chart_type": "column",
                    "categories": ["W1", "W2"],
                    "series": [{"name": "PPM", "values": [120, 180]}],
                }
            ],
        },
    }
    content = parse_weekly_content(raw)
    assert content.summary.startswith("Semana")
    assert len(content.activities) == 1
    assert len(content.activities[0].blocks) == 2
    assert content.presentation_plan.layout_profile == "field_case"


def test_default_layout_for_field_sector():
    assert default_layout_for_sector("FIELD") == "field_case"
    assert default_layout_for_sector("IQC") == "analytical"
