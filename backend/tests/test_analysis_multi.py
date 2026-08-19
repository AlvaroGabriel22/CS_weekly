"""Múltiplas análises num pedido só (formato `analyses` da IA)."""
import asyncio
import json

import app.services.analysis_ai as ai
from app.services.analysis_engine import run_recipe
from app.services.llm_service import LLMResponse

COLS = ["Modelo", "Sintoma", "Quantidade de Sintomas", "Mês", "Assistência"]
ROWS = [
    ["SM-A556E", "Tela com falha", "18", "Julho", "AT-1001"],
    ["SM-A556E", "Não liga", "15", "Julho", "AT-1002"],
    ["SM-A346M", "Tela com falha", "11", "Julho", "AT-1001"],
]


class _FakeMulti:
    def __init__(self, *a, **k): pass
    async def generate(self, prompt, system=None, images=None, json_mode=False):
        payload = {"analyses": [
            {"operation": "sum", "value": "Quantidade de Sintomas",
             "group_by": "Sintoma", "top": 3, "order": "desc",
             "label": "Top sintomas", "unit": "", "decimals": 0},
            {"operation": "sum", "value": "Quantidade de Sintomas",
             "group_by": "Assistência", "top": 3, "order": "desc",
             "label": "Top assistências", "unit": "", "decimals": 0},
        ]}
        return LLMResponse(content=json.dumps(payload), model="fake")


def test_two_analyses_in_one_request(monkeypatch):
    monkeypatch.setattr(ai, "LLMService", _FakeMulti)
    recipes, source = asyncio.get_event_loop().run_until_complete(
        ai.build_recipes("top 3 sintomas e top 3 assistências", COLS, ROWS)
    )
    assert source == "ai"
    assert len(recipes) == 2
    out = [run_recipe(r, COLS, ROWS) for r in recipes]
    assert out[0]["rows"][0] == ["Tela com falha", "29"]   # 18+11
    assert out[1]["rows"][0] == ["AT-1001", "29"]          # 18+11


class _FakeSingle:
    def __init__(self, *a, **k): pass
    async def generate(self, prompt, system=None, images=None, json_mode=False):
        payload = {"operation": "sum", "value": "Quantidade de Sintomas",
                   "group_by": "Sintoma", "label": "Total", "decimals": 0}
        return LLMResponse(content=json.dumps(payload), model="fake")


def test_single_object_format_still_works(monkeypatch):
    """Compatibilidade: se a IA devolver um objeto só (sem `analyses`)."""
    monkeypatch.setattr(ai, "LLMService", _FakeSingle)
    recipes, _ = asyncio.get_event_loop().run_until_complete(
        ai.build_recipes("total por sintoma", COLS, ROWS)
    )
    assert len(recipes) == 1
    assert run_recipe(recipes[0], COLS, ROWS)["rows"]


def test_value_with_number_instead_of_column_is_recovered():
    """Caso real (gemma): a IA põe um NÚMERO em 'value' ("58") em vez do nome
    da coluna, e a coluna certa fica em 'numerator'. Deve calcular mesmo assim."""
    receita = {"operation": "sum", "numerator": "Quantidade de Sintomas",
               "denominator": None, "value": "58", "group_by": "Sintoma",
               "top": 3, "order": "desc", "label": "Top 3", "unit": "", "decimals": 0}
    out = run_recipe(receita, COLS, ROWS)
    assert out["rows"][0] == ["Tela com falha", "29"]  # 18 + 11
    assert out["columns"][0] == "Sintoma"


def test_count_is_corrected_to_sum_when_quantity_column_exists():
    """Caso real: a IA escolhe 'count' (conta linhas) quando o usuário pediu a
    'quantidade total de ocorrências' e a planilha TEM coluna de quantidade.
    Deve virar sum sobre essa coluna — senão o número sai errado (6 vs 88)."""
    from app.services.analysis_ai import _clean_recipe

    receita_gemma = {"operation": "count", "numerator": "Sintoma", "value": None,
                     "group_by": "Sintoma", "top": 3, "order": "desc",
                     "label": "Top 3", "unit": "", "decimals": 0}
    fixed = _clean_recipe(dict(receita_gemma), COLS)
    assert fixed["operation"] == "sum"
    assert fixed["value"] == "Quantidade de Sintomas"
    out = run_recipe(fixed, COLS, ROWS)
    assert out["rows"][0] == ["Tela com falha", "29"]  # 18+11, não "2" linhas


def test_count_is_kept_when_there_is_no_quantity_column():
    """Sem coluna de quantidade, contar linhas é o correto — não mexer."""
    from app.services.analysis_ai import _clean_recipe

    cols = ["Modelo", "Sintoma", "Mês"]
    rows = [["A", "Tela", "Julho"], ["B", "Tela", "Julho"], ["C", "Não liga", "Julho"]]
    fixed = _clean_recipe({"operation": "count", "group_by": "Sintoma",
                           "label": "Ocorrências", "decimals": 0}, cols)
    assert fixed["operation"] == "count"
    out = run_recipe(fixed, cols, rows)
    assert dict(out["rows"])["Tela"] == "2"


def test_duplicate_recipes_are_deduped():
    """A IA às vezes devolve N análises com rótulos diferentes mas o MESMO
    cálculo — mostrar a mesma tabela duas vezes confunde o usuário."""
    from app.services.analysis_ai import _dedupe

    base = {"operation": "sum", "value": "Quantidade de Sintomas",
            "group_by": "Sintoma", "top": 3, "order": "desc"}
    unique = _dedupe([dict(base, label="Top 3 Sintomas"),
                      dict(base, label="Top 3 Assistências"),
                      dict(base, group_by="Assistência", label="Por assistência")])
    assert len(unique) == 2
    assert unique[0]["label"] == "Top 3 Sintomas"
    assert unique[1]["group_by"] == "Assistência"


def test_unrequested_second_group_is_dropped():
    """Caso real: pedido só cita sintomas, mas a IA agrupou por Sintoma E
    Modelo — o ranking sai fatiado ('Tela com falha · SM-A556E')."""
    from app.services.analysis_ai import _clean_recipe

    pedido = "Top 3 piores sintomas pela quantidade total de ocorrências"
    fixed = _clean_recipe({"operation": "sum", "value": "Quantidade de Sintomas",
                           "group_by": "Sintoma", "group_by2": "Modelo",
                           "top": 3, "order": "desc", "label": "Top 3"},
                          COLS, pedido)
    assert fixed["group_by2"] is None
    out = run_recipe(fixed, COLS, ROWS)
    assert " · " not in out["rows"][0][0]


def test_requested_second_group_is_kept():
    """Se o pedido cita as duas colunas, o 2º agrupamento é legítimo."""
    from app.services.analysis_ai import _clean_recipe

    fixed = _clean_recipe({"operation": "sum", "value": "Quantidade de Sintomas",
                           "group_by": "Sintoma", "group_by2": "Modelo",
                           "label": "Por sintoma e modelo"},
                          COLS, "quantidade por sintoma e por modelo")
    assert fixed["group_by2"] == "Modelo"


def test_dedupe_uses_resolved_recipe():
    """Caso real: a IA devolveu a mesma análise duas vezes, uma com a coluna em
    'value' e outra em 'numerator'. Calculam o mesmo — deve sobrar uma."""
    from app.services.analysis_ai import _dedupe

    a = {"operation": "sum", "numerator": "Quantidade de Sintomas",
         "group_by": "Sintoma", "top": 3, "order": "desc", "label": "Sintomas"}
    b = {"operation": "sum", "value": "Quantidade de Sintomas",
         "group_by": "Sintoma", "top": 3, "order": "desc", "label": "Assistências"}
    assert len(_dedupe([a, b], COLS)) == 1
    assert len(_dedupe([a, b])) == 2  # sem colunas, comparação crua


def test_group_by_follows_the_column_named_in_the_request():
    """Caso real: pedimos 'top 3 assistências' e a IA repetiu group_by='Sintoma'
    (com o rótulo certo). O pedido nomeia a coluna — o código corrige."""
    from app.services.analysis_ai import _clean_recipe

    fixed = _clean_recipe(
        {"operation": "sum", "value": "Quantidade de Sintomas", "group_by": "Sintoma",
         "top": 3, "order": "desc", "label": "Top 3 Piores Assistências"},
        COLS,
        "Top 3 piores assistências, considerando a quantidade total de ocorrências",
    )
    assert fixed["group_by"] == "Assistência"


def test_group_by_is_kept_when_the_request_names_it():
    from app.services.analysis_ai import _clean_recipe

    fixed = _clean_recipe(
        {"operation": "sum", "value": "Quantidade de Sintomas", "group_by": "Sintoma",
         "top": 3, "order": "desc", "label": "Top 3"},
        COLS, "Top 3 piores sintomas",
    )
    assert fixed["group_by"] == "Sintoma"


def test_group_by_is_never_invented():
    """Sem agrupamento na receita, o código não cria um — mesmo que o pedido
    cite colunas. Um total não pode virar tabela por conta própria."""
    from app.services.analysis_ai import _clean_recipe

    fixed = _clean_recipe(
        {"operation": "sum", "value": "Quantidade de Sintomas", "label": "Total"},
        COLS, "total de sintomas no mês",
    )
    assert not fixed.get("group_by")
