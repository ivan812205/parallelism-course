from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.api.dependencies import UserIdDep
from app.application.dto import DashboardData
from app.services.dashboard import DashboardService

router = APIRouter(route_class=DishkaRoute, tags=["Аналитика"])


@router.get("/organizer/events/{event_id}/dashboard")
async def get_event_dashboard(
    event_id: int,
    organizer_id: UserIdDep,
    service: FromDishka[DashboardService],
) -> DashboardData:
    """Аналитика мероприятия: продажи и заполняемость (2 конкурентных запроса к БД)."""
    return await service.build(event_id=event_id, organizer_id=organizer_id)
