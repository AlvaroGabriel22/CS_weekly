"""Medição de texto com a fonte real (app/services/text_metrics.py).

As asserções são RELATIVAS de propósito: a suíte roda em Linux (dev/CI) e o
deploy é Windows, com outro conjunto de fontes. Fixar pixels quebraria numa
máquina e passaria na outra escondendo o erro.
"""
from app.services import text_metrics as tm


FAMILIA = "Arial"


def test_width_grows_with_the_text_and_with_the_font_size():
    curto = tm.text_width("Falha", FAMILIA, 14)
    longo = tm.text_width("Falha de bateria na linha 3", FAMILIA, 14)
    assert 0 < curto < longo

    assert tm.text_width("Falha", FAMILIA, 28) > curto * 1.8  # ~dobro


def test_bold_is_not_narrower_than_regular():
    normal = tm.text_width("Análise de falhas", FAMILIA, 14)
    negrito = tm.text_width("Análise de falhas", FAMILIA, 14, bold=True)
    assert negrito >= normal


def test_line_height_is_close_to_the_font_size():
    """ascent + descent costuma dar ~1,2 em. Se der algo fora disso, a fonte
    foi lida errado e toda a paginação sai torta."""
    altura = tm.line_height(FAMILIA, 18)
    em_polegadas = 18 / 72
    assert 1.0 * em_polegadas <= altura <= 1.6 * em_polegadas


def test_wrap_respects_the_box_width():
    texto = ("Durante a semana tratamos as falhas de bateria reportadas pela "
             "assistência técnica regional e revisamos o plano de ação.")
    largura = 3.0
    linhas = tm.wrap_text(texto, largura, FAMILIA, 12)
    assert len(linhas) > 1
    for linha in linhas:
        assert tm.text_width(linha, FAMILIA, 12) <= largura + 0.01


def test_narrower_box_produces_more_lines():
    texto = "Falha intermitente no carregamento durante o teste funcional."
    assert len(tm.wrap_text(texto, 2.0, FAMILIA, 12)) > len(
        tm.wrap_text(texto, 6.0, FAMILIA, 12)
    )


def test_a_single_word_longer_than_the_box_is_broken():
    linhas = tm.wrap_text("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 4, 1.0, FAMILIA, 14)
    assert len(linhas) > 1
    for linha in linhas:
        assert tm.text_width(linha, FAMILIA, 14) <= 1.01


def test_line_breaks_of_the_original_text_are_kept():
    linhas = tm.wrap_text("Equipamento: A276\nDefeito: não liga", 6.0, FAMILIA, 12)
    assert linhas[0].startswith("Equipamento")
    assert any(l.startswith("Defeito") for l in linhas)


def test_text_that_fits_keeps_the_original_size():
    encaixe = tm.fit_text("Título curto", width=6.0, height=1.0,
                          family=FAMILIA, size_pt=18)
    assert encaixe.font_size == 18
    assert not encaixe.overflow and not encaixe.truncated
    assert encaixe.height <= 1.0


def test_long_text_is_shrunk_before_being_cut():
    """Reduzir o corpo preserva o conteúdo; cortar perde informação. A ordem
    importa."""
    texto = ("Análise detalhada das falhas observadas na linha de montagem "
             "durante a semana, com as ações tomadas e os responsáveis. ") * 3
    encaixe = tm.fit_text(texto, width=4.0, height=1.2, family=FAMILIA, size_pt=14)
    assert encaixe.font_size < 14
    assert encaixe.font_size >= tm.MIN_FONT_PT


def test_text_that_does_not_fit_even_shrunk_is_marked_truncated():
    texto = "Linha de texto bem comprida para forçar o estouro. " * 40
    encaixe = tm.fit_text(texto, width=2.0, height=0.5, family=FAMILIA, size_pt=14)
    assert encaixe.overflow and encaixe.truncated
    assert encaixe.lines[-1].endswith("…")     # o corte fica visível
    assert encaixe.height <= 0.5 + 1e-6        # nunca invade o vizinho


def test_shrink_can_be_disabled():
    texto = "Texto que não cabe de jeito nenhum nesta caixa minúscula. " * 5
    encaixe = tm.fit_text(texto, width=1.5, height=0.4, family=FAMILIA,
                          size_pt=14, allow_shrink=False)
    assert encaixe.font_size == 14
    assert encaixe.overflow


def test_a_font_that_does_not_exist_is_reported_not_silently_replaced():
    """O PowerPoint substitui a fonte ausente e o layout muda. Isso tem que ser
    dito ANTES de gerar."""
    ref = tm.resolve_font("Fonte Que Nao Existe 12345")
    assert ref.exact is False
    assert "Fonte Que Nao Existe 12345" in tm.missing_fonts(
        ["Fonte Que Nao Existe 12345", None, ""]
    )


def test_measuring_still_works_with_a_missing_font():
    """Mesmo sem a fonte, medimos com a substituta — melhor que não medir."""
    largura = tm.text_width("Análise", "Fonte Que Nao Existe 12345", 14)
    assert largura > 0
