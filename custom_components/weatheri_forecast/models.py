"""Validated Weatheri data models and freshness policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from .const import AIR_MAX_AGE, AIR_MEASUREMENTS


@dataclass(frozen=True, slots=True)
class WeatheriDayForecast:
    date: date
    high: float
    low: float

    def as_dict(self) -> dict[str, Any]:
        return {"date": self.date.isoformat(), "high": self.high, "low": self.low}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> WeatheriDayForecast:
        return cls(date.fromisoformat(value["date"]), float(value["high"]), float(value["low"]))


@dataclass(frozen=True, slots=True)
class ForecastSnapshot:
    location: str
    source_date: date
    fetched_at: datetime
    today: WeatheriDayForecast
    tomorrow: WeatheriDayForecast

    def as_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "source_date": self.source_date.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
            "today": self.today.as_dict(),
            "tomorrow": self.tomorrow.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ForecastSnapshot:
        return cls(
            location=str(value["location"]),
            source_date=date.fromisoformat(value["source_date"]),
            fetched_at=datetime.fromisoformat(value["fetched_at"]),
            today=WeatheriDayForecast.from_dict(value["today"]),
            tomorrow=WeatheriDayForecast.from_dict(value["tomorrow"]),
        )


@dataclass(frozen=True, slots=True)
class AirQualitySnapshot:
    station: str
    source_updated_at: datetime
    fetched_at: datetime
    measurements: dict[str, float | None]

    def as_dict(self) -> dict[str, Any]:
        return {
            "station": self.station,
            "source_updated_at": self.source_updated_at.isoformat(),
            "fetched_at": self.fetched_at.isoformat(),
            "measurements": self.measurements,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AirQualitySnapshot:
        raw = value["measurements"]
        return cls(
            station=str(value["station"]),
            source_updated_at=datetime.fromisoformat(value["source_updated_at"]),
            fetched_at=datetime.fromisoformat(value["fetched_at"]),
            measurements={key: None if raw.get(key) is None else float(raw[key]) for key in AIR_MEASUREMENTS},
        )

    @property
    def missing_measurements(self) -> list[str]:
        return [key for key in AIR_MEASUREMENTS if self.measurements.get(key) is None]


def snapshot_is_current(snapshot: ForecastSnapshot | None, current_date: date) -> bool:
    """Return whether a forecast snapshot belongs to the current local date."""
    return snapshot is not None and snapshot.source_date == current_date


def air_data_age_minutes(snapshot: AirQualitySnapshot | None, now: datetime) -> float | None:
    """Return source observation age in minutes."""
    if snapshot is None:
        return None
    return max(0.0, (now - snapshot.source_updated_at).total_seconds() / 60)


def air_snapshot_is_current(snapshot: AirQualitySnapshot | None, now: datetime) -> bool:
    """Return whether air data is fresh and contains both default PM values."""
    return (
        air_snapshot_is_fresh(snapshot, now)
        and snapshot is not None
        and snapshot.measurements.get("pm10") is not None
        and snapshot.measurements.get("pm25") is not None
    )


def air_snapshot_is_fresh(snapshot: AirQualitySnapshot | None, now: datetime) -> bool:
    """Return whether an observation is inside the source-time freshness window."""
    if snapshot is None:
        return False
    age = now - snapshot.source_updated_at
    return age.total_seconds() >= 0 and age <= AIR_MAX_AGE


# Compatibility for consumers and fixtures written against v0.1.
WeatheriSnapshot = ForecastSnapshot
