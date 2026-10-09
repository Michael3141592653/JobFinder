"""Shared HTTP setup: one client configuration and a GET with retries."""

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

MAX_PARALLEL_REQUESTS = 20
USER_AGENT = "jobfinder (personal job search tool)"


def _is_retryable(error: BaseException) -> bool:
    """Retry network failures, rate limits and server errors, never other 4xx."""
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return status == 429 or status >= 500
    return isinstance(error, httpx.TransportError)


def new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        # pool=None: requests queue for a free connection instead of timing out
        timeout=httpx.Timeout(30, pool=None),
        limits=httpx.Limits(max_connections=MAX_PARALLEL_REQUESTS),
        headers={"User-Agent": USER_AGENT},
    )


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential(),  # 1s, then 2s
    reraise=True,
)
async def get(client: httpx.AsyncClient, url: str, params: dict | None = None) -> bytes:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.content
