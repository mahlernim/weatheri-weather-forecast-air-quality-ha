from datetime import UTC, date, datetime

from weatheri_forecast.models import (
    ForecastSnapshot,
    WeatheriDayForecast,
    snapshot_is_current,
)


def _snapshot(source_date: date) -> ForecastSnapshot:
    return ForecastSnapshot(
        location="부산",
        source_date=source_date,
        fetched_at=datetime(2026, 7, 19, 6, 0, tzinfo=UTC),
        today=WeatheriDayForecast(source_date, 31, 26),
        tomorrow=WeatheriDayForecast(date(2026, 7, 20), 32, 27),
    )


def test_same_day_snapshot_remains_current():
    assert snapshot_is_current(_snapshot(date(2026, 7, 19)), date(2026, 7, 19))


def test_snapshot_expires_at_date_boundary():
    assert not snapshot_is_current(_snapshot(date(2026, 7, 19)), date(2026, 7, 20))


def test_missing_snapshot_is_not_current():
    assert not snapshot_is_current(None, date(2026, 7, 19))
