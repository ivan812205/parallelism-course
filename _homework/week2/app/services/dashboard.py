import asyncio

from app.application.dto import DashboardData, OccupancyData, SalesData
from app.domain.enums import SeatStatus
from app.domain.exceptions import EventNotFoundError
from app.infrastructure.postgres.manager import DatabaseManager


class DashboardService:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def build(self, *, event_id: int, organizer_id: int) -> DashboardData:
        event = await self._db.events.get(event_id)
        if event is None or event.organizer_id != organizer_id:
            # 404, а не 403 — не раскрываем существование чужих мероприятий
            raise EventNotFoundError

        # Два независимых запроса КОНКУРЕНТНО, каждый в СВОЕЙ сессии
        # (одна async-сессия не допускает параллельных операций — урок 4).
        async with asyncio.TaskGroup() as tg:
            sales_task = tg.create_task(self._sales(event_id))
            occupancy_task = tg.create_task(self._occupancy(event_id))

        return DashboardData(
            event_title=event.title,
            starts_at=event.starts_at,
            sales=sales_task.result(),
            occupancy=occupancy_task.result(),
        )

    async def _sales(self, event_id: int) -> SalesData:
        async with self._db.transaction() as tx:
            paid_orders, revenue = await tx.bookings.paid_aggregate(event_id)
            sold_tickets = await tx.event_seats.count_status(event_id, SeatStatus.sold)
        average_order = revenue // paid_orders if paid_orders else 0
        return SalesData(
            paid_orders=paid_orders,
            sold_tickets=sold_tickets,
            revenue=revenue,
            average_order=average_order,
        )

    async def _occupancy(self, event_id: int) -> OccupancyData:
        async with self._db.transaction() as tx:
            counts = await tx.event_seats.count_by_status(event_id)
        total = sum(counts.values())
        reserved = counts.get(SeatStatus.reserved, 0)
        sold = counts.get(SeatStatus.sold, 0)
        occupancy_percent = round((reserved + sold) / total * 100, 2) if total else 0.0
        return OccupancyData(
            total=total,
            available=counts.get(SeatStatus.available, 0),
            reserved=reserved,
            sold=sold,
            occupancy_percent=occupancy_percent,
        )
