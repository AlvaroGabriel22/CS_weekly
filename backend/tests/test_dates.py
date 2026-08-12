from app.core.dates import normalize_timezone


def test_normalize_timezone_defaults_to_utc():
    assert normalize_timezone(None) == "UTC"
    assert normalize_timezone("") == "UTC"


def test_normalize_timezone_accepts_valid_iana_name():
    assert normalize_timezone("America/Sao_Paulo") == "America/Sao_Paulo"
    assert normalize_timezone("Europe/Lisbon") == "Europe/Lisbon"


def test_normalize_timezone_falls_back_for_invalid_name():
    assert normalize_timezone("Not/A_Real_Zone") == "UTC"
