"""Date handling utilities — QWI company week convention.

CONVENÇÃO DE SEMANAS (regra da empresa, NÃO é ISO 8601):
- A semana começa na segunda-feira.
- W1 do ano Y é a semana que começa na PRIMEIRA segunda-feira de janeiro de Y.
- Dias antes da primeira segunda (ex.: 01–04/jan/2026) pertencem à última
  semana do ano anterior.

Âncora de validação: 10/08/2026 é segunda-feira da W32
(1ª segunda de 2026 = 05/01; (10/08 − 05/01) / 7 = 31 → semana 32).

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
    """Primeira segunda-feira de janeiro do ano (início da W1)."""
    jan1 = date(year, 1, 1)
    # weekday(): Mon=0 ... Sun=6
    return jan1 + timedelta(days=(7 - jan1.weekday()) % 7)


def monday_of(dt: datetime | date) -> date:
    """Segunda-feira da semana que contém a data."""
    d = _as_date(dt)
    return d - timedelta(days=d.weekday())


def calculate_week_number(dt: datetime | date) -> Tuple[int, int]:
    """Número da semana na convenção da empresa. Retorna (week, year).

    A ordem (week, year) é mantida por compatibilidade com os chamadores.
    """
    monday = monday_of(dt)
    year = monday.year
    fm = first_monday(year)
    if monday < fm:
        # Dias antes da 1ª segunda pertencem à última semana do ano anterior
        year -= 1
        fm = first_monday(year)
    week = (monday - fm).days // 7 + 1
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
