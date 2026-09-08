from fastapi import APIRouter

from app.api.routes.checkout import router as checkout_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.events import router as events_router
from app.api.routes.locations import router as locations_router
from app.api.routes.organizer import router as organizer_router
from app.api.routes.pay import router as pay_router

__all__ = ("main_router",)

main_router = APIRouter()
main_router.include_router(locations_router)
main_router.include_router(events_router)
main_router.include_router(checkout_router)
main_router.include_router(organizer_router)
main_router.include_router(dashboard_router)
main_router.include_router(pay_router)
