"""Planejador determinístico do deck (app/services/deck_plan.py).

Cobre as três regras que existem por causa da auditoria do gerador antigo:
encaixe (e não índice), nada do modelo sobrando, e nada sumindo calado.
"""
import pytest

from app.services.deck_plan import (
    CHART,
    CLEAR,
    IMAGE,
    PARAGRAPHS,
    REMOVE,
    TABLE,
    TEXT,
    ActivityContent,
    build_plan,
)


def el(shape_id, slot, kind="text", y=0.5, x=0.1):
    return {"id": f"e{shape_id}", "type": kind, "slot": slot, "src_shape_id": shape_id,
            "x": x, "y": y, "w": 0.3, "h": 0.2}


def modelo(*slides) -> dict:
    return {"slides": [
        {"id": f"s{i}", "kind": s["kind"], "src_slide": i, "elements": s["elements"]}
        for i, s in enumerate(slides)
    ]}


CAPA = {"kind": "cover", "elements": [
    el(1, "title", y=0.3), el(2, "week_label", y=0.5), el(3, "body", y=0.6),
    el(9, "static", y=0.9),
]}
# molde simples: título + descrição
SO_TEXTO = {"kind": "custom", "elements": [el(10, "title", y=0.1), el(11, "body", y=0.3)]}
# molde com tabela
COM_TABELA = {"kind": "custom", "elements": [
    el(20, "title", y=0.1), el(21, "body", y=0.3), el(22, "table", "table", y=0.6),
]}
# molde com duas imagens
COM_IMAGENS = {"kind": "custom", "elements": [
    el(30, "title", y=0.1), el(31, "body", y=0.3),
    el(32, "image", "image", y=0.6, x=0.1), el(33, "image", "image", y=0.6, x=0.5),
]}


def acoes(slide) -> dict:
    """{shape_id: (ação, valor)}"""
    return {f.shape_id: (f.action, f.value) for f in slide.fills}


def test_cover_gets_the_week_and_clears_what_is_left_over():
    plano = build_plan(modelo(CAPA, SO_TEXTO), [ActivityContent(title="A", description="d")],
                       title="Weekly W33", subtitle="Semana 33 · CSI",
                       week_label="10/08 a 16/08")
    capa = plano.slides[0]
    assert capa.kind == "cover"
    mapa = acoes(capa)
    assert mapa[1] == (TEXT, "Weekly W33")
    assert mapa[2] == (TEXT, "10/08 a 16/08")     # data do modelo NÃO repete
    assert mapa[3] == (TEXT, "Semana 33 · CSI")
    assert 9 not in mapa                           # elemento fixo não é tocado


def test_variant_is_chosen_by_fit_not_by_order():
    """Regra 1: a atividade com tabela vai para o molde que TEM tabela, mesmo
    ele não sendo o primeiro do modelo."""
    plano = build_plan(
        modelo(CAPA, SO_TEXTO, COM_TABELA),
        [ActivityContent(title="Com tabela", description="d",
                         tables=[{"columns": ["A"], "rows": [["1"]]}])],
        title="W33",
    )
    conteudo = plano.slides[1]
    assert conteudo.src_slide == 2                 # o molde com tabela
    assert acoes(conteudo)[22][0] == TABLE


def test_activity_without_attachments_avoids_the_slide_full_of_holes():
    """O molde com dois slots de imagem perderia para o molde simples: slot
    vazio é buraco no slide."""
    plano = build_plan(
        modelo(CAPA, SO_TEXTO, COM_IMAGENS),
        [ActivityContent(title="Só texto", description="d")],
        title="W33",
    )
    assert plano.slides[1].src_slide == 1


def test_multi_block_slide_hosts_two_activities():
    """Modelo real do usuário tem DUAS atividades no mesmo slide: os pares
    título/descrição são pareados na ordem de leitura."""
    duplo = {"kind": "custom", "elements": [
        el(40, "title", y=0.10), el(41, "body", y=0.20),
        el(42, "title", y=0.50), el(43, "body", y=0.60),
    ]}
    plano = build_plan(
        modelo(CAPA, duplo),
        [ActivityContent(title="Primeira", description="uma"),
         ActivityContent(title="Segunda", description="duas")],
        title="W33",
    )
    assert len(plano.slides) == 2                  # capa + um slide de conteúdo
    mapa = acoes(plano.slides[1])
    assert mapa[40] == (TEXT, "Primeira")
    assert mapa[41] == (PARAGRAPHS, ["uma"])
    assert mapa[42] == (TEXT, "Segunda")
    assert mapa[43] == (PARAGRAPHS, ["duas"])


def test_unfilled_slots_are_cleared_or_removed():
    """Regra 2: sem isso, texto e anexo da semana anterior vazam para o deck."""
    plano = build_plan(
        modelo(CAPA, COM_IMAGENS),
        [ActivityContent(title="Sem anexo", description="d")],
        title="W33",
    )
    mapa = acoes(plano.slides[1])
    assert mapa[32] == (REMOVE, None)              # slots de imagem vazios saem
    assert mapa[33] == (REMOVE, None)


def test_body_slot_without_description_is_cleared_not_left_stale():
    plano = build_plan(modelo(CAPA, SO_TEXTO), [ActivityContent(title="Só título")],
                       title="W33")
    assert acoes(plano.slides[1])[11] == (CLEAR, None)


def test_extra_images_go_to_a_continuation_slide():
    """Regra 3: 3 imagens num molde de 2 não podem virar 2 imagens e silêncio."""
    plano = build_plan(
        modelo(CAPA, COM_IMAGENS),
        [ActivityContent(title="Evidências", description="d",
                         images=["a.png", "b.png", "c.png"])],
        title="W33",
    )
    assert len(plano.slides) == 3                  # capa + slide + continuação
    primeiro = acoes(plano.slides[1])
    assert primeiro[32] == (IMAGE, "a.png") and primeiro[33] == (IMAGE, "b.png")

    continuacao = acoes(plano.slides[2])
    assert continuacao[32] == (IMAGE, "c.png")
    assert continuacao[31] == (CLEAR, None)        # não repete a descrição
    assert continuacao[30] == (TEXT, "Evidências")  # mas diz de quem é
    assert plano.warnings == []


def test_content_with_no_matching_slot_is_reported_not_dropped():
    plano = build_plan(
        modelo(CAPA, SO_TEXTO),
        [ActivityContent(title="Com imagem", description="d", images=["a.png"])],
        title="W33",
    )
    assert plano.warnings, "sumiu uma imagem sem avisar"
    assert "imagem" in plano.warnings[0].lower()


def test_chart_slot_is_filled_with_chart_data():
    com_grafico = {"kind": "custom", "elements": [
        el(50, "title", y=0.1), el(51, "chart", "image", y=0.4),
    ]}
    grafico = {"categories": ["A", "B"], "series": [("Semana", [1.0, 2.0])]}
    plano = build_plan(
        modelo(CAPA, com_grafico),
        [ActivityContent(title="KPI", charts=[grafico])],
        title="W33",
    )
    assert acoes(plano.slides[1])[51] == (CHART, grafico)


def test_week_label_is_written_on_every_slide():
    plano = build_plan(
        modelo(CAPA, {"kind": "custom", "elements": [
            el(60, "title", y=0.1), el(61, "week_label", y=0.05)]}),
        [ActivityContent(title="A"), ActivityContent(title="B")],
        title="W33", week_label="10/08 a 16/08",
    )
    for slide in plano.slides[1:]:
        assert acoes(slide)[61] == (TEXT, "10/08 a 16/08")


def test_template_without_marked_fields_warns_instead_of_guessing():
    sem_marcas = {"kind": "custom", "elements": [el(70, "static"), el(71, "static")]}
    plano = build_plan(modelo(CAPA, sem_marcas), [ActivityContent(title="A")], title="W33")
    assert any("marque os campos" in w.lower() for w in plano.warnings)


def test_model_without_slides_is_rejected():
    with pytest.raises(ValueError):
        build_plan({"slides": []}, [], title="W33")


def test_activities_with_attachments_are_not_packed_together():
    """Um molde de dois blocos não diz qual slot de imagem é de qual bloco.
    Agrupar atividades COM anexo colocaria a evidência de uma ao lado do texto
    da outra — e a continuação sairia com o título errado."""
    duplo_com_imagem = {"kind": "custom", "elements": [
        el(80, "title", y=0.10), el(81, "body", y=0.20),
        el(82, "title", y=0.50), el(83, "body", y=0.60),
        el(84, "image", "image", y=0.80),
    ]}
    plano = build_plan(
        modelo(CAPA, duplo_com_imagem),
        [ActivityContent(title="Com foto", description="d", images=["a.png"]),
         ActivityContent(title="Outra", description="d2", images=["b.png"])],
        title="W33",
    )
    conteudo = [s for s in plano.slides if s.kind == "content"]
    assert len(conteudo) == 2, "cada atividade com anexo precisa do próprio slide"
    assert conteudo[0].activities == ["Com foto"]
    assert conteudo[1].activities == ["Outra"]


def test_activities_without_attachments_still_share_a_slide():
    """Sem anexo não há ambiguidade — aproveitar os dois blocos é melhor."""
    duplo_com_imagem = {"kind": "custom", "elements": [
        el(80, "title", y=0.10), el(81, "body", y=0.20),
        el(82, "title", y=0.50), el(83, "body", y=0.60),
        el(84, "image", "image", y=0.80),
    ]}
    plano = build_plan(
        modelo(CAPA, duplo_com_imagem),
        [ActivityContent(title="A", description="d"),
         ActivityContent(title="B", description="d2")],
        title="W33",
    )
    conteudo = [s for s in plano.slides if s.kind == "content"]
    assert len(conteudo) == 1
    assert conteudo[0].activities == ["A", "B"]


def test_description_without_a_body_slot_is_reported():
    """Se nenhum molde tem campo de descrição, o texto se perderia calado."""
    so_titulo = {"kind": "custom", "elements": [el(90, "title", y=0.1)]}
    plano = build_plan(
        modelo(CAPA, so_titulo),
        [ActivityContent(title="A", description="descrição que não tem onde entrar")],
        title="W33",
    )
    assert any("descrição de" in w for w in plano.warnings)


def test_continuation_slide_belongs_to_the_owner_activity():
    """A imagem que sobra é da atividade dona — o slide de continuação não pode
    sair com o título de outra."""
    plano = build_plan(
        modelo(CAPA, COM_IMAGENS),
        [ActivityContent(title="Primeira", description="d"),
         ActivityContent(title="Segunda", description="d", images=["a.png", "b.png", "c.png"])],
        title="W33",
    )
    continuacao = [s for s in plano.slides if s.kind == "content"][-1]
    assert continuacao.activities == ["Segunda"]
    assert acoes(continuacao)[30] == (TEXT, "Segunda")


def test_activity_date_slot_is_filled_per_block():
    """Modelos costumam ter a data de cada atividade. Sem slot próprio ela
    repetiria a data da semana do modelo."""
    duplo = {"kind": "custom", "elements": [
        el(100, "title", y=0.10), el(101, "activity_date", y=0.10, x=0.8),
        el(102, "body", y=0.20),
        el(103, "title", y=0.50), el(104, "activity_date", y=0.50, x=0.8),
        el(105, "body", y=0.60),
    ]}
    plano = build_plan(
        modelo(CAPA, duplo),
        [ActivityContent(title="A", description="d", date_label="11/08"),
         ActivityContent(title="B", description="d2", date_label="13/08")],
        title="W33",
    )
    mapa = acoes(plano.slides[1])
    assert mapa[101] == (TEXT, "11/08")
    assert mapa[104] == (TEXT, "13/08")


def test_activity_date_without_value_is_cleared():
    com_data = {"kind": "custom", "elements": [
        el(110, "title", y=0.1), el(111, "activity_date", y=0.1, x=0.8),
    ]}
    plano = build_plan(modelo(CAPA, com_data), [ActivityContent(title="A")], title="W33")
    assert acoes(plano.slides[1])[111] == (CLEAR, None)
