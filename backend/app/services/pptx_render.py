"""Executa um DeckPlan sobre o .pptx do usuário — a etapa que gera o arquivo.

O `deck_plan` decide (dados puros, sem tocar em arquivo) e este módulo executa,
usando só as primitivas de `pptx_mutate`. A separação é o que permite testar
toda a decisão sem gerar .pptx, e testar a execução com um plano de mentira.

Como o deck é montado: cada slide do plano DUPLICA o slide-molde do original e
é preenchido; no fim, os slides-modelo são apagados. Assim o arquivo de saída
tem exatamente os slides do plano, na ordem do plano, e tudo o que não foi
tocado — tema, master, fundo, decoração — continua byte a byte como o usuário
desenhou.

Encaixe de texto: antes de escrever, mede-se com a fonte real
(`text_metrics`). Se não couber na caixa do modelo, reduz-se o corpo; se nem
no mínimo couber, corta-se e AVISA-SE. A regra é a mesma do resto do plano:
nada some calado.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services import pptx_mutate as mut
from app.services import text_metrics as tm
from app.services.deck_plan import (
    CHART, CLEAR, DeckPlan, IMAGE, PARAGRAPHS, REMOVE, TABLE, TEXT,
)

logger = logging.getLogger(__name__)

EMU_PER_INCH = 914400.0
# Margem interna padrão de uma caixa de texto do PowerPoint (0,1" nas laterais,
# 0,05" em cima e embaixo). Medir contra a caixa cheia superestimaria o espaço.
INSET_W = 0.2
INSET_H = 0.1
DEFAULT_FAMILY = "Calibri"
DEFAULT_SIZE_PT = 14.0


@dataclass
class RenderResult:
    path: str
    slides: int
    warnings: list[str] = field(default_factory=list)


def _elements_by_shape(layout: dict) -> dict[int, dict]:
    """Índice shape_id → elemento do modelo (de onde vem fonte/corpo/estilo)."""
    indice: dict[int, dict] = {}
    for slide in (layout or {}).get("slides") or []:
        for element in slide.get("elements") or []:
            shape_id = element.get("src_shape_id")
            if shape_id:
                indice[int(shape_id)] = element
    return indice


def _font_of(element: dict | None) -> tuple[str, float, bool, bool]:
    if not element:
        return DEFAULT_FAMILY, DEFAULT_SIZE_PT, False, False
    family = str(element.get("font_family") or DEFAULT_FAMILY)
    try:
        size = float(element.get("font_size") or DEFAULT_SIZE_PT)
    except (TypeError, ValueError):
        size = DEFAULT_SIZE_PT
    return family, size, bool(element.get("bold")), bool(element.get("italic"))


def _box_inches(shape) -> tuple[float, float]:
    """Área útil da caixa, em polegadas, já descontadas as margens internas."""
    largura = float(shape.width or 0) / EMU_PER_INCH - INSET_W
    altura = float(shape.height or 0) / EMU_PER_INCH - INSET_H
    return max(largura, 0.5), max(altura, 0.2)


def _fit_lines(
    lines: list[str], shape, element: dict | None,
) -> tuple[list[str], float, bool]:
    """Encaixa as linhas na caixa do modelo.

    Devolve (linhas, corpo em pt, cortou). O texto devolvido é o ORIGINAL (não
    o quebrado): quem quebra linha é o PowerPoint, e com o corpo já ajustado
    ele chega no mesmo resultado que medimos. Só quando nem o corpo mínimo
    resolve é que cortamos de fato.
    """
    family, size, bold, italic = _font_of(element)
    largura, altura = _box_inches(shape)

    corpo = size
    while True:
        quebradas = [
            fragmento
            for linha in lines
            for fragmento in tm.wrap_text(linha, largura, family, corpo, bold, italic)
        ]
        altura_linha = tm.line_height(family, corpo, bold, italic)
        total = len(quebradas) * altura_linha
        if total <= altura or corpo - tm.SHRINK_STEP_PT < tm.MIN_FONT_PT:
            break
        corpo -= tm.SHRINK_STEP_PT

    if total <= altura:
        return lines, corpo, False

    # Não coube nem no mínimo: corta por LINHA ORIGINAL, contando quantas
    # linhas quebradas cada uma gasta — cortar a lista quebrada devolveria
    # pedaços de frase remontados errado.
    cabem = max(1, int(altura // altura_linha)) if altura_linha else 1
    mantidas: list[str] = []
    gasto = 0
    for linha in lines:
        custo = len(tm.wrap_text(linha, largura, family, corpo, bold, italic))
        if gasto + custo > cabem:
            break
        mantidas.append(linha)
        gasto += custo
    if not mantidas:
        mantidas = [lines[0]]
    mantidas[-1] = mantidas[-1].rstrip() + "…"
    return mantidas, corpo, True


def _write_text(shape, element, value: Any, paragraphs: bool) -> str | None:
    """Escreve texto com encaixe. Devolve aviso quando precisou cortar."""
    linhas = (
        [str(v) for v in value if str(v).strip()] if paragraphs
        else [str(value)]
    )
    if not linhas:
        mut.clear_text(shape)
        return None

    linhas, corpo, cortou = _fit_lines(linhas, shape, element)
    if paragraphs:
        mut.set_paragraphs(shape, linhas)
    else:
        mut.set_text(shape, linhas[0])
    mut.set_font_size(shape, corpo)

    if cortou:
        return (
            f"O texto “{linhas[0][:40]}…” não cabe na caixa do modelo e foi "
            "cortado. Encurte o texto ou aumente a caixa no modelo."
        )
    return None


def _apply(fill, shape, slide, element: dict | None) -> str | None:
    """Executa UMA operação do plano. Devolve aviso, se houver."""
    if fill.action == REMOVE:
        mut.remove_shape(shape)
        return None
    if fill.action == CLEAR:
        mut.clear_text(shape)
        return None
    if fill.action == TEXT:
        return _write_text(shape, element, fill.value, paragraphs=False)
    if fill.action == PARAGRAPHS:
        return _write_text(shape, element, fill.value or [], paragraphs=True)
    if fill.action == TABLE:
        dados = fill.value or {}
        relatorio = mut.fill_table(
            shape, dados.get("columns") or [], dados.get("rows") or []
        )
        perdidas, colunas = relatorio["dropped_rows"], relatorio["dropped_columns"]
        if perdidas or colunas:
            partes = []
            if perdidas:
                partes.append(f"{perdidas} linha(s)")
            if colunas:
                partes.append(f"{colunas} coluna(s)")
            return (
                f"A tabela do modelo é menor que os dados: {', '.join(partes)} "
                "ficaram de fora."
            )
        return None
    if fill.action == IMAGE:
        mut.swap_image(shape, fill.value)
        return None
    if fill.action == CHART:
        dados = fill.value or {}
        series = [
            (s.get("name") or "", s.get("values") or [])
            for s in dados.get("series") or []
        ]
        mut.set_chart_data(shape, slide, dados.get("categories") or [], series)
        return None
    logger.warning("Ação desconhecida no plano: %s", fill.action)
    return None


def _font_warnings(layout: dict) -> list[str]:
    """Fonte que a máquina não tem = deck sai diferente do modelo. Avisa ANTES."""
    familias = {
        str(e.get("font_family"))
        for s in (layout or {}).get("slides") or []
        for e in s.get("elements") or []
        if e.get("font_family")
    }
    ausentes = tm.missing_fonts(familias)
    if not ausentes:
        return []
    return [
        f"A fonte {', '.join(ausentes)} do modelo não está instalada neste "
        "servidor. O PowerPoint vai substituí-la e o espaçamento pode mudar."
    ]


def render_plan(
    template_path: str | Path,
    layout: dict,
    plan: DeckPlan,
    output_path: str | Path,
) -> RenderResult:
    """Gera o .pptx executando o plano sobre o modelo do usuário."""
    if not plan.slides:
        raise mut.PptxMutateError("O plano do deck está vazio.")
    origem = Path(template_path)
    if not origem.exists():
        raise mut.PptxMutateError(
            "O arquivo do modelo não está mais no servidor. Envie-o novamente."
        )

    presentation = mut.open_presentation(origem)
    originais = mut.slide_count(presentation)
    elementos = _elements_by_shape(layout)
    warnings = list(plan.warnings) + _font_warnings(layout)

    for slide_plan in plan.slides:
        if not 0 <= slide_plan.src_slide < originais:
            warnings.append(
                f"O modelo mudou e o slide {slide_plan.src_slide + 1} não existe "
                "mais. Reimporte o modelo."
            )
            continue
        destino = mut.duplicate_slide(presentation, slide_plan.src_slide)
        por_id = {
            int(shape.shape_id): shape
            for shape in destino.shapes
            if getattr(shape, "shape_id", None) is not None
        }
        for fill in slide_plan.fills:
            shape = por_id.get(fill.shape_id)
            if shape is None:
                continue  # shape sumiu do modelo: nada a fazer, nada a perder
            try:
                aviso = _apply(fill, shape, destino, elementos.get(fill.shape_id))
            except Exception as error:
                logger.warning(
                    "Falha ao preencher slot %s (shape %s): %s",
                    fill.slot, fill.shape_id, error,
                )
                warnings.append(
                    f"Não foi possível preencher o campo “{fill.slot}” de um "
                    "slide. Ele ficou como estava no modelo."
                )
                continue
            if aviso:
                warnings.append(aviso)

    # Só agora: os moldes já foram todos duplicados.
    for _ in range(originais):
        mut.delete_slide(presentation, 0)

    caminho = mut.save(presentation, output_path)
    # Avisos repetidos (mesma caixa apertada em vários slides) viram um só.
    unicos = list(dict.fromkeys(warnings))
    logger.info(
        "Deck gerado por mutação | slides=%d | avisos=%d | %s",
        mut.slide_count(presentation), len(unicos), caminho,
    )
    return RenderResult(path=caminho, slides=mut.slide_count(presentation),
                        warnings=unicos)
