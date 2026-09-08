from sqlalchemy import select

from app.application.dto import LocationData, SeatData
from app.infrastructure.postgres.models import Location, Seat
from app.infrastructure.postgres.repositories.base import BaseRepo


class LocationRepo(BaseRepo):
    async def list_all(self) -> list[LocationData]:
        result = await self.session.scalars(select(Location).order_by(Location.id))
        return [LocationData.model_validate(loc) for loc in result.all()]

    async def get(self, location_id: int) -> LocationData | None:
        location = await self.session.get(Location, location_id)
        return LocationData.model_validate(location) if location else None

    async def list_seats(self, location_id: int) -> list[SeatData]:
        result = await self.session.scalars(
            select(Seat).where(Seat.location_id == location_id).order_by(Seat.id)
        )
        return [self._seat_data(seat) for seat in result.all()]

    async def list_seat_ids(self, location_id: int) -> list[int]:
        result = await self.session.scalars(
            select(Seat.id).where(Seat.location_id == location_id)
        )
        return list(result.all())

    @staticmethod
    def _seat_data(seat: Seat) -> SeatData:
        return SeatData(
            id=seat.id,
            location_id=seat.location_id,
            sector=seat.sector,
            row=seat.row,
            number=seat.number,
            x=seat.x,
            y=seat.y,
        )
