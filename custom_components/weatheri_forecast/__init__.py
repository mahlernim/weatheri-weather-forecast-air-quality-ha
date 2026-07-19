"""Weatheri Weather & Air integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WeatheriApi
from .catalog import ForecastLocation, get_location
from .const import (
    CONF_AIR_REGION_CODE, CONF_AIR_STATION, CONF_FORECAST_GROUP,
    CONF_FORECAST_NAME, CONF_FORECAST_RID, DOMAIN, ENTRY_VERSION, PLATFORMS,
)
from .coordinator import WeatheriAirCoordinator, WeatheriForecastCoordinator
from .url import build_air_url, build_forecast_url, canonicalize_forecast_url


@dataclass(slots=True)
class WeatheriRuntimeData:
    location: ForecastLocation
    forecast: WeatheriForecastCoordinator
    air: WeatheriAirCoordinator | None


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a version 1 pasted-URL entry to catalog-backed data."""
    if entry.version >= ENTRY_VERSION:
        return True
    if entry.version != 1:
        return False
    raw_url = entry.data.get(CONF_URL) or entry.data.get("forecast_url")
    endpoint = canonicalize_forecast_url(raw_url)
    location = get_location(endpoint.rid)
    hass.config_entries.async_update_entry(
        entry,
        data={
            CONF_FORECAST_RID: location.rid,
            CONF_FORECAST_GROUP: location.forecast_group,
            CONF_FORECAST_NAME: location.name,
            CONF_AIR_REGION_CODE: location.air_region_code,
            CONF_AIR_STATION: None,
        },
        version=ENTRY_VERSION,
        title=location.name,
        unique_id=location.rid,
    )
    return True


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

    registry = er.async_get(hass)
    if old_entity_id := registry.async_get_entity_id("sensor", DOMAIN, f"{location.rid}_last_success"):
        registry.async_remove(old_entity_id)
    pm25_entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{location.rid}_pm25")
    generated_pm25_id = f"sensor.weatheri_{endpoint.entity_slug}_pm2_5"
    stable_pm25_id = f"sensor.weatheri_{endpoint.entity_slug}_pm25"
    if pm25_entity_id == generated_pm25_id and not registry.async_get(stable_pm25_id):
        registry.async_update_entity(pm25_entity_id, new_entity_id=stable_pm25_id)

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
