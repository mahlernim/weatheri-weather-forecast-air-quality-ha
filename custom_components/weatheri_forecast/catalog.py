"""Packaged Weatheri forecast-location catalog."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ForecastLocation:
    """A supported Weatheri forecast location."""

    rid: str
    name: str
    label: str
    forecast_group: str
    air_region_code: str

    @property
    def entity_slug(self) -> str:
        """Return a stable entity slug; retain the public Busan IDs."""
        return "busan" if self.rid == "1101010100" else f"location_{self.rid}"


def _load_catalog() -> dict[str, ForecastLocation]:
    path = Path(__file__).with_name("location_catalog.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    catalog = {
        rid: ForecastLocation(
            rid=rid,
            name=value["name"],
            label=value["label"],
            forecast_group=value["forecast_group"],
            air_region_code=value["air_region_code"],
        )
        for rid, value in raw.items()
    }
    if len(catalog) != len(set(catalog)):
        raise RuntimeError("Weatheri location catalog contains duplicate rid values")
    return catalog


LOCATIONS = _load_catalog()


def get_location(rid: str) -> ForecastLocation:
    """Return one supported location."""
    try:
        return LOCATIONS[rid]
    except KeyError as err:
        raise ValueError(f"Unsupported Weatheri forecast rid: {rid}") from err


def location_options() -> list[tuple[str, str]]:
    """Return selector values and labels in Korean collation-friendly order."""
    return [(item.rid, item.label) for item in sorted(LOCATIONS.values(), key=lambda x: x.label)]
