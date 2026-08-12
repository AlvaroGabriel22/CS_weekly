from datetime import UTC, datetime

from app.services.business import get_week_info


def test_get_week_info():
    dt = datetime(2026, 7, 8, tzinfo=UTC)
    week, year = get_week_info(dt)
    assert isinstance(week, int)
    assert isinstance(year, int)
    assert 1 <= week <= 53
    assert year == 2026
