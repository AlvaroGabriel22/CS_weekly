from app.models import QualitySector
from app.services.prompt_composer import PromptComposer, SECTOR_PLAYBOOKS


def test_all_sectors_have_playbooks():
    for sector in QualitySector:
        assert sector in SECTOR_PLAYBOOKS
        assert len(SECTOR_PLAYBOOKS[sector]) > 50


def test_field_playbook_mentions_measurements():
    assert "measurement_table" in SECTOR_PLAYBOOKS[QualitySector.FIELD]


def test_presentation_plan_prompt_includes_blocks_doc():
    from app.models import User

    composer = PromptComposer()
    user = User(
        id="u1",
        email="a@b.com",
        hashed_password="x",
        name="Field Analyst",
        department="Quality",
        role="Analyst",
        sector=QualitySector.FIELD,
    )
    result = composer.compose_presentation_plan_prompt(
        user=user,
        analysis_draft="Activity 1: device failure on A20",
        attachment_inventory="- attachment_id=1 | type=image",
    )
    assert "device_info" in result.system_prompt
    assert "field_case" in result.system_prompt
    assert "Activity 1" in result.user_prompt
