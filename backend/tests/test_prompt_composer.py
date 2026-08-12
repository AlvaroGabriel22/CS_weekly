from app.services.prompt_composer import PromptComposer
from app.models import Language, ObjectivityLevel, QualitySector, TechnicalLevel, WritingTone, User, WritingProfile


def test_prompt_composer_creates_sections():
    composer = PromptComposer()
    user = User(
        id="test-id",
        email="test@test.com",
        hashed_password="hash",
        name="Test User",
        department="Quality",
        role="Analyst",
        sector=QualitySector.CSI,
    )
    user.writing_profile = WritingProfile(
        user_id="test-id",
        default_language=Language.PT,
        writing_tone=WritingTone.SPECIALIST,
        objectivity=ObjectivityLevel.HIGH,
        technical_level=TechnicalLevel.MEDIUM,
        personal_prompt="Be objective.",
    )

    result = composer.compose_weekly_prompt(
        user=user,
        evidence_dossier="### Activity 1: Audit\nDate: Monday 06/07/2026\nAttachments: none.",
        week_number=28,
        year=2026,
        language=Language.PT,
        period_label="06/07–12/07",
    )

    assert result.system_prompt
    assert "MX CS" in result.system_prompt
    assert "CSI" in result.system_prompt
    assert "Week 28" in result.user_prompt
    assert "06/07–12/07" in result.user_prompt
    assert "Be objective" in result.user_prompt
    assert "Activity 1: Audit" in result.user_prompt
    assert "EXECUTIVE WRITING MANDATE" in result.system_prompt
    assert "transcribe" in result.system_prompt
    assert len(result.sections) >= 5


def test_activity_analysis_prompt():
    composer = PromptComposer()
    prompt = composer.compose_activity_analysis_prompt(
        "Inspection audit", "Performed line inspection", ["audit", "quality"]
    )
    assert "Inspection audit" in prompt
    assert "audit" in prompt
