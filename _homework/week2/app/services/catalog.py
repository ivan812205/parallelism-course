from app.application.dto import (
    EventData,
    EventSeatData,
    LocationData,
    LocationDetailData,
    SeatData,
)
from app.domain.exceptions import EventNotFoundError, LocationNotFoundError
from app.infrastructure.postgres.manager import DatabaseManager


class CatalogService:
    """Чтение справочных данных (площадки, мероприятия, места). В ДЗ не участвует,
    но эндпоинты обязаны присутствовать и работать."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def list_locations(self) -> list[LocationData]:
        return await self._db.locations.list_all()

    async def get_location(self, location_id: int) -> LocationDetailData:
        location = await self._db.locations.get(location_id)
        if location is None:
            raise LocationNotFoundError
        seats = await self._db.locations.list_seats(location_id)
        return LocationDetailData(location=location, seats=seats)

    async def list_location_seats(self, location_id: int) -> list[SeatData]:
        location = await self._db.locations.get(location_id)
        if location is None:
            raise LocationNotFoundError
        return await self._db.locations.list_seats(location_id)

    async def list_events(self) -> list[EventData]:
        return await self._db.events.list_all()

    async def get_event(self, event_id: int) -> EventData:
        event = await self._db.events.get(event_id)
        if event is None:
            raise EventNotFoundError
        return event

    async def list_event_seats(self, event_id: int) -> list[EventSeatData]:
        event = await self._db.events.get(event_id)
        if event is None:
            raise EventNotFoundError
        return await self._db.event_seats.list_by_event(event_id)
