"""Independent forecast and air-quality coordinators."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from functools import partial
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import WeatheriApi, WeatheriApiError
from .const import AIR_MAX_AGE, DEFAULT_UPDATE_INTERVAL, DOMAIN, STORE_VERSION
from .models import (
    AirQualitySnapshot,
    ForecastSnapshot,
    air_data_age_minutes,
    air_snapshot_is_current,
    air_snapshot_is_fresh,
    snapshot_is_current,
)
from .parser import WeatheriParseError, parse_air_quality_html, parse_forecast_html
from .url import WeatheriUrl

_LOGGER = logging.getLogger(__name__)


class _WeatheriCoordinatorBase:
    last_success: datetime | None
    last_attempt: datetime | None
    last_attempt_success: bool | None
    last_error: str | None
    using_cached_data: bool

    def _init_health(self) -> None:
        self.last_success = None
        self.last_attempt = None
        self.last_attempt_success = None
        self.last_error = None
        self.using_cached_data = False
        self._cancel_expiration: Callable[[], None] | None = None

    def _schedule_expiration(self, expires_at: datetime) -> None:
        self.async_cancel_expiration()
        delay = max(0.1, (expires_at - dt_util.now()).total_seconds() + 0.1)
        self._cancel_expiration = async_call_later(self.hass, delay, self._handle_expiration)

    @callback
    def _handle_expiration(self, _now: datetime) -> None:
        self._cancel_expiration = None
        self.async_set_updated_data(self.data)

    @callback
    def async_cancel_expiration(self) -> None:
        if self._cancel_expiration is not None:
            self._cancel_expiration()
            self._cancel_expiration = None


class WeatheriForecastCoordinator(
    _WeatheriCoordinatorBase, DataUpdateCoordinator[ForecastSnapshot]
):
    """Fetch and retain complete same-day forecasts."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, endpoint: WeatheriUrl, api: WeatheriApi) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=f"{DOMAIN}_{endpoint.rid}_forecast",
            update_interval=DEFAULT_UPDATE_INTERVAL, always_update=True,
        )
        self.entry, self.endpoint, self.api = entry, endpoint, api
        self.store: Store[dict] = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}.forecast")
        self._init_health()

    @property
    def is_data_current(self) -> bool:
        return snapshot_is_current(self.data, dt_util.now().date())

    async def async_initialize(self) -> None:
        await self._async_load_cache()
        await self.async_refresh()
        if self.data is None or not self.is_data_current:
            raise ConfigEntryNotReady(self.last_error or "No current Weatheri forecast")

    async def _async_load_cache(self) -> None:
        stored = await self.store.async_load()
        if not stored:
            return
        try:
            snapshot = ForecastSnapshot.from_dict(stored["snapshot"])
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Ignoring invalid Weatheri forecast cache: %s", err)
            return
        if not snapshot_is_current(snapshot, dt_util.now().date()):
            await self.store.async_remove()
            return
        self.data = snapshot
        self.last_success = snapshot.fetched_at
        self.using_cached_data = True
        self._schedule_forecast_expiration(snapshot)

    async def _async_update_data(self) -> ForecastSnapshot:
        now = dt_util.now()
        self.last_attempt = now
        try:
            html = await self.api.async_fetch_html(self.endpoint.canonical)
            snapshot = await self.hass.async_add_executor_job(partial(
                parse_forecast_html, html, location=self.endpoint.location,
                current_date=now.date(), fetched_at=now,
            ))
        except (WeatheriApiError, WeatheriParseError) as err:
            self.last_attempt_success, self.last_error = False, str(err)
            if snapshot_is_current(self.data, now.date()):
                self.using_cached_data = True
                self._schedule_forecast_expiration(self.data)
                _LOGGER.warning("Weatheri forecast failed; retaining same-day data: %s", err)
                return self.data
            self.using_cached_data = False
            raise UpdateFailed(str(err)) from err
        self.last_success, self.last_attempt_success = now, True
        self.last_error, self.using_cached_data = None, False
        await self.store.async_save({"snapshot": snapshot.as_dict()})
        self._schedule_forecast_expiration(snapshot)
        return snapshot

    def _schedule_forecast_expiration(self, snapshot: ForecastSnapshot) -> None:
        now = dt_util.now()
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self._schedule_expiration(next_midnight)


class WeatheriAirCoordinator(
    _WeatheriCoordinatorBase, DataUpdateCoordinator[AirQualitySnapshot]
):
    """Fetch and retain one station independently of forecast data."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, endpoint: WeatheriUrl,
        air_url: str, station: str, api: WeatheriApi,
    ) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=f"{DOMAIN}_{endpoint.rid}_air",
            update_interval=DEFAULT_UPDATE_INTERVAL, always_update=True,
        )
        self.entry, self.endpoint, self.air_url, self.station, self.api = entry, endpoint, air_url, station, api
        self.store: Store[dict] = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}.air")
        self._init_health()

    @property
    def is_data_current(self) -> bool:
        return air_snapshot_is_current(self.data, dt_util.now())

    @property
    def is_observation_fresh(self) -> bool:
        return air_snapshot_is_fresh(self.data, dt_util.now())

    @property
    def data_age_minutes(self) -> float | None:
        return air_data_age_minutes(self.data, dt_util.now())

    async def async_initialize(self) -> None:
        await self._async_load_cache()
        await self.async_refresh()  # Air failure never blocks an otherwise valid forecast entry.

    async def _async_load_cache(self) -> None:
        stored = await self.store.async_load()
        if not stored:
            return
        try:
            snapshot = AirQualitySnapshot.from_dict(stored["snapshot"])
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Ignoring invalid Weatheri air cache: %s", err)
            return
        if snapshot.station != self.station or dt_util.now() - snapshot.source_updated_at > AIR_MAX_AGE:
            await self.store.async_remove()
            return
        self.data = snapshot
        self.last_success = snapshot.fetched_at
        self.using_cached_data = True
        self._schedule_expiration(snapshot.source_updated_at + AIR_MAX_AGE)

    async def _async_update_data(self) -> AirQualitySnapshot:
        now = dt_util.now()
        self.last_attempt = now
        try:
            html = await self.api.async_fetch_html(self.air_url)
            snapshot = await self.hass.async_add_executor_job(partial(
                parse_air_quality_html, html, station=self.station,
                fetched_at=now, local_tz=now.tzinfo,
            ))
        except (WeatheriApiError, WeatheriParseError) as err:
            self.last_attempt_success, self.last_error = False, str(err)
            if self.data is not None and now - self.data.source_updated_at <= AIR_MAX_AGE:
                self.using_cached_data = True
                self._schedule_expiration(self.data.source_updated_at + AIR_MAX_AGE)
                _LOGGER.warning("Weatheri air update failed; retaining fresh observation: %s", err)
                return self.data
            self.data = None
            self.using_cached_data = False
            self.async_cancel_expiration()
            raise UpdateFailed(str(err)) from err
        self.last_success, self.last_attempt_success = now, True
        self.last_error, self.using_cached_data = None, False
        await self.store.async_save({"snapshot": snapshot.as_dict()})
        self._schedule_expiration(snapshot.source_updated_at + AIR_MAX_AGE)
        return snapshot
