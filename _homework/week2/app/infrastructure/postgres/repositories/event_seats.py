from datetime import datetime

from sqlalchemy import func, select, update

from app.application.dto import EventSeatData, LockedSeatData
from app.domain.enums import SeatStatus
from app.infrastructure.postgres.models import EventSeat, Seat
from app.infrastructure.postgres.repositories.base import BaseRepo


class EventSeatRepo(BaseRepo):
    async def lock(self, event_id: int, seat_ids: list[int]) -> list[LockedSeatData]:
        """SELECT ... FOR UPDATE по выбранным местам — блокирует строки до commit."""
        result = await self.session.execute(
            select(EventSeat.id, EventSeat.seat_id, EventSeat.status, EventSeat.price)
            .where(EventSeat.event_id == event_id, EventSeat.id.in_(seat_ids))
            .with_for_update()
        )
        return [
            LockedSeatData(id=row.id, seat_id=row.seat_id, status=row.status, price=row.price)
            for row in result.all()
        ]

    async def mark_reserved(
        self,
        seat_ids: list[int],
        booking_id: int,
        reserved_until: datetime,
    ) -> None:
        await self.session.execute(
            update(EventSeat)
            .where(EventSeat.id.in_(seat_ids))
            .values(
                status=SeatStatus.reserved,
                booking_id=booking_id,
                reserved_until=reserved_until,
            )
        )

    async def mark_sold(self, booking_id: int) -> None:
        await self.session.execute(
            update(EventSeat)
            .where(EventSeat.booking_id == booking_id)
            .values(status=SeatStatus.sold)
        )

    async def release(self, booking_ids: list[int]) -> None:
        """Возвращает места в продажу: снимает резерв просроченных броней."""
        await self.session.execute(
            update(EventSeat)
            .where(EventSeat.booking_id.in_(booking_ids))
            .values(status=SeatStatus.available, booking_id=None, reserved_until=None)
        )

    def create_for_event(self, event_id: int, seat_ids: list[int], price: int) -> None:
        self.session.add_all(
            EventSeat(event_id=event_id, seat_id=seat_id, price=price) for seat_id in seat_ids
        )

    async def list_by_event(self, event_id: int) -> list[EventSeatData]:
        result = await self.session.execute(
            select(EventSeat, Seat)
            .join(Seat, EventSeat.seat_id == Seat.id)
            .where(EventSeat.event_id == event_id)
            .order_by(EventSeat.id)
        )
        return [
            EventSeatData(
                id=event_seat.id,
                event_id=event_seat.event_id,
                seat_id=event_seat.seat_id,
                sector=seat.sector,
                row=seat.row,
                number=seat.number,
                x=seat.x,
                y=seat.y,
                price=event_seat.price,
                status=event_seat.status,
                reserved_until=event_seat.reserved_until,
                booking_id=event_seat.booking_id,
            )
            for event_seat, seat in result.all()
        ]

    async def count_status(self, event_id: int, status: SeatStatus) -> int:
        return await self.session.scalar(
            select(func.count(EventSeat.id)).where(
                EventSeat.event_id == event_id,
                EventSeat.status == status,
            )
        ) or 0

    async def count_by_status(self, event_id: int) -> dict[SeatStatus, int]:
        result = await self.session.execute(
            select(EventSeat.status, func.count(EventSeat.id))
            .where(EventSeat.event_id == event_id)
            .group_by(EventSeat.status)
        )
        return {seat_status: count for seat_status, count in result.all()}
