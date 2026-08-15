"""Date handling utilities — QWI company week convention.

CONVENÇÃO DE SEMANAS (regra da empresa, NÃO é ISO 8601):
- A semana começa na segunda-feira.
- W1 do ano Y é a semana (seg–dom) que CONTÉM o dia 1º de janeiro de Y —
  mesmo que ela comece em dezembro do ano anterior.
- O ano de uma semana é o ano do seu DOMINGO (último dia): a semana
  29/12/2025–04/01/2026 é a W1 de 2026.

Âncora de validação: 10/08/2026 é segunda-feira da W33
(W1/2026 começa em 29/12/2025; (10/08 − 29/12) / 7 = 32 → semana 33).

Qualquer código que calcule número de semana DEVE usar este módulo.
"""
from datetime import datetime, timezone, date, timedelta
from typing import Tuple


def normalize_to_utc(dt: datetime | str) -> datetime:
    """Normalize any datetime to UTC"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt


def to_iso_string(dt: datetime) -> str:
    """Convert datetime to RFC3339 format (2026-08-07T14:30:00Z)"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace('+00:00', 'Z')


def normalize_to_iso_date(dt: datetime | date) -> str:
    """Convert to ISO date string (YYYY-MM-DD)"""
    if isinstance(dt, datetime):
        dt = dt.date()
    return dt.isoformat()


def _as_date(dt: datetime | date) -> date:
    return dt.date() if isinstance(dt, datetime) else dt


def first_monday(year: int) -> date:
    """Segunda-feira da W1 do ano: a segunda da semana que contém 1º/jan.

    (Nome mantido por compatibilidade com os chamadores; pode cair em
    dezembro do ano anterior.)
    """
    jan1 = date(year, 1, 1)
    # weekday(): Mon=0 ... Sun=6
    return jan1 - timedelta(days=jan1.weekday())


def monday_of(dt: datetime | date) -> date:
    """Segunda-feira da semana que contém a data."""
    d = _as_date(dt)
    return d - timedelta(days=d.weekday())


def calculate_week_number(dt: datetime | date) -> Tuple[int, int]:
    """Número da semana na convenção da empresa. Retorna (week, year).

    A ordem (week, year) é mantida por compatibilidade com os chamadores.
    """
    monday = monday_of(dt)
    # O ano da semana é o ano do DOMINGO: a semana que contém 1º/jan
    # pertence ao ano novo (é a W1 dele).
    year = (monday + timedelta(days=6)).year
    week = (monday - first_monday(year)).days // 7 + 1
    return week, year


def weeks_in_year(year: int) -> int:
    """Quantidade de semanas do ano na convenção da empresa (52 ou 53)."""
    return (first_monday(year + 1) - first_monday(year)).days // 7


def get_week_boundaries(year: int, week: int) -> Tuple[date, date]:
    """Segunda e domingo da semana (convenção da empresa)."""
    monday = first_monday(year) + timedelta(weeks=week - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_week_days(date_in_week: datetime | date) -> list[date]:
    """Get all 7 days of week (Mon-Sun)"""
    monday = monday_of(date_in_week)
    return [monday + timedelta(days=i) for i in range(7)]


def is_same_day(date1: datetime | date, date2: datetime | date) -> bool:
    """Check if two datetimes are same day"""
    return _as_date(date1) == _as_date(date2)


def format_date_br(dt: datetime | date) -> str:
    """Format date as DD/MM/YYYY"""
    return _as_date(dt).strftime('%d/%m/%Y')


def days_since_epoch(dt: datetime | date) -> int:
    """Days since Unix epoch"""
    epoch = date(1970, 1, 1)
    return (_as_date(dt) - epoch).days
