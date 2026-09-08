"""Сервис мониторинга покупок: читает события из Kafka и раздаёт агрегаты по WebSocket.

Запуск: uv run uvicorn monitoring.main:app --port 8001
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from monitoring.config import MonitoringSettings
from monitoring.dto import PaymentActivityData
from monitoring.monitoring_database import MonitoringDatabase
from monitoring.purchase_aggregator import PurchaseAggregator
from monitoring.purchase_batch_consumer import PurchaseBatchConsumer
from monitoring.websocket_hub import WebSocketHub

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = MonitoringSettings()
database = MonitoringDatabase(settings.postgres)
# очередь между консьюмером и воркером рассылки
activity_queue: asyncio.Queue[list[PaymentActivityData] | None] = asyncio.Queue(
    maxsize=settings.websocket.queue_maxsize
)
hub = WebSocketHub(queue=activity_queue, config=settings.websocket)
consumer = PurchaseBatchConsumer(
    config=settings.kafka,
    database=database,
    aggregator=PurchaseAggregator(),
    queue=activity_queue,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await hub.start()
    await consumer.start()
    try:
        yield
    finally:
        # сначала перестаём читать брокер, потом гасим рассылку и пул соединений
        await consumer.stop()
        await hub.stop()
        await database.close()


app = FastAPI(title="Мониторинг оплат «Афиши»", lifespan=lifespan)


@app.websocket("/ws/payments")
async def payments_activity(websocket: WebSocket) -> None:
    """Поток активности оплат для менеджера платформы."""
    await websocket.accept()
    hub.register(websocket)
    try:
        while True:
            # входящие сообщения не нужны, читаем только чтобы заметить разрыв
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.unregister(websocket)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "monitoring.main:app",
        host=settings.app.host,
        port=settings.app.port,
    )
