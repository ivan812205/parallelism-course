import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.application.dto import DashboardData
from app.config import ReportConfig
from app.pdf_reports import generate_event_dashboard_pdf

logger = logging.getLogger(__name__)


class EventReportBuilder:
    """Собирает PDF-отчёт по дашборду мероприятия. reportlab синхронный и тяжёлый,
    поэтому сборка уходит в поток и не блокирует событийный цикл воркера."""

    FILE_TEMPLATE = "event_{event_id}_{stamp}.pdf"

    def __init__(self, config: ReportConfig) -> None:
        self._directory = Path(config.directory)

    async def build(self, *, event_id: int, dashboard: DashboardData) -> Path:
        generated_at = datetime.now(timezone.utc)
        output_path = self._directory / self.FILE_TEMPLATE.format(
            event_id=event_id,
            stamp=generated_at.strftime("%Y%m%d-%H%M%S-%f"),
        )
        report_path = await asyncio.to_thread(
            generate_event_dashboard_pdf,
            dashboard,
            output_path,
            generated_at,
        )
        logger.info("Отчёт по мероприятию %s собран: %s", event_id, report_path)
        return report_path
