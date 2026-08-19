"""Interpretação do pedido do usuário → RECEITA de análise.

A IA lê o pedido em português + os cabeçalhos e uma amostra de linhas, e devolve
APENAS a receita estruturada (qual coluna, qual operação). Nenhum número vem
daqui — o cálculo é feito por app/services/analysis_engine.py.

Se a IA estiver indisponível ou responder fora do contrato, há um fallback
heurístico que cobre os pedidos mais comuns (percentual/soma/média por coluna),
para o usuário não ficar travado.
"""
from __future__ import annotations

import json
import re
import logging

from app.services.analysis_engine import (
    OPERATIONS,
    _norm,
    resolve_column,
    validate_recipe,
)
from app.services.llm_service import LLMService, QUALITY_DEPT_CONTEXT

logger = logging.getLogger(__name__)

SAMPLE_ROWS = 6

RECIPE_SYSTEM = (
    f"{QUALITY_DEPT_CONTEXT} "
    "Você traduz um pedido de análise em uma RECEITA estruturada. Você NÃO "
    "calcula nada — apenas indica QUAIS COLUNAS e QUAL OPERAÇÃO usar.\n"
    "Operações válidas: sum (soma), avg (média), count (contagem), "
    "ratio (percentual/razão entre duas colunas), min, max.\n"
    "Use EXATAMENTE os nomes de coluna fornecidos.\n"
    "IMPORTANTE — sum vs. count: se a planilha JÁ TEM uma coluna numérica com a "
    "quantidade (ex.: 'Quantidade de Sintomas', 'Ocorrências', 'Total'), use "
    "operation='sum' com value=essa coluna. Só use count quando NÃO houver "
    "coluna de quantidade (aí cada linha vale 1). 'quantidade total de "
    "ocorrências' quase sempre significa SOMAR a coluna de quantidade.\n"
    "Preencha SEMPRE 'value' (para sum/avg/min/max/count) ou 'numerator' e "
    "'denominator' (para ratio) com NOMES DE COLUNA — nunca com números.\n"
    "O pedido pode conter MAIS DE UMA análise (ex.: 'top 3 sintomas E top 3 "
    "assistências'). Responda SEMPRE com a lista `analyses`, com um objeto por "
    "análise pedida (1 a 4).\n"
    "Formato da resposta (JSON puro):\n"
    '{"analyses":[\n'
    '{"operation":"ratio","numerator":"<coluna>","denominator":"<coluna>",'
    '"value":"<coluna p/ sum|avg|min|max|count>","group_by":"<coluna ou vazio>",'
    '"group_by2":"<2ª coluna de agrupamento ou vazio>","top":<0 = todos, N = top N>,'
    '"order":"desc|asc",'
    '"label":"<nome curto do indicador>","unit":"%" apenas para percentual, senão string vazia "",'
    '"chart_type":"column|bar|line|pie|none","decimals":0..3}\n'
    "]}\n"
    "Regras: para percentual use ratio com unit '%'. Só preencha group_by se o "
    "pedido indicar um agrupamento (por linha, por turno, por defeito...). "
    "Se o pedido pedir DOIS agrupamentos ('por modelo e por mês'), use group_by "
    "e group_by2. Para rankings ('top 3 piores', 'os 5 maiores') use top=N com "
    "order='desc'; para 'os menores' use order='asc'. "
    "Se o pedido for ambíguo, escolha a interpretação mais provável. "
    "Responda APENAS com o JSON."
)


def _sample_block(columns: list[str], rows: list[list]) -> str:
    sample = [columns] + [list(map(str, r))[: len(columns)] for r in rows[:SAMPLE_ROWS]]
    return json.dumps(sample, ensure_ascii=False)


def _parse_json(raw: str) -> dict | None:
    if not raw:
        return None
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(raw[start:end])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def heuristic_recipe(request: str, columns: list[str]) -> dict | None:
    """Fallback sem IA: cobre os pedidos mais comuns.

    Procura uma operação pelas palavras do pedido e casa colunas citadas.
    """
    text = (request or "").lower()
    mentioned = [c for c in columns if c and c.lower() in text]

    # agrupamento explícito ("por linha", "por turno"...)
    group = None
    for col in columns:
        if col and f"por {col.lower()}" in text:
            group = col
            break

    if any(w in text for w in ("percentual", "porcentagem", "%", "taxa", "fpy", "razão", "razao")):
        if len(mentioned) >= 2:
            return {"operation": "ratio", "numerator": mentioned[0],
                    "denominator": mentioned[1], "group_by": group,
                    "label": "Percentual", "unit": "%", "chart_type": "column",
                    "decimals": 1}
        return None
    for word, op in (("soma", "sum"), ("total", "sum"), ("média", "avg"), ("media", "avg"),
                     ("contagem", "count"), ("quantos", "count"), ("máximo", "max"),
                     ("maximo", "max"), ("mínimo", "min"), ("minimo", "min")):
        if word in text:
            value = mentioned[0] if mentioned else None
            if op == "count" or value:
                return {"operation": op, "value": value, "group_by": group,
                        "label": value or "Contagem", "unit": "",
                        "chart_type": "column", "decimals": 0 if op in ("sum", "count") else 1}
    return None


# Cabeçalhos que indicam uma coluna de QUANTIDADE já somável na planilha.
_QTY_HINTS = ("quantidade", "qtd", "qtde", "ocorrenc", "ocorrênc", "total",
              "contagem", "volume", "count")


def _quantity_column(columns: list[str]) -> str | None:
    """Coluna de quantidade (ex.: 'Quantidade de Sintomas'), se existir."""
    for col in columns:
        low = str(col or "").lower()
        if any(hint in low for hint in _QTY_HINTS):
            return col
    return None


def _drop_unrequested_group2(parsed: dict, request: str) -> None:
    """Remove o 2º agrupamento quando o pedido não pediu por ele.

    Um agrupamento a mais quebra os totais em pedaços ("Tela com falha ·
    SM-A556E") e descaracteriza o ranking que o usuário pediu. Só mantemos
    group_by2 se o pedido citar a coluna ou pedir dois agrupamentos.
    """
    group2 = parsed.get("group_by2")
    if not group2 or not request:
        return
    text = _norm(request)
    if _norm(group2) in text or (request or "").lower().count("por ") > 1:
        return
    parsed["group_by2"] = None
    logger.info("2º agrupamento '%s' descartado: não foi pedido.", group2)


def _align_group_by(parsed: dict, request: str, columns: list[str]) -> None:
    """Corrige o agrupamento quando o pedido nomeia outra coluna.

    Modelos menores costumam repetir o agrupamento da análise anterior: pedimos
    "top 3 assistências" e vem group_by='Sintoma' (com o rótulo certo!). Se o
    pedido cita uma coluna e a escolhida NÃO aparece nele, trocamos.

    Só corrige um agrupamento existente — nunca cria um que não foi pedido.
    """
    current = parsed.get("group_by")
    if not current or not request:
        return
    text = _norm(request)
    if _norm(current) in text:
        return                                  # a escolha do modelo foi citada
    used = {str(parsed.get(key) or "") for key in ("value", "numerator", "denominator")}
    found: list[tuple[int, str]] = []
    for col in columns:
        if col in used:
            continue                            # coluna de métrica, não de corte
        name = _norm(col)
        if len(name) < 4:                       # nomes curtos casam por acidente
            continue
        position = text.find(name)
        if position >= 0:
            found.append((position, col))
    if not found:
        return
    chosen = min(found)[1]
    if chosen != current:
        parsed["group_by"] = chosen
        logger.info("Agrupamento corrigido: '%s' → '%s' (citado no pedido).",
                    current, chosen)


def _clean_recipe(parsed: dict, columns: list[str], request: str = "") -> dict | None:
    """Valida o esqueleto da receita e descarta colunas inexistentes."""
    if not isinstance(parsed, dict):
        return None
    if str(parsed.get("operation", "")).lower() not in OPERATIONS:
        return None
    for key in ("numerator", "denominator", "value", "group_by", "group_by2"):
        name = parsed.get(key)
        if name and resolve_column(str(name), columns) is None:
            parsed[key] = None
    # 'count' agrupado quando existe coluna de quantidade quase sempre é engano
    # do modelo: o usuário quer SOMAR as ocorrências, não contar linhas.
    # (Vem antes do ajuste de agrupamento: define qual coluna é a métrica.)
    if str(parsed.get("operation")).lower() == "count" and parsed.get("group_by"):
        qty = _quantity_column(columns)
        if qty and qty != parsed.get("group_by"):
            parsed["operation"] = "sum"
            parsed["value"] = qty
            logger.info("Receita ajustada: count → sum sobre '%s'", qty)
    _drop_unrequested_group2(parsed, request)
    _align_group_by(parsed, request, columns)
    return parsed


def split_request(request: str) -> list[str]:
    """Divide um pedido composto em partes ("A e B", "A; B").

    Modelos pequenos costumam atender só a primeira parte de um pedido duplo;
    dividir e perguntar uma de cada vez é mais confiável. Só divide quando as
    duas partes parecem análises completas (têm verbo/indicador próprio).
    """
    text = (request or "").strip()
    if not text:
        return []
    parts: list[str] = []
    for chunk in re.split(r"\s*;\s*|\s+e\s+(?=top|os\s|as\s|total|soma|média|media|percentual|quantidade|contagem)", text, flags=re.IGNORECASE):
        chunk = chunk.strip(" ,.;")
        if len(chunk) >= 8:
            parts.append(chunk)
    return parts if len(parts) > 1 else [text]


_SIGNATURE_KEYS = ("operation", "value", "numerator", "denominator",
                   "group_by", "group_by2", "top", "order")


def recipe_signature(recipe: dict, columns: list[str] | None = None) -> tuple:
    """Identidade de cálculo da receita (o rótulo não conta).

    Com as colunas em mãos, compara a receita RESOLVIDA — duas receitas com a
    coluna em slots diferentes (`value` vs. `numerator`) calculam a mesma coisa
    e precisam ter a mesma assinatura.
    """
    if columns:
        try:
            resolved = validate_recipe(recipe, columns)
            return ("resolved",) + tuple(resolved.get(key) for key in _SIGNATURE_KEYS)
        except Exception:  # receita inválida: cai na comparação crua
            pass
    return tuple(str(recipe.get(key) or "").strip().lower() for key in _SIGNATURE_KEYS)


def _dedupe(recipes: list[dict], columns: list[str] | None = None) -> list[dict]:
    """Descarta receitas que calculam exatamente a mesma coisa.

    Modelos menores às vezes devolvem N análises com rótulos diferentes mas o
    mesmo agrupamento — mostrar a mesma tabela duas vezes confunde o usuário.
    """
    seen: set[tuple] = set()
    unique: list[dict] = []
    for recipe in recipes:
        signature = recipe_signature(recipe, columns)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(recipe)
    return unique


async def _one_recipe(request: str, columns: list[str], rows: list[list]) -> dict | None:
    """Pede UMA receita para um pedido simples (usado ao dividir compostos)."""
    prompt = (
        f"Pedido do usuário: \"{request.strip()}\"\n"
        f"Colunas e amostra da planilha (primeira linha = cabeçalhos):\n"
        f"{_sample_block(columns, rows)}\n"
        "Gere a receita agora."
    )
    try:
        response = await LLMService().generate(prompt, RECIPE_SYSTEM, json_mode=True)
        parsed = _parse_json(response.content)
        if isinstance(parsed, dict):
            inner = parsed.get("analyses")
            if isinstance(inner, list) and inner:
                parsed = inner[0]
            return _clean_recipe(parsed, columns, request)
    except Exception as error:
        logger.warning("Falha ao gerar receita de parte do pedido: %s", error)
    return heuristic_recipe(request, columns)


async def build_recipes(
    request: str, columns: list[str], rows: list[list], max_recipes: int = 4
) -> tuple[list[dict], str]:
    """Uma OU MAIS receitas a partir do pedido (ex.: "top 3 sintomas E top 3
    assistências" → duas receitas). Devolve (receitas, origem).

    Levanta ValueError com mensagem PT se nada for compreendido.
    """
    prompt = (
        f"Pedido do usuário: \"{request.strip()}\"\n"
        f"Colunas e amostra da planilha (primeira linha = cabeçalhos):\n"
        f"{_sample_block(columns, rows)}\n"
        "Gere a(s) receita(s) agora."
    )
    try:
        service = LLMService()
        response = await service.generate(prompt, RECIPE_SYSTEM, json_mode=True)
        parsed = _parse_json(response.content)
        recipes: list[dict] = []
        if isinstance(parsed, dict):
            raw_list = parsed.get("analyses")
            if isinstance(raw_list, list):          # múltiplas análises
                for item in raw_list[:max_recipes]:
                    clean = _clean_recipe(item, columns, request)
                    if clean:
                        recipes.append(clean)
            else:                                   # uma análise só (formato antigo)
                clean = _clean_recipe(parsed, columns, request)
                if clean:
                    recipes.append(clean)
        recipes = _dedupe(recipes, columns)
        # Pedido composto ("A e B") mas a IA entendeu menos análises do que foi
        # pedido (ou repetiu a mesma receita)? Divide o pedido e resolve cada
        # parte separadamente — modelos menores acertam muito mais com pedidos
        # simples e um agrupamento por vez.
        parts = split_request(request)
        if len(parts) > 1 and len(recipes) < len(parts):
            split_recipes: list[dict] = []
            for part in parts[:max_recipes]:
                one = await _one_recipe(part, columns, rows)
                if one:
                    one.setdefault("label", part[:60])
                    split_recipes.append(one)
            split_recipes = _dedupe(split_recipes, columns)
            if len(split_recipes) > 1:
                logger.info("Pedido composto dividido em %d análises", len(split_recipes))
                return split_recipes, "ai"
        if recipes:
            return recipes, "ai"
        logger.warning("Receita da IA fora do contrato; tentando heurística.")
    except Exception as error:
        logger.warning("IA indisponível para gerar receita (%s); usando heurística.", error)

    fallback = heuristic_recipe(request, columns)
    if fallback:
        return [fallback], "heuristic"
    raise ValueError(
        "Não consegui entender o que calcular. Tente descrever com as colunas da "
        "planilha, por exemplo: “percentual de Aprovados sobre Inspecionados por Linha”."
    )


async def build_recipe(request: str, columns: list[str], rows: list[list]) -> tuple[dict, str]:
    """Compatibilidade: primeira receita de `build_recipes`."""
    recipes, source = await build_recipes(request, columns, rows)
    return recipes[0], source
