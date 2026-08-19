"""Motor determinístico de análise de planilhas (sem IA).

Os números são a parte crítica: se estes testes passam, o cálculo entregue ao
usuário é confiável independentemente do modelo de IA usado para interpretar o
pedido.
"""
import pytest

from app.services.analysis_engine import (
    AnalysisError,
    compare_with_previous,
    resolve_column,
    run_recipe,
    to_number,
    validate_recipe,
)

COLS = ["Data", "Linha", "Inspecionados", "Aprovados", "Reprovados", "Tipo de defeito"]
ROWS = [
    ["11/08/2026", "Linha 1", "500", "480", "20", "Solda fria"],
    ["11/08/2026", "Linha 3", "400", "340", "60", "Etiqueta"],
    ["12/08/2026", "Linha 1", "520", "500", "20", "Solda fria"],
    ["12/08/2026", "Linha 3", "380", "330", "50", "Parafuso"],
]


def test_ratio_grouped_is_arithmetically_correct():
    out = run_recipe(
        {"operation": "ratio", "numerator": "Aprovados", "denominator": "Inspecionados",
         "group_by": "Linha", "label": "FPY", "unit": "%", "chart_type": "column",
         "decimals": 1},
        COLS, ROWS,
    )
    # Linha 1: (480+500)/(500+520) = 96.078… ; Linha 3: (340+330)/(400+380) = 85.897…
    assert out["rows"] == [["Linha 1", "96.1%"], ["Linha 3", "85.9%"]]
    assert out["chart"]["chart_type"] == "column"
    assert out["chart"]["series"][0]["values"] == [96.1, 85.9]
    assert out["columns"] == ["Linha", "FPY"]


def test_sum_without_group():
    out = run_recipe({"operation": "sum", "value": "Reprovados", "label": "Reprovados",
                      "decimals": 0}, COLS, ROWS)
    assert out["total"] == 150
    assert out["rows"] == [["Total", "150"]]


def test_sum_grouped_by_text_column():
    out = run_recipe({"operation": "sum", "value": "Reprovados", "group_by": "Tipo de defeito",
                      "label": "Reprovados", "chart_type": "pie", "decimals": 0}, COLS, ROWS)
    assert dict(out["rows"])["Solda fria"] == "40"
    assert dict(out["rows"])["Etiqueta"] == "60"
    assert out["chart"]["chart_type"] == "pie"


def test_avg_min_max():
    avg = run_recipe({"operation": "avg", "value": "Inspecionados", "label": "Média",
                      "decimals": 1}, COLS, ROWS)
    assert avg["total"] == 450.0  # (500+400+520+380)/4
    mx = run_recipe({"operation": "max", "value": "Inspecionados", "label": "Máx",
                     "decimals": 0}, COLS, ROWS)
    assert mx["total"] == 520
    mn = run_recipe({"operation": "min", "value": "Inspecionados", "label": "Mín",
                     "decimals": 0}, COLS, ROWS)
    assert mn["total"] == 380


def test_column_matching_is_forgiving():
    """Casa 'aprovados' minúsculo/sem acento com o cabeçalho real."""
    assert resolve_column("aprovados", COLS) == 3
    assert resolve_column("LINHA", COLS) == 1
    assert resolve_column("tipo de defeito", COLS) == 5
    assert resolve_column("nao existe", COLS) is None


def test_number_parsing_ptbr_and_symbols():
    assert to_number("1.234,56") == 1234.56
    assert to_number("1,234.56") == 1234.56
    assert to_number("85%") == 85.0
    assert to_number("R$ 10") == 10.0
    assert to_number("") is None
    assert to_number("texto") is None


def test_invalid_operation_raises_clear_error():
    with pytest.raises(AnalysisError):
        run_recipe({"operation": "hackear", "value": "Reprovados"}, COLS, ROWS)


def test_unknown_column_requires_confirmation():
    spec = validate_recipe({"operation": "sum", "value": "ColunaInexistente"}, COLS)
    assert spec["needs_confirmation"] is True
    assert spec["confidence"] == "low"
    with pytest.raises(AnalysisError):
        run_recipe({"operation": "sum", "value": "ColunaInexistente"}, COLS, ROWS)


def test_no_valid_numbers_raises():
    rows = [["x", "Linha 1", "abc", "def", "ghi", "z"]]
    with pytest.raises(AnalysisError):
        run_recipe({"operation": "sum", "value": "Inspecionados"}, COLS, rows)


def test_compare_with_previous():
    out = run_recipe({"operation": "sum", "value": "Reprovados", "label": "Reprovados",
                      "decimals": 0}, COLS, ROWS)
    txt = compare_with_previous(out, previous_total=120.0, decimals=0)
    assert "acima" in txt
    assert compare_with_previous(out, previous_total=150.0, decimals=0).endswith("anterior.")
    assert compare_with_previous(out, previous_total=None) is None


def test_full_table_reading_trims_empty_columns(tmp_path):
    """A leitura completa (para cálculo) não deve trazer colunas vazias à
    direita — elas poluiriam o formulário de confirmação de colunas."""
    from openpyxl import Workbook
    from app.services.table_extract import extract_full_table

    wb = Workbook()
    ws = wb.active
    ws.append(["Data", "Linha", "Inspecionados", "Aprovados"])
    ws.append(["11/08/2026", "Linha 1", 500, 480])
    ws.append(["12/08/2026", "Linha 3", 400, 340])
    path = tmp_path / "t.xlsx"
    wb.save(str(path))

    table = extract_full_table(path.read_bytes(), "t.xlsx")
    assert table["columns"] == ["Data", "Linha", "Inspecionados", "Aprovados"]
    assert len(table["rows"]) == 2
    # e o motor calcula sobre ela
    out = run_recipe({"operation": "ratio", "numerator": "Aprovados",
                      "denominator": "Inspecionados", "group_by": "Linha",
                      "label": "FPY", "unit": "%", "decimals": 1},
                     table["columns"], table["rows"])
    assert out["rows"] == [["Linha 1", "96.0%"], ["Linha 3", "85.0%"]]


def test_unit_placeholder_from_ai_is_not_appended():
    """A IA às vezes devolve unit='vazio'/'none'/'un' quando não há unidade —
    isso nunca pode virar sufixo no número ('55vazio')."""
    for junk in ("vazio", "none", "N/A", "un", "unidade", ""):
        out = run_recipe({"operation": "sum", "value": "Reprovados",
                          "group_by": "Tipo de defeito", "label": "Reprovados",
                          "unit": junk, "decimals": 0}, COLS, ROWS)
        assert dict(out["rows"])["Etiqueta"] == "60", f"unit={junk!r} vazou no valor"
    # unidade real continua sendo aplicada
    out = run_recipe({"operation": "sum", "value": "Reprovados", "label": "Reprovados",
                      "unit": "pçs", "decimals": 0}, COLS, ROWS)
    assert out["rows"][0][1] == "150pçs"


# ── Ranking (top N) e agrupamento por dois campos ───────────────────────────
# Calibrado com uma planilha real de assistência técnica:
# colunas Modelo | Sintoma | Quantidade de Sintomas | Mês | Assistência
ASSIST_COLS = ["Modelo", "Sintoma", "Quantidade de Sintomas", "Mês", "Assistência"]
ASSIST_ROWS = [
    ["SM-A556E", "Tela com falha", "18", "Julho", "AT-1001"],
    ["SM-A556E", "Bateria fraca", "12", "Julho", "AT-1002"],
    ["SM-A556E", "Não liga", "15", "Julho", "AT-1003"],
    ["SM-A346M", "Tela com falha", "11", "Julho", "AT-1004"],
    ["SM-A346M", "Não liga", "16", "Julho", "AT-1005"],
    ["SM-A556E", "Tela com falha", "20", "Agosto", "AT-1006"],
    ["SM-A346M", "Bateria fraca", "9", "Agosto", "AT-1007"],
]


def test_top_n_ranking_desc():
    """'Top 3 piores sintomas' → ordena por valor e corta em 3."""
    out = run_recipe({"operation": "sum", "value": "Quantidade de Sintomas",
                      "group_by": "Sintoma", "label": "Ocorrências",
                      "top": 3, "order": "desc", "decimals": 0},
                     ASSIST_COLS, ASSIST_ROWS)
    # Tela: 18+11+20=49 ; Não liga: 15+16=31 ; Bateria: 12+9=21
    assert out["rows"] == [["Tela com falha", "49"], ["Não liga", "31"],
                           ["Bateria fraca", "21"]]


def test_top_n_ranking_asc_gets_smallest():
    out = run_recipe({"operation": "sum", "value": "Quantidade de Sintomas",
                      "group_by": "Sintoma", "label": "Ocorrências",
                      "top": 1, "order": "asc", "decimals": 0},
                     ASSIST_COLS, ASSIST_ROWS)
    assert out["rows"] == [["Bateria fraca", "21"]]


def test_group_by_two_columns():
    """'por modelo e por mês' → chave composta 'Modelo · Mês'."""
    out = run_recipe({"operation": "sum", "value": "Quantidade de Sintomas",
                      "group_by": "Modelo", "group_by2": "Mês",
                      "label": "Ocorrências", "top": 4, "decimals": 0},
                     ASSIST_COLS, ASSIST_ROWS)
    assert out["columns"][0] == "Modelo · Mês"
    linhas = dict(out["rows"])
    assert linhas["SM-A556E · Julho"] == "45"   # 18+12+15
    assert linhas["SM-A556E · Agosto"] == "20"
    assert linhas["SM-A346M · Julho"] == "27"   # 11+16


def test_recipe_with_swapped_slots_is_normalized():
    """Modelos menores às vezes põem a coluna em 'numerator' numa soma.
    Caso real observado com gemma: deve calcular, não pedir confirmação."""
    recipe_da_ia = {"operation": "sum", "numerator": "Quantidade de Sintomas",
                    "denominator": None, "value": None, "group_by": "Sintoma",
                    "top": 3, "order": "desc", "label": "Top 3", "unit": None,
                    "decimals": 0}
    spec = validate_recipe(recipe_da_ia, ASSIST_COLS)
    assert spec["needs_confirmation"] is False
    out = run_recipe(recipe_da_ia, ASSIST_COLS, ASSIST_ROWS)
    assert out["rows"][0] == ["Tela com falha", "49"]


def test_ratio_with_value_instead_of_numerator_is_normalized():
    recipe = {"operation": "ratio", "value": "Aprovados",
              "denominator": "Inspecionados", "group_by": "Linha",
              "label": "FPY", "unit": "%", "decimals": 1}
    out = run_recipe(recipe, COLS, ROWS)
    assert out["rows"] == [["Linha 1", "96.1%"], ["Linha 3", "85.9%"]]


def test_total_covers_all_groups_even_when_the_table_is_truncated():
    """Com mais grupos que o limite de exibição, o total precisa continuar
    sendo o da base inteira — senão vai um número errado para o deck."""
    from app.services.analysis_engine import MAX_GROUPS

    columns = ["Cod", "Qtd"]
    rows = [[f"C{i}", "1"] for i in range(200)]
    out = run_recipe({"operation": "sum", "value": "Qtd", "group_by": "Cod",
                      "label": "Ocorrências", "decimals": 0}, columns, rows)
    assert len(out["rows"]) == MAX_GROUPS
    assert out["total"] == 200            # e não 30
    assert out["groups_total"] == 200
    assert "de 200 grupos" in out["summary"]


def test_top_n_keeps_the_grand_total_and_does_not_warn():
    """Top N é um corte PEDIDO pelo usuário: nada de aviso, mas o total
    continua sendo o da base."""
    columns = ["Sintoma", "Qtd"]
    rows = [["A", "10"], ["B", "6"], ["C", "3"], ["D", "1"]]
    out = run_recipe({"operation": "sum", "value": "Qtd", "group_by": "Sintoma",
                      "top": 2, "order": "desc", "label": "Top 2", "decimals": 0},
                     columns, rows)
    assert [r[0] for r in out["rows"]] == ["A", "B"]
    assert out["total"] == 20             # 10+6+3+1, não 16
    assert "grupos)" not in out["summary"]
