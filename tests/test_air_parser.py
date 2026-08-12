from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from weatheri_forecast.models import AirQualitySnapshot, air_snapshot_is_current
from weatheri_forecast.parser import (
    WeatheriParseError,
    discover_air_stations,
    parse_air_quality_html,
)

TZ = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 7, 19, 18, 30, tzinfo=TZ)


def _html(*, time="26.07.19 18:00", header=None, values=None, station="덕천동"):
    header = header or ["지역", "미세먼지 (PM10)", "초미세먼지 (PM2.5)", "오존", "이산화질소", "일산화탄소", "아황산가스", "대기통합지수"]
    values = values or [station, "34", "13", "0.058", "0.007", "0.3", "0.003", "74"]
    heads = "".join(f"<th>{value}</th>" for value in header)
    cells = "".join(f"<td>{value}</td><td></td>" for value in values)
    return f"<html><meta charset='utf-8'><body><p>한국환경공단, {time}</p><table><tr>{heads}</tr><tr>{cells}</tr></table></body></html>"


def test_discovers_korean_station_and_parses_all_measurements():
    html = _html()
    assert discover_air_stations(html) == ["덕천동"]
    data = parse_air_quality_html(html, station="덕천동", fetched_at=NOW, local_tz=TZ)
    assert data.station == "덕천동"
    assert data.measurements == {
        "pm10": 34, "pm25": 13, "ozone": 0.058, "nitrogen_dioxide": 0.007,
        "carbon_monoxide": 0.3, "sulfur_dioxide": 0.003, "aqi": 74,
    }


def test_reordered_columns_are_mapped_by_header():
    header = ["지역", "오존", "대기통합지수", "초미세먼지 (PM2.5)", "아황산가스", "미세먼지 (PM10)", "일산화탄소", "이산화질소"]
    values = ["덕천동", "0.058", "74", "13", "0.003", "34", "0.3", "0.007"]
    data = parse_air_quality_html(_html(header=header, values=values), station="덕천동", fetched_at=NOW, local_tz=TZ)
    assert data.measurements["pm10"] == 34
    assert data.measurements["nitrogen_dioxide"] == 0.007


def test_dash_and_missing_cell_only_remove_individual_measurements():
    data = parse_air_quality_html(
        _html(values=["덕천동", "34", "13", "-", "0.007", "0.3", "0.003"]),
        station="덕천동", fetched_at=NOW, local_tz=TZ,
    )
    assert data.measurements["ozone"] is None
    assert data.measurements["aqi"] is None
    assert data.missing_measurements == ["ozone", "aqi"]
    assert air_snapshot_is_current(data, NOW)


@pytest.mark.parametrize("bad", ["abc", "-1", "99999"])
def test_malformed_pm_value_rejects_update(bad):
    with pytest.raises(WeatheriParseError):
        parse_air_quality_html(_html(values=["덕천동", bad, "13", "0.1", "0.1", "0.1", "0.1", "50"]), station="덕천동", fetched_at=NOW, local_tz=TZ)


def test_future_timestamp_rejected_and_stale_timestamp_parsed_but_not_current():
    with pytest.raises(WeatheriParseError):
        parse_air_quality_html(_html(time="26.07.19 19:00"), station="덕천동", fetched_at=NOW, local_tz=TZ)
    stale = parse_air_quality_html(_html(time="26.07.19 14:00"), station="덕천동", fetched_at=NOW, local_tz=TZ)
    assert not air_snapshot_is_current(stale, NOW)


def test_three_hour_age_boundary_and_pm_pair_requirement():
    measurements = {"pm10": 10.0, "pm25": 5.0, "ozone": None, "nitrogen_dioxide": None, "carbon_monoxide": None, "sulfur_dioxide": None, "aqi": None}
    exact = AirQualitySnapshot("덕천동", NOW - timedelta(hours=3), NOW, measurements)
    assert air_snapshot_is_current(exact, NOW)
    assert not air_snapshot_is_current(exact, NOW + timedelta(seconds=1))
    partial = AirQualitySnapshot("덕천동", NOW, NOW, {**measurements, "pm25": None})
    assert not air_snapshot_is_current(partial, NOW)


def test_snapshot_round_trip():
    snapshot = parse_air_quality_html(_html(), station="덕천동", fetched_at=NOW, local_tz=TZ)
    assert AirQualitySnapshot.from_dict(snapshot.as_dict()) == snapshot
