"""PPTX layout constants and localized strings."""

from pptx.dml.color import RGBColor

FONT = "Arial"
BRAND = RGBColor(0x0C, 0x37, 0x9C)
INK = RGBColor(0x18, 0x1F, 0x2E)
MUTED = RGBColor(0x5C, 0x65, 0x74)
SOFT = RGBColor(0x6D, 0x9E, 0xEB)
LINE = RGBColor(0xDE, 0xE3, 0xEB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x15, 0x80, 0x3D)
RED = RGBColor(0xB9, 0x1C, 0x1C)
AMBER = RGBColor(0xB4, 0x5F, 0x06)

PAGE_W = 13.333
PAGE_H = 7.5
MARGIN_L = 0.75
LEFT_W = 5.85
DIVIDER_X = 6.82
RIGHT_X = 7.10
RIGHT_W = 5.50
FULL_W = 9.6
CONTENT_TOP = 1.32
CONTENT_BOTTOM = 6.88
FOOTER_Y = 7.08

CHAR_W_FACTOR = 0.56
LINE_H_FACTOR = 1.32
MAX_CONTENT_SLIDES = 18

STRINGS: dict[str, dict[str, str]] = {
    "pt": {
        "week": "Semana",
        "cover_tagline": "Relatório gerado a partir das atividades e evidências registradas.",
        "synthesis": "SÍNTESE DA SEMANA",
        "highlights": "DESTAQUES",
        "kpi_table": "EVOLUÇÃO DOS KPIS",
        "kpi": "KPI",
        "result": "Resultado",
        "trend": "Tendência",
        "treatments": "Tratativas",
        "impact": "Impacto",
        "conclusions": "CONCLUSÕES",
        "next_steps": "PRÓXIMOS PASSOS",
        "evidences": "Evidências",
        "device_info": "Identificação",
        "measurements": "Medições",
        "countermeasures": "Contramedidas",
        "footer": "QWI · Quality Weekly Intelligence",
        "action": "Ação",
        "owner": "Responsável",
        "status": "Status",
        "due": "Prazo",
        "parameter": "Parâmetro",
        "value": "Valor",
        "unit": "Unidade",
        "limit": "Limite",
        "pass_fail": "Status",
    },
    "en": {
        "week": "Week",
        "cover_tagline": "Report generated from the registered activities and evidence.",
        "synthesis": "WEEK IN BRIEF",
        "highlights": "HIGHLIGHTS",
        "kpi_table": "KPI EVOLUTION",
        "kpi": "KPI",
        "result": "Result",
        "trend": "Trend",
        "treatments": "Actions taken",
        "impact": "Impact",
        "conclusions": "CONCLUSIONS",
        "next_steps": "NEXT STEPS",
        "evidences": "Evidence",
        "device_info": "Device identification",
        "measurements": "Measurements",
        "countermeasures": "Countermeasures",
        "footer": "QWI · Quality Weekly Intelligence",
        "action": "Action",
        "owner": "Owner",
        "status": "Status",
        "due": "Due",
        "parameter": "Parameter",
        "value": "Value",
        "unit": "Unit",
        "limit": "Limit",
        "pass_fail": "Status",
    },
}
