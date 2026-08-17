"""Aprendizado do padrão de montagem (style_learning)."""
from app.services.style_learning import (
    apply_profile_style,
    dominant,
    extract_style,
    merge_profiles,
)

LAYOUT = {
    "slides": [
        {"kind": "cover", "elements": [
            {"type": "text", "text": "Weekly W33", "font_size": 40, "bold": True},
        ]},
        {"kind": "custom", "elements": [
            {"type": "text", "text": "Auditoria linha 3", "font_size": 28,
             "bold": True, "font_family": "Georgia", "color": "#0C379C"},
            {"type": "text", "text": "Descrição da atividade em texto corrido.",
             "font_size": 14, "font_family": "Georgia"},
            {"type": "table", "attachment_id": "t1"},
        ]},
    ]
}


def test_extract_style_reads_fonts_and_sizes():
    style = extract_style(LAYOUT)
    assert style["fonts"]["Georgia"] == 2
    assert style["title_size"] == 28
    assert style["body_size"] == 14
    assert style["bold_title_ratio"] == 1.0
    assert style["content_slides"] == 1


def test_merge_keeps_recent_weight():
    old = extract_style(LAYOUT)
    new = dict(old, title_size=20.0)
    merged = merge_profiles(old, new, alpha=0.35)
    # EMA: 28*0.65 + 20*0.35 = 25.2
    assert merged["title_size"] == 25.2
    assert dominant(merged["fonts"], "Calibri") == "Georgia"


def test_apply_profile_style_snaps_to_user_pattern():
    profile = extract_style(LAYOUT)
    generated = {
        "slides": [
            {"kind": "cover", "elements": []},
            {"kind": "custom", "elements": [
                {"type": "text", "text": "Título novo", "font_size": 22},
                {"type": "text", "text": "corpo", "font_size": 12},
            ]},
        ]
    }
    styled = apply_profile_style(generated, profile, sample_count=3)
    els = styled["slides"][1]["elements"]
    assert els[0]["font_family"] == "Georgia"
    assert els[0]["font_size"] == 28   # snap ao título do usuário
    assert els[0]["color"] == "#0C379C"
    assert els[1]["font_size"] == 14   # snap ao corpo


def test_extract_style_rejects_empty():
    assert extract_style({}) is None
    assert extract_style({"slides": []}) is None
