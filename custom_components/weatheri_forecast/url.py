"""Internal Weatheri URL construction and legacy URL parsing."""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from .catalog import ForecastLocation, get_location

ALLOWED_HOSTS = {"weatheri.co.kr", "www.weatheri.co.kr"}
FORECAST_PATH = "/forecast/forecast01.php"
AIR_PATH = "/special/special05_1.php"


class WeatheriUrlError(ValueError):
    """Raised when a legacy Weatheri URL is invalid or unsupported."""


@dataclass(frozen=True, slots=True)
class WeatheriUrl:
    """A constructed Weatheri endpoint."""

    canonical: str
    rid: str
    location: str
    entity_slug: str
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
        entity_slug=location.entity_slug,
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


def canonicalize_forecast_url(raw_url: str) -> WeatheriUrl:
    """Parse a version 1 URL and match it to the packaged catalog."""
    try:
        parsed = urlsplit(raw_url.strip())
    except ValueError as err:
        raise WeatheriUrlError("The URL could not be parsed") from err
    if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise WeatheriUrlError("The URL must use HTTPS and the Weatheri domain")
    if parsed.username or parsed.password or parsed.port or parsed.fragment:
        raise WeatheriUrlError("Credentials, custom ports, and fragments are not allowed")
    if parsed.path.rstrip("/") != FORECAST_PATH:
        raise WeatheriUrlError("The URL must point to forecast01.php")
    query = parse_qs(parsed.query, keep_blank_values=True)
    rid = _single_query_value(query, "rid")
    group = _single_query_value(query, "k")
    name = _single_query_value(query, "a_name").strip()
    if not re.fullmatch(r"\d{6,12}", rid):
        raise WeatheriUrlError("Invalid Weatheri rid")
    try:
        location = get_location(rid)
    except ValueError as err:
        raise WeatheriUrlError("The location is not in the supported catalog") from err
    if group != location.forecast_group or name != location.name:
        raise WeatheriUrlError("The legacy URL parameters do not match the location catalog")
    return build_forecast_url(location)


def _single_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key)
    if values is None or len(values) != 1:
        raise WeatheriUrlError(f"The URL must contain exactly one {key} parameter")
    return values[0]
