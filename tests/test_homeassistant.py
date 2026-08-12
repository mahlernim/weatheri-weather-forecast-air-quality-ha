"""Home Assistant integration tests; skipped in parser-only environments."""

from unittest.mock import AsyncMock, patch
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

pytest.importorskip("homeassistant")
pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weatheri_forecast.api import WeatheriApiError
from custom_components.weatheri_forecast.catalog import get_location
from custom_components.weatheri_forecast.const import (
    CONF_AIR_REGION_CODE,
    CONF_AIR_STATION,
    CONF_FORECAST_GROUP,
    CONF_FORECAST_NAME,
    CONF_FORECAST_RID,
    DOMAIN,
    ENTRY_VERSION,
    NO_AIR_STATION,
)
from custom_components.weatheri_forecast.binary_sensor import (
    WeatheriAirHealth,
    WeatheriForecastHealth,
)
from custom_components.weatheri_forecast.sensor import (
    AIR_SENSORS,
    TEMPERATURES,
    WeatheriAirSensor,
    WeatheriTemperatureSensor,
)
from custom_components.weatheri_forecast.coordinator import (
    WeatheriAirCoordinator,
    WeatheriForecastCoordinator,
)
from custom_components.weatheri_forecast.url import build_air_url, build_forecast_url

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.mark.asyncio
async def test_dropdown_progression_and_forecast_only(hass):
    with (
        patch(
            "custom_components.weatheri_forecast.config_flow._validate_forecast", new=AsyncMock()
        ),
        patch(
            "custom_components.weatheri_forecast.config_flow._load_air_page",
            new=AsyncMock(return_value=("<html/>", ["덕천동", "화명동"])),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is data_entry_flow.FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_FORECAST_RID: "1101010100"}
        )
        assert result["step_id"] == "air_station"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_AIR_STATION: NO_AIR_STATION}
        )
        assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_AIR_STATION] is None


@pytest.mark.asyncio
async def test_duplicate_rid_is_prevented(hass):
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="1101010100",
        data={CONF_FORECAST_RID: "1101010100"},
    ).add_to_hass(hass)
    with patch(
        "custom_components.weatheri_forecast.config_flow._validate_forecast", new=AsyncMock()
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_FORECAST_RID: "1101010100"},
        )
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_reconfigure_station_without_changing_location(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1101010100",
        version=ENTRY_VERSION,
        data={
            CONF_FORECAST_RID: "1101010100",
            CONF_FORECAST_GROUP: "9",
            CONF_FORECAST_NAME: "부산",
            CONF_AIR_REGION_CODE: "13",
            CONF_AIR_STATION: None,
        },
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.weatheri_forecast.config_flow._load_air_page",
            new=AsyncMock(return_value=("<html/>", ["덕천동"])),
        ),
        patch("custom_components.weatheri_forecast.config_flow.parse_air_quality_html"),
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_AIR_STATION: "덕천동"}
        )
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert entry.data[CONF_FORECAST_RID] == "1101010100"
    assert entry.data[CONF_AIR_STATION] == "덕천동"


def test_entity_policy():
    assert [item.key for item in TEMPERATURES] == [
        "today_high",
        "today_low",
        "tomorrow_high",
        "tomorrow_low",
    ]
    enabled = [item.key for item in AIR_SENSORS if item.entity_registry_enabled_default]
    disabled = [item.key for item in AIR_SENSORS if not item.entity_registry_enabled_default]
    assert enabled == ["pm10", "pm25"]
    assert disabled == ["ozone", "nitrogen_dioxide", "carbon_monoxide", "sulfur_dioxide", "aqi"]
    sensor_source = (
        __import__("pathlib").Path(__file__).parents[1]
        / "custom_components/weatheri_forecast/sensor.py"
    ).read_text(encoding="utf-8")
    assert "WeatheriLastSuccessSensor" not in sensor_source


class _SequenceApi:
    def __init__(self, *responses):
        self.responses = list(responses)

    async def async_fetch_html(self, _url):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _forecast_html(today=19, tomorrow=20):
    return f"""
    <table><tr><td>07월 {today}일</td><td>07월 {tomorrow}일</td></tr><tr>
    <td onclick='showthree("1")'>29˚C 26˚C</td>
    <td onclick='showthree("2")'>32˚C 27˚C</td>
    </tr></table>
    """


def _air_html():
    return """
    <p>한국환경공단, 26.07.19 18:00</p><table>
    <tr><th>지역</th><th>미세먼지 (PM10)</th><th>초미세먼지 (PM2.5)</th><th>오존</th><th>이산화질소</th><th>일산화탄소</th><th>아황산가스</th><th>대기통합지수</th></tr>
    <tr><td>덕천동</td><td>34</td><td>13</td><td>-</td><td>0.007</td><td>0.3</td><td>0.003</td><td>74</td></tr>
    </table>
    """


def test_translation_independent_entity_object_ids(hass):
    """Entity IDs must not change when translated names contain punctuation."""
    location = get_location("1101010100")
    endpoint = build_forecast_url(location)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=location.rid, version=ENTRY_VERSION)
    forecast = WeatheriForecastCoordinator(hass, entry, endpoint, _SequenceApi())
    air = WeatheriAirCoordinator(
        hass, entry, endpoint, build_air_url("13"), "덕천동", _SequenceApi()
    )
    assert WeatheriTemperatureSensor(forecast, TEMPERATURES[0]).suggested_object_id == "today_high"
    assert WeatheriAirSensor(air, AIR_SENSORS[1]).suggested_object_id == "pm25"
    assert WeatheriForecastHealth(forecast).suggested_object_id == "data_current"
    assert WeatheriAirHealth(air).suggested_object_id == "air_data_current"


@pytest.mark.asyncio
async def test_independent_coordinators_cache_recovery_and_expiration(hass):
    location = get_location("1101010100")
    endpoint = build_forecast_url(location)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=location.rid,
        version=ENTRY_VERSION,
        data={CONF_FORECAST_RID: location.rid},
    )
    entry.add_to_hass(hass)
    current = [datetime(2026, 7, 19, 18, 30, tzinfo=ZoneInfo("Asia/Seoul"))]
    forecast_api = _SequenceApi(
        _forecast_html(), WeatheriApiError("forecast down"), WeatheriApiError("forecast down")
    )
    air_api = _SequenceApi(_air_html(), WeatheriApiError("air down"), WeatheriApiError("air down"))
    forecast = WeatheriForecastCoordinator(hass, entry, endpoint, forecast_api)
    air = WeatheriAirCoordinator(hass, entry, endpoint, build_air_url("13"), "덕천동", air_api)
    with patch(
        "custom_components.weatheri_forecast.coordinator.dt_util.now",
        side_effect=lambda: current[0],
    ):
        await forecast.async_initialize()
        await air.async_initialize()
        assert forecast.is_data_current and air.is_data_current
        assert air.data.measurements["ozone"] is None

        current[0] = datetime(2026, 7, 19, 20, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        await forecast.async_refresh()
        await air.async_refresh()
        assert forecast.using_cached_data and forecast.is_data_current
        assert air.using_cached_data and air.is_data_current

        current[0] = datetime(2026, 7, 20, 0, 1, tzinfo=ZoneInfo("Asia/Seoul"))
        await forecast.async_refresh()
        await air.async_refresh()
        assert not forecast.is_data_current
        assert not air.is_data_current
        assert air.data is None
    forecast.async_shutdown()
    air.async_cancel_expiration()


@pytest.mark.asyncio
async def test_midnight_expiration_refreshes_and_retries_delayed_source(hass):
    location = get_location("1101010100")
    endpoint = build_forecast_url(location)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=location.rid,
        version=ENTRY_VERSION,
        data={CONF_FORECAST_RID: location.rid},
    )
    entry.add_to_hass(hass)
    current = [datetime(2026, 7, 19, 23, 55, tzinfo=ZoneInfo("Asia/Seoul"))]
    api = _SequenceApi(
        _forecast_html(),
        _forecast_html(),
        _forecast_html(20, 21),
    )
    forecast = WeatheriForecastCoordinator(hass, entry, endpoint, api)

    with patch(
        "custom_components.weatheri_forecast.coordinator.dt_util.now",
        side_effect=lambda: current[0],
    ):
        await forecast.async_initialize()
        forecast.async_cancel_expiration()
        current[0] = datetime(2026, 7, 20, 0, 0, 1, tzinfo=ZoneInfo("Asia/Seoul"))
        forecast._handle_expiration(current[0])
        await hass.async_block_till_done()

        assert not forecast.is_data_current
        assert forecast.rollover_retry_count == 1
        assert forecast._cancel_retry is not None

        await forecast.async_refresh()
        assert forecast.is_data_current
        assert forecast.rollover_retry_count == 0
        assert forecast._cancel_retry is None

    forecast.async_shutdown()
