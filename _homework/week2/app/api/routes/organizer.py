from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.api.dependencies import UserIdDep
from app.api.requests import EventCreate
from app.application.dto import EventData
from app.services.organizer import OrganizerService

router = APIRouter(prefix="/organizer/events", route_class=DishkaRoute, tags=["Организатор"])


@router.get("")
async def list_organizer_events(
    organizer_id: UserIdDep,
    service: FromDishka[OrganizerService],
) -> list[EventData]:
    return await service.list_events(organizer_id)


@router.post("")
async def create_event(
    payload: EventCreate,
    organizer_id: UserIdDep,
    service: FromDishka[OrganizerService],
) -> EventData:
    return await service.create_event(
        organizer_id,
        location_id=payload.location_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        starts_at=payload.starts_at,
        base_price=payload.base_price,
    )
