import asyncio
import random

import httpx

_RETRY_STATUSES = frozenset({429, 503, 504})


class BaseHTTPConnector:
    """Общий HTTP-клиент к внешнему API: пул соединений (один AsyncClient),
    опциональный rate limiter на семафоре (урок 7) и повтор при 429/503 и
    сетевых ошибках с экспоненциальным backoff + jitter (урок 8)."""

    def __init__(
        self,
        base_url: str,
        timeout: float,
        headers: dict[str, str] | None = None,
        rate_limit_requests: int | None = None,
        rate_limit_interval: float = 1.0,
        retry_count: int = 1,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=timeout)
        self._rate_limit_requests = rate_limit_requests
        self._rate_limit_interval = rate_limit_interval
        if rate_limit_requests:
            self._rate_limiter = asyncio.Semaphore(rate_limit_requests)
        self._retry_count = retry_count

    async def close_client(self) -> None:
        await self._client.aclose()

    async def _release_permit_later(self) -> None:
        await asyncio.sleep(self._rate_limit_interval)
        self._rate_limiter.release()

    async def _backoff(self, attempt: int) -> None:
        delay = 0.1 * 2**attempt + random.uniform(0, 0.1)
        await asyncio.sleep(delay)

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        # урок 8: уважаем Retry-After (секунды); HTTP-дату не парсим — падаем на backoff
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    async def request(
        self,
        method: str,
        url: str,
        *,
        retry: bool = False,
        **kwargs: object,
    ) -> httpx.Response:
        attempts = self._retry_count if retry else 1

        for attempt in range(attempts):
            if self._rate_limit_requests:
                await self._rate_limiter.acquire()
                asyncio.create_task(self._release_permit_later())

            try:
                response = await self._client.request(method, url, **kwargs)
            except (httpx.NetworkError, httpx.TimeoutException):
                if attempt == attempts - 1:
                    raise
                await self._backoff(attempt)
                continue

            if response.status_code not in _RETRY_STATUSES or attempt == attempts - 1:
                return response

            retry_after = self._parse_retry_after(response)
            if retry_after is not None:
                await asyncio.sleep(retry_after)
            else:
                await self._backoff(attempt)

        raise RuntimeError("unreachable")  # цикл всегда возвращает/бросает на последней попытке
