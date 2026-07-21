from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.api.dependencies import UserIdDep
from app.api.requests import PaymentCreate
from app.application.dto import PaymentResultData
from app.services.payment import PaymentService

router = APIRouter(prefix="/bookings", route_class=DishkaRoute, tags=["Оплата"])


@router.post("/{booking_id}/pay")
async def pay_booking(
    booking_id: int,
    payload: PaymentCreate,
    user_id: UserIdDep,
    service: FromDishka[PaymentService],
) -> PaymentResultData:
    return await service.pay(
        booking_id,
        user_id,
        payment_method=payload.payment_method,
        with_protection=payload.with_protection,
    )
