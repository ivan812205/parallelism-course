import httpx


class BaseHTTPConnector:
    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url
        self.headers = headers

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        return await httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
        ).request(method, url, **kwargs)
