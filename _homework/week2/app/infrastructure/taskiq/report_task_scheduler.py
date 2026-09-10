from app.application.dto import DashboardData
from app.tasks.reports import build_event_dashboard_report


class ReportTaskScheduler:
    """Реализация порта планирования отчёта поверх taskiq: кладёт задачу в очередь
    отчётов. Дашборд уезжает JSON-ом, поэтому воркер не ходит в базу второй раз."""

    async def schedule(self, *, event_id: int, dashboard: DashboardData) -> None:
        await build_event_dashboard_report.kiq(
            event_id=event_id,
            dashboard=dashboard.model_dump(mode="json"),
        )
