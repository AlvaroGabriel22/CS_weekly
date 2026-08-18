"""Executor dedicado para o enriquecimento de IA em background.

Motivação (QA-046): a análise de IA de atividades/anexos leva vários segundos
e cada tarefa segura uma conexão do banco enquanto o LLM responde. Rodando isso
no threadpool de 40 threads do Starlette, poucas dezenas de criações simultâneas
esgotam o pool de conexões (15) e as requisições web passam a receber 500.

Solução: um pool próprio com concorrência baixa (o LLM local serializa de
qualquer modo), garantindo que no máximo `BACKGROUND_AI_WORKERS` conexões fiquem
ocupadas por tarefas de IA ao mesmo tempo — o restante do pool fica livre para a
web. Tarefas excedentes ficam na fila do executor SEM abrir conexão (só abrem
`SessionLocal` quando começam a rodar).
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_executor = ThreadPoolExecutor(
    max_workers=max(1, settings.BACKGROUND_AI_WORKERS),
    thread_name_prefix="qwi-ai",
)


def submit_background(fn, *args) -> None:
    """Agenda fn(*args) no pool de IA. Nunca propaga exceção ao chamador."""
    def _run() -> None:
        try:
            fn(*args)
        except Exception:
            logger.exception("Tarefa de background falhou: %s", getattr(fn, "__name__", fn))

    _executor.submit(_run)


def shutdown_background() -> None:
    """Encerra o pool (chamado no shutdown do app)."""
    _executor.shutdown(wait=False, cancel_futures=True)
