import httpx
from fastapi import HTTPException, status

from samokat.infrastructure.api_connectors.base import BaseHTTPConnector
from samokat.infrastructure.api_connectors.schemas import (
    AddressSuggestionData,
    ResolvedAddressData,
)


class AddressConnector(BaseHTTPConnector):
    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        headers: dict[str, str] | None = None,
        token_refresh_path: str = "/auth/token/refresh",
    ) -> None:
        super().__init__(
            base_url=base_url,
            headers=headers,
        )
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_refresh_path = token_refresh_path
        self._access_token: str | None = None

    async def suggest_addresses(
        self,
        query: str,
    ) -> list[AddressSuggestionData]:
        response = await self._request_with_token_refresh(
            "GET",
            "/suggest",
            params={"query": query},
        )
        response.raise_for_status()
        data = response.json()

        return [
            AddressSuggestionData(
                id=item["id"],
                address_text=item["address_text"],
                lat=item["lat"],
                lon=item["lon"],
            )
            for item in data["suggestions"]
        ]

    async def get_address_full_info(
        self,
        address_id: str,
    ) -> ResolvedAddressData:
        response = await self._request_with_token_refresh(
            "GET",
            "/resolve",
            params={"address_id": address_id},
        )
        response.raise_for_status()
        data = response.json()

        return ResolvedAddressData(
            address_text=data["address_text"],
            lat=data["lat"],
            lon=data["lon"],
        )

    async def _request_with_token_refresh(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        response = await self._request(
            method,
            url,
            **self._with_auth_header(kwargs),
        )

        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=response.json()["detail"],
            )

        if response.status_code != 401:
            return response

        await self._refresh_token()
        return await self._request(
            method,
            url,
            **self._with_auth_header(kwargs),
        )

    async def _refresh_token(self) -> None:
        response = await self._request(
            "POST",
            self._token_refresh_path,
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        response.raise_for_status()
        data = response.json()
        self._access_token = data["access_token"]

    def _with_auth_header(self, kwargs: dict) -> dict:
        if self._access_token is None:
            return kwargs

        headers = {
            **kwargs.get("headers", {}),
            "Authorization": f"Bearer {self._access_token}",
        }

        return {
            **kwargs,
            "headers": headers,
        }
