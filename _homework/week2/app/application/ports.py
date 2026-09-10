from typing import Protocol

from app.application.dto import DashboardData


class EventReportScheduler(Protocol):
    """Ставит сборку PDF-отчёта в фон. Сервисам не важно, чем именно она исполняется."""

    async def schedule(self, *, event_id: int, dashboard: DashboardData) -> None: ...


class ProtectionRecalculationScheduler(Protocol):
    """Ставит дорасчёт страховки в фон для брони, которой не хватило времени в ручке."""

    async def schedule(self, booking_id: int) -> None: ...
