"""Converte as atividades da semana no conteúdo neutro que o plano consome.

Existe para manter `deck_plan` sem qualquer conhecimento do ORM: lá o encaixe
é testado com objetos de mentira, aqui é onde o Activity/Attachment do banco
vira `ActivityContent`. Se amanhã a origem for outra (importação, API), só
este arquivo muda.

Classificação do anexo — a mesma regra do dossiê da IA, para os dois caminhos
enxergarem a semana igual:

- tem `kpi_data["table"]` → tabela (vai para um slot de tabela do modelo);
- é imagem (tipo ou mime) → evidência (vai para um slot de imagem);
- o resto (PDF, planilha sem tabela extraída) não entra no deck — o modelo não
  tem onde encaixar um arquivo genérico.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from app.services.deck_plan import ActivityContent

logger = logging.getLogger(__name__)

# Descrição longa demais vira parede de texto: o encaixe reduziria o corpo até
# o ilegível. Cortamos aqui, com aviso, e não no meio da renderização.
MAX_DESCRIPTION_CHARS = 1200


def _is_image(attachment: Any) -> bool:
    if getattr(attachment, "file_type", None) == "image":
        return True
    return str(getattr(attachment, "mime_type", "") or "").startswith("image/")


def _table_of(attachment: Any) -> dict | None:
    dados = getattr(attachment, "kpi_data", None)
    if not isinstance(dados, dict):
        return None
    tabela = dados.get("table")
    if not isinstance(tabela, dict):
        return None
    colunas = tabela.get("columns") or []
    linhas = tabela.get("rows") or []
    if not colunas or not linhas:
        return None
    return {"columns": list(colunas), "rows": [list(linha) for linha in linhas]}


def _date_label(activity: Any) -> str:
    data = getattr(activity, "activity_date", None)
    try:
        return data.strftime("%d/%m") if data else ""
    except Exception:
        return ""


def activities_to_content(activities: Iterable[Any]) -> list[ActivityContent]:
    """Converte as atividades, na ordem recebida, ignorando o que não existe.

    Anexo cujo arquivo sumiu do disco é descartado AQUI, não na geração: assim
    o planejador não reserva um slot de imagem para um arquivo inexistente e
    o slide não sai com um buraco.
    """
    conteudos: list[ActivityContent] = []
    for activity in activities:
        tabelas: list[dict] = []
        imagens: list[str] = []
        for attachment in getattr(activity, "attachments", None) or []:
            tabela = _table_of(attachment)
            if tabela:
                tabelas.append(tabela)
                continue
            if not _is_image(attachment):
                continue
            caminho = getattr(attachment, "file_path", None)
            if caminho and Path(caminho).exists():
                imagens.append(str(caminho))
            else:
                logger.warning("Anexo sem arquivo em disco, fora do deck: %s", caminho)

        descricao = str(getattr(activity, "description", "") or "").strip()
        if len(descricao) > MAX_DESCRIPTION_CHARS:
            descricao = descricao[:MAX_DESCRIPTION_CHARS].rstrip() + "…"

        conteudos.append(ActivityContent(
            title=str(getattr(activity, "title", "") or "").strip(),
            description=descricao,
            date_label=_date_label(activity),
            tables=tabelas,
            images=imagens,
        ))
    return conteudos
