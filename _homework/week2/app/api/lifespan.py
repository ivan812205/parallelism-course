from contextlib import asynccontextmanager

from dishka import AsyncContainer
from fastapi import FastAPI

from app.add_event_data import seed_event_data
from app.infrastructure.kafka.purchase_event_publisher import PurchaseEventPublisher
from app.infrastructure.postgres.manager import PostgresClient
from app.services.event_view_collector import EventViewCollector
from app.services.purchase_event_generator import PurchaseEventGenerator
from app.tasks.brokers import API_BROKERS


def create_lifespan(container: AsyncContainer):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        postgres = await container.get(PostgresClient)
        async with postgres.session() as db:
            await seed_event_data(db.session)

        collector = await container.get(EventViewCollector)
        await collector.start()
        # приложение только кладёт задачи в очереди, выполняют их воркеры taskiq
        for broker in API_BROKERS:
            await broker.startup()

        publisher = await container.get(PurchaseEventPublisher)
        await publisher.start()
        generator = await container.get(PurchaseEventGenerator)
        await generator.start()
        try:
            yield
        finally:
            # сначала перестаём производить события, потом гасим продюсера
            await generator.stop()
            await publisher.stop()
            # остаток агрегатов уходит в базу до закрытия пула соединений
            await collector.stop()
            for broker in API_BROKERS:
                await broker.shutdown()

    return lifespan
