from datetime import datetime

from app.application.dto import EventData
from app.domain.exceptions import LocationNotFoundError
from app.infrastructure.postgres.manager import DatabaseManager


class OrganizerService:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def list_events(self, organizer_id: int) -> list[EventData]:
        return await self._db.events.list_by_organizer(organizer_id)

    async def create_event(
        self,
        organizer_id: int,
        *,
        location_id: int,
        title: str,
        description: str | None,
        category: str,
        starts_at: datetime,
        base_price: int,
    ) -> EventData:
        location = await self._db.locations.get(location_id)
        if location is None:
            raise LocationNotFoundError

        event = await self._db.events.create(
            organizer_id=organizer_id,
            location_id=location_id,
            title=title,
            description=description,
            category=category,
            starts_at=starts_at,
            base_price=base_price,
        )
        # заводим места мероприятия по местам площадки — иначе событие нечего бронировать
        seat_ids = await self._db.locations.list_seat_ids(location_id)
        self._db.event_seats.create_for_event(event.id, seat_ids, base_price)
        await self._db.commit()
        return event
