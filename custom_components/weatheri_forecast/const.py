"""Constants for Weatheri Weather & Air."""

from datetime import timedelta

DOMAIN = "weatheri_forecast"
NAME = "Weatheri Weather & Air"
PLATFORMS = ["sensor", "binary_sensor"]

CONF_FORECAST_RID = "forecast_rid"
CONF_FORECAST_GROUP = "forecast_group"
CONF_FORECAST_NAME = "forecast_name"
CONF_AIR_REGION_CODE = "air_region_code"
CONF_AIR_STATION = "air_station"
CONF_FORECAST_URL = "forecast_url"  # Version 1 migration only.

ENTRY_VERSION = 2
NO_AIR_STATION = "__forecast_only__"
DEFAULT_UPDATE_INTERVAL = timedelta(hours=1)
AIR_MAX_AGE = timedelta(hours=3)
AIR_FUTURE_TOLERANCE = timedelta(minutes=5)
HTTP_TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 1_000_000
STORE_VERSION = 2

AIR_MEASUREMENTS = (
    "pm10",
    "pm25",
    "ozone",
    "nitrogen_dioxide",
    "carbon_monoxide",
    "sulfur_dioxide",
    "aqi",
)
