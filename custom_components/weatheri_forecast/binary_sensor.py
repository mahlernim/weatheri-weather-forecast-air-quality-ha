"""Forecast and air freshness diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WeatheriRuntimeData
from .const import DOMAIN
from .coordinator import WeatheriAirCoordinator, WeatheriForecastCoordinator
from .entity import WeatheriEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime: WeatheriRuntimeData = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = [WeatheriForecastHealth(runtime.forecast)]
    if runtime.air:
        entities.append(WeatheriAirHealth(runtime.air))
    async_add_entities(entities)


class _HealthBase(WeatheriEntity, BinarySensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:database-check"

    @property
    def available(self) -> bool:
        return True

    @staticmethod
    def _attempt_attributes(coordinator) -> dict[str, Any]:
        return {
            "last_success": coordinator.last_success.isoformat()
            if coordinator.last_success
            else None,
            "last_attempt": coordinator.last_attempt.isoformat()
            if coordinator.last_attempt
            else None,
            "last_attempt_success": coordinator.last_attempt_success,
            "last_error": coordinator.last_error,
            "using_cached_data": coordinator.using_cached_data,
        }


class WeatheriForecastHealth(_HealthBase):
    _attr_translation_key = "data_current"

    def __init__(self, coordinator: WeatheriForecastCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.endpoint.rid}_data_current"

    @property
    def suggested_object_id(self) -> str:
        """Return a translation-independent registry object ID."""
        return "data_current"

    @property
    def is_on(self) -> bool:
        return self.coordinator.is_data_current

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            "source_date": data.source_date.isoformat() if data else None,
            **self._attempt_attributes(self.coordinator),
            "rollover_retry_count": self.coordinator.rollover_retry_count,
        }


class WeatheriAirHealth(_HealthBase):
    _attr_translation_key = "air_data_current"

    def __init__(self, coordinator: WeatheriAirCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.endpoint.rid}_air_data_current"

    @property
    def suggested_object_id(self) -> str:
        """Return a translation-independent registry object ID."""
        return "air_data_current"

    @property
    def is_on(self) -> bool:
        return self.coordinator.is_data_current

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        age = self.coordinator.data_age_minutes
        return {
            "station": self.coordinator.station,
            "source_updated_at": data.source_updated_at.isoformat() if data else None,
            **self._attempt_attributes(self.coordinator),
            "data_age_minutes": round(age, 1) if age is not None else None,
            "missing_measurements": data.missing_measurements if data else [],
        }
