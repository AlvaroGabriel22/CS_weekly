from app.core.activity_directives import (
    activity_requests_image_analysis,
    parse_activity_directives,
)


def test_parse_analisar_imagem_removes_command():
    description = "CASR impactou o indicador.\n/analisar imagem\nDetalhe final."
    directives = parse_activity_directives(description)

    assert directives.analyze_images is True
    assert "/analisar imagem" not in directives.clean_description
    assert "CASR impactou o indicador." in directives.clean_description
    assert "Detalhe final." in directives.clean_description


def test_parse_analyze_image_english():
    directives = parse_activity_directives("/analyze image\nShort note.")
    assert directives.analyze_images is True
    assert directives.clean_description == "Short note."


def test_parse_quero_que_analise():
    directives = parse_activity_directives(
        "/quero que vc analise a imagem do defeito\nTexto principal."
    )
    assert directives.analyze_images is True
    assert directives.clean_description == "Texto principal."


def test_no_directive_keeps_description():
    text = "Auditoria concluída sem NC crítica."
    directives = parse_activity_directives(text)
    assert directives.analyze_images is False
    assert directives.clean_description == text


class _Activity:
    def __init__(self, description: str | None):
        self.description = description


def test_activity_requests_image_analysis():
    assert activity_requests_image_analysis(_Activity("/analisar imagem")) is True
    assert activity_requests_image_analysis(_Activity("Sem comando")) is False
