import asyncio

import httpx


class BaseHTTPConnector:
    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        rate_limit_requests: int | None = None,
        rate_limit_interval: int | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, headers=headers)
        self.rate_limit_requests = rate_limit_requests
        if rate_limit_requests:
            self._rate_limiter = asyncio.Semaphore(rate_limit_requests)
            self._rate_limit_interval = rate_limit_interval

    async def close_client(self):
        await self._client.aclose()

    async def release_rate_limiter_later(self):
        await asyncio.sleep(self._rate_limit_interval + 0.05)
        self._rate_limiter.release()

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        if self.rate_limit_requests:
            await self._rate_limiter.acquire()
            _ = asyncio.create_task(self.release_rate_limiter_later())

        return await self._client.request(method, url, **kwargs)
