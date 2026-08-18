import logging
import base64
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

QUALITY_DEPT_CONTEXT = (
    "Context: you work for the Quality department of the MX CS division, composed of the sectors "
    "QM (quality management), QA (quality assurance), OQC (outgoing quality control), "
    "IQC (incoming quality control), FIELD (field/market quality) and CSI (quality innovation: "
    "software and automation solutions for quality performance). "
    "Use quality engineering terminology correctly (NC, PPM, FPY, rework, action plan, FMEA, 8D)."
)


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int | None = None
    finish_reason: str | None = None


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        images: list[str] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        images: list[str] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        user_message: dict = {"role": "user", "content": prompt}
        if images:
            user_message["images"] = images
        messages.append(user_message)

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": settings.OLLAMA_NUM_CTX,
                "num_predict": settings.OLLAMA_NUM_PREDICT,
            },
        }
        if json_mode:
            # Constrains decoding to valid JSON; small models often drift to
            # Markdown otherwise.
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data.get("message", {}).get("content", "")
        finish = data.get("done_reason")
        logger.info("LLM response generated | model=%s | length=%d", self.model, len(content))
        if finish == "length":
            # Resposta cortada por limite de tokens — o JSON pode vir inválido e
            # cair no fallback silenciosamente. Alerta para diagnóstico (QA-033).
            logger.warning(
                "LLM truncou a resposta (done_reason=length) | model=%s | "
                "considere aumentar OLLAMA_NUM_PREDICT/NUM_CTX", self.model,
            )

        return LLMResponse(
            content=content,
            model=self.model,
            finish_reason=finish,
        )

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


class OpenAICompatProvider(LLMProvider):
    """API externa compatível com OpenAI (POST {base}/chat/completions).

    Suporta imagens (multimodal, content parts com data URL) e json_mode
    (response_format). Configurada via LLM_BASE_URL / LLM_API_KEY / LLM_MODEL.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL or "gpt-4o"

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        images: list[str] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if images:
            # Multimodal: texto + imagens como data URLs (base64, mesmo formato
            # que o Ollama recebe — aqui embrulhado no content-parts da OpenAI).
            parts: list[dict] = [{"type": "text", "text": prompt}]
            for image_b64 in images:
                parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                })
            messages.append({"role": "user", "content": parts})
        else:
            messages.append({"role": "user", "content": prompt})

        payload: dict = {"model": self.model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content", "") or ""
        usage = data.get("usage") or {}
        logger.info(
            "LLM response generated | provider=openai_compat | model=%s | length=%d",
            self.model, len(content),
        )
        if choice.get("finish_reason") == "length":
            logger.warning(
                "LLM truncou a resposta (finish_reason=length) | model=%s (QA-033)",
                self.model,
            )
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            tokens_used=usage.get("total_tokens"),
            finish_reason=choice.get("finish_reason"),
        )

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/models", headers=self._headers()
                )
                return response.status_code == 200
        except Exception:
            return False


class RateLimitedProvider(LLMProvider):
    """Fila GLOBAL com janela deslizante: no máximo N requisições por minuto.

    As chamadas são serializadas — quem chega espera a vez em vez de estourar
    o limite da API (ex.: 3/min). Compartilhada por todo o backend.
    """

    def __init__(self, inner: LLMProvider, per_minute: int):
        import asyncio
        from collections import deque

        self.inner = inner
        self.per_minute = max(1, per_minute)
        self._lock = asyncio.Lock()
        self._recent: deque[float] = deque()

    async def _wait_turn(self) -> None:
        import asyncio
        import time

        async with self._lock:
            now = time.monotonic()
            while self._recent and now - self._recent[0] > 60.0:
                self._recent.popleft()
            if len(self._recent) >= self.per_minute:
                wait = 60.0 - (now - self._recent[0]) + 0.05
                logger.info("LLM rate limit | aguardando %.1fs na fila", wait)
                await asyncio.sleep(wait)
                now = time.monotonic()
                while self._recent and now - self._recent[0] > 60.0:
                    self._recent.popleft()
            self._recent.append(time.monotonic())

    async def generate(self, prompt, system_prompt=None, images=None, json_mode=False) -> LLMResponse:
        await self._wait_turn()
        return await self.inner.generate(prompt, system_prompt, images, json_mode)

    async def is_available(self) -> bool:
        return await self.inner.is_available()


class FallbackProvider(LLMProvider):
    """Tenta o provedor primário; se indisponível/falhar, cai para o reserva."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self.primary = primary
        self.fallback = fallback

    async def generate(self, prompt, system_prompt=None, images=None, json_mode=False) -> LLMResponse:
        try:
            return await self.primary.generate(prompt, system_prompt, images, json_mode)
        except Exception as error:
            logger.warning("LLM primário falhou (%s) — usando fallback local", error)
            return await self.fallback.generate(prompt, system_prompt, images, json_mode)

    async def is_available(self) -> bool:
        return await self.primary.is_available() or await self.fallback.is_available()


_default_provider: LLMProvider | None = None


def default_provider() -> LLMProvider:
    """Provedor global montado a partir do .env (singleton — a fila de rate
    limit precisa ser compartilhada por todas as instâncias de LLMService)."""
    global _default_provider
    if _default_provider is None:
        if settings.LLM_PROVIDER == "openai_compat" and settings.LLM_BASE_URL:
            provider: LLMProvider = OpenAICompatProvider()
            provider = RateLimitedProvider(provider, settings.LLM_RATE_LIMIT_PER_MIN)
            if settings.LLM_FALLBACK_TO_OLLAMA:
                provider = FallbackProvider(provider, OllamaProvider())
            logger.info(
                "LLM: openai_compat (%s @ %s), fila %d/min, fallback=%s",
                settings.LLM_MODEL, settings.LLM_BASE_URL,
                settings.LLM_RATE_LIMIT_PER_MIN, settings.LLM_FALLBACK_TO_OLLAMA,
            )
        else:
            provider = OllamaProvider()
        _default_provider = provider
    return _default_provider


class LLMService:
    """Abstraction layer for all LLM communication. Swap providers without touching business logic."""

    def __init__(self, provider: LLMProvider | None = None):
        self._provider = provider or default_provider()

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    def set_provider(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        images: list[str] | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        return await self._provider.generate(prompt, system_prompt, images, json_mode)

    async def is_available(self) -> bool:
        return await self._provider.is_available()

    async def analyze_activity(self, activity_text: str) -> str:
        system = (
            f"You are a quality engineering analyst. {QUALITY_DEPT_CONTEXT} "
            "Extract structured metadata from activity descriptions. "
            "Respond in JSON format with fields: project, supplier, line, process, product, category, "
            "activity_type, defect_type, related_kpis (array), keywords (array), technical_summary. "
            "In technical_summary, write an analytical reading of the activity (what it addresses and why "
            "it matters for quality), not a rewording of the input. Use null for fields without evidence."
        )
        response = await self.generate(activity_text, system, json_mode=True)
        return response.content

    async def generate_image_caption(self, context: str) -> str:
        system = (
            "You are a technical quality analyst. Generate a professional technical caption "
            "for an image used in a quality weekly report. Be concise and objective."
        )
        response = await self.generate(f"Generate a technical caption for this context:\n{context}", system)
        return response.content

    async def analyze_image(self, file_path: str, context: str) -> str:
        system = (
            f"You are a corporate quality analyst. {QUALITY_DEPT_CONTEXT} "
            "Analyze the evidence image thoroughly without inventing facts. "
            "Extract EVERYTHING useful: read any visible numbers, labels, table values, chart axes, "
            "part codes, defect marks, or measurements. Respond only with valid JSON containing: "
            "caption (technical, 1 sentence), observations (array of specific findings, each citing what "
            "is visible), possible_impact (what this evidence means for quality performance), "
            "visible_text (transcribe every readable text, number and value), "
            "device_info (optional object with model, serial, failure_mode when visible on device/label photos)."
        )
        with open(file_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("ascii")
        response = await self.generate(
            f"Analyze this evidence for the following activity:\n{context}",
            system,
            images=[encoded],
            json_mode=True,
        )
        return response.content

    async def analyze_spreadsheet(self, summary: str) -> str:
        system = (
            f"You are a quality data analyst. {QUALITY_DEPT_CONTEXT} "
            "Analyze the spreadsheet rows like an analyst preparing a management briefing: "
            "identify what is being measured, compute or read totals, extremes, and variations, "
            "compare against any visible targets/limits, and flag anomalies. "
            "Respond in JSON with: kpis (array of {name, value, unit} using real numbers from the data), "
            "trends (array of specific statements citing figures), "
            "anomalies (array of outliers), "
            "measurements (array of {param, value, unit, limit, status} when rows contain parametric data), "
            "time_series (optional object with categories[] and values[] when a time column exists), "
            "summary (2-3 analytical sentences with the main numeric finding). "
            "Use only numbers present in the data; never invent values."
        )
        response = await self.generate(
            f"Analyze this spreadsheet data:\n{summary}", system, json_mode=True
        )
        return response.content

    async def generate_weekly_content(
        self,
        analysis_prompt: str,
        analysis_system: str | None,
        plan_prompt_builder: Callable[[str], tuple[str, str | None]],
    ) -> str:
        """Three-step generation: deep analysis → presentation plan → validated JSON."""
        system = analysis_system or (
            "You are an expert corporate weekly report writer. Analyze and organize "
            "only the supplied evidence. Never invent results, impacts, KPIs, or causes."
        )
        analysis_draft = await self.generate(analysis_prompt, system)

        plan_prompt, plan_system = plan_prompt_builder(analysis_draft.content)
        plan_sys = plan_system or (
            "You are a presentation editor for executive quality reports. "
            "Design slide structure from analytical drafts without inventing data."
        )
        plan_draft = await self.generate(plan_prompt, plan_sys)

        format_system = (
            "You convert analytical drafts into strict JSON for a PowerPoint generator. "
            "Preserve language and analytical content faithfully. "
            "Do not add information absent from the drafts. "
            "Respond ONLY with the JSON object."
        )
        format_prompt = (
            "Merge the ANALYSIS DRAFT and PRESENTATION PLAN below into one JSON object:\n"
            "{\n"
            '  "summary": string,\n'
            '  "highlights": [string],\n'
            '  "activities": [{\n'
            '    "source": int,\n'
            '    "title": string,\n'
            '    "date": string,\n'
            '    "sector": string|null,\n'
            '    "activity_kind": string|null,\n'
            '    "content_mode": "transcribe"|"compress",\n'
            '    "narrative": string,\n'
            '    "impact": string,\n'
            '    "facts": [string],\n'
            '    "actions": [string],\n'
            '    "blocks": [visual block objects]\n'
            "  }],\n"
            '  "kpis": [string],\n'
            '  "kpi_table": [{"kpi","result","trend"}],\n'
            '  "conclusions": [string],\n'
            '  "next_steps": [string],\n'
            '  "archetype": "executivo"|"operacional"|"analitico",\n'
            '  "narrative": string,\n'
            '  "presentation_plan": {\n'
            '    "layout_profile": "executive"|"operational"|"analytical"|"field_case",\n'
            '    "sidebar": [],\n'
            '    "global_blocks": [visual block objects]\n'
            "  }\n"
            "}\n\n"
            "Visual block types (use ONLY when data exists in drafts):\n"
            "- device_info: {type, title?, fields: {label: value}}\n"
            "- measurement_table: {type, title, columns[], rows[][]}\n"
            "- generic_table: {type, title, columns[], rows[][]}\n"
            "- countermeasure_table: {type, title, rows[{action, owner, status, due}]}\n"
            "- chart: {type, title, chart_type, categories[], series[{name, values[]}], insight?}\n"
            "- image_row: {type, title?, images[{attachment_id, caption?}]}\n"
            "- text: {type, text}\n\n"
            f"ANALYSIS DRAFT:\n{analysis_draft.content}\n\n"
            f"PRESENTATION PLAN:\n{plan_draft.content}"
        )
        response = await self.generate(format_prompt, format_system, json_mode=True)
        return response.content
