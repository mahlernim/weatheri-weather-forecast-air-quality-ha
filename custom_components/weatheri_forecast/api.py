"""Bounded HTTP client for Weatheri pages."""

from __future__ import annotations

import asyncio
import aiohttp

from .const import HTTP_TIMEOUT_SECONDS, MAX_RESPONSE_BYTES

_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
    "User-Agent": (
        "Weatheri-Weather-Air-Home-Assistant/0.2.2 "
        "(+https://github.com/mahlernim/weatheri-weather-forecast-air-quality-ha)"
    ),
}


class WeatheriApiError(Exception):
    """Raised when Weatheri cannot be fetched safely."""


class WeatheriApi:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_fetch_html(self, url: str) -> str:
        """Fetch at most one megabyte and decode it strictly as UTF-8."""
        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
        try:
            async with asyncio.timeout(HTTP_TIMEOUT_SECONDS + 1):
                async with self._session.get(url, timeout=timeout, headers=_REQUEST_HEADERS) as response:
                    if response.status != 200:
                        raise WeatheriApiError(f"Weatheri returned HTTP {response.status}")
                    if response.content_length is not None and response.content_length > MAX_RESPONSE_BYTES:
                        raise WeatheriApiError("Weatheri response is too large")
                    chunks: list[bytes] = []
                    received = 0
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        received += len(chunk)
                        if received > MAX_RESPONSE_BYTES:
                            raise WeatheriApiError("Weatheri response is too large")
                        chunks.append(chunk)
                    payload = b"".join(chunks)
        except WeatheriApiError:
            raise
        except (TimeoutError, aiohttp.ClientError) as err:
            raise WeatheriApiError(f"Unable to fetch Weatheri: {err}") from err
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as err:
            raise WeatheriApiError("Weatheri response is not valid UTF-8") from err
