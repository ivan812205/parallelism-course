from typing import Any

from app.application.dto import PaymentQuoteData
from app.infrastructure.api_connectors.base import BaseHTTPConnector


class PaymentConnector(BaseHTTPConnector):
    """Расчёт и оплата критичны → retry=True (мок отдаёт 429 периодически)."""

    async def calculate(self, booking_id: int, amount: int, currency: str) -> PaymentQuoteData:
        response = await self.request(
            "POST",
            "/payment/calculate",
            retry=True,
            json={"booking_id": booking_id, "amount": amount, "currency": currency},
        )
        response.raise_for_status()
        return PaymentQuoteData(**response.json())

    async def pay(
        self,
        booking_id: int,
        amount: int,
        currency: str,
        payment_method: str,
    ) -> dict[str, Any]:
        response = await self.request(
            "POST",
            "/payment/pay",
            retry=True,
            json={
                "booking_id": booking_id,
                "amount": amount,
                "currency": currency,
                "payment_method": payment_method,
            },
        )
        response.raise_for_status()
        return response.json()
