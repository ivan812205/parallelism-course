from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.postgres.models import Event, EventSeat, Location, Seat


async def seed_event_data(session: AsyncSession) -> None:
    """Наполняет БД тестовыми данными (одна площадка, 50 мест, одно мероприятие).
    Идемпотентно: если данные уже есть — выходит."""
    async with session.begin():
        if await session.scalar(select(func.count(Location.id))):
            return

        location = Location(
            name="Центральный зал",
            city="Москва",
            address="Тверская улица, 1",
        )
        session.add(location)
        await session.flush()

        seats = [
            Seat(
                location_id=location.id,
                sector="Основной сектор",
                row=row,
                number=number,
                x=number * 50,
                y=row * 50,
            )
            for row in range(1, 6)
            for number in range(1, 11)
        ]
        session.add_all(seats)
        await session.flush()

        event = Event(
            organizer_id=1,
            location_id=location.id,
            title="Python Конференция",
            description="Тестовое мероприятие для домашнего задания",
            category="конференция",
            starts_at=datetime.now(timezone.utc) + timedelta(days=30),
            base_price=5000,
        )
        session.add(event)
        await session.flush()

        session.add_all(
            EventSeat(event_id=event.id, seat_id=seat.id, price=event.base_price)
            for seat in seats
        )
