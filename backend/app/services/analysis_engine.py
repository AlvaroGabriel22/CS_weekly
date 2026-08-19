"""Motor determinístico de análise de planilhas.

Divisão de responsabilidades (importante):
  • A IA apenas INTERPRETA o pedido do usuário e devolve uma RECEITA
    estruturada (qual coluna, qual operação, agrupar por quê).
  • Este módulo EXECUTA a receita com aritmética pura — nenhum número vem do
    LLM. Assim os resultados são auditáveis, reprodutíveis e não variam com o
    modelo. Da segunda semana em diante a receita salva roda sem chamar IA.

Vocabulário FECHADO de operações (nada de código gerado por IA sendo
executado): sum, avg, count, ratio (percentual/razão), min, max.
Opcionalmente agrupado por uma coluna (group_by).
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

OPERATIONS = {"sum", "avg", "count", "ratio", "min", "max"}
CHART_TYPES = {"column", "bar", "line", "pie", "none"}
MAX_GROUPS = 30  # categorias no gráfico/tabela


class AnalysisError(Exception):
    """Erro com mensagem pronta para o usuário (PT)."""


# ───────────────────────────── normalização ─────────────────────────────────

def _norm(text: str) -> str:
    """Normaliza nome de coluna para casar 'Nº Aprovados' com 'aprovados'."""
    text = str(text or "").strip().lower()
    for a, b in (("á", "a"), ("à", "a"), ("ã", "a"), ("â", "a"), ("é", "e"),
                 ("ê", "e"), ("í", "i"), ("ó", "o"), ("õ", "o"), ("ô", "o"),
                 ("ú", "u"), ("ç", "c")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "", text)


# Palavras que a IA usa para dizer "sem unidade" — não viram sufixo no número.
_EMPTY_UNITS = {"", "vazio", "none", "null", "nenhum", "nenhuma", "n/a", "na",
                "un", "unidade", "unidades", "-", "sem unidade", "count",
                "contagem", "número", "numero", "qtd", "quantidade"}


def _clean_unit(raw: object) -> str:
    """Unidade válida ('%', 'kg'…) ou '' quando a IA disser que não há."""
    unit = str(raw or "").strip()
    return "" if unit.lower() in _EMPTY_UNITS else unit[:10]


def resolve_column(name: str, columns: list[str]) -> int | None:
    """Índice da coluna cujo cabeçalho casa com `name` (exato → normalizado →
    contido). Devolve None se não achar."""
    if not name:
        return None
    target = _norm(name)
    normalized = [_norm(c) for c in columns]
    if target in normalized:
        return normalized.index(target)
    for idx, col in enumerate(normalized):
        if col and (target in col or col in target):
            return idx
    return None


def to_number(value: Any) -> float | None:
    """Converte célula em número, tolerando '1.234,56', '85%', 'R$ 10'."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("%", "").replace("R$", "").replace(" ", "")
    # 1.234,56 (pt-BR) → 1234.56 ; 1,234.56 (en) → 1234.56
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") \
            else text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


# ───────────────────────────── validação da receita ──────────────────────────

def validate_recipe(recipe: dict, columns: list[str]) -> dict:
    """Valida a receita contra as colunas reais. Devolve a receita normalizada
    com os índices resolvidos e um nível de confiança.

    Levanta AnalysisError com mensagem clara se for irrecuperável.
    """
    if not isinstance(recipe, dict):
        raise AnalysisError("Não consegui entender o que calcular.")

    operation = str(recipe.get("operation", "")).strip().lower()
    if operation not in OPERATIONS:
        raise AnalysisError(
            "Não consegui identificar o cálculo pedido. "
            "Tente algo como “média de X por linha” ou “percentual de aprovados”."
        )

    resolved: dict[str, Any] = {
        "operation": operation,
        "label": str(recipe.get("label") or "Resultado")[:80],
        # Normaliza a unidade: a IA às vezes devolve literalmente "vazio",
        # "none", "un" etc. quando não há unidade — tratamos como sem sufixo.
        "unit": _clean_unit(recipe.get("unit")),
        "chart_type": (str(recipe.get("chart_type") or "column").lower()
                       if str(recipe.get("chart_type") or "column").lower() in CHART_TYPES
                       else "column"),
        "decimals": min(max(int(recipe.get("decimals", 1) or 0), 0), 3),
    }

    # Modelos menores às vezes trocam os slots: colocam a coluna em
    # `numerator` mesmo numa soma/média, ou em `value` numa razão. Normaliza
    # antes de validar — é erro de preenchimento, não de entendimento.
    recipe = dict(recipe)
    # Descarta valores que não correspondem a nenhuma coluna (modelos menores
    # às vezes põem um NÚMERO no lugar do nome da coluna, ex.: "value": "58").
    for key in ("numerator", "denominator", "value", "group_by", "group_by2"):
        raw = recipe.get(key)
        if raw and resolve_column(str(raw), columns) is None:
            recipe[key] = None
    if operation != "ratio" and not recipe.get("value"):
        recipe["value"] = recipe.get("numerator") or recipe.get("denominator")
    if operation == "ratio":
        if not recipe.get("numerator") and recipe.get("value"):
            recipe["numerator"] = recipe.get("value")

    misses: list[str] = []

    def _col(key: str, required: bool) -> int | None:
        raw = recipe.get(key)
        if not raw:
            if required:
                misses.append(key)
            return None
        idx = resolve_column(str(raw), columns)
        if idx is None:
            misses.append(f"{key}={raw}")
        return idx

    if operation == "ratio":
        resolved["numerator"] = _col("numerator", True)
        resolved["denominator"] = _col("denominator", True)
    elif operation == "count":
        resolved["value"] = _col("value", False)  # count não exige coluna
    else:
        resolved["value"] = _col("value", True)

    resolved["group_by"] = _col("group_by", False)
    # Agrupamento por um SEGUNDO campo (ex.: "por modelo e por mês").
    resolved["group_by2"] = _col("group_by2", False)
    # Ranking: top N (maiores) ou bottom N (menores). 0 = todos.
    try:
        resolved["top"] = max(0, min(int(recipe.get("top") or 0), MAX_GROUPS))
    except (TypeError, ValueError):
        resolved["top"] = 0
    resolved["order"] = "asc" if str(recipe.get("order", "")).lower() == "asc" else "desc"
    resolved["missing"] = misses
    # Confiança: alta se resolveu tudo; baixa se faltou algo essencial.
    resolved["confidence"] = "low" if misses else "high"
    if misses and operation != "count":
        # Não conseguimos casar colunas essenciais → o chamador deve pedir
        # confirmação ao usuário em vez de entregar número errado.
        resolved["needs_confirmation"] = True
    else:
        resolved["needs_confirmation"] = False
    return resolved


# ───────────────────────────── execução ──────────────────────────────────────

def _aggregate(operation: str, values: list[float]) -> float | None:
    if not values:
        return None
    if operation == "sum":
        return sum(values)
    if operation == "avg":
        return sum(values) / len(values)
    if operation == "min":
        return min(values)
    if operation == "max":
        return max(values)
    if operation == "count":
        return float(len(values))
    return None


def run_recipe(recipe: dict, columns: list[str], rows: list[list[Any]]) -> dict:
    """Executa a receita sobre a planilha. Aritmética pura, sem IA.

    Devolve {"rows": [[grupo, valor_formatado], ...], "chart": {...} | None,
             "summary": "...", "total": float | None}
    """
    spec = validate_recipe(recipe, columns)
    if spec["needs_confirmation"]:
        raise AnalysisError(
            "Não consegui identificar com segurança as colunas necessárias. "
            "Confirme quais colunas usar."
        )

    operation = spec["operation"]
    group_idx = spec["group_by"]
    decimals = spec["decimals"]
    unit = spec["unit"]

    def cell(row: list[Any], idx: int | None) -> Any:
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    # Agrupa por 1 ou 2 campos (ou um único grupo "Total")
    group2_idx = spec.get("group_by2")
    buckets: dict[str, list[list[Any]]] = {}
    for row in rows:
        if group_idx is None:
            key = "Total"
        else:
            part1 = str(cell(row, group_idx) or "").strip()
            if not part1:
                continue  # linha sem grupo é ignorada
            key = part1
            if group2_idx is not None:
                part2 = str(cell(row, group2_idx) or "").strip()
                if not part2:
                    continue
                key = f"{part1} · {part2}"
        buckets.setdefault(key, []).append(row)

    if not buckets:
        raise AnalysisError("A planilha não tem linhas de dados para calcular.")

    results: list[tuple[str, float]] = []
    for key, group_rows in buckets.items():
        if operation == "ratio":
            num = [to_number(cell(r, spec["numerator"])) for r in group_rows]
            den = [to_number(cell(r, spec["denominator"])) for r in group_rows]
            total_num = sum(v for v in num if v is not None)
            total_den = sum(v for v in den if v is not None)
            if not total_den:
                continue
            value = total_num / total_den * (100 if unit == "%" or not unit else 1)
        elif operation == "count":
            idx = spec.get("value")
            if idx is None:
                value = float(len(group_rows))
            else:
                value = float(sum(1 for r in group_rows if str(cell(r, idx) or "").strip()))
        else:
            nums = [to_number(cell(r, spec["value"])) for r in group_rows]
            nums = [n for n in nums if n is not None]
            agg = _aggregate(operation, nums)
            if agg is None:
                continue
            value = agg
        results.append((key, round(value, decimals)))

    if not results:
        raise AnalysisError(
            "Não encontrei números válidos nas colunas indicadas. "
            "Confira se a planilha tem os dados esperados."
        )

    # Total sobre TODOS os grupos — calculado ANTES de qualquer corte, senão o
    # número reportado seria só o dos grupos exibidos (30 em vez de 200).
    total = None
    if len(results) == 1:
        total = results[0][1]
    elif operation in {"sum", "count"}:
        total = round(sum(v for _, v in results), decimals)

    # Ranking: ordena e corta os N primeiros ("top 3 piores sintomas").
    top_n = spec.get("top") or 0
    if top_n or spec.get("order") == "asc":
        results.sort(key=lambda kv: kv[1], reverse=(spec.get("order") != "asc"))
    groups_total = len(results)
    results = results[: (top_n or MAX_GROUPS)]
    # Corte por limite do sistema (não pedido pelo usuário) precisa ser dito.
    omitted = 0 if top_n else groups_total - len(results)

    suffix = unit if unit else ("%" if operation == "ratio" else "")
    fmt = f"{{:.{decimals}f}}"
    table_rows = [[k, f"{fmt.format(v)}{suffix}"] for k, v in results]

    chart = None
    if spec["chart_type"] != "none" and len(results) >= 2:
        chart = {
            "chart_type": spec["chart_type"],
            "categories": [k for k, _ in results],
            "series": [{"name": spec["label"], "values": [v for _, v in results]}],
        }

    group_label = columns[group_idx] if group_idx is not None and group_idx < len(columns) else None
    if group_label and group2_idx is not None and group2_idx < len(columns):
        group_label = f"{group_label} · {columns[group2_idx]}"
    if group_label:
        summary = f"{spec['label']} por {group_label}: " + "; ".join(
            f"{k} {fmt.format(v)}{suffix}" for k, v in results[:6]
        )
    else:
        summary = f"{spec['label']}: {fmt.format(results[0][1])}{suffix}"
    if omitted:
        summary += f" (mostrando {len(results)} de {groups_total} grupos)"

    return {
        "label": spec["label"],
        "columns": [group_label or "Item", spec["label"]],
        "rows": table_rows,
        "chart": chart,
        "summary": summary[:400],
        "total": total,
        "operation": operation,
        "group_by": group_label,
        "groups_total": groups_total,
        "groups_shown": len(results),
    }


def compare_with_previous(current: dict, previous_total: float | None, decimals: int = 1) -> str | None:
    """Frase de comparação com a semana anterior (se houver base)."""
    if previous_total is None or current.get("total") is None:
        return None
    delta = current["total"] - previous_total
    if abs(delta) < 10 ** -decimals:
        return f"{current['label']}: estável em relação à semana anterior."
    direction = "acima" if delta > 0 else "abaixo"
    return (f"{current['label']}: {abs(delta):.{decimals}f} {direction} "
            f"da semana anterior ({previous_total:.{decimals}f}).")
