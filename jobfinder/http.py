"""Shared HTTP client: one configuration and GET with retries."""

from types import TracebackType

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential
from tenacity.wait import wait_base

MAX_PARALLEL_REQUESTS = 20
MAX_ATTEMPTS = 3
USER_AGENT = "jobfinder (personal job search tool)"


def _is_retryable(error: BaseException) -> bool:
    """Retry network failures, rate limits and server errors, never other 4xx."""
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return status == 429 or status >= 500
    return isinstance(error, httpx.TransportError)


class HttpClient:
    """Use as `async with HttpClient() as http:` so connections are closed at the end."""

    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,  # tests pass a fake server
        retry_wait: wait_base | None = None,  # tests pass wait_none() to skip the waits
    ) -> None:
        self._client = httpx.AsyncClient(
            transport=transport,
            # pool=None: requests queue for a free connection instead of timing out
            timeout=httpx.Timeout(30, pool=None),
            limits=httpx.Limits(max_connections=MAX_PARALLEL_REQUESTS),
            headers={"User-Agent": USER_AGENT},
        )
        self._retry_policy = AsyncRetrying(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(MAX_ATTEMPTS),
            wait=retry_wait or wait_exponential(),  # 1s, then 2s
            reraise=True,
        )

    async def __aenter__(self) -> "HttpClient":
        return self

    async def __aexit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def _get_once(self, url: str) -> bytes:
        response = await self._client.get(url)
        response.raise_for_status()
        return response.content

    async def get(self, url: str) -> bytes:
        # copy() per call, as tenacity's own @retry does, so concurrent calls share no state
        return await self._retry_policy.copy()(self._get_once, url)
