from datetime import UTC, datetime

from app.models import Activity, ActivityMetadata, Attachment, ImageUsage, QualitySector, User
from app.services.business import WeeklyService


def _user(sector: QualitySector = QualitySector.IQC) -> User:
    return User(
        id="user-1",
        email="a@b.com",
        hashed_password="x",
        name="Analyst",
        department="Quality",
        role="Analyst",
        sector=sector,
    )


def _build_activity() -> Activity:
    activity = Activity(
        id="act-1",
        user_id="user-1",
        title="Análise de defeitos IQC",
        description="Estratificação dos defeitos de recebimento do fornecedor XYZ.",
        activity_date=datetime(2026, 7, 8, 14, 0, tzinfo=UTC),
        week_number=28,
        year=2026,
    )
    activity.metadata_entry = ActivityMetadata(
        activity_id="act-1",
        supplier="XYZ",
        category="IQC",
        related_kpis=["PPM", "Retrabalho"],
        technical_summary="Concentração de defeitos dimensionais no lote 42.",
    )
    image = Attachment(
        id="att-1",
        activity_id="act-1",
        filename="foto.png",
        original_filename="defeito_lote42.png",
        file_path="/tmp/foto.png",
        file_type="image",
        file_size=100,
        include_in_weekly=True,
        ai_caption="Trinca visível na borda do componente.",
        ai_analysis={
            "caption": "Trinca visível na borda do componente.",
            "observations": ["Trinca de ~3mm", "Marca de identificação L42"],
            "possible_impact": "Risco de rejeição do lote completo.",
            "visible_text": "LOTE 42",
        },
    )
    sheet = Attachment(
        id="att-2",
        activity_id="act-1",
        filename="dados.xlsx",
        original_filename="defeitos_semana.xlsx",
        file_path="/tmp/dados.xlsx",
        file_type="spreadsheet",
        file_size=200,
        include_in_weekly=True,
        kpi_data={
            "summary": "PPM subiu de 120 para 180 na semana.",
            "kpis": [{"name": "PPM", "value": 180}],
            "trends": ["PPM +50% vs semana anterior"],
            "anomalies": ["Pico de defeitos na terça-feira"],
            "preview": [
                {"dia": "seg", "defeitos": "2"},
                {"dia": "ter", "defeitos": "9"},
            ],
        },
    )
    activity.attachments = [image, sheet]
    return activity


def test_dossier_includes_all_evidence_layers():
    activity = _build_activity()
    activity.description = (
        "Estratificação dos defeitos de recebimento do fornecedor XYZ.\n/analisar imagem"
    )
    service = WeeklyService(db=None)
    dossier = service._build_evidence_dossier([activity], _user())

    assert "Author sector: IQC" in dossier
    assert "Análise de defeitos IQC" in dossier
    assert "supplier=XYZ" in dossier
    assert "analyze_images_requested: True" in dossier
    assert "id=att-1" in dossier
    assert "Trinca de ~3mm" in dossier
    assert "PPM subiu de 120 para 180" in dossier
    assert "tabular preview" in dossier
    assert "/analisar imagem" not in dossier


def test_dossier_image_without_command_is_visual_reference_only():
    activity = _build_activity()
    service = WeeklyService(db=None)
    dossier = service._build_evidence_dossier([activity], _user())

    assert "analyze_images_requested: False" in dossier
    assert "visual reference only" in dossier
    assert "Trinca de ~3mm" not in dossier


def test_dossier_excludes_store_only_attachments():
    activity = _build_activity()
    activity.attachments[0].image_usage = ImageUsage.STORE_ONLY
    service = WeeklyService(db=None)
    dossier = service._build_evidence_dossier([activity], _user())
    assert "defeito_lote42.png" not in dossier
    assert "defeitos_semana.xlsx" in dossier


def test_attachment_inventory_lists_ids():
    service = WeeklyService(db=None)
    inventory = service._build_attachment_inventory([_build_activity()])
    assert "attachment_id=att-1" in inventory
    assert "attachment_id=att-2" in inventory
