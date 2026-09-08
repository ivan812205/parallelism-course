from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.api.dependencies import UserIdDep
from app.api.requests import BookingCreate
from app.application.dto import CheckoutResultData
from app.services.checkout import CheckoutService

router = APIRouter(route_class=DishkaRoute, tags=["Оформление"])


@router.post("/events/{event_id}/checkout")
async def prepare_checkout(
    event_id: int,
    payload: BookingCreate,
    user_id: UserIdDep,
    service: FromDishka[CheckoutService],
) -> CheckoutResultData:
    """Временно бронирует места и возвращает итоговую стоимость и страховку."""
    return await service.checkout(
        event_id=event_id,
        user_id=user_id,
        seat_ids=payload.seat_ids,
    )
