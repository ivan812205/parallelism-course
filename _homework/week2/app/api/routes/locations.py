from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.application.dto import LocationData, LocationDetailData, SeatData
from app.services.catalog import CatalogService

router = APIRouter(prefix="/locations", route_class=DishkaRoute, tags=["Площадки"])


@router.get("")
async def list_locations(service: FromDishka[CatalogService]) -> list[LocationData]:
    return await service.list_locations()


@router.get("/{location_id}")
async def get_location(
    location_id: int,
    service: FromDishka[CatalogService],
) -> LocationDetailData:
    return await service.get_location(location_id)


@router.get("/{location_id}/seats")
async def list_location_seats(
    location_id: int,
    service: FromDishka[CatalogService],
) -> list[SeatData]:
    return await service.list_location_seats(location_id)
