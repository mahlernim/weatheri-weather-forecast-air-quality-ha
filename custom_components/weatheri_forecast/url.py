"""Internal Weatheri endpoint construction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlencode, urlunsplit

from .catalog import ForecastLocation

FORECAST_PATH = "/forecast/forecast01.php"
AIR_PATH = "/special/special05_1.php"


class WeatheriUrlError(ValueError):
    """Raised when a Weatheri endpoint parameter is invalid."""


@dataclass(frozen=True, slots=True)
class WeatheriUrl:
    """A constructed Weatheri endpoint."""

    canonical: str
    rid: str
    location: str
    forecast_group: str
    air_region_code: str


def build_forecast_url(location: ForecastLocation) -> WeatheriUrl:
    """Construct a forecast URL from the packaged catalog."""
    query = urlencode(
        {"rid": location.rid, "k": location.forecast_group, "a_name": location.name},
        encoding="utf-8",
    )
    return WeatheriUrl(
        canonical=urlunsplit(("https", "www.weatheri.co.kr", FORECAST_PATH, query, "")),
        rid=location.rid,
        location=location.name,
        forecast_group=location.forecast_group,
        air_region_code=location.air_region_code,
    )


def build_air_url(region_code: str) -> str:
    """Construct an air-quality region URL."""
    if not re.fullmatch(r"\d{1,3}", region_code):
        raise WeatheriUrlError("Invalid Weatheri air-region code")
    return urlunsplit(
        ("https", "www.weatheri.co.kr", AIR_PATH, urlencode({"a": region_code}), "")
    )
