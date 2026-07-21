from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.application.dto import EventData, EventSeatData
from app.services.catalog import CatalogService

router = APIRouter(prefix="/events", route_class=DishkaRoute, tags=["Мероприятия"])


@router.get("")
async def list_events(service: FromDishka[CatalogService]) -> list[EventData]:
    return await service.list_events()


@router.get("/{event_id}")
async def get_event(event_id: int, service: FromDishka[CatalogService]) -> EventData:
    return await service.get_event(event_id)


@router.get("/{event_id}/seats")
async def list_event_seats(
    event_id: int,
    service: FromDishka[CatalogService],
) -> list[EventSeatData]:
    return await service.list_event_seats(event_id)
