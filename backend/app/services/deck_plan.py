"""Planejador determinístico do deck: o que vai em cada slot de cada slide.

Recebe o MODELO já marcado (slots + âncoras) e o conteúdo da semana, e devolve
um PLANO — dados puros, sem tocar em .pptx. Quem executa o plano é o exportador
por mutação (`pptx_mutate`). Separar assim deixa toda a decisão testável sem
gerar arquivo.

Três regras que vêm da auditoria do gerador antigo:

1. **Encaixe, não índice.** O molde de cada atividade é escolhido pelo que ela
   TEM (tabela? imagem? gráfico?), e não por `molds[min(idx, len-1)]`, que dava
   à 3ª atividade em diante sempre o último molde.
2. **Nada sobra do modelo.** Todo slot não preenchido é limpo ou removido. Era
   assim que a data e a atividade da semana anterior vazavam para o deck novo.
3. **Nada some calado.** O que não couber vira slide de continuação; o que nem
   assim couber entra em `warnings` para a interface avisar.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

logger = logging.getLogger(__name__)

MAX_SLIDES = 40

# Ações que o exportador sabe executar sobre um shape do .pptx.
TEXT = "text"
PARAGRAPHS = "paragraphs"
TABLE = "table"
IMAGE = "image"
CHART = "chart"
CLEAR = "clear"
REMOVE = "remove"


@dataclass
class ActivityContent:
    """Conteúdo de UMA atividade da semana, já normalizado.

    Estrutura neutra de propósito: o planejador não conhece o ORM, então dá
    para testar todo o encaixe sem banco.
    """
    title: str
    description: str = ""
    date_label: str = ""                               # "20/07" — data da atividade
    tables: list[dict] = field(default_factory=list)   # {"columns": [...], "rows": [...]}
    images: list[str] = field(default_factory=list)    # caminhos de arquivo
    charts: list[dict] = field(default_factory=list)   # {"categories": [...], "series": [...]}


@dataclass
class Fill:
    """Uma operação sobre um shape do modelo."""
    shape_id: int
    slot: str
    action: str
    value: Any = None


@dataclass
class SlidePlan:
    src_slide: int          # índice do slide-molde dentro do .pptx original
    kind: str               # "cover" | "content"
    fills: list[Fill]
    activities: list[str] = field(default_factory=list)   # títulos, para log/aviso


@dataclass
class DeckPlan:
    slides: list[SlidePlan]
    warnings: list[str] = field(default_factory=list)


@dataclass
class _Variant:
    """Inventário de slots de um slide-molde."""
    src_slide: int
    kind: str
    titles: list[dict] = field(default_factory=list)
    bodies: list[dict] = field(default_factory=list)
    dates: list[dict] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    charts: list[dict] = field(default_factory=list)
    week_labels: list[dict] = field(default_factory=list)

    @property
    def blocks(self) -> int:
        """Quantas atividades cabem neste molde (pares título/descrição)."""
        return max(len(self.titles), len(self.bodies), 1)

    @property
    def fillable(self) -> list[dict]:
        return (self.titles + self.bodies + self.dates + self.tables
                + self.images + self.charts + self.week_labels)


def _reading_order(elements: Sequence[dict]) -> list[dict]:
    """Ordem de leitura (de cima para baixo, da esquerda para a direita).

    É o que pareia o título do bloco 1 com a descrição do bloco 1 num molde que
    tem duas atividades no mesmo slide.
    """
    return sorted(elements, key=lambda e: (round(float(e.get("y") or 0), 3),
                                           round(float(e.get("x") or 0), 3)))


def _variant(slide: dict, index: int) -> _Variant:
    grupos: dict[str, list[dict]] = {
        "title": [], "body": [], "activity_date": [], "table": [], "image": [],
        "chart": [], "week_label": [],
    }
    for element in slide.get("elements") or []:
        slot = element.get("slot")
        if slot in grupos and element.get("src_shape_id"):
            grupos[slot].append(element)
    src = slide.get("src_slide")
    return _Variant(
        src_slide=int(src) if src is not None else index,
        kind=str(slide.get("kind") or "custom"),
        titles=_reading_order(grupos["title"]),
        bodies=_reading_order(grupos["body"]),
        dates=_reading_order(grupos["activity_date"]),
        tables=_reading_order(grupos["table"]),
        images=_reading_order(grupos["image"]),
        charts=_reading_order(grupos["chart"]),
        week_labels=_reading_order(grupos["week_label"]),
    )


def _score(variant: _Variant, janela: Sequence[ActivityContent]) -> float:
    """Quão bem este molde acomoda estas atividades.

    Premia slot atendido, penaliza slot que ficaria vazio (buraco no slide) e
    conteúdo que sobraria (slide de continuação a mais).
    """
    precisa_titulo = sum(1 for a in janela if a.title)
    precisa_corpo = sum(1 for a in janela if a.description)
    precisa_tabela = sum(len(a.tables) for a in janela)
    precisa_imagem = sum(len(a.images) for a in janela)
    precisa_grafico = sum(len(a.charts) for a in janela)

    score = 1.5 * len(janela)                      # preferir aproveitar os blocos
    score += 3 * min(len(variant.titles), precisa_titulo)
    score += 3 * min(len(variant.bodies), precisa_corpo)
    score += 4 * min(len(variant.tables), precisa_tabela)
    score += 4 * min(len(variant.images), precisa_imagem)
    score += 5 * min(len(variant.charts), precisa_grafico)

    score -= 2.0 * max(0, len(variant.tables) - precisa_tabela)
    score -= 2.0 * max(0, len(variant.images) - precisa_imagem)
    score -= 3.0 * max(0, len(variant.charts) - precisa_grafico)
    score -= 1.0 * max(0, len(variant.titles) - precisa_titulo)
    score -= 1.0 * max(0, len(variant.bodies) - precisa_corpo)

    score -= 2.0 * max(0, precisa_tabela - len(variant.tables))
    score -= 2.0 * max(0, precisa_imagem - len(variant.images))
    score -= 4.0 * max(0, precisa_grafico - len(variant.charts))
    # Título/descrição sem campo é conteúdo PERDIDO (anexo sobrando só gera
    # slide de continuação). Peso alto para nunca compensar o bônus de empacotar.
    score -= 6.0 * max(0, precisa_titulo - len(variant.titles))
    score -= 6.0 * max(0, precisa_corpo - len(variant.bodies))
    return score


def _pode_agrupar(variant: _Variant, janela: Sequence[ActivityContent]) -> bool:
    """Só junta várias atividades num slide quando não há dúvida de a quem
    pertence cada anexo.

    Um molde de dois blocos não diz qual slot de imagem é do bloco 1 e qual é
    do bloco 2. Agrupando atividades COM anexo, a evidência de uma apareceria
    ao lado do texto da outra — e o slide de continuação sairia com o título
    da atividade errada. Com anexo, uma atividade por slide.
    """
    if len(janela) <= 1:
        return True
    com_anexo = any(a.tables or a.images or a.charts for a in janela)
    tem_slot = bool(variant.tables or variant.images or variant.charts)
    return not (com_anexo and tem_slot)


def _fill_slide(
    variant: _Variant,
    janela: Sequence[ActivityContent],
    week_label: str,
    *,
    continuation: bool = False,
) -> tuple[SlidePlan, dict[str, list]]:
    """Monta o plano de UM slide e devolve o que sobrou (para continuação)."""
    fills: list[Fill] = []
    usados: set[int] = set()

    def marca(element: dict, action: str, value: Any = None) -> None:
        shape_id = element.get("src_shape_id")
        if not shape_id:
            return
        usados.add(int(shape_id))
        fills.append(Fill(int(shape_id), str(element.get("slot")), action, value))

    for element in variant.week_labels:
        marca(element, TEXT, week_label)

    for index, element in enumerate(variant.titles):
        if index < len(janela) and janela[index].title:
            marca(element, TEXT, janela[index].title)

    for index, element in enumerate(variant.bodies):
        if continuation:
            continue  # a descrição já foi no primeiro slide da atividade
        if index < len(janela) and janela[index].description:
            marca(element, PARAGRAPHS, janela[index].description.splitlines())

    for index, element in enumerate(variant.dates):
        if index < len(janela) and janela[index].date_label:
            marca(element, TEXT, janela[index].date_label)

    # Texto sem campo no modelo é conteúdo PERDIDO — tem que ser dito.
    perdidos: list[str] = []
    if not continuation:
        for index, atividade in enumerate(janela):
            if atividade.title and index >= len(variant.titles):
                perdidos.append(f"título de “{atividade.title}”")
            if atividade.description and index >= len(variant.bodies):
                perdidos.append(f"descrição de “{atividade.title}”")

    # Anexos são do slide inteiro: distribuídos na ordem das atividades.
    tabelas = [t for a in janela for t in a.tables]
    imagens = [i for a in janela for i in a.images]
    graficos = [c for a in janela for c in a.charts]

    for element in variant.tables:
        if tabelas:
            marca(element, TABLE, tabelas.pop(0))
    for element in variant.images:
        if imagens:
            marca(element, IMAGE, imagens.pop(0))
    for element in variant.charts:
        if graficos:
            marca(element, CHART, graficos.pop(0))

    # Slot que não recebeu conteúdo NÃO pode manter o do modelo.
    for element in variant.fillable:
        shape_id = element.get("src_shape_id")
        if not shape_id or int(shape_id) in usados:
            continue
        acao = CLEAR if element.get("type") == "text" else REMOVE
        fills.append(Fill(int(shape_id), str(element.get("slot")), acao))

    plano = SlidePlan(
        src_slide=variant.src_slide,
        kind="content",
        fills=fills,
        activities=[a.title for a in janela],
    )
    return plano, {"tables": tabelas, "images": imagens, "charts": graficos,
                   "texts": perdidos}


def _cover_plan(variant: _Variant, title: str, subtitle: str, week_label: str) -> SlidePlan:
    fills: list[Fill] = []
    usados: set[int] = set()

    def marca(element: dict, action: str, value: Any = None) -> None:
        shape_id = element.get("src_shape_id")
        if not shape_id:
            return
        usados.add(int(shape_id))
        fills.append(Fill(int(shape_id), str(element.get("slot")), action, value))

    if variant.titles:
        marca(variant.titles[0], TEXT, title)
    for element in variant.week_labels:
        marca(element, TEXT, week_label or subtitle)
    if variant.bodies and subtitle:
        marca(variant.bodies[0], TEXT, subtitle)

    for element in variant.fillable:
        shape_id = element.get("src_shape_id")
        if not shape_id or int(shape_id) in usados:
            continue
        acao = CLEAR if element.get("type") == "text" else REMOVE
        fills.append(Fill(int(shape_id), str(element.get("slot")), acao))

    return SlidePlan(src_slide=variant.src_slide, kind="cover", fills=fills)


def build_plan(
    template_layout: dict,
    activities: Sequence[ActivityContent],
    *,
    title: str,
    subtitle: str = "",
    week_label: str = "",
) -> DeckPlan:
    """Plano completo do deck a partir do modelo marcado + conteúdo da semana."""
    slides_modelo = (template_layout or {}).get("slides") or []
    if not slides_modelo:
        raise ValueError("Modelo sem slides.")

    variantes = [_variant(slide, index) for index, slide in enumerate(slides_modelo)]
    capa = next((v for v in variantes if v.kind == "cover"), None)
    moldes = [v for v in variantes if v is not capa and v.fillable]

    warnings: list[str] = []
    plano: list[SlidePlan] = []

    if capa:
        plano.append(_cover_plan(capa, title, subtitle, week_label))
    else:
        warnings.append("O modelo não tem slide de capa marcado.")

    if not moldes:
        warnings.append(
            "Nenhum slide do modelo tem campos marcados. Marque os campos na "
            "aba Templates para o conteúdo da semana entrar."
        )
        return DeckPlan(slides=plano, warnings=warnings)

    restantes = list(activities)
    while restantes and len(plano) < MAX_SLIDES:
        melhor: tuple[float, _Variant, list[ActivityContent]] | None = None
        for variante in moldes:
            for tamanho in range(1, min(variante.blocks, len(restantes)) + 1):
                janela = restantes[:tamanho]
                if not _pode_agrupar(variante, janela):
                    continue
                pontos = _score(variante, janela)
                if melhor is None or pontos > melhor[0]:
                    melhor = (pontos, variante, janela)
        assert melhor is not None
        _, variante, janela = melhor

        slide, sobra = _fill_slide(variante, janela, week_label)
        plano.append(slide)
        restantes = restantes[len(janela):]
        if sobra["texts"]:
            warnings.append(
                f"Sem campo no modelo para: {', '.join(sobra['texts'])}. "
                "Marque um campo de título/descrição na aba Templates."
            )

        # Sobrou anexo da atividade? Continua num slide igual, sem repetir a
        # descrição — melhor que descartar em silêncio.
        while (sobra["tables"] or sobra["images"] or sobra["charts"]) and len(plano) < MAX_SLIDES:
            extra = ActivityContent(
                title=janela[0].title if janela else "",
                tables=list(sobra["tables"]),
                images=list(sobra["images"]),
                charts=list(sobra["charts"]),
            )
            candidatos = [v for v in moldes if _capacidade(v, extra)]
            if not candidatos:
                warnings.append(_aviso_sobra(sobra, janela))
                break
            escolhido = max(candidatos, key=lambda v: _score(v, [extra]))
            slide_extra, sobra = _fill_slide(escolhido, [extra], week_label, continuation=True)
            plano.append(slide_extra)

    if restantes:
        warnings.append(
            f"{len(restantes)} atividade(s) não couberam no limite de "
            f"{MAX_SLIDES} slides e ficaram de fora."
        )

    logger.info("Plano do deck | slides=%d | avisos=%d", len(plano), len(warnings))
    return DeckPlan(slides=plano, warnings=warnings)


def _capacidade(variante: _Variant, conteudo: ActivityContent) -> bool:
    """O molde consegue acomodar ao menos um item que sobrou?"""
    return bool(
        (conteudo.tables and variante.tables)
        or (conteudo.images and variante.images)
        or (conteudo.charts and variante.charts)
    )


def _aviso_sobra(sobra: dict[str, list], janela: Sequence[ActivityContent]) -> str:
    partes = []
    if sobra["tables"]:
        partes.append(f"{len(sobra['tables'])} tabela(s)")
    if sobra["images"]:
        partes.append(f"{len(sobra['images'])} imagem(ns)")
    if sobra["charts"]:
        partes.append(f"{len(sobra['charts'])} gráfico(s)")
    atividade = janela[0].title if janela else "a semana"
    return (
        f"{', '.join(partes)} de “{atividade}” não couberam: o modelo não tem "
        "campo desse tipo. Marque um campo no modelo ou remova o anexo."
    )
