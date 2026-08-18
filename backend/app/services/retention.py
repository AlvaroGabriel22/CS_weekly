"""Retenção de PPTX gerados (QA-010).

Cada geração grava um `weekly_<id>.pptx` novo em uploads/reports/; sem limpeza,
o disco cresce sem limite. Mantemos as N versões mais recentes por
(usuário, ano, semana) e removemos os arquivos das versões mais antigas.
Roda no startup — barato e sem depender de Celery/beat.
"""
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import WeeklyReport

logger = logging.getLogger(__name__)
settings = get_settings()


def cleanup_old_reports() -> int:
    """Remove os .pptx das versões antigas além do limite configurado.

    Não apaga linhas do banco (o histórico de versões continua listável); só
    libera o arquivo pesado. Retorna quantos arquivos removeu.
    """
    keep = settings.PPTX_RETENTION_PER_WEEK
    if keep <= 0:
        return 0

    removed = 0
    db = SessionLocal()
    try:
        reports = (
            db.query(WeeklyReport)
            .order_by(
                WeeklyReport.user_id,
                WeeklyReport.year.desc(),
                WeeklyReport.week_number.desc(),
                WeeklyReport.version.desc(),
            )
            .all()
        )
        seen: dict[tuple, int] = {}
        for r in reports:
            key = (r.user_id, r.year, r.week_number)
            seen[key] = seen.get(key, 0) + 1
            if seen[key] <= keep or not r.pptx_path:
                continue
            path = Path(r.pptx_path)
            try:
                if path.exists():
                    path.unlink()
                    removed += 1
            except Exception:
                logger.warning("Falha ao remover PPTX antigo: %s", r.pptx_path)
    finally:
        db.close()

    if removed:
        logger.info("Retenção: %d PPTX antigos removidos", removed)
    return removed
