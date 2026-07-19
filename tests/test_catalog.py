from collections import Counter

from weatheri_forecast.catalog import LOCATIONS, get_location, location_options
from weatheri_forecast.url import build_air_url, build_forecast_url


def test_nationwide_catalog_is_unique_and_contains_busans_mapping():
    assert len(LOCATIONS) == 172
    assert len({item.rid for item in LOCATIONS.values()}) == 172
    busan = get_location("1101010100")
    assert (busan.name, busan.forecast_group, busan.air_region_code) == ("부산", "9", "13")
    assert "rid=1101010100" in build_forecast_url(busan).canonical
    assert build_air_url(busan.air_region_code).endswith("a=13")


def test_ambiguous_names_have_distinct_labels():
    names = Counter(item.name for item in LOCATIONS.values())
    assert names["광주"] == 2
    labels = [label for _, label in location_options() if label.endswith("광주")]
    assert labels == ["경기 · 광주", "광주"]


def test_all_catalog_fields_and_korean_labels_are_present():
    for rid, item in LOCATIONS.items():
        assert rid.isdigit()
        assert item.name and item.label and item.forecast_group.isdigit()
        assert item.air_region_code.isdigit()
