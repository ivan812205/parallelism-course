import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from app.application.dto import DashboardData
from app.config import ReportConfig
from app.pdf_reports import generate_event_dashboard_pdf

logger = logging.getLogger(__name__)


class EventReportBuilder:
    """Собирает PDF-отчёт по дашборду мероприятия в отдельном процессе: reportlab
    считает на чистом Python и GIL не отпускает, поэтому поток дал бы только
    видимость параллелизма — воркер всё равно стоял бы на генерации. Задача при этом
    остаётся асинхронной и продолжает освобождать событийный цикл воркера."""

    FILE_TEMPLATE = "event_{event_id}_{stamp}.pdf"

    def __init__(self, config: ReportConfig, executor: ProcessPoolExecutor) -> None:
        self._directory = Path(config.directory)
        self._executor = executor

    async def build(self, *, event_id: int, dashboard: DashboardData) -> Path:
        generated_at = datetime.now(timezone.utc)
        output_path = self._directory / self.FILE_TEMPLATE.format(
            event_id=event_id,
            stamp=generated_at.strftime("%Y%m%d-%H%M%S-%f"),
        )
        loop = asyncio.get_running_loop()
        report_path = await loop.run_in_executor(
            self._executor,
            generate_event_dashboard_pdf,
            dashboard,
            output_path,
            generated_at,
        )
        logger.info("Отчёт по мероприятию %s собран: %s", event_id, report_path)
        return report_path
