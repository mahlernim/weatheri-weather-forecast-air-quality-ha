import pytest

pytest.importorskip("aiohttp")

from weatheri_forecast.api import WeatheriApi, WeatheriApiError


class _Content:
    def __init__(self, chunks):
        self._chunks = chunks

    async def iter_chunked(self, size):
        for chunk in self._chunks:
            yield chunk


class _Response:
    def __init__(self, chunks, *, status=200, length=None):
        self.status = status
        self.content_length = length
        self.content = _Content(chunks)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _Session:
    def __init__(self, response):
        self.response = response

    def get(self, *args, **kwargs):
        return self.response


@pytest.mark.asyncio
async def test_reads_multiple_chunks_and_korean_utf8():
    encoded = "부산 덕천동".encode()
    api = WeatheriApi(_Session(_Response([encoded[:5], encoded[5:]])))
    assert await api.async_fetch_html("https://www.weatheri.co.kr/") == "부산 덕천동"


@pytest.mark.asyncio
async def test_rejects_http_error_declared_size_streamed_size_and_invalid_utf8():
    with pytest.raises(WeatheriApiError, match="HTTP 503"):
        await WeatheriApi(_Session(_Response([], status=503))).async_fetch_html("https://example")
    with pytest.raises(WeatheriApiError, match="too large"):
        await WeatheriApi(_Session(_Response([], length=1_000_001))).async_fetch_html("https://example")
    with pytest.raises(WeatheriApiError, match="too large"):
        await WeatheriApi(_Session(_Response([b"x" * 600_000, b"y" * 600_000]))).async_fetch_html("https://example")
    with pytest.raises(WeatheriApiError, match="UTF-8"):
        await WeatheriApi(_Session(_Response([b"\xff"]))).async_fetch_html("https://example")
