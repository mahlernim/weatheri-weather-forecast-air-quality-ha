"""HTML parsers for Weatheri forecast and air-quality pages."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, tzinfo

from bs4 import BeautifulSoup, Tag

from .const import AIR_FUTURE_TOLERANCE, AIR_MEASUREMENTS
from .models import AirQualitySnapshot, ForecastSnapshot, WeatheriDayForecast

_DATE_PATTERN = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_TEMP_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?)\s*[˚°]\s*C", re.IGNORECASE)
_SHOWTHREE_PATTERN = re.compile(r'^showthree\(["\'](\d+)["\']\)$')
_SOURCE_TIME_PATTERN = re.compile(
    r"한국환경공단\s*,\s*(\d{2})\.(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})"
)
_AIR_HEADERS = {
    "pm10": ("PM10", "미세먼지"),
    "pm25": ("PM2.5", "초미세먼지"),
    "ozone": ("오존",),
    "nitrogen_dioxide": ("이산화질소",),
    "carbon_monoxide": ("일산화탄소",),
    "sulfur_dioxide": ("아황산가스",),
    "aqi": ("대기통합지수", "통합대기지수"),
}
_AIR_LIMITS = {
    "pm10": (0, 2000), "pm25": (0, 2000), "ozone": (0, 5),
    "nitrogen_dioxide": (0, 5), "carbon_monoxide": (0, 100),
    "sulfur_dioxide": (0, 5), "aqi": (0, 1000),
}


class WeatheriParseError(ValueError):
    """Raised when a Weatheri page is incomplete or unexpected."""


def parse_forecast_html(
    html: str, *, location: str, current_date: date, fetched_at: datetime
) -> ForecastSnapshot:
    soup = BeautifulSoup(html, "html.parser")
    cells = _indexed_summary_cells(soup)
    today_cell, tomorrow_cell = cells.get(1), cells.get(2)
    if today_cell is None or tomorrow_cell is None:
        raise WeatheriParseError("Today or tomorrow summary cell is missing")
    summary_table = today_cell.find_parent("table")
    if summary_table is None or tomorrow_cell not in summary_table.descendants:
        raise WeatheriParseError("Today and tomorrow are not in one summary table")
    parsed_dates = _summary_dates(summary_table, current_date)
    expected_tomorrow = current_date + timedelta(days=1)
    if len(parsed_dates) < 2 or parsed_dates[0] != current_date or parsed_dates[1] != expected_tomorrow:
        raise WeatheriParseError("Forecast dates do not match today and tomorrow")
    today_high, today_low = _summary_temperatures(today_cell)
    tomorrow_high, tomorrow_low = _summary_temperatures(tomorrow_cell)
    return ForecastSnapshot(
        location, current_date, fetched_at,
        WeatheriDayForecast(current_date, today_high, today_low),
        WeatheriDayForecast(expected_tomorrow, tomorrow_high, tomorrow_low),
    )


def discover_air_stations(html: str) -> list[str]:
    """Return station labels from the Weatheri observation table."""
    soup = BeautifulSoup(html, "html.parser")
    table, header_row, _ = _find_air_table(soup)
    stations: list[str] = []
    rows = table.find_all("tr")
    start = rows.index(header_row)
    for row in rows[start + 1:]:
        cells = _row_cells(row)
        if len(cells) >= 2 and cells[0] and cells[0] not in stations:
            stations.append(cells[0])
    if not stations:
        raise WeatheriParseError("No air-quality stations were found")
    return stations


def parse_air_quality_html(
    html: str, *, station: str, fetched_at: datetime, local_tz: tzinfo
) -> AirQualitySnapshot:
    """Parse one monitoring-station observation using semantic headers."""
    soup = BeautifulSoup(html, "html.parser")
    source_updated_at = _source_timestamp(soup, local_tz)
    if source_updated_at - fetched_at > AIR_FUTURE_TOLERANCE:
        raise WeatheriParseError("Air-quality source timestamp is in the future")
    table, header_row, columns = _find_air_table(soup)
    target: list[str] | None = None
    rows = table.find_all("tr")
    start = rows.index(header_row)
    for row in rows[start + 1:]:
        cells = _row_cells(row)
        if cells and cells[0] == station:
            target = cells
            break
    if target is None:
        raise WeatheriParseError(f"Air-quality station was not found: {station}")
    measurements: dict[str, float | None] = {}
    for key in AIR_MEASUREMENTS:
        index = columns[key]
        raw = target[index] if index < len(target) else "-"
        measurements[key] = _parse_air_value(key, raw)
    return AirQualitySnapshot(station, source_updated_at, fetched_at, measurements)


def _find_air_table(soup: BeautifulSoup) -> tuple[Tag, Tag, dict[str, int]]:
    for row in soup.find_all("tr"):
        cells = _row_cells(row)
        if len(cells) < 8 or not any("PM10" in cell for cell in cells) or not any("PM2.5" in cell for cell in cells):
            continue
        columns: dict[str, int] = {}
        for key, aliases in _AIR_HEADERS.items():
            for alias in aliases:
                matches = [i for i, cell in enumerate(cells) if alias in cell]
                if matches:
                    columns[key] = matches[0]
                    break
        if set(columns) == set(AIR_MEASUREMENTS) and len(set(columns.values())) == len(AIR_MEASUREMENTS):
            table = row.find_parent("table")
            if table is not None:
                return table, row, columns
    raise WeatheriParseError("Air-quality observation table is missing")


def _source_timestamp(soup: BeautifulSoup, local_tz: tzinfo) -> datetime:
    match = _SOURCE_TIME_PATTERN.search(soup.get_text(" ", strip=True))
    if not match:
        raise WeatheriParseError("Air-quality source timestamp is missing")
    year, month, day, hour, minute = (int(part) for part in match.groups())
    try:
        return datetime(2000 + year, month, day, hour, minute, tzinfo=local_tz)
    except ValueError as err:
        raise WeatheriParseError("Air-quality source timestamp is invalid") from err


def _parse_air_value(key: str, raw: str) -> float | None:
    value = raw.strip()
    if value in {"", "-"}:
        return None
    try:
        parsed = float(value.replace(",", ""))
    except ValueError as err:
        raise WeatheriParseError(f"Invalid {key} value: {value}") from err
    lower, upper = _AIR_LIMITS[key]
    if not lower <= parsed <= upper:
        raise WeatheriParseError(f"{key} value is outside the valid range: {parsed}")
    return parsed


def _row_cells(row: Tag) -> list[str]:
    values = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"], recursive=False)]
    return [value for value in values if value]


def _indexed_summary_cells(soup: BeautifulSoup) -> dict[int, Tag]:
    cells: dict[int, Tag] = {}
    for cell in soup.find_all("td", onclick=True):
        match = _SHOWTHREE_PATTERN.fullmatch(str(cell.get("onclick", "")).strip())
        if match:
            cells[int(match.group(1))] = cell
    return cells


def _summary_dates(summary_table: Tag, current_date: date) -> list[date]:
    dates: list[date] = []
    for month_text, day_text in _DATE_PATTERN.findall(summary_table.get_text(" ", strip=True)):
        parsed = _infer_date(int(month_text), int(day_text), current_date)
        if not dates or dates[-1] != parsed:
            dates.append(parsed)
    return dates


def _infer_date(month: int, day: int, reference: date) -> date:
    candidates: list[date] = []
    for year in (reference.year - 1, reference.year, reference.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError as err:
            raise WeatheriParseError(f"Invalid forecast date {month}/{day}") from err
    return min(candidates, key=lambda candidate: abs((candidate - reference).days))


def _summary_temperatures(cell: Tag) -> tuple[float, float]:
    values = [float(value) for value in _TEMP_PATTERN.findall(cell.get_text(" ", strip=True))]
    if len(values) < 2:
        raise WeatheriParseError("High or low temperature is missing")
    high, low = values[0], values[1]
    if any(value < -50 or value > 60 for value in (high, low)):
        raise WeatheriParseError("Temperature is outside the valid range")
    if high < low:
        raise WeatheriParseError("High temperature is lower than low temperature")
    return high, low
