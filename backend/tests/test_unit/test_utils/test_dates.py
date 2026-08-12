import pytest
from datetime import datetime, date
from app.core.dates import calculate_week_number, get_week_boundaries, normalize_to_iso_date


class TestDateUtils:
    """Unit tests para utilidades de data"""

    def test_calculate_week_number_friday_aug_7_2026(self):
        """Friday Aug 7, 2026 deve estar na semana 32"""
        dt = datetime(2026, 8, 7, 12, 0, 0)
        week_num, year = calculate_week_number(dt)

        assert week_num == 32
        assert year == 2026

    def test_calculate_week_number_entire_week_same(self):
        """Todas as datas da mesma semana devem ter o mesmo week_number"""
        monday = datetime(2026, 8, 3)  # Monday
        friday = datetime(2026, 8, 7)  # Friday
        sunday = datetime(2026, 8, 9)  # Sunday

        week_monday, year_monday = calculate_week_number(monday)
        week_friday, year_friday = calculate_week_number(friday)
        week_sunday, year_sunday = calculate_week_number(sunday)

        assert week_monday == week_friday == week_sunday == 32
        assert year_monday == year_friday == year_sunday == 2026

    def test_calculate_week_number_adjacent_weeks(self):
        """Semanas adjacentes devem ter week_numbers diferentes"""
        friday_week32 = datetime(2026, 8, 7)  # Week 32
        friday_week33 = datetime(2026, 8, 14)  # Week 33

        week32, _ = calculate_week_number(friday_week32)
        week33, _ = calculate_week_number(friday_week33)

        assert week33 == week32 + 1
        assert week33 == 33

    def test_calculate_week_number_sunday_vs_monday(self):
        """Sunday da semana anterior e Monday da mesma semana devem estar em semanas diferentes"""
        sunday_prev = datetime(2026, 8, 2)  # Sunday week 31
        monday_next = datetime(2026, 8, 3)  # Monday week 32

        week_sunday, _ = calculate_week_number(sunday_prev)
        week_monday, _ = calculate_week_number(monday_next)

        assert week_sunday == 31
        assert week_monday == 32

    def test_get_week_boundaries_week_32_2026(self):
        """Week 32 de 2026 deve ser 3 a 9 de agosto"""
        monday, sunday = get_week_boundaries(2026, 32)

        assert monday.year == 2026
        assert monday.month == 8
        assert monday.day == 3

        assert sunday.year == 2026
        assert sunday.month == 8
        assert sunday.day == 9

    def test_get_week_boundaries_spans_7_days(self):
        """Boundaries devem retornar exatamente 7 dias"""
        monday, sunday = get_week_boundaries(2026, 32)

        delta = sunday - monday
        assert delta.days == 6  # Segunda a domingo = 6 dias após segunda

    def test_get_week_boundaries_multiple_weeks(self):
        """Diferentes semanas devem ter boundaries diferentes"""
        mon1, sun1 = get_week_boundaries(2026, 32)
        mon2, sun2 = get_week_boundaries(2026, 33)

        assert mon1 != mon2
        assert sun1 != sun2
        assert mon2 > sun1

    def test_normalize_to_iso_date_removes_time(self):
        """Normalizar deve remover informações de tempo"""
        dt = datetime(2026, 8, 7, 14, 30, 45)
        iso_str = normalize_to_iso_date(dt)

        assert iso_str == '2026-08-07'
        assert 'T' not in iso_str
        assert ':' not in iso_str

    def test_normalize_to_iso_date_pads_single_digits(self):
        """Meses/dias com 1 dígito devem ser padronizados com 2 dígitos"""
        dt = datetime(2026, 1, 5, 0, 0, 0)
        iso_str = normalize_to_iso_date(dt)

        assert iso_str == '2026-01-05'

    def test_year_boundary_transition(self):
        """Transição de ano deve mudar year corretamente"""
        dec31_2025 = datetime(2025, 12, 31)
        jan1_2026 = datetime(2026, 1, 1)

        week_dec31, year_dec31 = calculate_week_number(dec31_2025)
        week_jan1, year_jan1 = calculate_week_number(jan1_2026)

        assert year_dec31 == 2025
        assert year_jan1 == 2026

    def test_leap_year_feb_28_29(self):
        """Leap year deve ter Feb 29"""
        feb28_2024 = date(2024, 2, 28)
        feb29_2024 = date(2024, 2, 29)
        mar1_2024 = date(2024, 3, 1)

        # 2024 é leap year
        assert (mar1_2024 - feb28_2024).days == 2

    @pytest.mark.parametrize('day,month,year,expected_week', [
        (7, 8, 2026, 32),   # Friday
        (3, 8, 2026, 32),   # Monday
        (9, 8, 2026, 32),   # Sunday
        (14, 8, 2026, 33),  # Next Friday
        (1, 1, 2026, 1),    # Jan 1
    ])
    def test_week_numbers_parametrized(self, day, month, year, expected_week):
        """Testa múltiplos week_numbers com parametrização"""
        dt = datetime(year, month, day)
        week_num, _ = calculate_week_number(dt)

        assert week_num == expected_week

    def test_time_doesnt_affect_week_number(self):
        """Horas/minutos/segundos não devem afetar week_number"""
        d1 = datetime(2026, 8, 7, 0, 0, 0)
        d2 = datetime(2026, 8, 7, 12, 30, 45)
        d3 = datetime(2026, 8, 7, 23, 59, 59)

        week1, _ = calculate_week_number(d1)
        week2, _ = calculate_week_number(d2)
        week3, _ = calculate_week_number(d3)

        assert week1 == week2 == week3 == 32
