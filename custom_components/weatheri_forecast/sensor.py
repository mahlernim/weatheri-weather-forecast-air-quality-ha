"""Forecast temperature and air-quality sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WeatheriRuntimeData
from .const import DOMAIN
from .coordinator import WeatheriAirCoordinator, WeatheriForecastCoordinator
from .entity import WeatheriEntity
from .models import AirQualitySnapshot, ForecastSnapshot


@dataclass(frozen=True, kw_only=True)
class TemperatureDescription(SensorEntityDescription):
    value_fn: Callable[[ForecastSnapshot], float]


TEMPERATURES = (
    TemperatureDescription(key="today_high", translation_key="today_high", device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, value_fn=lambda x: x.today.high),
    TemperatureDescription(key="today_low", translation_key="today_low", device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, value_fn=lambda x: x.today.low),
    TemperatureDescription(key="tomorrow_high", translation_key="tomorrow_high", device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, value_fn=lambda x: x.tomorrow.high),
    TemperatureDescription(key="tomorrow_low", translation_key="tomorrow_low", device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, value_fn=lambda x: x.tomorrow.low),
)


AIR_SENSORS = (
    SensorEntityDescription(key="pm10", translation_key="pm10", device_class=SensorDeviceClass.PM10, native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0),
    SensorEntityDescription(key="pm25", translation_key="pm25", device_class=SensorDeviceClass.PM25, native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0),
    SensorEntityDescription(key="ozone", translation_key="ozone", native_unit_of_measurement="ppm", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3, entity_registry_enabled_default=False),
    SensorEntityDescription(key="nitrogen_dioxide", translation_key="nitrogen_dioxide", native_unit_of_measurement="ppm", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3, entity_registry_enabled_default=False),
    SensorEntityDescription(key="carbon_monoxide", translation_key="carbon_monoxide", native_unit_of_measurement="ppm", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1, entity_registry_enabled_default=False),
    SensorEntityDescription(key="sulfur_dioxide", translation_key="sulfur_dioxide", native_unit_of_measurement="ppm", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=3, entity_registry_enabled_default=False),
    SensorEntityDescription(key="aqi", translation_key="aqi", native_unit_of_measurement="AQI", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, entity_registry_enabled_default=False),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    runtime: WeatheriRuntimeData = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [WeatheriTemperatureSensor(runtime.forecast, item) for item in TEMPERATURES]
    if runtime.air:
        entities.extend(WeatheriAirSensor(runtime.air, item) for item in AIR_SENSORS)
    async_add_entities(entities)


class WeatheriTemperatureSensor(WeatheriEntity, SensorEntity):
    entity_description: TemperatureDescription

    def __init__(self, coordinator: WeatheriForecastCoordinator, description: TemperatureDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.endpoint.rid}_{description.key}"

    @property
    def suggested_object_id(self) -> str:
        """Keep the registry object ID independent from translated display names."""
        return self.entity_description.key

    @property
    def available(self) -> bool:
        return self.coordinator.is_data_current

    @property
    def native_value(self) -> float | None:
        if not self.available or self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class WeatheriAirSensor(WeatheriEntity, SensorEntity):
    def __init__(self, coordinator: WeatheriAirCoordinator, description: SensorEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.endpoint.rid}_{description.key}"

    @property
    def suggested_object_id(self) -> str:
        """Keep PM2.5 and other registry object IDs stable across languages."""
        return self.entity_description.key

    @property
    def available(self) -> bool:
        return self.coordinator.is_observation_fresh and self.native_value is not None

    @property
    def native_value(self) -> float | None:
        data: AirQualitySnapshot | None = self.coordinator.data
        return None if data is None else data.measurements.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {"station": self.coordinator.station}
