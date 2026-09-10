import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from app.application.dto import (
    CheckoutBookingData,
    CheckoutResultData,
    CheckoutSeatData,
)
from app.application.ports import ProtectionRecalculationScheduler
from app.config import BookingConfig
from app.domain.enums import SeatStatus
from app.domain.exceptions import (
    EventNotFoundError,
    PaymentUnavailableError,
    SeatsNotFoundError,
    SeatsUnavailableError,
)
from app.infrastructure.api_connectors.payment import PaymentConnector
from app.infrastructure.api_connectors.protection import ProtectionConnector
from app.infrastructure.postgres.manager import DatabaseManager

CURRENCY = "RUB"


class CheckoutService:
    def __init__(
        self,
        db: DatabaseManager,
        payment: PaymentConnector,
        protection: ProtectionConnector,
        protection_scheduler: ProtectionRecalculationScheduler,
        config: BookingConfig,
    ) -> None:
        self._db = db
        self._payment = payment
        self._protection = protection
        self._protection_scheduler = protection_scheduler
        self._ttl_minutes = config.ttl_minutes

    async def checkout(
        self,
        *,
        event_id: int,
        user_id: int,
        seat_ids: list[int],
    ) -> CheckoutResultData:
        reserved_until = datetime.now(timezone.utc) + timedelta(minutes=self._ttl_minutes)

        event = await self._db.events.get(event_id)
        if event is None:
            raise EventNotFoundError

        # Короткая транзакция: лочим места (FOR UPDATE), бронируем, коммитим —
        # чтобы не держать row-lock во время медленных внешних вызовов.
        locked = await self._db.event_seats.lock(event_id, seat_ids)
        if len(locked) != len(set(seat_ids)):
            raise SeatsNotFoundError
        if any(seat.status is not SeatStatus.available for seat in locked):
            raise SeatsUnavailableError

        base_amount = sum(seat.price for seat in locked)
        booking_id = await self._db.bookings.create(
            event_id=event_id,
            user_id=user_id,
            amount=base_amount,
            reserved_until=reserved_until,
        )
        await self._db.event_seats.mark_reserved(seat_ids, booking_id, reserved_until)
        await self._db.commit()

        # Конкурентно: платёж (критичен, с retry) и страховка (best-effort, timeout+None).
        try:
            async with asyncio.TaskGroup() as tg:
                payment_task = tg.create_task(
                    self._payment.calculate(booking_id, base_amount, CURRENCY)
                )
                protection_task = tg.create_task(
                    self._protection.calculate(
                        booking_id, base_amount, event.category, event.starts_at
                    )
                )
        except* httpx.HTTPError as eg:
            raise PaymentUnavailableError from eg

        payment = payment_task.result()
        protection = protection_task.result()

        await self._db.bookings.set_quote(
            booking_id,
            payment.commission,
            protection.price if protection else None,
        )
        await self._db.commit()

        if protection is None:
            # API страховки не ответил в отведённый таймаут: отдаём результат без неё,
            # а расчёт дожимает фоновая задача
            await self._protection_scheduler.schedule(booking_id)

        return CheckoutResultData(
            booking=CheckoutBookingData(
                id=booking_id,
                event_title=event.title,
                starts_at=event.starts_at,
                seats=[
                    CheckoutSeatData(id=seat.id, seat_id=seat.seat_id, price=seat.price)
                    for seat in locked
                ],
                base_amount=base_amount,
                payment_commission=payment.commission,
                protection_price=protection.price if protection else None,
                with_protection=False,
                reserved_until=reserved_until,
            ),
            payment=payment,
            protection=protection,
        )
