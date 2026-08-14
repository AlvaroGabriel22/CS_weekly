"""Tradução por IA dos textos do editor de montagem (pt/en/ko).

O frontend envia a lista de textos dos elementos do deck; a resposta devolve
a lista traduzida NA MESMA ORDEM. Determinístico no contrato, tolerante no
parse (o LLM local pode devolver cercas de markdown etc.).
"""

import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models import User
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

LANG_NAMES = {"pt": "português do Brasil", "en": "inglês", "ko": "coreano"}

SYSTEM_PROMPT = (
    "Você é um tradutor e revisor profissional de apresentações corporativas de "
    "qualidade industrial. Para cada texto: (1) corrija erros de ortografia e "
    "digitação SEM alterar o sentido, o conteúdo ou o tom do texto; (2) traduza "
    "o resultado para o idioma alvo. Se o texto já estiver no idioma alvo, "
    "apenas devolva-o com a ortografia corrigida. Preserve números, códigos "
    "(ex.: W32, NC, PPM, FPY), nomes próprios e quebras de linha (\\n). Não "
    "adicione comentários nem conteúdo novo. Responda APENAS com um objeto JSON "
    "no formato {\"texts\": [\"...\", ...]} com os resultados na MESMA ordem e "
    "quantidade da entrada."
)


class TranslateRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=200)
    target: Literal["pt", "en", "ko"]


class TranslateResponse(BaseModel):
    texts: list[str]


def _parse_texts(raw: str, expected: int) -> list[str] | None:
    """Extrai {"texts": [...]} da resposta, tolerando cercas de markdown."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    texts = data.get("texts") if isinstance(data, dict) else None
    if not isinstance(texts, list) or len(texts) != expected:
        return None
    return [str(t) for t in texts]


@router.post("/translate", response_model=TranslateResponse)
async def translate(
    data: TranslateRequest,
    current_user: User = Depends(get_current_user),
):
    service = LLMService()
    if not await service.is_available():
        raise HTTPException(503, detail="IA indisponível no momento. Tente novamente.")

    payload = json.dumps({"texts": data.texts}, ensure_ascii=False)
    prompt = (
        f"Corrija a ortografia e traduza os textos abaixo para "
        f"{LANG_NAMES[data.target]}.\n"
        f"Entrada:\n{payload}"
    )
    try:
        response = await service.generate(prompt, SYSTEM_PROMPT, json_mode=True)
    except Exception as error:
        logger.warning("Tradução falhou | err=%s", error)
        raise HTTPException(503, detail="IA indisponível no momento. Tente novamente.")

    texts = _parse_texts(response.content, len(data.texts))
    if texts is None:
        # uma segunda tentativa costuma resolver formatação fora do contrato
        try:
            retry = await service.generate(prompt, SYSTEM_PROMPT, json_mode=True)
            texts = _parse_texts(retry.content, len(data.texts))
        except Exception:
            texts = None
    if texts is None:
        raise HTTPException(502, detail="A IA não retornou uma tradução válida.")
    return TranslateResponse(texts=texts)
