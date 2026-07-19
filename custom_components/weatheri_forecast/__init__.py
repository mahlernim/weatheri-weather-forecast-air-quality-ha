"""Weatheri Weather & Air integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WeatheriApi
from .catalog import ForecastLocation, get_location
from .const import (
    CONF_AIR_STATION,
    CONF_FORECAST_RID,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import WeatheriAirCoordinator, WeatheriForecastCoordinator
from .url import build_air_url, build_forecast_url


@dataclass(slots=True)
class WeatheriRuntimeData:
    location: ForecastLocation
    forecast: WeatheriForecastCoordinator
    air: WeatheriAirCoordinator | None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    location = get_location(entry.data[CONF_FORECAST_RID])
    endpoint = build_forecast_url(location)
    api = WeatheriApi(async_get_clientsession(hass))
    forecast = WeatheriForecastCoordinator(hass, entry, endpoint, api)
    await forecast.async_initialize()

    air: WeatheriAirCoordinator | None = None
    if station := entry.data.get(CONF_AIR_STATION):
        air = WeatheriAirCoordinator(
            hass, entry, endpoint, build_air_url(location.air_region_code), station, api
        )
        await air.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = WeatheriRuntimeData(location, forecast, air)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        runtime: WeatheriRuntimeData = hass.data[DOMAIN].pop(entry.entry_id)
        runtime.forecast.async_cancel_expiration()
        if runtime.air:
            runtime.air.async_cancel_expiration()
    return unloaded
