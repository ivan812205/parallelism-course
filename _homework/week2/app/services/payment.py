from datetime import datetime, timezone

import httpx

from app.application.dto import PaymentResultData
from app.domain.enums import BookingStatus
from app.domain.exceptions import (
    BookingNotFoundError,
    BookingNotPayableError,
    PaymentUnavailableError,
)
from app.infrastructure.api_connectors.payment import PaymentConnector
from app.infrastructure.postgres.manager import DatabaseManager

CURRENCY = "RUB"


class PaymentService:
    def __init__(self, db: DatabaseManager, payment: PaymentConnector) -> None:
        self._db = db
        self._payment = payment

    async def pay(
        self,
        booking_id: int,
        user_id: int,
        *,
        payment_method: str,
        with_protection: bool,
    ) -> PaymentResultData:
        booking = await self._db.bookings.get(booking_id)
        if booking is None or booking.user_id != user_id:
            raise BookingNotFoundError
        if booking.status is not BookingStatus.pending_payment:
            raise BookingNotPayableError

        reserved_until = booking.reserved_until
        if reserved_until.tzinfo is None:
            reserved_until = reserved_until.replace(tzinfo=timezone.utc)
        if reserved_until < datetime.now(timezone.utc):
            raise BookingNotPayableError

        charged = booking.amount + booking.payment_commission
        if with_protection and booking.protection_price:
            charged += booking.protection_price

        try:
            result = await self._payment.pay(
                booking.id, charged, CURRENCY, payment_method
            )
        except httpx.HTTPError as exc:
            raise PaymentUnavailableError from exc

        await self._db.bookings.mark_paid(booking.id, with_protection)
        await self._db.event_seats.mark_sold(booking.id)
        await self._db.commit()

        return PaymentResultData(
            booking_id=booking.id,
            status=BookingStatus.paid,
            charged_amount=charged,
            transaction_id=result["transaction_id"],
        )
