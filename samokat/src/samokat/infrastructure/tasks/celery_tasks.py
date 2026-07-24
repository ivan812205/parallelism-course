import asyncio
import logging

from dishka import Scope

from samokat.infrastructure.tasks.celery_app import celery_app
from samokat.infrastructure.tasks.config import settings
from samokat.ioc import create_container
from samokat.services.darkstore_sync import DarkstoreSyncService
from samokat.services.reports import ReportService

logger = logging.getLogger(__name__)


@celery_app.task(name="sync_darkstore_products_and_prices")
def sync_darkstore_products_and_prices() -> None:
    async def _helper() -> None:
        container = create_container(settings)
        logger.info("Darkstore products sync started")
        async with container(scope=Scope.REQUEST) as request_container:
            service = await request_container.get(DarkstoreSyncService)
            await service.sync_products_and_prices()
        logger.info("Darkstore products sync finished")

    asyncio.run(_helper())


@celery_app.task(name="generate_order_report")
def generate_order_report(report_id: str) -> None:
    async def _helper() -> None:
        container = create_container(settings)
        logger.info("Report started")
        async with container(scope=Scope.REQUEST) as request_container:
            service = await request_container.get(ReportService)
            await service.generate_orders_report(report_id)
        logger.info("Report finished")

    asyncio.run(_helper())
