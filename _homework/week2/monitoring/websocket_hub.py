import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from monitoring.config import WebSocketConfig
from monitoring.dto import PaymentActivityData

logger = logging.getLogger(__name__)


class WebSocketHub:
    """Держит подключения менеджеров и рассылает им агрегаты из очереди.
    Отправки идут конкурентно, у каждого клиента свой таймаут: медленный клиент
    пропускает обновление, но соединение сохраняет."""

    def __init__(
        self,
        queue: asyncio.Queue[list[PaymentActivityData] | None],
        config: WebSocketConfig,
    ) -> None:
        self._queue = queue
        self._config = config
        self._connections: set[WebSocket] = set()
        self._worker: asyncio.Task[None] | None = None

    def register(self, connection: WebSocket) -> None:
        self._connections.add(connection)
        logger.info("Менеджер подключился, активных соединений %s", len(self._connections))

    def unregister(self, connection: WebSocket) -> None:
        self._connections.discard(connection)
        logger.info("Менеджер отключился, активных соединений %s", len(self._connections))

    async def start(self) -> None:
        self._worker = asyncio.create_task(self._broadcast(), name="websocket-broadcaster")

    async def stop(self) -> None:
        if self._worker is None:
            return
        await self._queue.put(None)
        await self._worker
        self._worker = None

    async def _broadcast(self) -> None:
        while True:
            aggregates = await self._queue.get()
            if aggregates is None:
                return
            if not self._connections:
                continue
            payload = {
                "type": "payment_activity",
                "items": [aggregate.model_dump() for aggregate in aggregates],
            }
            # snapshot: во время рассылки набор соединений может измениться
            await asyncio.gather(
                *(self._send(connection, payload) for connection in tuple(self._connections))
            )

    async def _send(self, connection: WebSocket, payload: dict) -> None:
        try:
            async with asyncio.timeout(self._config.send_timeout_seconds):
                await connection.send_json(payload)
        except TimeoutError:
            logger.warning(
                "Клиент не принял обновление за %s с, соединение оставляем",
                self._config.send_timeout_seconds,
            )
        except (WebSocketDisconnect, RuntimeError) as error:
            # RuntimeError starlette кидает при отправке в уже закрытый сокет
            logger.info("Соединение закрыто (%s), убираем из рассылки", type(error).__name__)
            self.unregister(connection)
