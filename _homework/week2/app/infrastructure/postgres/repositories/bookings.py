from datetime import datetime

from sqlalchemy import delete, func, select, update

from app.application.dto import BookingData
from app.domain.enums import BookingStatus
from app.infrastructure.postgres.models import Booking
from app.infrastructure.postgres.repositories.base import BaseRepo


class BookingRepo(BaseRepo):
    async def create(
        self,
        *,
        event_id: int,
        user_id: int,
        amount: int,
        reserved_until: datetime,
    ) -> int:
        booking = Booking(
            event_id=event_id,
            user_id=user_id,
            amount=amount,
            payment_commission=0,
            protection_price=None,
            with_protection=False,
            status=BookingStatus.pending_payment,
            reserved_until=reserved_until,
        )
        self.session.add(booking)
        await self.session.flush()
        return booking.id

    async def get(self, booking_id: int) -> BookingData | None:
        booking = await self.session.get(Booking, booking_id)
        return BookingData.model_validate(booking) if booking else None

    async def set_quote(
        self,
        booking_id: int,
        payment_commission: int,
        protection_price: int | None,
    ) -> None:
        await self.session.execute(
            update(Booking)
            .where(Booking.id == booking_id)
            .values(payment_commission=payment_commission, protection_price=protection_price)
        )

    async def mark_paid(self, booking_id: int, with_protection: bool) -> None:
        await self.session.execute(
            update(Booking)
            .where(Booking.id == booking_id)
            .values(status=BookingStatus.paid, with_protection=with_protection)
        )

    async def set_protection_price(self, booking_id: int, protection_price: int) -> bool:
        """Пишет цену страховки только той брони, которая всё ещё ждёт оплаты."""
        result = await self.session.execute(
            update(Booking)
            .where(
                Booking.id == booking_id,
                Booking.status == BookingStatus.pending_payment,
            )
            .values(protection_price=protection_price)
        )
        return result.rowcount == 1

    async def list_expired(self, now: datetime) -> list[int]:
        """Неоплаченные брони, у которых истёк срок резерва."""
        result = await self.session.scalars(
            select(Booking.id).where(
                Booking.status == BookingStatus.pending_payment,
                Booking.reserved_until < now,
            )
        )
        return list(result.all())

    async def delete(self, booking_ids: list[int]) -> None:
        await self.session.execute(delete(Booking).where(Booking.id.in_(booking_ids)))

    async def paid_aggregate(self, event_id: int) -> tuple[int, int]:
        """(кол-во оплаченных броней, выручка) по мероприятию."""
        paid_orders, revenue = (
            await self.session.execute(
                select(
                    func.count(Booking.id),
                    func.coalesce(func.sum(Booking.amount), 0),
                ).where(
                    Booking.event_id == event_id,
                    Booking.status == BookingStatus.paid,
                )
            )
        ).one()
        return paid_orders, revenue
