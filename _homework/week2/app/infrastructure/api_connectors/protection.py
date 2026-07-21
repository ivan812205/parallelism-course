from datetime import datetime

import httpx

from app.application.dto import ProtectionQuoteData
from app.infrastructure.api_connectors.base import BaseHTTPConnector


class ProtectionConnector(BaseHTTPConnector):
    """Страховка некритична: жёсткий таймаут (client timeout), без ретраев.
    При таймауте/5xx/сетевой ошибке возвращаем None — оформление идёт без неё."""

    async def calculate(
        self,
        booking_id: int,
        ticket_amount: int,
        event_category: str,
        event_starts_at: datetime,
    ) -> ProtectionQuoteData | None:
        try:
            response = await self.request(
                "POST",
                "/protection/calculate",
                retry=False,
                json={
                    "booking_id": booking_id,
                    "ticket_amount": ticket_amount,
                    "event_category": event_category,
                    "event_starts_at": event_starts_at.isoformat(),
                },
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        return ProtectionQuoteData(**response.json())
