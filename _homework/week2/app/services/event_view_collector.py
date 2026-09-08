import asyncio
import logging

from app.config import EventViewConfig
from app.infrastructure.postgres.manager import PostgresClient

logger = logging.getLogger(__name__)


class EventViewCollector:
    """Копит уникальные просмотры в памяти и пишет их в PostgreSQL агрегатами:
    сбрасывает по числу событий или по таймеру, а при остановке приложения
    дописывает остаток, чтобы просмотры не потерялись."""

    STOP_SENTINEL = -1

    def __init__(self, postgres: PostgresClient, config: EventViewConfig) -> None:
        self._postgres = postgres
        self._config = config
        self._queue: asyncio.Queue[int] = asyncio.Queue(maxsize=config.queue_maxsize)
        self._views_by_event: dict[int, int] = {}
        self._worker: asyncio.Task[None] | None = None

    def register(self, event_id: int) -> None:
        """Вызывается из обработчика запроса: отдать просмотр воркеру, не дожидаясь базы."""
        try:
            self._queue.put_nowait(event_id)
        except asyncio.QueueFull:
            logger.warning(
                "Очередь просмотров переполнена, просмотр мероприятия %s потерян", event_id
            )

    async def start(self) -> None:
        self._worker = asyncio.create_task(self._collect(), name="event-view-collector")

    async def stop(self) -> None:
        """Просит воркер завершиться: он добирает очередь и делает финальный сброс."""
        if self._worker is None:
            return
        await self._queue.put(self.STOP_SENTINEL)
        await self._worker
        self._worker = None

    async def _collect(self) -> None:
        loop = asyncio.get_running_loop()
        flush_at = loop.time() + self._config.flush_interval_seconds
        views_since_flush = 0
        while True:
            try:
                event_id = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=max(flush_at - loop.time(), 0.0),
                )
            except TimeoutError:
                await self._flush()
                views_since_flush = 0
                flush_at = loop.time() + self._config.flush_interval_seconds
                continue

            if event_id == self.STOP_SENTINEL:
                self._drain_queue()
                await self._flush()
                return

            self._views_by_event[event_id] = self._views_by_event.get(event_id, 0) + 1
            views_since_flush += 1
            if views_since_flush >= self._config.flush_every_events:
                await self._flush()
                views_since_flush = 0
                flush_at = loop.time() + self._config.flush_interval_seconds

    def _drain_queue(self) -> None:
        while True:
            try:
                event_id = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            if event_id == self.STOP_SENTINEL:
                continue
            self._views_by_event[event_id] = self._views_by_event.get(event_id, 0) + 1

    async def _flush(self) -> None:
        if not self._views_by_event:
            return
        batch, self._views_by_event = self._views_by_event, {}
        try:
            async with self._postgres.session() as db:
                await db.event_views.increment(batch)
                await db.commit()
        except Exception:
            # воркер не имеет права умереть: возвращаем агрегаты в буфер до следующего сброса
            for event_id, views_count in batch.items():
                self._views_by_event[event_id] = (
                    self._views_by_event.get(event_id, 0) + views_count
                )
            logger.exception("Просмотры %s мероприятий не записаны, вернулись в буфер", len(batch))
            return
        logger.info("Записаны просмотры: %s", batch)
