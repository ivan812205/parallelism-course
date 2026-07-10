import asyncio
import random

import httpx


class BaseHTTPConnector:
    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        rate_limit_requests: int | None = None,
        rate_limit_interval: int | None = None,
        retry_count: int = 2,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, headers=headers)
        self.rate_limit_requests = rate_limit_requests
        if rate_limit_requests:
            self._rate_limiter = asyncio.Semaphore(rate_limit_requests)
            self._rate_limit_interval = rate_limit_interval
        self.retry_count = retry_count

    async def close_client(self):
        await self._client.aclose()

    async def release_rate_limiter_later(self):
        await asyncio.sleep(self._rate_limit_interval + 0.05)
        self._rate_limiter.release()

    async def _exponential_backoff_sleep(self, attempt: int):
        delay = 0.5 * 2 ** (attempt + 1)
        jitter = random.uniform(0.1, 0.5)

        await asyncio.sleep(delay + jitter)

    async def _request(
        self,
        method: str,
        url: str,
        retry: bool = False,
        **kwargs,
    ) -> httpx.Response:
        attempts = self.retry_count if retry else 1

        for attempt in range(attempts):
            if self.rate_limit_requests:
                await self._rate_limiter.acquire()
                _ = asyncio.create_task(self.release_rate_limiter_later())

            try:
                response = await self._client.request(method, url, **kwargs)
            except (httpx.NetworkError, httpx.TimeoutException):
                if attempt == attempts - 1:
                    raise

                await self._exponential_backoff_sleep(attempt)
                continue

            if (
                response.status_code not in (429, 503) or
                attempt == attempts - 1
            ):
                return response

            await self._exponential_backoff_sleep(attempt)
