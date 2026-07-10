import httpx


class BaseHTTPConnector:
    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, headers=headers)

    async def close_client(self):
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        return await self._client.request(method, url, **kwargs)
