from typing import Any

from dishka.integrations.taskiq import FromDishka, inject

from app.application.dto import DashboardData
from app.services.event_report_builder import EventReportBuilder
from app.tasks.brokers import reports_broker


@reports_broker.task(task_name="reports.event_dashboard")
@inject
async def build_event_dashboard_report(
    event_id: int,
    dashboard: dict[str, Any],
    builder: FromDishka[EventReportBuilder],
) -> str:
    """Дашборд едет в задачу как JSON: воркер не ходит в базу повторно и собирает
    отчёт ровно по тем данным, которые увидел организатор."""
    report_path = await builder.build(
        event_id=event_id,
        dashboard=DashboardData.model_validate(dashboard),
    )
    return str(report_path)
