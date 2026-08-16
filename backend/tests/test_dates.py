"""Convenção de semanas da empresa: W1 contém o 1º de janeiro; o ano da
semana é o ano do seu domingo. Âncora validada com o usuário: 10/08/2026 = W33."""
from datetime import date

from app.core.dates import calculate_week_number, get_week_boundaries, weeks_in_year


def test_anchor_week_w33_2026():
    assert calculate_week_number(date(2026, 8, 10)) == (33, 2026)
    assert calculate_week_number(date(2026, 8, 14)) == (33, 2026)
    assert calculate_week_number(date(2026, 8, 16)) == (33, 2026)


def test_w1_contains_january_first():
    # 29/12/2025 (seg) – 04/01/2026 (dom) é a W1 de 2026
    assert calculate_week_number(date(2025, 12, 29)) == (1, 2026)
    assert calculate_week_number(date(2026, 1, 1)) == (1, 2026)
    assert calculate_week_number(date(2026, 1, 4)) == (1, 2026)
    assert calculate_week_number(date(2026, 1, 5)) == (2, 2026)


def test_week_year_follows_sunday():
    start, end = get_week_boundaries(2026, 1)
    assert start == date(2025, 12, 29)
    assert end == date(2026, 1, 4)


def test_weeks_in_year():
    assert weeks_in_year(2026) == 52
    assert weeks_in_year(2028) == 53
