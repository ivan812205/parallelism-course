from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request

from app.application.dto import EventData, EventSeatData
from app.services.catalog import CatalogService
from app.services.event_reader import EventReader
from app.services.event_view_tracker import EventViewTracker

router = APIRouter(prefix="/events", route_class=DishkaRoute, tags=["Мероприятия"])


@router.get("")
async def list_events(service: FromDishka[CatalogService]) -> list[EventData]:
    return await service.list_events()


@router.get("/{event_id}")
async def get_event(
    event_id: int,
    request: Request,
    reader: FromDishka[EventReader],
    views: FromDishka[EventViewTracker],
) -> EventData:
    event = await reader.get_event(event_id)
    await views.track(event_id, request.client.host if request.client else None)
    return event


@router.get("/{event_id}/seats")
async def list_event_seats(
    event_id: int,
    service: FromDishka[CatalogService],
) -> list[EventSeatData]:
    return await service.list_event_seats(event_id)
