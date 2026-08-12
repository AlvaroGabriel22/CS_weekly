from app.services.text_sanitize import sanitize_weekly_content, sanitize_executive_text


def test_strips_forbidden_phrases():
    text = "O resultado indica que o PPM subiu."
    assert "indica que" not in sanitize_executive_text(text)
    assert "PPM subiu" in sanitize_executive_text(text)


def test_sanitize_weekly_clears_sidebar_and_truncates_narrative():
    data = {
        "summary": "Resumo com indica que algo mudou.",
        "activities": [
            {
                "source": 1,
                "title": "Teste",
                "content_mode": "compress",
                "narrative": "x " * 200,
                "facts": ["fato " * 30],
            }
        ],
        "presentation_plan": {
            "sidebar": ["synthesis", "highlights"],
        },
    }
    result = sanitize_weekly_content(data)
    assert result["presentation_plan"]["sidebar"] == []
    assert len(result["activities"][0]["narrative"]) <= 280
