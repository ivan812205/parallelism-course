from datetime import datetime

from sqlalchemy import select

from app.application.dto import EventData
from app.infrastructure.postgres.models import Event
from app.infrastructure.postgres.repositories.base import BaseRepo


class EventRepo(BaseRepo):
    async def get(self, event_id: int) -> EventData | None:
        event = await self.session.get(Event, event_id)
        return EventData.model_validate(event) if event else None

    async def list_all(self) -> list[EventData]:
        result = await self.session.scalars(select(Event).order_by(Event.id))
        return [EventData.model_validate(event) for event in result.all()]

    async def list_by_organizer(self, organizer_id: int) -> list[EventData]:
        result = await self.session.scalars(
            select(Event).where(Event.organizer_id == organizer_id).order_by(Event.id)
        )
        return [EventData.model_validate(event) for event in result.all()]

    async def create(
        self,
        *,
        organizer_id: int,
        location_id: int,
        title: str,
        description: str | None,
        category: str,
        starts_at: datetime,
        base_price: int,
    ) -> EventData:
        event = Event(
            organizer_id=organizer_id,
            location_id=location_id,
            title=title,
            description=description,
            category=category,
            starts_at=starts_at,
            base_price=base_price,
        )
        self.session.add(event)
        await self.session.flush()
        return EventData.model_validate(event)
