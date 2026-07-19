"""Base entities for Weatheri Weather & Air."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WeatheriAirCoordinator, WeatheriForecastCoordinator


class WeatheriEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: WeatheriForecastCoordinator | WeatheriAirCoordinator) -> None:
        super().__init__(coordinator)
        endpoint = coordinator.endpoint
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, endpoint.rid)},
            manufacturer="Weatheri (unofficial data source)",
            model="Regional Weather & Air",
            name=f"Weatheri {endpoint.location}",
            configuration_url=endpoint.canonical,
        )
