"""Dropdown onboarding and air-station reconfiguration."""

from __future__ import annotations

from functools import partial
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from homeassistant.util import dt as dt_util

from .api import WeatheriApi, WeatheriApiError
from .catalog import ForecastLocation, get_location, location_options
from .const import (
    CONF_AIR_REGION_CODE, CONF_AIR_STATION, CONF_FORECAST_GROUP,
    CONF_FORECAST_NAME, CONF_FORECAST_RID, DOMAIN, ENTRY_VERSION, NO_AIR_STATION,
)
from .parser import (
    WeatheriParseError, discover_air_stations, parse_air_quality_html, parse_forecast_html,
)
from .url import build_air_url, build_forecast_url

_LOGGER = logging.getLogger(__name__)


def _selector(options: list[tuple[str, str]]) -> SelectSelector:
    return SelectSelector(SelectSelectorConfig(
        options=[{"value": value, "label": label} for value, label in options],
        mode=SelectSelectorMode.DROPDOWN,
        sort=False,
    ))


async def _validate_forecast(hass: HomeAssistant, location: ForecastLocation) -> None:
    endpoint = build_forecast_url(location)
    now = dt_util.now()
    html = await WeatheriApi(async_get_clientsession(hass)).async_fetch_html(endpoint.canonical)
    await hass.async_add_executor_job(partial(
        parse_forecast_html, html, location=location.name,
        current_date=now.date(), fetched_at=now,
    ))


async def _load_air_page(hass: HomeAssistant, location: ForecastLocation) -> tuple[str, list[str]]:
    html = await WeatheriApi(async_get_clientsession(hass)).async_fetch_html(
        build_air_url(location.air_region_code)
    )
    stations = await hass.async_add_executor_job(discover_air_stations, html)
    return html, stations


class WeatheriForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one forecast location and at most one air station."""

    VERSION = ENTRY_VERSION

    def __init__(self) -> None:
        self._location: ForecastLocation | None = None
        self._air_html: str | None = None
        self._stations: list[str] = []
        self._reconfigure = False

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                location = get_location(user_input[CONF_FORECAST_RID])
                await _validate_forecast(self.hass, location)
            except ValueError:
                errors[CONF_FORECAST_RID] = "invalid_location"
            except WeatheriApiError:
                errors["base"] = "cannot_connect"
            except WeatheriParseError as err:
                _LOGGER.warning("Weatheri forecast validation failed: %s", err)
                errors["base"] = "invalid_forecast_data"
            except Exception:  # pragma: no cover
                _LOGGER.exception("Unexpected Weatheri forecast setup error")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(location.rid)
                self._abort_if_unique_id_configured()
                self._location = location
                return await self.async_step_air_station()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_FORECAST_RID): _selector(location_options())}),
            errors=errors,
        )

    async def async_step_air_station(self, user_input=None):
        if self._location is None:
            return self.async_abort(reason="unknown")
        errors: dict[str, str] = {}
        if self._air_html is None:
            try:
                self._air_html, self._stations = await _load_air_page(self.hass, self._location)
            except (WeatheriApiError, WeatheriParseError):
                self._stations = []
                errors["base"] = "cannot_connect_air"

        if user_input is not None:
            selected = user_input[CONF_AIR_STATION]
            station = None if selected == NO_AIR_STATION else selected
            if station is not None and station not in self._stations:
                errors[CONF_AIR_STATION] = "invalid_station"
            elif station is not None:
                try:
                    now = dt_util.now()
                    await self.hass.async_add_executor_job(partial(
                        parse_air_quality_html, self._air_html, station=station,
                        fetched_at=now, local_tz=now.tzinfo,
                    ))
                except WeatheriParseError as err:
                    _LOGGER.warning("Weatheri air validation failed: %s", err)
                    errors["base"] = "invalid_air_data"
            if not errors or (station is None and set(errors) == {"base"}):
                data = {
                    CONF_FORECAST_RID: self._location.rid,
                    CONF_FORECAST_GROUP: self._location.forecast_group,
                    CONF_FORECAST_NAME: self._location.name,
                    CONF_AIR_REGION_CODE: self._location.air_region_code,
                    CONF_AIR_STATION: station,
                }
                if self._reconfigure:
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(), data_updates=data
                    )
                return self.async_create_entry(title=self._location.name, data=data)

        options = [(NO_AIR_STATION, "Forecast only / 대기정보 사용 안 함")]
        options.extend((station, station) for station in self._stations)
        return self.async_show_form(
            step_id="air_station",
            data_schema=vol.Schema({
                vol.Required(CONF_AIR_STATION, default=NO_AIR_STATION): _selector(options)
            }),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        self._location = get_location(entry.data[CONF_FORECAST_RID])
        self._reconfigure = True
        return await self.async_step_air_station(user_input)
