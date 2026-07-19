import pytest

from weatheri_forecast.url import WeatheriUrlError, canonicalize_forecast_url


VALID_URL = (
    "https://www.weatheri.co.kr/forecast/forecast01.php?"
    "rid=1101010100&k=9&a_name=%EB%B6%80%EC%82%B0"
)


def test_canonicalize_valid_url():
    result = canonicalize_forecast_url(VALID_URL)
    assert result.rid == "1101010100"
    assert result.location == "부산"
    assert result.entity_slug == "busan"
    assert result.canonical == VALID_URL


def test_canonicalizes_host_and_query_order():
    result = canonicalize_forecast_url(
        "https://weatheri.co.kr/forecast/forecast01.php?a_name=%EB%B6%80%EC%82%B0&k=9&rid=1101010100"
    )
    assert result.canonical == VALID_URL


@pytest.mark.parametrize(
    "url",
    [
        "http://www.weatheri.co.kr/forecast/forecast01.php?rid=1101010100&k=9&a_name=Busan",
        "https://example.com/forecast/forecast01.php?rid=1101010100&k=9&a_name=Busan",
        "https://www.weatheri.co.kr/main01_2.php?rid=1101010100&k=9&a_name=Busan",
        "https://www.weatheri.co.kr/forecast/forecast01.php?rid=abc&k=9&a_name=Busan",
        "https://www.weatheri.co.kr/forecast/forecast01.php?rid=1101010100&a_name=Busan",
        "https://www.weatheri.co.kr/forecast/forecast01.php?rid=1101010100&k=9&a_name=",
        "https://user:pass@www.weatheri.co.kr/forecast/forecast01.php?rid=1101010100&k=9&a_name=Busan",
    ],
)
def test_rejects_unsupported_url(url):
    with pytest.raises(WeatheriUrlError):
        canonicalize_forecast_url(url)
