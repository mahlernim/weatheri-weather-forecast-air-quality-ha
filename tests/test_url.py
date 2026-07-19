import pytest

from weatheri_forecast.catalog import get_location
from weatheri_forecast.url import WeatheriUrlError, build_air_url, build_forecast_url


def test_builds_forecast_url_from_catalog():
    result = build_forecast_url(get_location("1101010100"))
    assert result.rid == "1101010100"
    assert result.location == "부산"
    assert result.canonical == (
        "https://www.weatheri.co.kr/forecast/forecast01.php?"
        "rid=1101010100&k=9&a_name=%EB%B6%80%EC%82%B0"
    )


@pytest.mark.parametrize("region_code", ["", "KR", "13.0", "1234"])
def test_rejects_invalid_air_region_code(region_code):
    with pytest.raises(WeatheriUrlError):
        build_air_url(region_code)
