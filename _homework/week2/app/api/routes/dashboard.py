from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.api.dependencies import UserIdDep
from app.application.dto import DashboardData
from app.services.dashboard import DashboardService
from app.tasks.reports import build_event_dashboard_report

router = APIRouter(route_class=DishkaRoute, tags=["Аналитика"])


@router.get("/organizer/events/{event_id}/dashboard")
async def get_event_dashboard(
    event_id: int,
    organizer_id: UserIdDep,
    service: FromDishka[DashboardService],
) -> DashboardData:
    """Аналитика мероприятия: продажи и заполняемость (2 конкурентных запроса к БД)."""
    dashboard = await service.build(event_id=event_id, organizer_id=organizer_id)
    # PDF-отчёт по этим же данным собирается в фоне
    await build_event_dashboard_report.kiq(
        event_id=event_id,
        dashboard=dashboard.model_dump(mode="json"),
    )
    return dashboard
